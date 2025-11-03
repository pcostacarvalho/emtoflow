import os

def create_shape_input(path, id_name, NQ3):
    """
    Create a SHAPE input file for EMTO.

    Parameters
    ----------
    filename : str
        Name of the output SHAPE file (e.g., 'fept.dat').
    job_name : str
        The JOBNAM (e.g., 'fept').
    smx_file : str
        Path to the .tfh file (e.g., '../smx/fept.tfh').
    NQ3 : int
        Number of atoms (determines number of ASR lines).
    """

    template = f"""SHAPE     HP......=N
JOBNAM...={id_name:<10} MSGL.=  1
FOR001=../smx/{id_name}.tfh
DIR002=./
DIR006=./
Lmax..= 30 NSR..=129 NFI..= 11
NPRN..=  0 IVEF.=  3
****** Relative atomic sphere radii ASR(1:NQ) ******
"""

    # Add ASR lines based on NQ3
    for i in range(1, NQ3 + 1):
        template += f"ASR({i}).= 1.0\n"

    with open(f"{path}/shp/{id_name}.dat", "w") as f:
        f.write(template)

    print(f"SHAPE input file '{path}/shp/{id_name}.dat' created successfully.")