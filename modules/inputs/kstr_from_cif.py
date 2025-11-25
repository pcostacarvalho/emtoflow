import numpy as np
import os
from modules.parse_cif import get_LatticeVectors
from modules.inputs.kstr import create_kstr_input
from modules.lat_detector import get_emto_lattice_info, parse_emto_structure

def create_kstr_input_from_cif(
    cif_file=None,
    output_path=None,
    job_name=None,
    dmax=None,
    ca_ratio=None,
    lat=None,
    nl=None,
    structure=None
    ):
    """
    Create a KSTR input file from a CIF file or pre-parsed structure.

    This is a wrapper around create_kstr_input() that automatically extracts
    lattice vectors and atomic positions from the CIF file or uses a pre-parsed
    structure dict for efficiency.

    Parameters
    ----------
    cif_file : str, optional
        Path to CIF file (required if structure is None)
    output_path : str
        Folder to save the generated .dat file
    job_name : str
        Name of the EMTO job
    dmax : float
        Maximum distance parameter
    ca_ratio : float, optional
        Override c/a ratio (scales z-coordinates)
    lat : int, optional
        Bravais lattice type (1-14). If None, will be auto-detected.
    nl : int, optional
        Number of layers. If not provided, will be auto-determined from
        electronic structure (f->3, d->2, p->1)
    structure : dict, optional
        Pre-parsed structure dict from parse_emto_structure(). If provided,
        cif_file will be ignored. This improves efficiency when creating
        multiple inputs from the same CIF.

    Returns
    -------
    dict : Dictionary containing extracted parameters (NL, NQ3, a, b, c, atoms)
    """

    # Get structure info from pre-parsed dict or parse CIF
    if structure is not None:
        # Use pre-parsed structure (efficient for multiple calls)
        lattice_info = structure
    else:
        # Parse CIF (backward compatibility)
        if cif_file is None:
            raise ValueError("Either cif_file or structure must be provided")
        lattice_info = get_emto_lattice_info(cif_file)
    
    # Use provided LAT or auto-detected
    if lat is None:
        lat = lattice_info['lat']
        print(f"Auto-detected LAT={lat} ({lattice_info['lattice_name']})")
    else:
        print(f"Using provided LAT={lat}")
        if lat != lattice_info['lat']:
            print(f"WARNING: Provided LAT={lat} differs from auto-detected LAT={lattice_info['lat']} ({lattice_info['lattice_name']})")
    
    # Extract data from lattice_info
    # lattice_matrix = lattice_info['matrix']
    lattice_matrix = np.array([lattice_info['BSX'], lattice_info['BSY'], lattice_info['BSZ']])
    # atomic_positions = lattice_info['coords']

    a = lattice_info['a']
    b = lattice_info['b']
    c = lattice_info['c']

    atoms = lattice_info['atoms']
    
    
    # Normalize to lattice parameter 'a'
    A = a / a  # = 1.0
    B = b / a
    
    if ca_ratio is None:
        C = lattice_info['c']/a
    else:
        C = ca_ratio
        # Scale ALL z-components proportionally
        scale_factor = ca_ratio / lattice_info['coa']
        lattice_matrix = lattice_matrix.copy()
        lattice_matrix[:, 2] = lattice_matrix[:, 2] * scale_factor
        
    # normalized_lattice = lattice_matrix / a
    atomic_positions = lattice_info['fractional_coords'] @ lattice_matrix

        # Determine NL
    if nl is None:
        # Auto-determine from electronic structure
        NLs = []
        for atom in set(atoms):
            if 'f' in atom.electronic_structure:
                NLs.append(3)
            elif 'd' in atom.electronic_structure:
                NLs.append(2)
            elif 'p' in atom.electronic_structure:
                NLs.append(1)
        
        NL = max(NLs)
        print(f"Auto-determined NL={NL} from electronic structure")
    else:
        NL = nl
        print(f"Using provided NL={NL}")
    
    NQ3 = len(atomic_positions)
    
    # Create output directory structure
    os.makedirs(output_path, exist_ok=True)
    os.makedirs(f"{output_path}/smx", exist_ok=True)  # NEW LINE
    
    # Call the low-level function
    create_kstr_input(
        path=output_path,
        id_name=job_name,
        DMAX=dmax,
        LAT=lat,
        NL=NL,
        NQ3=NQ3,
        A=A,
        B=B,
        C=C,
        lattice_vectors=lattice_matrix,
        lattice_positions=atomic_positions
    )
    
    return {
        'NL': NL,
        'NQ3': NQ3,
        'a': a,
        'b': b,
        'c': c,
        'atoms': [atom.symbol for atom in atoms],
        'lat': lat,
        'lattice_name': lattice_info['lattice_name']
    }
