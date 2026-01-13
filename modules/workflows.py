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
from modules.structure_builder import create_emto_structure

def create_emto_inputs(
    output_path,
    job_name,
    cif_file=None,
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
    account="naiss2025-1-38"
):
    """
    Create complete EMTO input files for c/a and SWS sweeps.

    Supports two workflows:
    1. CIF workflow: Provide cif_file
    2. Parameter workflow: Provide lat, a, sites

    Parameters
    ----------
    output_path : str
        Base output directory
    job_name : str
        Job identifier (e.g., 'fept')
    cif_file : str, optional
        Path to CIF file (for CIF workflow)
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

    Returns
    -------
    None

    Examples
    --------
    # CIF workflow (existing)
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


    # ==================== SWEEP OVER C/A RATIOS ====================
    print(f"\nCreating input files for {len(ca_ratios)} c/a ratios and {len(sws_values)} SWS values...")


    
    for ratio in ca_ratios:
        print(f"\n  c/a = {ratio:.2f}")
        
        file_id_ratio = f"{job_name}_{ratio:.2f}"
        
        # ==================== CREATE KSTR INPUT ====================
        create_kstr_input(
            structure=structure,
            output_path=output_path,
            id_ratio=file_id_ratio,
            dmax=dmax,
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
    
