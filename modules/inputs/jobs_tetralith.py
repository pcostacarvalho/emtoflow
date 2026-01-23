
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
        {shape_executable} < ${{id_ratio}}_${{r}}.dat > shp_${{r}}.log

        # Check SHAPE completion via log content
        if [ ! -f shp_${{r}}.log ] || ! grep -q "Shape function completed" shp_${{r}}.log 2>/dev/null; then
            echo "SHAPE failed!"
            exit 1
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

