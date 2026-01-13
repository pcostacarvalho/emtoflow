import numpy as np
import os
from modules.inputs import (
    create_kstr_input,
    create_shape_input,
    create_kgrn_input,
    create_kfcd_input,
    write_serial_sbatch,
    write_parallel_sbatch
)
from modules.lat_detector import parse_emto_structure
from modules.alloy_input import ( 
    validate_alloy_input, 
    create_alloy_structure
    )
from modules.kstr_template import copy_kstr_template

def create_emto_inputs(
    output_path,
    job_name,
    cif_file,
    is_alloy=False,
    lattice_type=None,
    elements=None,
    concentrations=None,
    nl=None,
    dmax=None,
    ca_ratios=None,
    sws_values=None,
    magnetic = None,
    create_job_script=True,
    job_mode='serial',  # 'serial' or 'parallel'
    prcs=1,
    time="00:30:00",
    account="naiss2025-1-38"
):
    """
    Create complete EMTO input files for c/a and SWS sweeps.

    
    Parameters
    ----------
    output_path : str
        Base output directory
    job_name : str
        Job identifier (e.g., 'fept')
    dmax : float
        Maximum distance parameter for KSTR
    lat : int, optional
        Bravais lattice type (1-14). If None and from_cif=True, will be auto-detected.
        Required when from_cif=False.
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
    # Mode 1: From CIF (new way - LAT auto-detected)
    create_emto_inputs(
        output_path="./fept_sweep",
        job_name="fept",
        dmax=1.3,
        lat=None,  # Auto-detected from CIF
        ca_ratios=[0.92, 0.96, 1.00],
        sws_values=[2.60, 2.65, 2.70],
        from_cif=True,
        cif_file="FePt.cif",
        nl=3  # optional
    )
    """

    if magnetic not in ['P', 'F']:
        raise ValueError("Magnetic parameter must be 'P' (paramagnetic) or 'F' (ferromagnetic).")

    # ==================== CREATE DIRECTORY STRUCTURE ====================
    subfolders = ['smx', 'shp', 'pot', 'chd', 'fcd', 'tmp']
    os.makedirs(output_path, exist_ok=True)
    for subfolder in subfolders:
        os.makedirs(os.path.join(output_path, subfolder), exist_ok=True)

    print(f"Created directory structure in: {output_path}")

    # ==================== BUILD STRUCTURE ====================
 
    if cif_file is not None and is_alloy:
        raise ValueError("Input from cif file and alloy calculation not supported simultaneously.")
    
    if cif_file is not None:
 
        structure = None

        print(f"\nParsing CIF file: {cif_file}")
        structure = parse_emto_structure(cif_file)
        print(f"  Detected lattice: LAT={structure['lat']} ({structure['lattice_name']})")
        print(f"  Number of atoms: NQ3={structure['NQ3']}")
        print(f"  Maximum NL: {structure['NL']}")


        if ca_ratios is None:
            ca_ratios = [structure['coa']]

        if sws_values is None:
            volume = structure['a']*structure['b']*structure['c']/structure['NQ3']
            sws_values = [(3*volume/(4*np.pi) )**(1/3)]

    elif is_alloy:

        print(f"\nValidating alloy input...")

        if sws_values is None:
            raise ValueError("An initial SWS value must be provided for alloy calculations.")

        if lattice_type in ('fcc', 'bcc', 'sc'):
            ca_ratios = [1.0]

        validate_alloy_input(
            lattice_type=lattice_type,
            elements=elements,
            concentrations=concentrations,
            sws=sws_values[0],
            nl=nl
        )

        print("✓ Validation passed")

        structure = create_alloy_structure(
            lattice_type=lattice_type,
            elements=elements,
            concentrations=concentrations,
            initial_sws=sws_values[0],
            nl=nl
        )


    # ==================== SWEEP OVER C/A RATIOS ====================
    print(f"\nCreating input files for {len(ca_ratios)} c/a ratios and {len(sws_values)} SWS values...")


    
    for ratio in ca_ratios:
        print(f"\n  c/a = {ratio:.2f}")
        
        file_id_ratio = f"{job_name}_{ratio:.2f}"
        
        # ==================== CREATE KSTR INPUT ====================

        # Use pre-parsed structure (parsed once at the beginning)

        if cif_file is not None:
            create_kstr_input(
                structure=structure,
                output_path=output_path,
                id_ratio=file_id_ratio,
                dmax=dmax,
                ca_ratio=ratio
            )
        elif is_alloy:
            copy_kstr_template(
                lattice_type=lattice_type,
                structure=structure,
                output_path=output_path,
                job_name=job_name
            )
    

        # ==================== CREATE SHAPE INPUT ====================

        create_shape_input(
            structure=structure,
            path=output_path,
            id_ratio=file_id_ratio
        )


        # ==================== SWEEP OVER SWS VALUES ====================
        for sws in sws_values:
            file_id_full = f"{file_id_ratio}_{sws:.2f}"

            # Create KGRN input

            create_kgrn_input(
                structure=structure,
                path=output_path,
                id_full=file_id_full,
                id_ratio=file_id_ratio,
                SWS=sws,
                magnetic= magnetic if magnetic is not None else 'P'
            )
 
            # Create KFCD input

            create_kfcd_input(
                structure=structure,
                path=output_path,
                id_ratio=file_id_ratio,
                id_full=file_id_full
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
                id_ratio=job_name
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
                id_ratio=job_name
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
    
