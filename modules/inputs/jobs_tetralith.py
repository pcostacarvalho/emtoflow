
def write_serial_sbatch(path, ratios, volumes, job_name, prcs=1, time="00:30:00", account="naiss2025-1-38", id_ratio="fept",
                        kstr_executable="kstr.exe", shape_executable="shape.exe",
                        kgrn_executable="kgrn_mpi.x", kfcd_executable="kfcd.exe"):
    """Write serial SBATCH script for volume optimization."""
    
        # Format numbers to 2 decimal places
    ratios_str = ' '.join(f"{r:.2f}" for r in ratios)
    volumes_str = ' '.join(f"{v:.2f}" for v in volumes)

    script = f"""#! /bin/bash -l
#SBATCH -A {account}
#SBATCH --exclusive
#SBATCH -n {prcs}
#SBATCH -t {time}
#SBATCH -J {job_name}

module load buildenv-intel/2023a-eb

id_ratio="{id_ratio}"

for r in {ratios_str}; do

    echo "c/a ratio: $r"

    cd smx

    # Check if KSTR output already exists and is complete
    if [ -f {id_ratio}_${{r}}.prn ] && [ -s {id_ratio}_${{r}}.prn ] && grep -q "KSTR:     Finished at:" {id_ratio}_${{r}}.prn 2>/dev/null; then
        echo "Skipping KSTR for c/a=$r (output already exists and is complete)"
    else
        echo "Running KSTR:"
        {kstr_executable} < {id_ratio}_${{r}}.dat > smx_${{r}}.log

        # Check KSTR completion via .prn content
        if [ ! -f {id_ratio}_${{r}}.prn ] || ! grep -q "KSTR:     Finished at:" {id_ratio}_${{r}}.prn 2>/dev/null; then
            echo "KSTR failed for c/a=$r: .prn file missing or incomplete!"
            grep "Try DMAX" smx_${{r}}.log
            echo "Skipping entire c/a=$r ratio (SHAPE, KGRN, KFCD will not run for this ratio)"
            cd ../
            continue
        else
            echo "DONE!"
        fi
    fi

    echo "Info about DMAX:"
    grep -A1 "Primv" smx_${{r}}.log

    cd ../shp

    # Check if SHAPE output already exists and is complete
    if [ -f shp_${{r}}.log ] && [ -s shp_${{r}}.log ] && grep -q "Shape function completed" shp_${{r}}.log 2>/dev/null; then
        echo "Skipping SHAPE for c/a=$r (output already exists and is complete)"
    else
        echo "Running SHAPE:"
        {shape_executable} < ${{id_ratio}}_${{r}}.dat > shp_${{r}}.log

        # Check SHAPE completion via log content
        if [ ! -f shp_${{r}}.log ] || ! grep -q "Shape function completed" shp_${{r}}.log 2>/dev/null; then
            echo "SHAPE failed for c/a=$r!"
            echo "Skipping entire c/a=$r ratio (KGRN, KFCD will not run for this ratio)"
            cd ../
            continue
        else
            echo "DONE!"
        fi
    fi

    cd ../

    for v in {volumes_str}; do

        echo "WSW: $v"

        # Check if KGRN output already exists and is complete
        if [ -f {id_ratio}_${{r}}_${{v}}.prn ] && [ -s {id_ratio}_${{r}}_${{v}}.prn ] && grep -q "KGRN: OK  Finished at:" {id_ratio}_${{r}}_${{v}}.prn 2>/dev/null; then
            echo "Skipping KGRN for c/a=$r, SWS=$v (output already exists and is complete)"
        else
            echo "Running KGRN:"
            mpirun -n {prcs}  {kgrn_executable} < {id_ratio}_${{r}}_${{v}}.dat > kgrn_${{r}}_${{v}}.log

            # Check KGRN completion via .prn content
            if [ ! -f {id_ratio}_${{r}}_${{v}}.prn ] || ! grep -q "KGRN: OK  Finished at:" {id_ratio}_${{r}}_${{v}}.prn 2>/dev/null; then
                echo "KGRN failed for c/a=$r, SWS=$v!"
                echo "Skipping c/a=$r, SWS=$v (KFCD will not run for this combination)"
                continue
            else
                echo "DONE!"
            fi
        fi

        cd fcd/

        # Check if KFCD output already exists and is complete
        if [ -f {id_ratio}_${{r}}_${{v}}.prn ] && [ -s {id_ratio}_${{r}}_${{v}}.prn ] && grep -q "KFCD: OK  Finished at:" {id_ratio}_${{r}}_${{v}}.prn 2>/dev/null; then
            echo "Skipping KFCD for c/a=$r, SWS=$v (output already exists and is complete)"
        else
            echo "Running KFCD:"
            {kfcd_executable} < {id_ratio}_${{r}}_${{v}}.dat > kfcd_${{r}}_${{v}}.log

            # Check KFCD completion via .prn content
            if [ ! -f {id_ratio}_${{r}}_${{v}}.prn ] || ! grep -q "KFCD: OK  Finished at:" {id_ratio}_${{r}}_${{v}}.prn 2>/dev/null; then
                echo "KFCD failed for c/a=$r, SWS=$v!"
                echo "Skipping c/a=$r, SWS=$v and continuing to next SWS value..."
                cd ../
                continue
            else
                echo "DONE!"
            fi
        fi

        cd ../
        
    done

done
"""
    
    with open(f"{path}/{job_name}.sh", "w") as f:
        f.write(script)
# Revised syntax (typo in the comment, should be 'syntax')
# There is no code to insert here, just correcting the comment to "revise syntax"


def write_parallel_sbatch(path, ratios, volumes, job_name, prcs=1, time="00:30:00", account="naiss2025-1-38", id_ratio="fept",
                          kstr_executable="kstr.exe", shape_executable="shape.exe",
                          kgrn_executable="kgrn_mpi.x", kfcd_executable="kfcd.exe"):
    """Write parallel SBATCH scripts with proper dependencies."""
    
    # Stage 1: KSTR and SHAPE (one per ratio)
    for r in ratios: 
        r_fmt = f"{r:.2f}"
        r_var = r_fmt.replace('.', '_')
        
        script = f"""#! /bin/bash -l
#SBATCH -A {account}
#SBATCH --exclusive
#SBATCH -n {prcs}
#SBATCH -t {time}
#SBATCH -J {job_name}_prep_r{r_fmt}

module load buildenv-intel/2023a-eb

id_ratio="{id_ratio}"
r={r_fmt}

cd smx

# Check if KSTR output already exists and is complete
if [ -f {id_ratio}_${{r}}.prn ] && [ -s {id_ratio}_${{r}}.prn ] && grep -q "KSTR:     Finished at:" {id_ratio}_${{r}}.prn 2>/dev/null; then
    echo "Skipping KSTR for c/a=$r (output already exists and is complete)"
else
    echo "Running KSTR:"
    {kstr_executable} < {id_ratio}_${{r}}.dat > smx_${{r}}.log

    # Check KSTR completion via .prn content
    if [ ! -f {id_ratio}_${{r}}.prn ] || ! grep -q "KSTR:     Finished at:" {id_ratio}_${{r}}.prn 2>/dev/null; then
        echo "KSTR failed: .prn file missing or incomplete!"
        grep "Try DMAX" smx_${{r}}.log
        exit 1
    else
        echo "DONE!"
    fi
fi

echo "Info about DMAX:"
grep -A1 "Primv" smx_${{r}}.log

cd ../shp

# Check if SHAPE output already exists and is complete
if [ -f shp_${{r}}.log ] && [ -s shp_${{r}}.log ] && grep -q "Shape function completed" shp_${{r}}.log 2>/dev/null; then
    echo "Skipping SHAPE for c/a=$r (output already exists and is complete)"
else
    echo "Running SHAPE:"
    {shape_executable} < {id_ratio}_${{r}}.dat > shp_${{r}}.log

    # Check SHAPE completion via log content
    if [ ! -f shp_${{r}}.log ] || ! grep -q "Shape function completed" shp_${{r}}.log 2>/dev/null; then
        echo "SHAPE failed!"
        exit 1
    else
        echo "DONE!"
    fi
fi

cd ../
"""

        with open(f"{path}/{job_name}_prep_r{r_fmt}.sh", "w") as f:
            f.write(script)

    # Stage 2: KGRN and KFCD (one per r,v pair, depends on Stage 1)
    for r in ratios:
        r_fmt = f"{r:.2f}"
        r_var = r_fmt.replace('.', '_')

        for v in volumes:
            v_fmt = f"{v:.2f}"

            script = f"""#! /bin/bash -l
#SBATCH -A {account}
#SBATCH --exclusive
#SBATCH -n {prcs}
#SBATCH -t {time}
#SBATCH -J {job_name}_r{r_fmt}_v{v_fmt}
#SBATCH --dependency=afterok:$PREP_R{r_var}_JOBID

module load buildenv-intel/2023a-eb

id_ratio="{id_ratio}"
r={r_fmt}
v={v_fmt}

# Check if KGRN output already exists and is complete
if [ -f {id_ratio}_${{r}}_${{v}}.prn ] && [ -s {id_ratio}_${{r}}_${{v}}.prn ] && grep -q "KGRN: OK  Finished at:" {id_ratio}_${{r}}_${{v}}.prn 2>/dev/null; then
    echo "Skipping KGRN for c/a=$r, SWS=$v (output already exists and is complete)"
else
    echo "Running KGRN:"
    mpirun -n {prcs} {kgrn_executable} < {id_ratio}_${{r}}_${{v}}.dat > kgrn_${{r}}_${{v}}.log

    # Check KGRN completion via .prn content
    if [ ! -f {id_ratio}_${{r}}_${{v}}.prn ] || ! grep -q "KGRN: OK  Finished at:" {id_ratio}_${{r}}_${{v}}.prn 2>/dev/null; then
        echo "KGRN failed!"
        exit 1
    else
        echo "DONE!"
    fi
fi

cd fcd/

# Check if KFCD output already exists and is complete
if [ -f {id_ratio}_${{r}}_${{v}}.prn ] && [ -s {id_ratio}_${{r}}_${{v}}.prn ] && grep -q "KFCD: OK  Finished at:" {id_ratio}_${{r}}_${{v}}.prn 2>/dev/null; then
    echo "Skipping KFCD for c/a=$r, SWS=$v (output already exists and is complete)"
else
    echo "Running KFCD:"
    {kfcd_executable} < {id_ratio}_${{r}}_${{v}}.dat > kfcd_${{r}}_${{v}}.log

    # Check KFCD completion via .prn content
    if [ ! -f {id_ratio}_${{r}}_${{v}}.prn ] || ! grep -q "KFCD: OK  Finished at:" {id_ratio}_${{r}}_${{v}}.prn 2>/dev/null; then
        echo "KFCD failed!"
        exit 1
    else
        echo "DONE!"
    fi
fi

cd ../
"""
            
            with open(f"{path}/{job_name}_r{r_fmt}_v{v_fmt}.sh", "w") as f:
                f.write(script)
    
    # Write submission script
    submit_script = "#!/bin/bash\n# Submit preparation jobs and store job IDs\n"
    
    for r in ratios:  
        r_fmt = f"{r:.2f}"
        r_var = r_fmt.replace('.', '_')
        submit_script += f'PREP_R{r_var}_JOBID=$(sbatch --parsable {job_name}_prep_r{r_fmt}.sh)\n'
    
    submit_script += "\n# Submit computation jobs with dependencies\n"
    for r in ratios:  
        r_fmt = f"{r:.2f}"
        r_var = r_fmt.replace('.', '_')
        for v in volumes: 
            v_fmt = f"{v:.2f}"
            submit_script += f'sbatch --dependency=afterok:$PREP_R{r_var}_JOBID {job_name}_r{r_fmt}_v{v_fmt}.sh\n'
    
    with open(f"{path}/submit_{job_name}.sh", "w") as f:
        f.write(submit_script)


def create_master_job_scripts(generated_files, master_config, output_dir):
    """
    Create individual job scripts and master submission script for generated YAML files.

    This function creates SLURM job scripts for batch submission of multiple
    optimization runs generated by generate_percentages.

    Parameters
    ----------
    generated_files : list of str
        List of paths to generated YAML files
    master_config : dict
        Master configuration dictionary containing SLURM parameters:
        - slurm_account: SLURM account (default: 'naiss2025-1-38')
        - prcs: Number of processors per job (default: 8)
        - slurm_time: Time limit in HH:MM:SS format (default: '02:00:00')
    output_dir : Path
        Directory where YAML files and job scripts will be created

    Returns
    -------
    None
        Creates job scripts in the output directory

    Examples
    --------
    >>> from pathlib import Path
    >>> from modules.inputs.jobs_tetralith import create_master_job_scripts
    >>> 
    >>> generated_files = ['config1.yaml', 'config2.yaml']
    >>> master_config = {
    ...     'slurm_account': 'naiss2025-1-38',
    ...     'prcs': 8,
    ...     'slurm_time': '02:00:00'
    ... }
    >>> output_dir = Path('./output')
    >>> create_master_job_scripts(generated_files, master_config, output_dir)
    """
    import os
    from pathlib import Path

    # Get SLURM parameters from config
    account = master_config.get('slurm_account', 'naiss2025-1-38')
    prcs = master_config.get('prcs', 8)
    time_limit = master_config.get('slurm_time', '02:00:00')

    # Get absolute path to run_optimization.py
    # Assume it's in bin/ relative to the project root
    # Find project root by looking for modules directory
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent
    run_optimization_script = project_root / "bin" / "run_optimization.py"
    run_optimization_abs = run_optimization_script.resolve()

    if not run_optimization_script.exists():
        print(f"⚠ Warning: run_optimization.py not found at {run_optimization_script}")
        print("  Skipping job script creation.")
        return

    print("\n" + "=" * 70)
    print("CREATING JOB SCRIPTS")
    print("=" * 70)
    print(f"Account: {account}")
    print(f"Processors per job: {prcs}")
    print(f"Time limit: {time_limit}")
    print(f"Number of jobs: {len(generated_files)}")
    print("-" * 70)

    # Create individual job scripts
    job_script_paths = []
    for yaml_file in generated_files:
        yaml_path = Path(yaml_file)
        # Extract job name from filename (remove extension)
        job_name = yaml_path.stem

        # Create job script content
        job_script_content = f"""#!/bin/bash -l
#SBATCH -A {account}
#SBATCH --exclusive
#SBATCH -n {prcs}
#SBATCH -t {time_limit}
#SBATCH -J {job_name}_optimization

module load buildenv-intel/2023a-eb
module load Mambaforge/23.3.1-1-hpc1 

conda activate env

# Run optimization with this YAML file
python {run_optimization_abs} "{yaml_path.resolve()}" > {job_name}.log
"""

        # Write individual job script
        job_script_path = output_dir / f"job_{job_name}.sh"
        with open(job_script_path, 'w') as f:
            f.write(job_script_content)
        os.chmod(job_script_path, 0o755)
        job_script_paths.append(job_script_path)

        print(f"  Created: {job_script_path.name}")

    # Create master submission script
    master_script_content = f"""#!/bin/bash -l
# Master job script for batch submission
# Generated automatically - do not edit manually
# Submits separate jobs for each generated YAML config file

# Change to script directory
cd "{output_dir.resolve()}"

# Submit each job script
"""
    for job_script_path in job_script_paths:
        job_name = job_script_path.stem.replace('job_', '')
        master_script_content += f"""
echo "Submitting job for {job_name}..."
sbatch {job_script_path.name}
sleep 1
"""

    master_script_content += """
echo ""
echo "All jobs submitted!"
echo "Check status with: squeue -u $USER"
"""

    # Write master script
    master_script_path = output_dir / "master_job_script.sh"
    with open(master_script_path, 'w') as f:
        f.write(master_script_content)
    os.chmod(master_script_path, 0o755)

    print("-" * 70)
    print(f"✓ Created {len(job_script_paths)} individual job scripts")
    print(f"✓ Created master submission script: {master_script_path.name}")
    print("\nTo submit all jobs, run:")
    print(f"  bash {master_script_path}")
    print("=" * 70 + "\n")

