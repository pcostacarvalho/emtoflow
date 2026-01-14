def create_job_ca(
    folder,
    filename
):
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

    template = f"""#! /bin/bash -l
#SBATCH -A naiss2025-1-38
#SBATCH --exclusive
#SBATCH -n 1
#SBATCH -t 00:30:00
#SBATCH -J fept_{folder}

module load buildenv-intel/2023a-eb

echo "Running {folder}"
echo ""

cd smx

echo "Running KSTR:"
#kstr.exe < fept_{folder}.dat > smx.log

if [ $? -ne 0 ]; then
    echo "KSTR failed!"
    exit 1
else
    echo "DONE!"
fi

echo "Info about DMAX:"
grep -A1 "Primv" smx.log

cd ../shp

echo "Running SHAPE:"
#shape.exe < fept_{folder}.dat > shp.log

if [ $? -ne 0 ]; then
    echo "SHAPE failed!"
    exit 1
else
    echo "DONE!"
fi

cd ../

echo "Running KGRN:"
mpirun -n 1  kgrn_mpi.x < fept_{folder}.dat > kgrn.log

if [ $? -ne 0 ]; then
    echo "KGRN failed!"
    exit 1
else
    echo "DONE!"
fi

cd fcd/ 

echo "Running KFCD:"
kfcd.exe < fept_{folder}.dat > kfcd.log

if [ $? -ne 0 ]; then
    echo "KGRN failed!"
    exit 1
else
    echo "DONE!"
fi

cd ../

"""

    with open(filename, "w") as f:
        f.write(template)

    print(f"Script for job file '{filename}' created successfully.")

def create_job_volume(
    name,
    filename,
    volumes
):
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

    template = f"""#! /bin/bash -l
#SBATCH -A naiss2025-1-38
#SBATCH --exclusive
#SBATCH -n 1
#SBATCH -t 00:30:00
#SBATCH -J fept_vol_opt

module load buildenv-intel/2023a-eb

cd smx

echo "Running KSTR:"
kstr.exe < {name}.dat > smx.log

if [ $? -ne 0 ]; then
    echo "KSTR failed!"
    exit 1
else
    echo "DONE!"
fi

echo "Info about DMAX:"
grep -A1 "Primv" smx.log

cd ../shp

echo "Running SHAPE:"
shape.exe < {name}.dat > shp.log

if [ $? -ne 0 ]; then
    echo "SHAPE failed!"
    exit 1
else
    echo "DONE!"
fi

cd ../

for i in {volumes}; do

    echo "Running KGRN:"
    mpirun -n 1  kgrn_mpi.x < {name}_$i.dat > kgrn_$i.log

    if [ $? -ne 0 ]; then
        echo "KGRN failed!"
        exit 1
    else
        echo "DONE!"
    fi

    cd fcd/ 

    echo "Running KFCD:"
    kfcd.exe < {name}_$i.dat > kfcd_$i.log

    if [ $? -ne 0 ]; then
        echo "KGRN failed!"
        exit 1
    else
        echo "DONE!"
    fi

    cd ../
    
done

"""

    with open(filename, "w") as f:
        f.write(template)

    print(f"Script for job file '{filename}' created successfully.")


def write_serial_sbatch(path,ratios, volumes, job_name, prcs=1, time="00:30:00", account="naiss2025-1-38", id_ratio="fept"):
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

    echo "Running KSTR:"
    kstr.exe < ${{id_ratio}}_${{r}}.dat > smx_${{r}}.log

    if [ $? -ne 0 ]; then
        echo "KSTR failed!"
        exit 1
    else
        echo "DONE!"
    fi

    echo "Info about DMAX:"
    grep -A1 "Primv" smx_${{r}}.log

    cd ../shp

    echo "Running SHAPE:"
    shape.exe < ${{id_ratio}}_${{r}}.dat > shp_${{r}}.log

    if [ $? -ne 0 ]; then
        echo "SHAPE failed!"
        exit 1
    else
        echo "DONE!"
    fi

    cd ../

    for v in {volumes_str}; do

        echo "WSW: $v"

        echo "Running KGRN:"
        mpirun -n {prcs}  kgrn_mpi.x < {id_ratio}_${{r}}_${{v}}.dat > kgrn_${{r}}_${{v}}.log

        if [ $? -ne 0 ]; then
            echo "KGRN failed!"
            exit 1
        else
            echo "DONE!"
        fi

        cd fcd/ 

        echo "Running KFCD:"
        kfcd.exe < {id_ratio}_${{r}}_${{v}}.dat > kfcd_${{r}}_${{v}}.log

        if [ $? -ne 0 ]; then
            echo "KFCD failed!"
            exit 1
        else
            echo "DONE!"
        fi

        cd ../
        
    done

done
"""
    
    with open(f"{path}/{job_name}.sh", "w") as f:
        f.write(script)


def write_parallel_sbatch(path, ratios, volumes, job_name, prcs=1, time="00:30:00", account="naiss2025-1-38", id_ratio="fept"):
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

echo "Running KSTR:"
kstr.exe < ${{id_ratio}}_${{r}}.dat > smx_${{r}}.log

if [ $? -ne 0 ]; then
    echo "KSTR failed!"
    exit 1
else
    echo "DONE!"
fi

echo "Info about DMAX:"
grep -A1 "Primv" smx_${{r}}.log

cd ../shp

echo "Running SHAPE:"
shape.exe < ${{id_ratio}}_${{r}}.dat > shp_${{r}}.log

if [ $? -ne 0 ]; then
    echo "SHAPE failed!"
    exit 1
else
    echo "DONE!"
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

echo "Running KGRN:"
mpirun -n {prcs} kgrn_mpi.x < {id_ratio}_${{r}}_${{v}}.dat > kgrn_${{r}}_${{v}}.log

if [ $? -ne 0 ]; then
    echo "KGRN failed!"
    exit 1
else
    echo "DONE!"
fi

cd fcd/ 

echo "Running KFCD:"
kfcd.exe < {id_ratio}_${{r}}_${{v}}.dat > kfcd_${{r}}_${{v}}.log

if [ $? -ne 0 ]; then
    echo "KFCD failed!"
    exit 1
else
    echo "DONE!"
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

