import numpy as np
import os
from modules.parse_cif import get_LatticeVectors
from modules.inputs.kstr import create_kstr_input
from modules.lat_detector import get_emto_lattice_info

def create_kstr_input_from_cif(
    cif_file,
    output_path,
    job_name,
    dmax,
    ca_ratio=None,
    lat = None,
    nl=None
    ):
    """
    Create a KSTR input file from a CIF file.
    
    This is a wrapper around create_kstr_input() that automatically extracts
    lattice vectors and atomic positions from the CIF file.
    
    Parameters
    ----------
    cif_file : str
        Path to CIF file
    output_path : str
        Folder to save the generated .dat file
    job_name : str
        Name of the EMTO job
    dmax : float
        Maximum distance parameter
    lat : int, optional
        Bravais lattice type (1-14). If None, will be auto-detected from CIF.
    nl : int, optional
        Number of layers. If not provided, will be auto-determined from 
        electronic structure (f->3, d->2, p->1)
    
    Returns
    -------
    dict : Dictionary containing extracted parameters (NL, NQ3, a, b, c, atoms)
    """
    
    # Get all lattice info including auto-detected LAT
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
