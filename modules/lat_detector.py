"""
EMTO LAT Number Detection and Primitive Vector Generation

This module automatically detects the EMTO LAT number from CIF files
and generates primitive vectors using EMTO's exact formulas.
"""

import numpy as np
from pymatgen.core import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer


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


def get_emto_lattice_info(cif_file):
    """
    Complete function to extract all EMTO lattice info from CIF.
    
    This is the main function you should use.
    
    Parameters
    ----------
    cif_file : str
        Path to CIF file
    
    Returns
    -------
    dict
        Dictionary containing:
        - lat: EMTO lattice number
        - lattice_name: Human-readable name
        - a, b, c: Lattice parameters (Angstrom)
        - alpha, beta, gamma: Angles (degrees)
        - boa, coa: Ratios b/a and c/a
        - BSX, BSY, BSZ: Primitive vectors (normalized to a)
        - crystal_system: Crystal system
        - centering: Centering type
        - matrix: 3x3 lattice matrix from pymatgen
        - coords: Atomic coordinates
        - atoms: List of atomic species
    """
    from modules.parse_cif import get_LatticeVectors
    
    # Get lattice parameters from existing function
    matrix, coords, a, b, c, atoms = get_LatticeVectors(cif_file)
    
    # Get angles from the conventional structure
    structure = Structure.from_file(cif_file)
    sga = SpacegroupAnalyzer(structure)
    conv_structure = sga.get_conventional_standard_structure()
    
    sites_frac = conv_structure.frac_coords

    alpha = conv_structure.lattice.alpha
    beta = conv_structure.lattice.beta
    gamma = conv_structure.lattice.gamma
    
    # Detect LAT number
    lat, lattice_name, crystal_system, centering = detect_lat_from_cif(cif_file)
    
    # Generate primitive vectors using EMTO formulas
    BSX, BSY, BSZ, boa, coa = generate_emto_primitive_vectors(
        lat, a, b, c, alpha, beta, gamma
    )
    
    return {
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
        'matrix': matrix,
        'coords': coords,
        'atoms': atoms,
        'fractional_coords': sites_frac
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