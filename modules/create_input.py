import os
import json
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
from modules.structure_builder import create_emto_structure, lattice_param_to_sws
from modules.dmax_optimizer import _run_dmax_optimization
from utils.config_parser import load_and_validate_config
from utils.aux_lists import prepare_ranges


def _save_structure_to_json(structure_pmg, structure_dict, filename):
    """
    Save structure information to JSON file for inspection.

    Parameters
    ----------
    structure_pmg : pymatgen.core.Structure
        Pymatgen Structure object
    structure_dict : dict
        EMTO structure dictionary
    filename : str
        Output JSON file path
    """
    # Create a serializable version of the structure
    structure_info = {
        'pymatgen_info': {
            'num_sites': len(structure_pmg.sites),
            'volume': float(structure_pmg.lattice.volume),
            'lattice_matrix': structure_pmg.lattice.matrix.tolist(),
            'sites': [
                {
                    'frac_coords': site.frac_coords.tolist(),
                    'cart_coords': site.coords.tolist(),
                    'species': str(site.species),
                    'occupancy': {str(k): float(v) for k, v in site.species.items()}
                }
                for site in structure_pmg.sites
            ]
        },
        'emto_structure': {}
    }

    # Convert structure_dict to JSON-serializable format
    for key, value in structure_dict.items():
        if isinstance(value, np.ndarray):
            structure_info['emto_structure'][key] = value.tolist()
        elif isinstance(value, (np.integer, np.floating)):
            structure_info['emto_structure'][key] = float(value)
        else:
            structure_info['emto_structure'][key] = value

    # Write to file
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w') as f:
        json.dump(structure_info, f, indent=2)


def create_emto_inputs(config):
    """
    Create complete EMTO input files for c/a and SWS sweeps.

    Supports two type of inputs:
    1. CIF: Provide cif_file
    2. Parameter workflow: Provide lat, a, sites

    The parameters should be passed through a config file: YAML/JSON file or dict
    Format:

    {
    # Required parameters
    output_path = ,
    job_name = ,

    # Structure
    cif_file = False,
    # Parameters below used if cif_file = False
    lat = None,
    a = None,
    sites = None,
    b = a,
    c = a (can be 1.633*a for HCP or set other value),
    alpha = 90,
    beta = 90,
    gamma = 90,
    ca_ratios = (provide a list with at least one value if cif_file = False),
    sws_values = (provide a list with at least one value if cif_file = False),
    auto_generate = False,
    magnetic = P,
    user_magnetic_moments = None,
    dmax = None,
    

    # Job script parameters
    create_job_script = True,
    job_mode = 'serial',
    prcs = 1,
    time = "00:30:00",
    account = "naiss2025-1-38",

    # Workflows

    # DMAX optimization parameters
    optimize_dmax = False,
    dmax_initial = 2.0,
    dmax_target_vectors = 100,
    dmax_vector_tolerance = 15,

    # Optimization
    optimize_ca = False,
    ca_step = 0.02,
    optimize_sws = False,
    sws_step = 0.05,
    eos_type = 'MO88',
    run_mode = 'local',

    #Executables (required if optimize_dmax = True or create_job_script = True)
    kstr_executable = "/home/x_pamca/postdoc_proj/emto/bin/kstr.exe",
    shape_executable = "/home/x_pamca/postdoc_proj/emto/bin/shape.exe",
    kgrn_executable = "/home/x_pamca/postdoc_proj/emto/bin/kgrn_mpi.x",
    kfcd_executable = "/home/x_pamca/postdoc_proj/emto/bin/kfcd.exe"
    }

    Parameters
    ----------
    output_path : str, required
        Base output directory 
    job_name : str, required
        Job identifier 
    cif_file : str, optional
        Path to CIF file
    config : str, Path, or dict, optional
        Configuration file path (YAML/JSON) or configuration dictionary.
        If provided, extracts all parameters from config.
        Individual parameters can override config values.
    lat : int, optional
        EMTO lattice type 1-14 (see LATTICE_TYPES.md)
        1=SC, 2=FCC, 3=BCC, 4=HCP, 5=BCT, etc.
    a : float, optional
        Lattice parameter a in Angstroms
    sites : list of dict, optional
        Site specifications 
        Format: [{'position': [x,y,z], 'elements': ['Fe','Pt'], 'concentrations': [0.5, 0.5]}]
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
    time : str, e.g. "02:00:00" 
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
        Path to KSTR executable (required if optimize_dmax=True or create_job_script = True)
    shape_executable: str, optional
        Path to SHAPE executable (required if create_job_script=True)
    kgrn_executable: str, optional
        Path to KGRN executable (required if create_job_script=True)
    kfcd_executable: str, optional
        Path to KFCD executable (required if create_job_script=True)
    Returns
    -------
    None

    Examples
    --------
    # Config file workflow (NEW - recommended)
    create_emto_inputs(config='optimization_config.yaml')

    # Config dict workflow (NEW)
    config_dict = {
        'output_path': './cu_sweep',
        'job_name': 'cu',
        'cif_file': 'Cu.cif',
        'dmax': 1.3,
        'ca_ratios': [1.00],
        'sws_values': [2.60, 2.65, 2.70],
        'magnetic': 'P'
    }

    config_dict = {
        'output_path': './fept_alloy',
        'job_name': 'fept',
        'lat': 2,  # FCC
        'a': 3.7,
        'sites': [{'position': [0,0,0], 'elements': ['Fe','Pt'],
                   'concentrations': [0.5, 0.5]}],
        'dmax': 1.3,
        'ca_ratios': [1.00],
        'sws_values': [2.60, 2.65, 2.70],
        'magnetic': 'F',
        'optimize_dmax': True,
        'dmax_initial': 2.5,
        'dmax_target_vectors': 100,
        'kstr_executable': "/path/to/kstr.exe"
    }
    
    create_emto_inputs(config=config_dict)
    
    """

    # ==================== HANDLE CONFIGURATION ====================
    # Load and validate configuration (applies defaults automatically)
    cfg = load_and_validate_config(config)

    # Extract parameters from config (all defaults already applied)
    output_path = cfg['output_path']
    job_name = cfg['job_name']
    cif_file = cfg['cif_file']
    lat = cfg['lat']
    a = cfg['a']
    sites = cfg['sites']
    b = cfg['b']
    c = cfg['c']
    alpha = cfg['alpha']
    beta = cfg['beta']
    gamma = cfg['gamma']
    dmax = cfg['dmax']
    ca_ratios = cfg['ca_ratios']
    sws_values = cfg['sws_values']
    auto_generate = cfg['auto_generate']
    ca_step = cfg['ca_step']
    sws_step = cfg['sws_step']
    n_points = cfg['n_points']
    magnetic = cfg['magnetic']
    user_magnetic_moments = cfg['user_magnetic_moments']
    create_job_script = cfg['create_job_script']
    job_mode = cfg['job_mode']
    prcs = cfg['prcs']
    slurm_time = cfg['slurm_time']
    slurm_account = cfg['slurm_account']
    optimize_dmax = cfg['optimize_dmax']
    dmax_initial = cfg['dmax_initial']
    dmax_target_vectors = cfg['dmax_target_vectors']
    dmax_vector_tolerance = cfg['dmax_vector_tolerance']
    kstr_executable = cfg['kstr_executable']
    shape_executable = cfg['shape_executable']
    kgrn_executable = cfg['kgrn_executable']
    kfcd_executable = cfg['kfcd_executable']


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
        structure_pmg, structure_dict = create_emto_structure(
            cif_file=cif_file,
            user_magnetic_moments=user_magnetic_moments
        )

    if lat is not None:
        # Parameter workflow (alloy or ordered structure)
        print(f"\nCreating structure from parameters...")
        print(f"  Lattice type: LAT={lat}")
        print(f"  Lattice parameter a: {a} Å")
        print(f"  Number of sites: {len(sites)}")

        structure_pmg, structure_dict = create_emto_structure(
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

    print(f"  Structure created: LAT={structure_dict['lat']} ({structure_dict['lattice_name']})")
    print(f"  Number of atoms: NQ3={structure_dict['NQ3']}")
    print(f"  Maximum NL: {structure_dict['NL']}")

    # Save structure to JSON file for inspection
    structure_file = os.path.join(output_path, f"{job_name}_structure.json")
    _save_structure_to_json(structure_pmg, structure_dict, structure_file)
    print(f"  Structure saved to: {structure_file}")

    # Auto-determine ca_ratios and sws_values if not provided
    if ca_ratios is None:
        ca_ratios = [structure_dict['coa']]

    if sws_values is None:
        sws_values = [lattice_param_to_sws(structure_pmg)]


    # ==================== DMAX OPTIMIZATION (OPTIONAL) ====================
    if optimize_dmax:
        # Auto-generate ranges if needed (validation already done in parser)
        if len(ca_ratios) <= 1 and auto_generate:
            print(f"Auto-generating c/a and SWS ranges for DMAX optimization...")
            ca_ratios, sws_values = prepare_ranges(
                ca_ratios=ca_ratios,
                sws_values=sws_values,
                ca_step=ca_step,
                sws_step=sws_step,
                n_points=n_points
            )

        print("\n" + "="*70)
        print("DMAX OPTIMIZATION WORKFLOW")
        print("="*70)

        dmax_per_ratio = _run_dmax_optimization(
            output_path=output_path,
            job_name=job_name,
            structure=structure_dict,
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
            structure=structure_dict,
            output_path=output_path,
            id_ratio=file_id_ratio,
            dmax=ratio_dmax,
            ca_ratio=ratio
        )
    

        # ==================== CREATE SHAPE INPUT ====================

        create_shape_input(
            structure=structure_dict,
            path=output_path,
            id_ratio=file_id_ratio
        )


        # ==================== SWEEP OVER SWS VALUES ====================
        for sws in sws_values:
            file_id_full = f"{file_id_ratio}_{sws:.2f}"

            # Create KGRN input

            create_kgrn_input(
                structure=structure_dict,
                path=output_path,
                id_full=file_id_full,
                id_ratio=file_id_ratio,
                SWS=sws,
                magnetic= magnetic if magnetic is not None else 'F'
            )
 
            # Create KFCD input

            create_kfcd_input(
                structure=structure_dict,
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
                time=slurm_time,
                account=slurm_account,
                id_ratio=job_name,
                kstr_executable=kstr_executable,
                shape_executable=shape_executable,
                kgrn_executable=kgrn_executable,
                kfcd_executable=kfcd_executable
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
                time=slurm_time,
                account=slurm_account,
                id_ratio=job_name,
                kstr_executable=kstr_executable,
                shape_executable=shape_executable,
                kgrn_executable=kgrn_executable,
                kfcd_executable=kfcd_executable
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
    
