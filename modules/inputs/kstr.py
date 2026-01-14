import numpy as np
import os

def create_kstr_input(
    structure, 
    output_path,
    id_ratio,
    dmax=None,
    ca_ratio=None
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

    lattice_info = structure
    
    # Use provided LAT or auto-detected
   
    lat = lattice_info['lat']
     

    # lattice_matrix = lattice_info['matrix']
    lattice_matrix = np.array([lattice_info['BSX'], lattice_info['BSY'], lattice_info['BSZ']])
    # atomic_positions = lattice_info['coords']

    a = lattice_info['a']
    b = lattice_info['b']
    c = lattice_info['c']
    
    
    # Normalize to lattice parameter 'a'
    A = a / a  # = 1.0
    B = b / a
    
    if ca_ratio is None:
        C = c/a
    else:
        C = ca_ratio
        # Scale ALL z-components proportionally
        scale_factor = ca_ratio / lattice_info['coa']
        lattice_matrix = lattice_matrix.copy()
        lattice_matrix[:, 2] = lattice_matrix[:, 2] * scale_factor
        
    # normalized_lattice = lattice_matrix / a
    atomic_positions = lattice_info['fractional_coords'] @ lattice_matrix

    NL = lattice_info['NL']

    NQ3 = lattice_info['NQ3']

    if dmax is None:
        dmax = 1.8

    # Validate job name length (Fortran fixed-format requirement)
    if len(id_ratio) > 10:
        raise ValueError(
            f"Job name '{id_ratio}' is too long ({len(id_ratio)} chars). "
            f"KSTR input format requires job names <= 10 characters. "
            f"Please use a shorter job name (e.g., shorten '{id_ratio}' to '{id_ratio[:10]}')."
        )

    # Create output directory structure
    os.makedirs(output_path, exist_ok=True)
    os.makedirs(f"{output_path}/smx", exist_ok=True)  # NEW LINE


    template = f"""KSTR      HP......=N                               xx xxx xx
JOBNAM...={id_ratio:<10} MSGL.=  1 MODE...=B STORE..=Y HIGH...=Y
DIR001=./
DIR006=
Slope and Madelung matrices
NL.....= {NL:>1} NLH...= 9 NLW...= 9 NDER..= 6 ITRANS= 3 NPRN..= 1
(K*W)^2..=   0.00000 DMAX....=    {dmax:>6.3f} RWATS...=      0.10
NQ3...= {NQ3:>2} LAT...={lat:>2} IPRIM.= 0 NGHBP.=13 NQR2..= 0        80
A........= {A:>.7f} B.......= {B:>.7f} C.......= {C:>.7f}
"""

    # Add lattice vectors
    for vec in lattice_matrix:
        template += f"{vec[0]:.8f}\t{vec[1]:.8f}\t{vec[2]:.8f}\n"

    # Add lattice positions
    for pos in atomic_positions:
        template += f"\t{pos[0]:.8f}\t{pos[1]:.8f}\t{pos[2]:.8f}\n"

    # Append fixed section
    for i in range(NQ3):
        template += f"a/w......= 0.70 0.70 0.70 0.70\n"

    template += f"""NL_mdl.= {2*NL + 1}
LAMDA....=    2.5000 AMAX....=    4.5000 BMAX....=    4.5000
"""
    
    with open(f"{output_path}/smx/{id_ratio}.dat", "w") as f:
        f.write(template)

    print(f"KSTR input file '{output_path}/smx/{id_ratio}.dat' created successfully.")
