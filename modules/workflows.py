import numpy as np
import os
from modules.inputs import (
    create_kstr_input,
    create_kstr_input_from_cif,
    create_shape_input,
    create_kgrn_input,
    create_kfcd_input,
    write_serial_sbatch,
    write_parallel_sbatch
)


def create_emto_inputs(
    output_path,
    job_name,
    dmax,
    lat,
    ca_ratios,
    sws_values,
    from_cif=False,
    cif_file=None,
    nl=None,
    create_job_script=True,
    job_mode='serial',  # 'serial' or 'parallel'
    prcs=1,
    time="00:30:00",
    account="naiss2025-1-38",
    # Legacy parameters (used when from_cif=False)
    fractional_coords=None,
    NL=None,
    NQ3=None,
    B=None
):
    """
    Create complete EMTO input files for c/a and SWS sweeps.
    
    Can work in two modes:
    1. from_cif=True: Read structure from CIF file (recommended)
    2. from_cif=False: Use provided lattice parameters (legacy)
    
    Parameters
    ----------
    output_path : str
        Base output directory
    job_name : str
        Job identifier (e.g., 'fept')
    dmax : float
        Maximum distance parameter for KSTR
    lat : int
        Bravais lattice type
    ca_ratios : list of float
        List of c/a ratios to sweep
    sws_values : list of float
        List of Wigner-Seitz radius values
    from_cif : bool, default=False
        If True, read structure from CIF file. If False, use provided parameters.
    cif_file : str, optional
        Path to CIF file (required if from_cif=True)
    nl : int, optional
        Number of layers (only used if from_cif=True). Auto-determined if not provided.
    fractional_coords : array, optional
        Fractional coordinates (required if from_cif=False)
    NL : int, optional
        Number of layers (required if from_cif=False)
    NQ3 : int, optional
        Number of atoms (required if from_cif=False)
    B : float, optional
        b/a ratio (required if from_cif=False)
    
    Returns
    -------
    dict : Summary of created files and parameters
    
    Examples
    --------
    # Mode 1: From CIF (new way)
    create_emto_inputs(
        output_path="./fept_sweep",
        job_name="fept",
        dmax=1.3,
        lat=5,
        ca_ratios=[0.92, 0.96, 1.00],
        sws_values=[2.60, 2.65, 2.70],
        from_cif=True,
        cif_file="FePt.cif",
        nl=3  # optional
    )
    
    # Mode 2: With parameters (old way - backward compatible)
    create_emto_inputs(
        output_path="./fept_sweep",
        job_name="fept",
        dmax=1.3,
        lat=5,
        ca_ratios=[0.92, 0.96, 1.00],
        sws_values=[2.60, 2.65, 2.70],
        from_cif=False,
        fractional_coords=np.array([[0, 0.5, 0.5], [0.5, 0, 0.5], ...]),
        NL=2,
        NQ3=4,
        B=1.0
    )
    """
    
    # ==================== INPUT VALIDATION ====================
    if from_cif:
        if cif_file is None:
            raise ValueError("cif_file must be provided when from_cif=True")
    else:
        if any(x is None for x in [fractional_coords, NL, NQ3, B]):
            raise ValueError("fractional_coords, NL, NQ3, B must be provided when from_cif=False")
    
    # ==================== CREATE DIRECTORY STRUCTURE ====================
    subfolders = ['smx', 'shp', 'pot', 'chd', 'fcd', 'tmp']
    os.makedirs(output_path, exist_ok=True)
    for subfolder in subfolders:
        os.makedirs(os.path.join(output_path, subfolder), exist_ok=True)
    
    print(f"Created directory structure in: {output_path}")
    
    # ==================== SWEEP OVER C/A RATIOS ====================
    print(f"\nCreating input files for {len(ca_ratios)} c/a ratios and {len(sws_values)} SWS values...")
    
    # Store metadata for return
    metadata = {}
    
    for ratio in ca_ratios:
        print(f"\n  c/a = {ratio:.2f}")
        
        file_id_ratio = f"{job_name}_{ratio:.2f}"
        
        # ==================== MODE 1: FROM CIF ====================
        if from_cif:
            # Use the CIF-aware function - it handles everything
            info = create_kstr_input_from_cif(
                cif_file=cif_file,
                output_path=output_path,
                job_name=file_id_ratio,
                dmax=dmax,
                lat=lat,
                nl=nl
            )
            
            # Extract info for SHAPE/KGRN/KFCD creation
            if not metadata:  # Store once
                metadata = {
                    'NL': info['NL'],
                    'NQ3': info['NQ3'],
                    'B': info['b'] / info['a'],
                    'atoms': info['atoms']
                }
        
        # ==================== MODE 2: WITH PARAMETERS ====================
        else:
            # Create lattice vectors for this c/a ratio
            lattice_vectors = np.array([
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, ratio]
            ])
            
            # Transform fractional -> cartesian
            cart_coords = fractional_coords @ lattice_vectors
            
            # Use low-level function
            create_kstr_input(
                path=output_path,
                id_name=file_id_ratio,
                NL=NL,
                NQ3=NQ3,
                A=1.0,
                B=B,
                C=ratio,
                DMAX=dmax,
                LAT=lat,
                lattice_vectors=lattice_vectors,
                lattice_positions=cart_coords
            )
            
            # Store metadata
            if not metadata:
                metadata = {
                    'NL': NL,
                    'NQ3': NQ3,
                    'B': B,
                    'atoms': None
                }
        
        # ==================== CREATE SHAPE INPUT (BOTH MODES) ====================
        create_shape_input(
            path=output_path,
            id_name=file_id_ratio,
            NQ3=metadata['NQ3']
        )
        
        # ==================== SWEEP OVER SWS VALUES ====================
        for sws in sws_values:
            file_id_full = f"{file_id_ratio}_{sws:.2f}"
            
            # Create KGRN input
            create_kgrn_input(
                path=output_path,
                id_namev=file_id_full,
                id_namer=file_id_ratio,
                SWS=sws
            )
            
            # Create KFCD input
            create_kfcd_input(
                path=output_path,
                id_namer=file_id_ratio,
                id_namev=file_id_full
            )
    # ==================== CREATE JOB SCRIPTS ====================
    if create_job_script:
        print(f"\nCreating {job_mode} job script...")
        
        if job_mode == 'serial':
            script_name = f"run_{job_name}"
            write_serial_sbatch(
                path=output_path,
                ratios=ca_ratios,
                volumes=sws_values,
                job_name=script_name,
                prcs=prcs,
                time=time,
                account=account,
                id_name=job_name
            )
            print(f"Created serial job script: {output_path}/{script_name}.sh")
            print(f"To submit: sbatch {script_name}.sh")
        
        elif job_mode == 'parallel':
            script_name = f"run_{job_name}"
            write_parallel_sbatch(
                path=output_path,
                ratios=ca_ratios,
                volumes=sws_values,
                job_name=script_name,
                prcs=prcs,
                time=time,
                account=account,
                id_name=job_name
            )
            print(f"Created parallel job scripts in: {output_path}/")
            print(f"To submit: bash {output_path}/submit_{script_name}.sh")


    # ==================== SUMMARY ====================
    n_kstr = len(ca_ratios)
    n_shape = len(ca_ratios)
    n_kgrn = len(ca_ratios) * len(sws_values)
    n_kfcd = len(ca_ratios) * len(sws_values)
    
    print("\n" + "="*70)
    print("WORKFLOW COMPLETE")
    print("="*70)
    print(f"Files created:")
    print(f"  KSTR:  {n_kstr} files in {output_path}/smx/")
    print(f"  SHAPE: {n_shape} files in {output_path}/shp/")
    print(f"  KGRN:  {n_kgrn} files in {output_path}/")
    print(f"  KFCD:  {n_kfcd} files in {output_path}/fcd/")
    print("="*70)
    
