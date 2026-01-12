"""
EMTO LAT Number Detection and Primitive Vector Generation

This module automatically detects the EMTO LAT number from CIF files
and generates primitive vectors using EMTO's exact formulas.
"""

import numpy as np
from pymatgen.core import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer


# ==================== MAGNETIC MOMENT DATABASE ====================
# Import centralized element database
from modules.element_database import DEFAULT_MOMENTS as DEFAULT_MAGNETIC_MOMENTS
from modules.element_database import DEFAULT_MOMENT_FALLBACK


def get_default_magnetic_moment(element_symbol):
    """
    Get default magnetic moment for an element.

    Parameters
    ----------
    element_symbol : str
        Element symbol (e.g., 'Fe', 'Pt')

    Returns
    -------
    float
        Default magnetic moment in Bohr magnetons
    """
    return DEFAULT_MAGNETIC_MOMENTS.get(element_symbol, DEFAULT_MOMENT_FALLBACK)


def get_inequivalent_atoms(structure):
    """
    Determine inequivalent atoms (IT) from symmetry analysis.

    Atoms are inequivalent if they cannot be transformed into each other
    by symmetry operations of the space group.

    Parameters
    ----------
    structure : Structure
        Pymatgen Structure object

    Returns
    -------
    dict
        Mapping from site index to IT number (starting from 1)
        Example: {0: 1, 1: 1, 2: 2, 3: 2} means atoms 0,1 are IT=1 and atoms 2,3 are IT=2
    """
    sga = SpacegroupAnalyzer(structure)
    symmetrized_structure = sga.get_symmetrized_structure()

    # Get equivalent sites - atoms in the same list are symmetrically equivalent
    equivalent_sites = symmetrized_structure.equivalent_indices

    # Create mapping: site_index -> IT number
    site_to_it = {}
    it_counter = 1

    # Each group of equivalent sites gets the same IT number
    for equiv_group in equivalent_sites:
        for site_idx in equiv_group:
            site_to_it[site_idx] = it_counter
        it_counter += 1

    return site_to_it


def map_to_lat_number(crystal_system, centering):
    """
    Map crystal system + centering to EMTO LAT number.
    
    Parameters
    ----------
    crystal_system : str
        Crystal system ('cubic', 'hexagonal', 'tetragonal', etc.)
    centering : str
        Centering type ('P', 'I', 'F', 'C', 'R')
    
    Returns
    -------
    lat : int
        EMTO lattice number (1-14)
    lattice_name : str
        Human-readable lattice name
    """
    mapping = {
        ('cubic', 'P'): (1, 'Simple cubic'),
        ('cubic', 'F'): (2, 'Face-centered cubic'),
        ('cubic', 'I'): (3, 'Body-centered cubic'),
        
        ('hexagonal', 'P'): (4, 'Hexagonal'),
        
        ('tetragonal', 'P'): (5, 'Simple tetragonal'),
        ('tetragonal', 'I'): (6, 'Body-centered tetragonal'),
        
        ('trigonal', 'R'): (7, 'Trigonal/Rhombohedral'),
        ('trigonal', 'P'): (7, 'Trigonal/Rhombohedral'),
        
        ('orthorhombic', 'P'): (8, 'Simple orthorhombic'),
        ('orthorhombic', 'C'): (9, 'Base-centered orthorhombic'),
        ('orthorhombic', 'I'): (10, 'Body-centered orthorhombic'),
        ('orthorhombic', 'F'): (11, 'Face-centered orthorhombic'),
        
        ('monoclinic', 'P'): (12, 'Simple monoclinic'),
        ('monoclinic', 'C'): (13, 'Base-centered monoclinic'),
        
        ('triclinic', 'P'): (14, 'Simple triclinic'),
    }
    
    key = (crystal_system, centering)
    if key not in mapping:
        raise ValueError(
            f"Unknown combination: {crystal_system} + {centering}\n"
            f"Valid combinations: {list(mapping.keys())}"
        )
    
    return mapping[key]


def detect_lat_from_cif(cif_file):
    """
    Detect EMTO LAT number from CIF file.
    
    Parameters
    ----------
    cif_file : str
        Path to CIF file
    
    Returns
    -------
    lat : int
        EMTO lattice number (1-14)
    lattice_name : str
        Human-readable name
    crystal_system : str
        Crystal system
    centering : str
        Centering type (P, I, F, C, R)
    """
    structure = Structure.from_file(cif_file)
    sga = SpacegroupAnalyzer(structure)
    
    # Get crystal system
    crystal_system = sga.get_crystal_system()
    
    # Get centering from space group symbol
    spacegroup_symbol = sga.get_space_group_symbol()
    centering = spacegroup_symbol[0]  # First letter
    
    # Map to LAT number
    lat, lattice_name = map_to_lat_number(crystal_system, centering)
    
    return lat, lattice_name, crystal_system, centering


def generate_emto_primitive_vectors(lat, a, b, c, alpha=90.0, beta=90.0, gamma=90.0):
    """
    Generate primitive vectors using EMTO's exact formulas.
    
    This follows the same formulas as EMTO's primv subroutine.
    
    Parameters
    ----------
    lat : int
        EMTO lattice number (1-14)
    a, b, c : float
        Lattice parameters (Angstrom)
    alpha, beta, gamma : float
        Crystallographic angles (degrees)
    
    Returns
    -------
    BSX : list
        X-components of three primitive vectors
    BSY : list
        Y-components of three primitive vectors
    BSZ : list
        Z-components of three primitive vectors
    boa : float
        b/a ratio
    coa : float
        c/a ratio
    """
    boa = b / a
    coa = c / a
    
    # Convert angles to radians
    alpha_rad = np.radians(alpha)
    beta_rad = np.radians(beta)
    gamma_rad = np.radians(gamma)
    
    # Initialize vectors
    BSX = [0.0, 0.0, 0.0]
    BSY = [0.0, 0.0, 0.0]
    BSZ = [0.0, 0.0, 0.0]
    
    if lat == 1:
        # Simple cubic
        BSX = [1.0, 0.0, 0.0]
        BSY = [0.0, 1.0, 0.0]
        BSZ = [0.0, 0.0, 1.0]
    
    elif lat == 2:
        # Face centered cubic
        BSX = [0.5, 0.5, 0.0]
        BSY = [0.0, 0.5, 0.5]
        BSZ = [0.5, 0.0, 0.5]
    
    elif lat == 3:
        # Body centered cubic
        BSX = [0.5, 0.5, -0.5]
        BSY = [-0.5, 0.5, 0.5]
        BSZ = [0.5, -0.5, 0.5]
    
    elif lat == 4:
        # Hexagonal
        BSX = [1.0, 0.0, 0.0]
        BSY = [-0.5, np.sqrt(3.0)/2.0, 0.0]
        BSZ = [0.0, 0.0, coa]
    
    elif lat == 5:
        # Simple tetragonal
        BSX = [1.0, 0.0, 0.0]
        BSY = [0.0, 1.0, 0.0]
        BSZ = [0.0, 0.0, coa]
    
    elif lat == 6:
        # Body centered tetragonal
        BSX = [1.0, 0.0, 0.0]
        BSY = [0.0, 1.0, 0.0]
        BSZ = [0.5, 0.5, coa/2.0]
    
    elif lat == 7:
        # Trigonal
        BSX = [0.0, 1.0, coa]
        BSY = [-np.sqrt(3.0)/2.0, -0.5, coa]
        BSZ = [np.sqrt(3.0)/2.0, -0.5, coa]
    
    elif lat == 8:
        # Simple orthorhombic
        BSX = [1.0, 0.0, 0.0]
        BSY = [0.0, boa, 0.0]
        BSZ = [0.0, 0.0, coa]
    
    elif lat == 9:
        # Base centered orthorhombic
        BSX = [0.5, -boa/2.0, 0.0]
        BSY = [0.5, boa/2.0, 0.0]
        BSZ = [0.0, 0.0, coa]
    
    elif lat == 10:
        # Body centered orthorhombic
        BSX = [0.5, -boa/2.0, coa/2.0]
        BSY = [0.5, boa/2.0, -coa/2.0]
        BSZ = [-0.5, boa/2.0, coa/2.0]
    
    elif lat == 11:
        # Face centered orthorhombic
        BSX = [0.5, 0.0, coa/2.0]
        BSY = [0.5, boa/2.0, 0.0]
        BSZ = [0.0, boa/2.0, coa/2.0]
    
    elif lat == 12:
        # Simple monoclinic
        BSX = [1.0, 0.0, 0.0]
        BSY = [boa * np.cos(gamma_rad), boa * np.sin(gamma_rad), 0.0]
        BSZ = [0.0, 0.0, coa]
    
    elif lat == 13:
        # Base centered monoclinic
        BSX = [0.0, -boa, 0.0]
        BSY = [0.5 * np.sin(gamma_rad), -0.5 * np.cos(gamma_rad), -0.5 * coa]
        BSZ = [0.5 * np.sin(gamma_rad), -0.5 * np.cos(gamma_rad), 0.5 * coa]
    
    elif lat == 14:
        # Simple triclinic
        BSX = [1.0, 0.0, 0.0]
        BSY = [boa * np.cos(gamma_rad), boa * np.sin(gamma_rad), 0.0]
        
        # Complex formula for third vector
        bsz_x = coa * np.cos(beta_rad)
        bsz_y = coa * (np.cos(alpha_rad) - np.cos(beta_rad) * np.cos(gamma_rad)) / np.sin(gamma_rad)
        bsz_z = coa * np.sqrt(
            1.0 - np.cos(gamma_rad)**2 - np.cos(alpha_rad)**2 - np.cos(beta_rad)**2 
            + 2.0 * np.cos(alpha_rad) * np.cos(beta_rad) * np.cos(gamma_rad)
        ) / np.sin(gamma_rad)
        BSZ = [bsz_x, bsz_y, bsz_z]
    
    else:
        raise ValueError(f"LAT={lat} not supported (must be 1-14)")
    
    # Check special case for trigonal (Fortran line 134)
    if lat == 7 and abs(BSZ[0]) < 1e-7:
        boa = -1.0
    
    return BSX, BSY, BSZ, boa, coa


def parse_emto_structure(cif_file, user_magnetic_moments=None):
    """
    Complete function to parse CIF and extract all EMTO structure information.

    This is the main function for the new workflow. It parses the CIF once
    and returns all information needed for KSTR, SHAPE, KGRN, and KFCD input generation.

    Parameters
    ----------
    cif_file : str
        Path to CIF file
    user_magnetic_moments : dict, optional
        User-provided magnetic moments per element symbol.
        Example: {'Fe': 2.5, 'Pt': 0.3}
        If not provided, uses default database values.

    Returns
    -------
    dict
        Comprehensive structure dictionary containing:

        **Lattice information:**
        - lat: EMTO lattice number (1-14)
        - lattice_name: Human-readable name (e.g., 'Simple tetragonal')
        - a, b, c: Lattice parameters (Angstrom)
        - alpha, beta, gamma: Crystallographic angles (degrees)
        - boa, coa: Ratios b/a and c/a
        - BSX, BSY, BSZ: Primitive vectors (normalized to a)
        - crystal_system: Crystal system (e.g., 'tetragonal')
        - centering: Centering type ('P', 'I', 'F', 'C', 'R')

        **Atomic information:**
        - NQ3: Total number of atoms in unit cell
        - NL: Number of angular momentum layers (auto-determined)
        - atoms: List of element symbols ['Pt', 'Pt', 'Fe', 'Fe']
        - unique_elements: List of unique elements ['Fe', 'Pt']
        - fractional_coords: Fractional coordinates (Nx3 array)
        - coords: Cartesian coordinates (Nx3 array, Angstrom)

        **KGRN-specific information:**
        - atom_info: List of dicts, one per atom, containing:
            - IQ: Atom index (1-based)
            - symbol: Element symbol (e.g., 'Fe')
            - IT: Inequivalent atom type (from symmetry analysis)
            - ITA: Alloy component index (always 1 for ordered structures)
            - conc: Concentration (always 1.0 for ordered structures)
            - default_moment: Default magnetic moment (Bohr magnetons)
            - a_scr: Screening parameter a (default 0.750)
            - b_scr: Screening parameter b (default 1.100)

        **Raw data (for advanced use):**
        - matrix: 3x3 lattice matrix from pymatgen
        - structure: Pymatgen Structure object (conventional cell)

    Examples
    --------
    >>> structure = parse_emto_structure('FePt.cif')
    >>> print(f"LAT={structure['lat']}, NQ3={structure['NQ3']}, NL={structure['NL']}")
    >>> for atom in structure['atom_info']:
    ...     print(f"IQ={atom['IQ']} {atom['symbol']} IT={atom['IT']}")
    """
    from modules.parse_cif import get_LatticeVectors

    # ==================== BASIC LATTICE EXTRACTION ====================
    # Get lattice parameters from existing function
    matrix, coords, a, b, c, atoms_species = get_LatticeVectors(cif_file)

    # Get angles and structure from pymatgen
    # IMPORTANT: EMTO requires CONVENTIONAL cell, not primitive!
    structure = Structure.from_file(cif_file)
    sga = SpacegroupAnalyzer(structure)
    conv_structure = sga.get_conventional_standard_structure()  # NOT get_primitive_standard_structure()

    sites_frac = conv_structure.frac_coords
    alpha = conv_structure.lattice.alpha
    beta = conv_structure.lattice.beta
    gamma = conv_structure.lattice.gamma

    # ==================== LAT DETECTION ====================
    lat, lattice_name, crystal_system, centering = detect_lat_from_cif(cif_file)

    # Generate primitive vectors using EMTO formulas
    BSX, BSY, BSZ, boa, coa = generate_emto_primitive_vectors(
        lat, a, b, c, alpha, beta, gamma
    )

    # ==================== ATOM INFORMATION ====================
    # Convert pymatgen Species to symbols
    atoms = [str(atom.symbol) for atom in atoms_species]
    unique_elements = sorted(set(atoms))  # Sorted for consistency
    NQ3 = len(atoms)

    # Determine NL from electronic structure (maximum orbital angular momentum)
    # NL represents the basis set size needed: includes ALL orbitals (core + valence)
    # NL=1: s,p orbitals needed
    # NL=2: s,p,d orbitals needed
    # NL=3: s,p,d,f orbitals needed
    NLs = []
    for atom_symbol in set(atoms):
        from pymatgen.core import Element
        elem = Element(atom_symbol)
        electronic_str = elem.electronic_structure

        # Check if f-orbitals are present (even as core electrons)
        if 'f' in electronic_str:
            NLs.append(3)
        # Check if d-orbitals are present
        elif 'd' in electronic_str:
            NLs.append(2)
        # Check if p-orbitals are present
        elif 'p' in electronic_str:
            NLs.append(1)
        else:
            NLs.append(1)  # Default to s,p (NL=1)

    NL = max(NLs) if NLs else 2  # Default to 2 if can't determine

    # ==================== INEQUIVALENT ATOMS (IT) ====================
    site_to_it = get_inequivalent_atoms(conv_structure)

    # ==================== BUILD ATOM_INFO LIST ====================
    atom_info = []

    for iq in range(NQ3):
        symbol = atoms[iq]

        # Get magnetic moment (user-provided or default)
        if user_magnetic_moments and symbol in user_magnetic_moments:
            moment = user_magnetic_moments[symbol]
        else:
            moment = get_default_magnetic_moment(symbol)

        atom_info.append({
            'IQ': iq + 1,  # 1-based indexing for EMTO
            'symbol': symbol,
            'IT': site_to_it[iq],  # From symmetry analysis
            'ITA': 1,  # Always 1 for ordered structures
            'conc': 1.0,  # Always 1.0 for ordered structures
            'default_moment': moment,
            'a_scr': 0.750,  # Default screening parameter
            'b_scr': 1.100,  # Default screening parameter
        })

    # ==================== RETURN COMPREHENSIVE DICTIONARY ====================
    return {
        # Lattice information
        'lat': lat,
        'lattice_name': lattice_name,
        'a': a,
        'b': b,
        'c': c,
        'alpha': alpha,
        'beta': beta,
        'gamma': gamma,
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
        'structure': conv_structure,
    }


# Backward compatibility alias
def get_emto_lattice_info(cif_file):
    """
    DEPRECATED: Use parse_emto_structure() instead.

    This function is kept for backward compatibility but returns
    the old subset of information only.
    """
    full_info = parse_emto_structure(cif_file)

    # Return only the old keys for backward compatibility
    return {
        'lat': full_info['lat'],
        'lattice_name': full_info['lattice_name'],
        'a': full_info['a'],
        'b': full_info['b'],
        'c': full_info['c'],
        'alpha': full_info['alpha'],
        'beta': full_info['beta'],
        'gamma': full_info['gamma'],
        'boa': full_info['boa'],
        'coa': full_info['coa'],
        'BSX': full_info['BSX'],
        'BSY': full_info['BSY'],
        'BSZ': full_info['BSZ'],
        'crystal_system': full_info['crystal_system'],
        'centering': full_info['centering'],
        'matrix': full_info['matrix'],
        'coords': full_info['coords'],
        'atoms': [str(a) for a in full_info['atoms']],  # Keep as strings
        'fractional_coords': full_info['fractional_coords']
    }


def validate_emto_vectors(cif_file, verbose=True):
    """
    Validate EMTO-generated vectors against pymatgen.
    
    Compares cell volumes to ensure correctness.
    
    Parameters
    ----------
    cif_file : str
        Path to CIF file
    verbose : bool
        Print detailed comparison
    
    Returns
    -------
    bool
        True if validation passes
    """
    from modules.parse_cif import get_LatticeVectors
    
    # Get pymatgen matrix
    pm_matrix, _, pm_a, pm_b, pm_c, _ = get_LatticeVectors(cif_file)
    
    # Get EMTO info
    emto_info = get_emto_lattice_info(cif_file)
    
    # Construct EMTO matrix from BSX, BSY, BSZ
    # Note: BSX, BSY, BSZ are the three vectors, need to construct matrix correctly
    emto_matrix = np.array([
        emto_info['BSX'],
        emto_info['BSY'],
        emto_info['BSZ']
    ]) * pm_a  # Scale back by 'a'
    
    # Compare volumes
    pm_volume = np.linalg.det(pm_matrix)
    emto_volume = np.linalg.det(emto_matrix)
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"Validation for: {cif_file}")
        print(f"{'='*60}")
        print(f"Detected: LAT={emto_info['lat']} ({emto_info['lattice_name']})")
        print(f"Crystal system: {emto_info['crystal_system']}, Centering: {emto_info['centering']}")
        print(f"\nPymatgen volume: {pm_volume:.6f} Å³")
        print(f"EMTO volume:     {emto_volume:.6f} Å³")
        print(f"Difference:      {abs(pm_volume - emto_volume):.6e} Å³")
        
        print(f"\nLattice parameters:")
        print(f"  a = {pm_a:.6f} Å")
        print(f"  b = {pm_b:.6f} Å  (b/a = {emto_info['boa']:.6f})")
        print(f"  c = {pm_c:.6f} Å  (c/a = {emto_info['coa']:.6f})")
        
        print(f"\nPrimitive vectors (normalized to a):")
        print(f"  BSX = [{emto_info['BSX'][0]:8.5f}, {emto_info['BSX'][1]:8.5f}, {emto_info['BSX'][2]:8.5f}]")
        print(f"  BSY = [{emto_info['BSY'][0]:8.5f}, {emto_info['BSY'][1]:8.5f}, {emto_info['BSY'][2]:8.5f}]")
        print(f"  BSZ = [{emto_info['BSZ'][0]:8.5f}, {emto_info['BSZ'][1]:8.5f}, {emto_info['BSZ'][2]:8.5f}]")
    
    is_valid = np.isclose(pm_volume, emto_volume, rtol=1e-5)
    
    if verbose:
        print(f"\nValidation: {'✓ PASS' if is_valid else '✗ FAIL'}")
        print(f"{'='*60}\n")
    
    return is_valid