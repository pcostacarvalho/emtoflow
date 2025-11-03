import numpy as np
import os
from modules.parse_cif import get_LatticeVectors
from modules.inputs.kstr import create_kstr_input


def create_kstr_input_from_cif(
    cif_file,
    output_path,
    job_name,
    dmax,
    lat,
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
    lat : int
        Bravais lattice type
    nl : int, optional
        Number of layers. If not provided, will be auto-determined from 
        electronic structure (f->3, d->2, p->1)
    
    Returns
    -------
    dict : Dictionary containing extracted parameters (NL, NQ3, a, b, c, atoms)
    """
    
    # Parse CIF file
    lattice_matrix, atomic_positions, a, b, c, atoms = get_LatticeVectors(cif_file)
    
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
    
    # Normalize to lattice parameter 'a'
    A = a / a  # = 1.0
    B = b / a
    C = c / a
    normalized_lattice = lattice_matrix / a
    normalized_positions = atomic_positions / a
    
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
        lattice_vectors=normalized_lattice,
        lattice_positions=normalized_positions
    )
    
    return {
        'NL': NL,
        'NQ3': NQ3,
        'a': a,
        'b': b,
        'c': c,
        'atoms': [atom.symbol for atom in atoms]
    }