import os

def create_kfcd_input(structure, path, id_namer, id_namev):
    """
    Create a KFCD input file for EMTO from structure dict.

    Parameters
    ----------
    structure : dict
        Structure dictionary from parse_emto_structure() (not used currently,
        but kept for consistent API)
    path : str
        Output directory path
    id_namer : str
        Job ID with ratio only (e.g., 'fept_0.96')
    id_namev : str
        Full job ID with volume (e.g., 'fept_0.96_2.65')
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