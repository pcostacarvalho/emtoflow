"""
EMTO Structure Builder
======================

Create EMTO structure dictionaries from CIF files or input parameters.

This module provides a unified interface for creating EMTO-compatible
structure dictionaries from either:
1. CIF files (experimental structures)
2. User-specified lattice parameters (for alloys, ordered structures, etc.)

Both workflows produce the same structure dictionary format for downstream
EMTO input generation.
"""

import numpy as np
from pymatgen.core import Structure, Lattice, Species
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from typing import Optional, Dict, Any, Tuple

from modules.lat_detector import (
    get_inequivalent_atoms,
    map_to_lat_number,
    generate_emto_primitive_vectors
)
from modules.element_database import get_default_moment

# ==================== CANONICAL (PRIMITIVE) STRUCTURE ====================

def _get_canonical_structure(structure_pmg: Structure) -> Structure:
    """
    Return the canonical structure representation used by the EMTO pipeline.

    - Parameter workflow: if user provided explicit LAT (stored as user_lat),
      do NOT convert to primitive.
    - CIF workflow: standardize to primitive cell to reduce atoms and keep
      downstream behavior consistent (important for alloy workflows too).
    """
    user_lat = structure_pmg.properties.get('user_lat', None) if structure_pmg.properties else None
    if user_lat is not None:
        return structure_pmg

    sga = SpacegroupAnalyzer(structure_pmg)
    return sga.get_primitive_standard_structure()


def _apply_substitutions_to_site_composition(
    site_composition: Dict[str, float],
    substitutions: Dict[str, Any]
) -> Dict[str, float]:
    """
    Apply substitutions to a single site's composition in a deterministic way.

    This supports:
    - Pure sites: {'Fe': 1.0}
    - Mixed-occupancy CIF sites: {'Fe': 0.7, 'Co': 0.3}

    Substitution format:
      substitutions = {
        'Fe': {'elements': ['Fe', 'Co'], 'concentrations': [0.5, 0.5]},
        ...
      }

    Behavior:
    - For each element in the site's composition:
      - If it has a substitution, replace its contribution by scaling the substitution mixture.
      - Otherwise, keep it.
    - Preserves explicit zero-concentration components from substitution definitions
      (keys are created even if the resulting concentration is 0.0).
    """
    if not substitutions:
        return dict(site_composition)

    out: Dict[str, float] = {}
    for elem, frac in site_composition.items():
        if elem in substitutions:
            subst = substitutions[elem]
            subst_elems = subst.get('elements', [])
            subst_concs = subst.get('concentrations', [])
            for sub_elem, sub_frac in zip(subst_elems, subst_concs):
                # Create key even if frac*sub_frac == 0.0 (zero-preservation)
                out[sub_elem] = out.get(sub_elem, 0.0) + float(frac) * float(sub_frac)
        else:
            out[elem] = out.get(elem, 0.0) + float(frac)

    return out


# ==================== ELEMENT SUBSTITUTIONS ====================
 
def apply_substitutions_to_structure(structure_pmg, substitutions):
    """
    Apply element substitutions to pymatgen Structure from CIF.
 
    This function replaces all sites of specified elements with partial
    occupancies for alloy calculations. All sites of the same element
    receive the same substitution.
 
    Parameters
    ----------
    structure_pmg : pymatgen.core.Structure
        Original structure from CIF file
    substitutions : dict
        Element substitutions mapping element symbols to new compositions.
        Format: {'Fe': {'elements': ['Fe', 'Co'], 'concentrations': [0.7, 0.3]},
                 'Pt': {'elements': ['Pt'], 'concentrations': [1.0]}}
 
    Returns
    -------
    pymatgen.core.Structure
        New structure with partial occupancies applied
 
    Raises
    ------
    ValueError
        If substitution references element not present in structure
 
    Examples
    --------
    >>> from pymatgen.core import Structure
    >>> # Original FePt structure
    >>> structure = Structure.from_file("FePt.cif")
    >>>
    >>> # Replace all Fe with Fe0.7Co0.3, keep Pt pure
    >>> substitutions = {
    ...     'Fe': {'elements': ['Fe', 'Co'], 'concentrations': [0.7, 0.3]},
    ...     'Pt': {'elements': ['Pt'], 'concentrations': [1.0]}
    ... }
    >>> new_structure = apply_substitutions_to_structure(structure, substitutions)
 
    Notes
    -----
    - All sites with the same element symbol receive the same substitution
    - Elements not in substitutions dictionary remain unchanged
    - For ordered structures, use parameter workflow (lat, a, sites) instead
    - Concentrations must sum to 1.0 (validated in config_parser)
    """
 
    # Get all unique elements in the structure
    structure_elements = set()
    for site in structure_pmg:
        # Handle both pure elements and species with partial occupancy
        if hasattr(site.specie, 'symbol'):
            structure_elements.add(site.specie.symbol)
        else:
            # Site already has partial occupancy
            for elem in site.species.elements:
                structure_elements.add(elem.symbol)
 
    # Check that all substitution keys exist in the structure
    for element in substitutions.keys():
        if element not in structure_elements:
            raise ValueError(
                f"Element '{element}' in substitutions not found in CIF structure. "
                f"Available elements: {', '.join(sorted(structure_elements))}"
            )
 
    # Create new structure with substitutions
    new_species = []
    new_coords = []
 
    for site in structure_pmg:
        # Get the element symbol for this site
        if hasattr(site.specie, 'symbol'):
            element_symbol = site.specie.symbol
        else:
            # Site has mixed occupancy - use dominant element
            element_symbol = max(site.species.items(), key=lambda x: x[1])[0].symbol
 
        position = site.frac_coords
 
        # Check if this element has a substitution
        if element_symbol in substitutions:
            subst = substitutions[element_symbol]
            elements = subst['elements']
            concentrations = subst['concentrations']
 
            # Create Species with partial occupancy
            if len(elements) == 1 and concentrations[0] == 1.0:
                # Pure element (no actual substitution)
                new_species.append(elements[0])
            else:
                # Mixed occupancy (CPA alloy)
                species_dict = {elem: conc for elem, conc in zip(elements, concentrations)}
                new_species.append(species_dict)
        else:
            # No substitution - keep original
            new_species.append(site.specie)
 
        new_coords.append(position)
 
    # Create new structure with substitutions
    new_structure = Structure(
        structure_pmg.lattice,
        new_species,
        new_coords,
        coords_are_cartesian=False
    )
 
    return new_structure
 
 

# ==================== SWS CONVERSION ====================

def lattice_param_to_sws(structure_pmg):
    """
    Convert lattice parameters to Wigner-Seitz radius using pymatgen structure.

    This function uses pymatgen to automatically calculate the number of atoms
    per unit cell, making it general for any lattice type (not just FCC/BCC/SC).

    Parameters
    ----------
    structure_pmg : pymatgen.core.Structure
        Pymatgen Structure object with lattice and sites defined

    Returns
    -------
    float
        SWS radius in atomic units (Bohr)

    Notes
    -----
    Calculation:
    1. Get unit cell volume from pymatgen lattice
    2. Get number of atoms from len(structure.sites)
    3. Calculate volume per atom = V_cell / n_atoms
    4. Calculate SWS = (3 * V_atom / (4*π))^(1/3)

    Examples
    --------
    >>> from pymatgen.core import Structure, Lattice
    >>> lattice = Lattice.cubic(3.7)
    >>> structure = Structure(lattice, ['Fe']*4,
    ...                      [[0,0,0], [0.5,0.5,0], [0.5,0,0.5], [0,0.5,0.5]])
    >>> sws = lattice_param_to_sws(structure)
    >>> print(f"SWS = {sws:.4f} Bohr")
    SWS = 2.6900 Bohr
    """
    BOHR_TO_ANGSTROM = 0.529177

    # Get lattice volume in Angstrom³
    V_cell_angstrom = structure_pmg.lattice.volume

    # Convert to Bohr³
    V_cell_bohr = V_cell_angstrom / (BOHR_TO_ANGSTROM ** 3)

    # Get number of atoms in unit cell from pymatgen (automatic!)
    n_atoms = len(structure_pmg.sites)

    # Volume per atom in Bohr³
    V_atom = V_cell_bohr / n_atoms

    # Wigner-Seitz radius in Bohr
    sws = (3 * V_atom / (4 * np.pi)) ** (1/3)

    return sws


# ==================== STRUCTURE CREATION FROM PARAMETERS ====================

def create_structure_from_params(lat, a, sites, b=None, c=None,
                                 alpha=90, beta=90, gamma=90):
    """
    Create pymatgen Structure from lattice parameters and site specifications.

    Supports all 14 EMTO/Bravais lattice types with smart defaults for
    common cases (cubic lattices, HCP).

    Parameters
    ----------
    lat : int
        EMTO Bravais lattice number (1-14):
        1=SC, 2=FCC, 3=BCC, 4=HCP, 5=Tetragonal-P, 6=Tetragonal-I,
        7=Orthorhombic-P, 8=Orthorhombic-I, 9=Orthorhombic-C,
        10=Orthorhombic-F, 11=Monoclinic-P, 12=Monoclinic-C,
        13=Triclinic, 14=Rhombohedral
    a : float
        Lattice parameter a in Angstroms
    sites : list of dict
        Site specifications with keys:
        - 'position': fractional coordinates [x, y, z]
        - 'elements': list of element symbols
        - 'concentrations': list of concentrations (must sum to 1.0 per site)

        Examples:
        [{'position': [0, 0, 0], 'elements': ['Fe', 'Pt'], 'concentrations': [0.5, 0.5]}]
        [{'position': [0, 0, 0], 'elements': ['Fe'], 'concentrations': [1.0]}]
    b : float, optional
        Lattice parameter b in Angstroms (defaults to a for cubic)
    c : float, optional
        Lattice parameter c in Angstroms (defaults to a for cubic, 1.633*a for HCP)
    alpha : float, optional
        Lattice angle α in degrees (default: 90)
    beta : float, optional
        Lattice angle β in degrees (default: 90)
    gamma : float, optional
        Lattice angle γ in degrees (default: 90 for most, 120 for HCP)

    Returns
    -------
    pymatgen.core.Structure
        Structure object with partial occupancies (for CPA alloys) or
        pure occupancies (for ordered structures)

    Notes
    -----
    - Defaults to cubic lattice (a=b=c, all angles 90°) if b, c not specified
    - HCP defaults: c = 1.633*a (ideal ratio), gamma = 120°
    - Works for both pure/ordered structures (conc=1.0) and disordered alloys (conc<1.0)

    Examples
    --------
    >>> # FCC Fe-Pt random alloy
    >>> sites = [{'position': [0, 0, 0], 'elements': ['Fe', 'Pt'],
    ...          'concentrations': [0.5, 0.5]}]
    >>> structure = create_structure_from_params(lat=2, a=3.7, sites=sites)

    >>> # Pure FCC Cu
    >>> sites = [{'position': [0, 0, 0], 'elements': ['Cu'], 'concentrations': [1.0]}]
    >>> structure = create_structure_from_params(lat=2, a=3.61, sites=sites)

    >>> # HCP with default c/a ratio
    >>> sites = [{'position': [0, 0, 0], 'elements': ['Co'], 'concentrations': [1.0]}]
    >>> structure = create_structure_from_params(lat=4, a=2.51, sites=sites)
    """
    # Set default values for cubic lattices
    if b is None:
        b = a
    if c is None:
        # Special case for HCP: use ideal c/a ratio
        if lat == 4:
            c = 1.633 * a
        else:
            c = a

    # Special case for HCP: gamma = 120°
    if lat == 4 and gamma == 90:
        gamma = 120

    # Get EMTO primitive vectors (in units of a, b, c)
    BSX, BSY, BSZ, boa, coa = generate_emto_primitive_vectors(
        lat, a, b, c, alpha, beta, gamma
    )

    # Convert to Cartesian coordinates (Angstroms)
    # IMPORTANT: BSX, BSY, BSZ are ALL in units of 'a' (not [a,b,c])
    # The ratios boa=b/a and coa=c/a are already encoded in the vectors
    lattice_matrix = np.array([
        [BSX[0] * a, BSX[1] * a, BSX[2] * a],
        [BSY[0] * a, BSY[1] * a, BSY[2] * a],
        [BSZ[0] * a, BSZ[1] * a, BSZ[2] * a]
    ])

    # Create Lattice object from actual primitive vectors
    lattice = Lattice(lattice_matrix)

    # Build species and coordinates lists
    species_list = []
    coords_list = []

    for site_spec in sites:
        position = site_spec['position']
        elements = site_spec['elements']
        concentrations = site_spec['concentrations']

        # Create species with partial occupancies
        if len(elements) == 1 and concentrations[0] == 1.0:
            # Pure occupancy (ordered structure)
            species_list.append(elements[0])
        else:
            # Mixed occupancy (CPA alloy)
            # Pass dictionary directly to Structure - it handles partial occupancies
            species_dict = {elem: conc for elem, conc in zip(elements, concentrations)}
            species_list.append(species_dict)

        coords_list.append(position)

    # Create Structure
    structure = Structure(lattice, species_list, coords_list)

    # Calculate and store SWS and LAT in properties
    sws = lattice_param_to_sws(structure)
    # IMPORTANT: Store original parameters and site specifications
    # - Original lattice params (a, b, c, angles) for reference (conventional cell scale)
    # - Pymatgen may convert to different representation (e.g., FCC → rhombohedral)
    # - Store original sites to preserve zero-concentration elements EMTO needs
    structure.properties = {
        'sws': sws,
        'user_lat': lat,
        'user_a': a,
        'user_b': b,
        'user_c': c,
        'user_alpha': alpha,
        'user_beta': beta,
        'user_gamma': gamma,
        'original_sites': sites
    }

    return structure


# ==================== EMTO STRUCTURE DICTIONARY CREATION ====================

def _structure_to_emto_dict(structure_pmg, user_magnetic_moments=None):
    """
    Convert pymatgen Structure to EMTO structure dictionary.

    Internal function that performs the core conversion logic.

    Parameters
    ----------
    structure_pmg : pymatgen.core.Structure
        Input structure (from CIF or created programmatically)
    user_magnetic_moments : dict, optional
        User-provided magnetic moments per element

    Returns
    -------
    dict
        EMTO structure dictionary with all required fields
    """
    # Canonicalize structure (primitive is important for CIF workflows)
    work_structure = _get_canonical_structure(structure_pmg)

    # Create SpacegroupAnalyzer for the canonical structure
    sga = SpacegroupAnalyzer(work_structure)

    # Optional: substitutions (used to define alloys in EMTO dict without
    # requiring pymatgen to carry zero-occupancy species)
    substitutions = (
        structure_pmg.properties.get('substitutions')
        if structure_pmg.properties else None
    )
    # Check if user provided explicit LAT (from parameter workflow)
    user_lat = structure_pmg.properties.get('user_lat', None) if structure_pmg.properties else None

    # Extract lattice parameters
    a = work_structure.lattice.a
    b = work_structure.lattice.b
    c = work_structure.lattice.c
    alpha = work_structure.lattice.alpha
    beta = work_structure.lattice.beta
    gamma = work_structure.lattice.gamma

    # Get matrix and coordinates
    matrix = work_structure.lattice.matrix
    coords = work_structure.cart_coords
    sites_frac = work_structure.frac_coords

    # Determine LAT number
    if user_lat is not None:
        # Use user-provided LAT (from parameter workflow)
        lat = user_lat
        # Get lattice name from LAT number (matching map_to_lat_number names)
        lat_to_name = {
            1: 'Simple cubic',
            2: 'Face-centered cubic',
            3: 'Body-centered cubic',
            4: 'Hexagonal',
            5: 'Simple tetragonal',
            6: 'Body-centered tetragonal',
            7: 'Trigonal/Rhombohedral',
            8: 'Simple orthorhombic',
            9: 'Base-centered orthorhombic',
            10: 'Face-centered orthorhombic',
            11: 'Body-centered orthorhombic',
            12: 'Simple monoclinic',
            13: 'Base-centered monoclinic',
            14: 'Triclinic'
        }
        lattice_name = lat_to_name.get(lat, f'LAT{lat}')
        crystal_system = sga.get_crystal_system()
        spacegroup_symbol = sga.get_space_group_symbol()
        centering = spacegroup_symbol[0]
    else:
        # Detect LAT from symmetry (CIF workflow)
        crystal_system = sga.get_crystal_system()
        spacegroup_symbol = sga.get_space_group_symbol()
        centering = spacegroup_symbol[0]  # First letter
        lat, lattice_name = map_to_lat_number(crystal_system, centering)

    # Generate primitive vectors using EMTO formulas
    BSX, BSY, BSZ, boa, coa = generate_emto_primitive_vectors(
        lat, a, b, c, alpha, beta, gamma
    )

    # ==================== ATOM INFORMATION ====================
    # Get inequivalent atoms (IT) from symmetry analysis
    site_to_it = get_inequivalent_atoms(work_structure)

    # Extract all unique elements across all sites (for NL calculation)
    # Include zero-concentration elements if original_sites or substitutions are available
    original_sites = structure_pmg.properties.get('original_sites') if structure_pmg.properties else None

    all_elements = set()
    if original_sites:
        # Use original sites to get ALL elements including zero-concentration ones
        for site_spec in original_sites:
            for elem in site_spec['elements']:
                all_elements.add(elem)
    # Include substitution elements (even if 0%); this is important for CPA/ITA consistency
    if substitutions:
        for _, subst in substitutions.items():
            for elem in subst.get('elements', []):
                all_elements.add(elem)

    # Fall back to pymatgen composition (canonical structure)
    for site in work_structure.sites:
        for elem in site.species.elements:
            all_elements.add(str(elem))

    unique_elements = sorted(all_elements)
    NQ3 = len(work_structure.sites)

    # Determine NL from electronic structure
    from pymatgen.core import Element
    NLs = []
    for atom_symbol in all_elements:
        elem = Element(atom_symbol)
        electronic_str = elem.electronic_structure

        if 'f' in electronic_str:
            NLs.append(4)
        elif 'd' in electronic_str:
            NLs.append(3)
        elif 'p' in electronic_str:
            NLs.append(2)
        else:
            NLs.append(1)

    NL = max(NLs) if NLs else 3

    # Build atom_info list with proper CPA support
    atom_info = []
    atoms = []  # Simple list of elements at each site (for reference)

    # original_sites already retrieved above for all_elements calculation
    # Reuse it here to preserve zero-concentration elements

    for iq, site in enumerate(work_structure.sites):
        it = site_to_it[iq]

        # Prefer explicit parameter-site specification for per-site CPA components,
        # because it may include zero-concentration elements that pymatgen drops.
        if user_lat is not None and original_sites and iq < len(original_sites):
            elements = original_sites[iq]['elements']
            concentrations = original_sites[iq]['concentrations']
            sorted_elements = sorted(zip(elements, concentrations), key=lambda x: x[0])
        else:
            # CIF or generic structure path:
            # - derive composition from canonical structure
            # - apply substitutions deterministically to define alloys (CPA/ITA)
            site_comp = site.species.as_dict()
            site_comp = _apply_substitutions_to_site_composition(site_comp, substitutions or {})
            sorted_elements = sorted(site_comp.items())

        # For the atoms list, store comma-separated elements for this site
        site_elements = ','.join([elem for elem, _ in sorted_elements])
        atoms.append(site_elements)

        # Create an entry for each element at this site (ITA = 1, 2, 3, ...)
        for ita, (element_symbol, concentration) in enumerate(sorted_elements, start=1):
            # Get magnetic moment
            if user_magnetic_moments and element_symbol in user_magnetic_moments:
                moment = user_magnetic_moments[element_symbol]
            else:
                moment = get_default_moment(element_symbol)

            atom_info.append({
                'IQ': iq + 1,
                'symbol': element_symbol,
                'IT': it,
                'ITA': ita,
                'conc': concentration,
                'default_moment': moment,
                'a_scr': 0.750,
                'b_scr': 1.100,
            })

    # Return comprehensive structure dictionary
    return {
        # Lattice information
        'lat': lat,
        'lattice_name': lattice_name,
        'a': a,
        'b': b,
        'c': c,
        # Note: alpha, beta, gamma omitted - redundant with BSX, BSY, BSZ
        'boa': boa,
        'coa': coa,
        'BSX': BSX,
        'BSY': BSY,
        'BSZ': BSZ,
        'crystal_system': crystal_system,
        'centering': centering,

        # Atomic information
        'NQ3': NQ3,
        'NL': NL,
        'atoms': atoms,
        'unique_elements': unique_elements,
        'fractional_coords': sites_frac,
        'coords': coords,

        # KGRN-specific
        'atom_info': atom_info,

        # Raw data
        'matrix': matrix,
        'structure': work_structure,
    }


def create_emto_structure(
    cif_file: Optional[str] = None,
    structure_pmg: Optional[Structure] = None,
    substitutions: Optional[Dict[str, Any]] = None,
    lat: Optional[int] = None,
    a: Optional[float] = None,
    sites: Optional[list] = None,
    b: Optional[float] = None,
    c: Optional[float] = None,
    alpha: float = 90,
    beta: float = 90,
    gamma: float = 90,
    user_magnetic_moments: Optional[Dict[str, float]] = None
) -> Tuple[Structure, Dict[str, Any]]:
    """
    Create EMTO structure dictionary from CIF file, pymatgen Structure, or input parameters.
 
    This is the main entry point for creating EMTO structures. It provides
    a unified interface that works for multiple workflows:
    1. From CIF file (experimental structures)
    2. From pymatgen Structure (e.g., after applying substitutions)
    3. From lattice parameters (for alloys, ordered structures, etc.)
 
    Parameters
    ----------
    cif_file : str, optional
        Path to CIF file. If provided, structure is loaded from CIF.
    structure_pmg : pymatgen.core.Structure, optional
        Pre-loaded pymatgen Structure object. Useful when applying
        element substitutions before EMTO conversion.
    lat : int, optional
        EMTO lattice number (1-14). Required if creating from parameters.
    a : float, optional
        Lattice parameter a in Angstroms. Required if creating from parameters.
    sites : list of dict, optional
        Site specifications. Required if creating from parameters.
    b, c : float, optional
        Lattice parameters b, c in Angstroms
    alpha, beta, gamma : float, optional
        Lattice angles in degrees
    user_magnetic_moments : dict, optional
        User-provided magnetic moments per element
 
    Returns
    -------
    structure_pmg : pymatgen.core.Structure
        Pymatgen Structure object
    structure_dict : dict
        EMTO structure dictionary containing:
        - Lattice information (lat, a, b, c, BSX, BSY, BSZ, etc.)
        - Atomic information (NQ3, NL, atom_info, etc.)
        - EMTO-specific data for input generation
 
    Raises
    ------
    ValueError
        If neither cif_file, structure_pmg, nor (lat, a, sites) are provided
 
    Examples
    --------
    >>> # From CIF file
    >>> structure_pmg, structure_dict = create_emto_structure(cif_file='FePt.cif')
 
    >>> # From pymatgen Structure (after substitutions)
    >>> pmg_struct = Structure.from_file('FePt.cif')
    >>> # ... apply substitutions to pmg_struct ...
    >>> structure_pmg, structure_dict = create_emto_structure(structure_pmg=pmg_struct)
 
    >>> # From parameters (FCC Fe-Pt alloy)
    >>> sites = [{'position': [0, 0, 0], 'elements': ['Fe', 'Pt'],
    ...          'concentrations': [0.5, 0.5]}]
    >>> structure_pmg, structure_dict = create_emto_structure(lat=2, a=3.7, sites=sites)
 
    >>> # From parameters (HCP Co with defaults)
    >>> sites = [{'position': [0, 0, 0], 'elements': ['Co'], 'concentrations': [1.0]}]
    >>> structure_pmg, structure_dict = create_emto_structure(lat=4, a=2.51, sites=sites)
    """
    # Determine which workflow to use
    if structure_pmg is not None:
        # Pre-loaded pymatgen Structure (e.g., after substitutions)
        structure_pmg.remove_oxidation_states()
    elif cif_file not in (None, False, ""):
        # CIF workflow
        structure_pmg = Structure.from_file(str(cif_file))
        structure_pmg.remove_oxidation_states()
    elif lat is not None and a is not None and sites is not None:
        # Parameter workflow
        structure_pmg = create_structure_from_params(
            lat, a, sites, b, c, alpha, beta, gamma
        )
    else:
        raise ValueError(
            "Must provide either:\n"
            "  1. cif_file='path/to/file.cif'\n"
            "  2. structure_pmg=<pymatgen Structure>\n"
            "  3. lat=<1-14>, a=<value>, sites=<list>"
        )

    # Store substitutions on the base structure (used during EMTO conversion).
    # This allows us to define CPA alloys without requiring pymatgen to keep
    # zero-occupancy species in the Structure itself.
    if substitutions:
        if structure_pmg.properties is None:
            structure_pmg.properties = {}
        structure_pmg.properties['substitutions'] = substitutions

    # Common: convert pymatgen Structure → EMTO dict
    structure_dict = _structure_to_emto_dict(structure_pmg, user_magnetic_moments)

    # Return the canonical structure actually used for EMTO downstream (primitive for CIF)
    return structure_dict['structure'], structure_dict
