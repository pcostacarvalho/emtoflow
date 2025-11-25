#! /bin/bash -l
#SBATCH -A naiss2025-1-38
#SBATCH --exclusive
#SBATCH -n 1
#SBATCH -t 00:30:00
#SBATCH -J run_fept

id_name="fept"

for r in 1.37; do

    echo "c/a ratio: $r"

    cd smx

    echo "Running KSTR:"
    kstr.exe < ${id_name}_${r}.dat > smx_${r}.log

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
    shape.exe < ${id_name}_${r}.dat > shp_${r}.log

    if [ $? -ne 0 ]; then
        echo "SHAPE failed!"
        exit 1
    else
        echo "DONE!"
    fi

    cd ../

    for v in 1.49; do

        echo "WSW: $v"

        echo "Running KGRN:"
        mpirun -n 1  kgrn_mpi.x < fept_${r}_${v}.dat > kgrn_${r}_${v}.log

        if [ $? -ne 0 ]; then
            echo "KGRN failed!"
            exit 1
        else
            echo "DONE!"
        fi

        cd fcd/ 

        echo "Running KFCD:"
        kfcd.exe < fept_${r}_${v}.dat > kfcd_${r}_${v}.log

        if [ $? -ne 0 ]; then
            echo "KFCD failed!"
            exit 1
        else
            echo "DONE!"
        fi

        cd ../
        
    done

done
