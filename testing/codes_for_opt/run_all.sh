#! /bin/bash -l

for i in 0.91  0.93  0.95  0.97  0.99  1.01  1.03; do 
    cd $i
    chmod +x run_fept_$i.sh
    sbatch run_fept_$i.sh
    cd ..
done
