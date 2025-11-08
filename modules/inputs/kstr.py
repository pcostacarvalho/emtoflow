import numpy as np
import os

def create_kstr_input(path, id_name, DMAX, LAT, NL, NQ3,
    A, B, C, lattice_vectors, lattice_positions):
    """
    Create a KSTR input file for EMTO.
    
    Parameters
    ----------
    filename : str
        Name of the output .smx file (e.g., 'fept.smx').
    job_name : str
        The JOBNAM (e.g., 'fept').
    NL : int
        Number of layers.
    NQ3 : int
        Value for NQ3 parameter.
    A, B, C : float
        Lattice constants.
    lattice_vectors : list[list[float]]
        3x3 matrix for lattice vectors.
    lattice_positions : list[list[float]]
        List of atomic positions.
    """

    template = f"""KSTR      HP......=N                               xx xxx xx
JOBNAM...={id_name:<10} MSGL.=  1 MODE...=B STORE..=Y HIGH...=Y
DIR001=./
DIR006=
Slope and Madelung matrices
NL.....= {NL:>1} NLH...= 9 NLW...= 9 NDER..= 6 ITRANS= 3 NPRN..= 1
(K*W)^2..=   0.00000 DMAX....=    {DMAX:>6.3f} RWATS...=      0.10
NQ3...= {NQ3:>2} LAT...={LAT:>2} IPRIM.= 0 NGHBP.=13 NQR2..= 0        80
A........= {A:>.7f} B.......= {B:>.7f} C.......= {C:>.7f}
"""

    # Add lattice vectors
    for vec in lattice_vectors:
        template += f"{vec[0]:.8f}\t{vec[1]:.8f}\t{vec[2]:.8f}\n"

    # Add lattice positions
    for pos in lattice_positions:
        template += f"\t{pos[0]:.8f}\t{pos[1]:.8f}\t{pos[2]:.8f}\n"

    # Append fixed section
    for i in range(NQ3):
        template += f"a/w......= 0.70 0.70 0.70 0.70\n"

    template += f"""NL_mdl.= {2*NL + 1}
LAMDA....=    2.5000 AMAX....=    4.5000 BMAX....=    4.5000
"""
    
    with open(f"{path}/smx/{id_name}.dat", "w") as f:
        f.write(template)

    print(f"KSTR input file '{path}/smx/{id_name}.dat' created successfully.")

