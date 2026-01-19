#! /bin/bash -l
#SBATCH -A naiss2025-1-38
#SBATCH --exclusive
#SBATCH -n 8
#SBATCH -t 02:00:00
#SBATCH -J run_CuMg

module load buildenv-intel/2023a-eb

id_ratio="CuMg"

for r in 1.62; do

    echo "c/a ratio: $r"

    cd smx

    echo "Running KSTR:"
    /home/x_pamca/postdoc_proj/emto/bin/kstr.exe < ${id_ratio}_${r}.dat > smx_${r}.log

    if [ $? -ne 0 ]; then
        echo "KSTR failed!"
        exit 1
    else
        echo "DONE!"
    fi

    echo "Info about DMAX:"
    grep -A1 "Primv" smx_${r}.log

    cd ../shp

    echo "Running SHAPE:"
    /home/x_pamca/postdoc_proj/emto/bin/shape.exe < ${id_ratio}_${r}.dat > shp_${r}.log

    if [ $? -ne 0 ]; then
        echo "SHAPE failed!"
        exit 1
    else
        echo "DONE!"
    fi

    cd ../

    for v in 3.35; do

        echo "WSW: $v"

        echo "Running KGRN:"
        mpirun -n 8  /home/x_pamca/postdoc_proj/emto/bin/kgrn_mpi.x < CuMg_${r}_${v}.dat > kgrn_${r}_${v}.log

        if [ $? -ne 0 ]; then
            echo "KGRN failed!"
            exit 1
        else
            echo "DONE!"
        fi

        cd fcd/

        echo "Running KFCD:"
        /home/x_pamca/postdoc_proj/emto/bin/kfcd.exe < CuMg_${r}_${v}.dat > kfcd_${r}_${v}.log

        if [ $? -ne 0 ]; then
            echo "KFCD failed!"
            exit 1
        else
            echo "DONE!"
        fi

        cd ../
        
    done

done
