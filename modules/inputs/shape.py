import os

def create_shape_input(structure, path, id_ratio):
    """
    Create a SHAPE input file for EMTO from structure dict.

    Parameters
    ----------
    structure : dict
        Structure dictionary from parse_emto_structure() containing NQ3
    path : str
        Output directory path
    id_ratio : str
        Job ID (e.g., 'fept_0.96')
    """

    # Extract NQ3 from structure
    NQ3 = structure['NQ3']

    template = f"""SHAPE     HP......=N
JOBNAM...={id_ratio:<10} MSGL.=  1
FOR001=../smx/{id_ratio}.tfh
DIR002=./
DIR006=./
Lmax..= 30 NSR..=129 NFI..= 11
NPRN..=  0 IVEF.=  3
****** Relative atomic sphere radii ASR(1:NQ) ******
"""

    # Add ASR lines based on NQ3
    # Format: ASR(1.)= 1.0 for i <= 9, ASR(10)= 1.0 for i >= 10
    for i in range(1, NQ3 + 1):
        if i <= 9:
            template += f"ASR({i}).= 1.0\n"
        else:
            template += f"ASR({i})= 1.0\n"

    with open(f"{path}/shp/{id_ratio}.dat", "w") as f:
        f.write(template)

    print(f"SHAPE input file '{path}/shp/{id_ratio}.dat' created successfully.")