import os

def create_kfcd_input(path, id_namer, id_namev):
    """
    Create a KFCD input file for EMTO.

    Parameters
    ----------
    filename : str
        Name of the output SHAPE file (e.g., 'fept.dat').
    job_name : str
        The JOBNAM (e.g., 'fept').
    shp_file : str
        Path to the .tfh file (e.g., '../shp/fept.shp').
    """

    template = f"""KFCD      HP......=N sno..=100                     xx xxx xx
JOBNAM...={id_namev:<10}                         MSGL.=  1
STRNAM...={id_namer}
DIR001=../smx/
DIR002=../chd/
FOR003=../shp/{id_namer}.shp
DIR004=../smx/
DIR006=
Lmaxs.= 30 NTH..= 41 NFI..= 81
OVCOR.=  Y UBG..=  N NPRN.=  0 NRM..=  0
"""

    with open(f"{path}/fcd/{id_namev}.dat", "w") as f:
        f.write(template)

    print(f"KFCD input file '{path}/fcd/{id_namev}.dat' created successfully.")