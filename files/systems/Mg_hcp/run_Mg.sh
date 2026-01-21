#! /bin/bash -l
#SBATCH -A naiss2025-1-38
#SBATCH --exclusive
#SBATCH -n 8
#SBATCH -t 02:00:00
#SBATCH -J run_Mg

module load buildenv-intel/2023a-eb

id_ratio="Mg"

for r in 1.62; do

    echo "c/a ratio: $r"

    cd smx

    echo "Running KSTR:"
    /home/x_pamca/postdoc_proj/emto/bin/kstr.exe < Mg_${r}.dat > smx_${r}.log

    # Check KSTR completion via .prn content
    if [ ! -f Mg_${r}.prn ] || ! grep -q "Finished at:" Mg_${r}.prn 2>/dev/null; then
        echo "KSTR failed: .prn file missing or incomplete!"
        grep "Try DMAX" smx_${r}.log
        exit 1
    else
        echo "DONE!"
    fi

    echo "Info about DMAX:"
    grep -A1 "Primv" smx_${r}.log

    cd ../shp

    echo "Running SHAPE:"
    /home/x_pamca/postdoc_proj/emto/bin/shape.exe < ${id_ratio}_${r}.dat > shp_${r}.log

    # Check SHAPE completion via log content
    if [ ! -f shp_${r}.log ] || ! grep -q "Shape function completed" shp_${r}.log 2>/dev/null; then
        echo "SHAPE failed!"
        exit 1
    else
        echo "DONE!"
    fi

    cd ../

    for v in 3.19; do

        echo "WSW: $v"

        echo "Running KGRN:"
        mpirun -n 8  /home/x_pamca/postdoc_proj/emto/bin/kgrn_mpi.x < Mg_${r}_${v}.dat > kgrn_${r}_${v}.log

        # Check KGRN completion via .prn content
        if [ ! -f Mg_${r}_${v}.prn ] || ! grep -q "Finished at:" Mg_${r}_${v}.prn 2>/dev/null; then
            echo "KGRN failed!"
            exit 1
        else
            echo "DONE!"
        fi

        cd fcd/

        echo "Running KFCD:"
        /home/x_pamca/postdoc_proj/emto/bin/kfcd.exe < Mg_${r}_${v}.dat > kfcd_${r}_${v}.log

        # Check KFCD completion via .prn content
        if [ ! -f Mg_${r}_${v}.prn ] || ! grep -q "Finished at:" Mg_${r}_${v}.prn 2>/dev/null; then
            echo "KFCD failed!"
            exit 1
        else
            echo "DONE!"
        fi

        cd ../
        
    done

done
