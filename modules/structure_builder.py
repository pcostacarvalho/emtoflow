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
from pymatgen.core import Structure, Lattice
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

from modules.lat_detector import (
    get_inequivalent_atoms,
    map_to_lat_number,
    generate_emto_primitive_vectors
)
from modules.element_database import get_default_moment


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
    # Check if user provided explicit LAT (from parameter workflow)
    user_lat = structure_pmg.properties.get('user_lat', None) if structure_pmg.properties else None

    # Create SpacegroupAnalyzer (needed for symmetry analysis)
    sga = SpacegroupAnalyzer(structure_pmg)

    # Decide whether to use as-is or convert to primitive
    if user_lat is not None:
        # User explicitly provided LAT and structure - respect their choice
        # Do NOT convert to primitive cell
        work_structure = structure_pmg
    else:
        # CIF workflow - standardize to primitive cell to reduce atoms
        work_structure = sga.get_primitive_standard_structure()

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
    # Include zero-concentration elements if original_sites are available
    original_sites = structure_pmg.properties.get('original_sites') if structure_pmg.properties else None

    all_elements = set()
    if original_sites:
        # Use original sites to get ALL elements including zero-concentration ones
        for site_spec in original_sites:
            for elem in site_spec['elements']:
                all_elements.add(elem)
    else:
        # Fall back to pymatgen composition
        for site in work_structure.sites:
            # site.species is a Composition object containing all elements at that site
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

        # If original sites are available, use them to get ALL elements (including 0% concentration)
        # Otherwise, fall back to pymatgen's composition (which filters out zeros)
        if original_sites and iq < len(original_sites):
            # Use original site specification - preserves zero-concentration elements
            elements = original_sites[iq]['elements']
            concentrations = original_sites[iq]['concentrations']
            sorted_elements = sorted(zip(elements, concentrations), key=lambda x: x[0])
        else:
            # Fall back to pymatgen composition (CIF workflow or no original sites)
            # site.species is a Composition: {'Fe': 0.5, 'Pt': 0.5} for alloys
            # or {'Cu': 1.0} for pure elements
            site_composition = site.species.as_dict()
            sorted_elements = sorted(site_composition.items())

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


def create_emto_structure(cif_file=None, lat=None, a=None, sites=None,
                         b=None, c=None, alpha=90, beta=90, gamma=90,
                         user_magnetic_moments=None):
    """
    Create EMTO structure dictionary from CIF file or input parameters.

    This is the main entry point for creating EMTO structures. It provides
    a unified interface that works for both workflows:
    1. From CIF file (experimental structures)
    2. From lattice parameters (for alloys, ordered structures, etc.)

    Parameters
    ----------
    cif_file : str, optional
        Path to CIF file. If provided, structure is loaded from CIF.
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
        If neither cif_file nor (lat, a, sites) are provided

    Examples
    --------
    >>> # From CIF file
    >>> structure_pmg, structure_dict = create_emto_structure(cif_file='FePt.cif')

    >>> # From parameters (FCC Fe-Pt alloy)
    >>> sites = [{'position': [0, 0, 0], 'elements': ['Fe', 'Pt'],
    ...          'concentrations': [0.5, 0.5]}]
    >>> structure_pmg, structure_dict = create_emto_structure(lat=2, a=3.7, sites=sites)

    >>> # From parameters (HCP Co with defaults)
    >>> sites = [{'position': [0, 0, 0], 'elements': ['Co'], 'concentrations': [1.0]}]
    >>> structure_pmg, structure_dict = create_emto_structure(lat=4, a=2.51, sites=sites)
    """
    # Determine which workflow to use
    if cif_file is not None:
        # CIF workflow
        structure_pmg = Structure.from_file(cif_file)
    elif lat is not None and a is not None and sites is not None:
        # Parameter workflow
        structure_pmg = create_structure_from_params(
            lat, a, sites, b, c, alpha, beta, gamma
        )
    else:
        raise ValueError(
            "Must provide either:\n"
            "  1. cif_file='path/to/file.cif'\n"
            "  2. lat=<1-14>, a=<value>, sites=<list>"
        )

    # Common: convert pymatgen Structure → EMTO dict
    return structure_pmg, _structure_to_emto_dict(structure_pmg, user_magnetic_moments)
