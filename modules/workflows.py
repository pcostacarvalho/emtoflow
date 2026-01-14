import os
import numpy as np
from typing import Union, Dict, Any
from pathlib import Path
from modules.inputs import (
    create_kstr_input,
    create_shape_input,
    create_kgrn_input,
    create_kfcd_input,
    write_serial_sbatch,
    write_parallel_sbatch
)
from modules.structure_builder import create_emto_structure
from modules.dmax_optimizer import _run_dmax_optimization
from utils.config_parser import load_and_validate_config, apply_config_defaults

def create_emto_inputs(
    output_path=None,
    job_name=None,
    cif_file=None,
    # Configuration file support
    config=None,
    # New parameter workflow parameters
    lat=None,
    a=None,
    sites=None,
    b=None,
    c=None,
    alpha=90,
    beta=90,
    gamma=90,
    # Common parameters
    dmax=None,
    ca_ratios=None,
    sws_values=None,
    magnetic=None,
    user_magnetic_moments=None,
    create_job_script=True,
    job_mode='serial',
    prcs=1,
    time="00:30:00",
    account="naiss2025-1-38",
    # DMAX optimization parameters
    optimize_dmax=False,
    dmax_initial=2.0,
    dmax_target_vectors=100,
    dmax_vector_tolerance=15,
    kstr_executable=None
):
    """
    Create complete EMTO input files for c/a and SWS sweeps.

    Supports three workflows:
    1. Config file workflow: Provide config (YAML/JSON file or dict)
    2. CIF workflow: Provide cif_file
    3. Parameter workflow: Provide lat, a, sites

    Parameters
    ----------
    output_path : str, optional
        Base output directory (required if config not provided)
    job_name : str, optional
        Job identifier (required if config not provided)
    cif_file : str, optional
        Path to CIF file (for CIF workflow)
    config : str, Path, or dict, optional
        Configuration file path (YAML/JSON) or configuration dictionary.
        If provided, extracts all parameters from config.
        Individual parameters can override config values.
    lat : int, optional
        EMTO lattice type 1-14 (for parameter workflow)
        1=SC, 2=FCC, 3=BCC, 4=HCP, 5=BCT, etc.
    a : float, optional
        Lattice parameter a in Angstroms (for parameter workflow)
    sites : list of dict, optional
        Site specifications (for parameter workflow)
        Format: [{'position': [x,y,z], 'elements': ['Fe','Pt'],
                  'concentrations': [0.5, 0.5]}]
    b, c : float, optional
        Lattice parameters b, c in Angstroms.
        Defaults: b=a, c=a (or c=1.633*a for HCP)
    alpha, beta, gamma : float, optional
        Lattice angles in degrees. Default: 90° (120° for HCP)
    dmax : float
        Maximum distance parameter for KSTR
    ca_ratios : list of float, optional
        List of c/a ratios to sweep. Auto-determined if None.
    sws_values : list of float, optional
        List of Wigner-Seitz radius values. Auto-determined if None.
    magnetic : str
        'P' for paramagnetic or 'F' for ferromagnetic
    user_magnetic_moments : dict, optional
        Custom magnetic moments per element, e.g. {'Fe': 2.5, 'Pt': 0.4}
    create_job_script : bool
        Whether to create SLURM job scripts
    job_mode : str
        'serial' or 'parallel'
    prcs : int
        Number of processors
    time : str
        Job time limit
    account : str
        SLURM account
    optimize_dmax : bool, optional
        Enable DMAX optimization workflow (default: False)
    dmax_initial : float, optional
        Initial DMAX guess for optimization (default: 2.0).
        Should be large enough for the LARGEST c/a ratio in your sweep,
        as optimization processes ratios in descending order.
        Tip: Start with a generous value (e.g., 2.5-3.0)
    dmax_target_vectors : int, optional
        Target number of k-vectors (default: 100)
    dmax_vector_tolerance : int, optional
        Acceptable deviation from target (default: 15)
    kstr_executable : str, optional
        Path to KSTR executable (required if optimize_dmax=True)

    Returns
    -------
    None

    Examples
    --------
    # Config file workflow (NEW - recommended)
    create_emto_inputs(config='optimization_config.yaml')

    # Config dict workflow (NEW)
    config_dict = {
        'base_path': './cu_sweep',
        'job_name': 'cu',
        'cif_file': 'Cu.cif',
        'dmax': 1.3,
        'ca_ratios': [1.00],
        'sws_values': [2.60, 2.65, 2.70],
        'magnetic': 'P'
    }
    create_emto_inputs(config=config_dict)

    # CIF workflow (existing - still supported)
    create_emto_inputs(
        output_path="./cu_sweep",
        job_name="cu",
        cif_file="Cu.cif",
        dmax=1.3,
        ca_ratios=[1.00],
        sws_values=[2.60, 2.65, 2.70],
        magnetic='P'
    )

    # Parameter workflow - FCC Fe-Pt random alloy (50-50)
    config_dict = {
        'base_path': './fept_alloy',
        'job_name': 'fept',
        'lat': 2,  # FCC
        'a': 3.7,
        'sites': [{'position': [0,0,0], 'elements': ['Fe','Pt'],
                   'concentrations': [0.5, 0.5]}],
        'dmax': 1.3,
        'ca_ratios': [1.00],
        'sws_values': [2.60, 2.65, 2.70],
        'magnetic': 'F'
    }
    create_emto_inputs(config=config_dict)

    # OR using individual parameters (old way still works)
    sites = [{'position': [0,0,0], 'elements': ['Fe','Pt'],
              'concentrations': [0.5, 0.5]}]
    create_emto_inputs(
        output_path="./fept_alloy",
        job_name="fept",
        lat=2,  # FCC
        a=3.7,
        sites=sites,
        dmax=1.3,
        ca_ratios=[1.00],
        sws_values=[2.60, 2.65, 2.70],
        magnetic='F'
    )

    # Parameter workflow - L10 FePt ordered structure
    config_dict = {
        'base_path': './fept_l10',
        'job_name': 'fept_l10',
        'lat': 5,  # BCT
        'a': 3.7,
        'c': 3.7*0.96,
        'sites': [
            {'position': [0,0,0], 'elements': ['Fe'], 'concentrations': [1.0]},
            {'position': [0.5,0.5,0.5], 'elements': ['Pt'], 'concentrations': [1.0]}
        ],
        'dmax': 1.3,
        'ca_ratios': [0.96],
        'sws_values': [2.60, 2.65],
        'magnetic': 'F'
    }
    create_emto_inputs(config=config_dict)

    # OR using individual parameters (old way still works)
    sites = [
        {'position': [0,0,0], 'elements': ['Fe'], 'concentrations': [1.0]},
        {'position': [0.5,0.5,0.5], 'elements': ['Pt'], 'concentrations': [1.0]}
    ]
    create_emto_inputs(
        output_path="./fept_l10",
        job_name="fept_l10",
        lat=5,  # BCT
        a=3.7,
        c=3.7*0.96,
        sites=sites,
        dmax=1.3,
        ca_ratios=[0.96],
        sws_values=[2.60, 2.65],
        magnetic='F'
    )

    # CIF workflow with DMAX optimization
    # Note: dmax_initial should be large enough for largest c/a (1.04)
    # Optimization processes ratios in descending order: 1.04 → 1.00 → 0.96 → 0.92
    create_emto_inputs(
        output_path="./fept_optimized",
        job_name="fept",
        cif_file="FePt.cif",
        ca_ratios=[0.92, 0.96, 1.00, 1.04],
        sws_values=[2.60, 2.65, 2.70],
        magnetic='F',
        optimize_dmax=True,
        dmax_initial=2.5,  # Large enough for c/a=1.04
        dmax_target_vectors=100,
        kstr_executable="/path/to/kstr.exe"
    )
    """

    # ==================== HANDLE CONFIGURATION ====================
    if config is not None:
        # Load and validate configuration
        cfg = load_and_validate_config(config)
        cfg = apply_config_defaults(cfg)

        # Extract parameters from config (use config as default, allow overrides)
        output_path = output_path or cfg.get('base_path')
        job_name = job_name or cfg.get('job_name')
        cif_file = cif_file or cfg.get('cif_file')
        lat = lat or cfg.get('lat')
        a = a or cfg.get('a')
        sites = sites or cfg.get('sites')
        b = b or cfg.get('b')
        c = c or cfg.get('c')
        alpha = alpha if alpha != 90 else cfg.get('alpha', 90)
        beta = beta if beta != 90 else cfg.get('beta', 90)
        gamma = gamma if gamma != 90 else cfg.get('gamma', 90)
        dmax = dmax or cfg.get('dmax')
        ca_ratios = ca_ratios or cfg.get('ca_ratios')
        sws_values = sws_values or cfg.get('sws_values')
        magnetic = magnetic or cfg.get('magnetic')
        user_magnetic_moments = user_magnetic_moments or cfg.get('user_magnetic_moments')
        create_job_script = cfg.get('create_job_script', create_job_script)
        job_mode = cfg.get('job_mode', job_mode)
        prcs = cfg.get('prcs', prcs)
        time = cfg.get('slurm_time', time)
        account = cfg.get('slurm_account', account)
        optimize_dmax = cfg.get('optimize_dmax', optimize_dmax)
        dmax_initial = cfg.get('dmax_initial', dmax_initial)
        dmax_target_vectors = cfg.get('dmax_target_vectors', dmax_target_vectors)
        dmax_vector_tolerance = cfg.get('dmax_vector_tolerance', dmax_vector_tolerance)
        kstr_executable = kstr_executable or cfg.get('kstr_executable')

    # Validate required parameters
    if output_path is None:
        raise ValueError("output_path is required (provide directly or via config)")
    if job_name is None:
        raise ValueError("job_name is required (provide directly or via config)")
    if dmax is None:
        raise ValueError("dmax is required (provide directly or via config)")
    if magnetic is None:
        raise ValueError("magnetic is required (provide directly or via config)")

    if magnetic not in ['P', 'F']:
        raise ValueError("Magnetic parameter must be 'P' (paramagnetic) or 'F' (ferromagnetic).")

    # ==================== CREATE DIRECTORY STRUCTURE ====================
    subfolders = ['smx', 'shp', 'pot', 'chd', 'fcd', 'tmp']
    os.makedirs(output_path, exist_ok=True)
    for subfolder in subfolders:
        os.makedirs(os.path.join(output_path, subfolder), exist_ok=True)

    print(f"Created directory structure in: {output_path}")

    # ==================== BUILD STRUCTURE ====================

    # Determine which workflow to use
    if cif_file is not None:
        # CIF workflow
        print(f"\nParsing CIF file: {cif_file}")
        structure = create_emto_structure(
            cif_file=cif_file,
            user_magnetic_moments=user_magnetic_moments
        )
        print(f"  Detected lattice: LAT={structure['lat']} ({structure['lattice_name']})")
        print(f"  Number of atoms: NQ3={structure['NQ3']}")
        print(f"  Maximum NL: {structure['NL']}")

        # Auto-determine ca_ratios and sws_values if not provided
        if ca_ratios is None:
            ca_ratios = [structure['coa']]

        if sws_values is None:
            volume = structure['a'] * structure['b'] * structure['c'] / structure['NQ3']
            sws_values = [(3 * volume / (4 * np.pi))**(1/3)]

    elif lat is not None and a is not None and sites is not None:
        # Parameter workflow (alloy or ordered structure)
        print(f"\nCreating structure from parameters...")
        print(f"  Lattice type: LAT={lat}")
        print(f"  Lattice parameter a: {a} Å")
        print(f"  Number of sites: {len(sites)}")

        structure = create_emto_structure(
            lat=lat,
            a=a,
            sites=sites,
            b=b,
            c=c,
            alpha=alpha,
            beta=beta,
            gamma=gamma,
            user_magnetic_moments=user_magnetic_moments
        )

        print(f"  Structure created: LAT={structure['lat']} ({structure['lattice_name']})")
        print(f"  Number of atoms: NQ3={structure['NQ3']}")
        print(f"  Maximum NL: {structure['NL']}")

        # Auto-determine ca_ratios if not provided
        if ca_ratios is None:
            # For cubic lattices, default to 1.0
            if lat in [1, 2, 3]:  # SC, FCC, BCC
                ca_ratios = [1.0]
            else:
                ca_ratios = [structure['coa']]

        # For parameter workflow, sws_values must be provided
        if sws_values is None:
            raise ValueError(
                "sws_values must be provided for parameter workflow. "
                "Example: sws_values=[2.60, 2.65, 2.70]"
            )

    else:
        raise ValueError(
            "Must provide either:\n"
            "  1. cif_file='path/to/file.cif'\n"
            "  2. lat=<1-14>, a=<value>, sites=<list>"
        )

    # ==================== DMAX OPTIMIZATION (OPTIONAL) ====================
    if optimize_dmax:

        if len(ca_ratios) <= 1:
            raise ValueError("At least two c/a ratio must be provided for DMAX optimization.")

        if kstr_executable is None:
            raise ValueError("kstr_executable must be provided when optimize_dmax=True")

        print("\n" + "="*70)
        print("DMAX OPTIMIZATION WORKFLOW")
        print("="*70)

        dmax_per_ratio = _run_dmax_optimization(
            output_path=output_path,
            job_name=job_name,
            structure=structure,
            ca_ratios=ca_ratios,
            dmax_initial=dmax_initial,
            target_vectors=dmax_target_vectors,
            vector_tolerance=dmax_vector_tolerance,
            kstr_executable=kstr_executable
        )

        if dmax_per_ratio is None:
            print("\n✗ DMAX optimization failed - aborting workflow")
            return

        print("\nProceeding to generate final input files with optimized DMAX values...")
    else:
        # Standard workflow - single DMAX for all ratios
        if dmax is None:
            raise ValueError("dmax must be provided when optimize_dmax=False")
        dmax_per_ratio = {ratio: dmax for ratio in ca_ratios}



    # ==================== SWEEP OVER C/A RATIOS ====================
    print(f"\nCreating input files for {len(ca_ratios)} c/a ratios and {len(sws_values)} SWS values...")


    for ratio in ca_ratios:
        print(f"\n  c/a = {ratio:.2f}")

        file_id_ratio = f"{job_name}_{ratio:.2f}"

        # Get DMAX for this ratio (optimized or standard)
        ratio_dmax = dmax_per_ratio[ratio]

        # ==================== CREATE KSTR INPUT ====================
        create_kstr_input(
            structure=structure,
            output_path=output_path,
            id_ratio=file_id_ratio,
            dmax=ratio_dmax,
            ca_ratio=ratio
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
                magnetic= magnetic if magnetic is not None else 'F'
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
    
