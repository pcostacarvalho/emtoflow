import numpy as np
import os

# Import input file generators
from modules.inputs import (
    create_kstr_input,
    create_shape_input,
    create_kgrn_input,
    create_kfcd_input
)


def create_inputs(params):

    path=params["path"]
    ratios=params["ratios"]
    name_id=params["name_id"]
    sws=params["sws"]
    NL=params["NL"]
    NQ3=params["NQ3"]
    B=params["B"]
    DMAX=params["DMAX"]
    LAT=params["LAT"]
    fractional_coors=params["fractional_coors"]

    # Subfolders to create inside each ratio folder
    subfolders = ['smx', 'shp', 'pot', 'chd', 'fcd']

    os.makedirs(path, exist_ok=True)

    for subfolder in subfolders:
        subfolder_path = os.path.join(path, subfolder)
        os.makedirs(subfolder_path, exist_ok=True)

    for r in ratios:
        lattice_vectors =  np.array([[1.0,  0.0, 0.0], [0.0,  1.0, 0.0], [0.0,  0.0, r]])
        cart_coords = fractional_coors @ lattice_vectors
        filer=f"{name_id}_{r:.2f}"

        create_kstr_input(
            path=path,
            id_name=f"{filer}",
            NL=NL, NQ3=NQ3,
            A=1, B=B, C=r,
            DMAX=DMAX, LAT=LAT,
            lattice_vectors=lattice_vectors,
            lattice_positions=cart_coords)

        create_shape_input(path=path, id_name=f"{filer}",NQ3=NQ3)

        for v in sws:
            filev=filer+f"_{v:.2f}"
        
            create_kgrn_input(path=path, id_namev=f"{filev}", id_namer=f"{filer}" ,SWS=v)

            create_kfcd_input(path=path, id_namev=f"{filev}", id_namer=f"{filer}")

    

    #         if len(sws) == 1:
                
    #             create_job_ca(
    #             folder=f"{filev}",
    #             filename=f"{path}/run_{filev}.sh")
        

    # if len(sws) > 1:
        
    #     create_job_volume(
    #     name=f"{name_id}",
    #     filename=f"run_{name_id}.sh",
    #     volumes=" ".join([f"{j:.2f}" for j in sws]))


