import numpy as np
import os

#######################################################################################

def create_kstr_input(path, id_name, DMAX, LAT, NL, NQ3,
    A, B, C, lattice_vectors, lattice_positions):
    """
    Create a KSTR input file for EMTO.

    Parameters
    ----------
    filename : str
        Name of the output .smx file (e.g., 'fept.smx').
    job_name : str
        The JOBNAM (e.g., 'fept').
    NL : int
        Number of layers.
    NQ3 : int
        Value for NQ3 parameter.
    A, B, C : float
        Lattice constants.
    lattice_vectors : list[list[float]]
        3x3 matrix for lattice vectors.
    lattice_positions : list[list[float]]
        List of atomic positions.
    """

    template = f"""KSTR      HP......=N                               xx xxx xx
JOBNAM...={id_name:<10} MSGL.=  1 MODE...=B STORE..=Y HIGH...=Y
DIR001=./
DIR006=
Slope and Madelung matrices
NL.....= {NL:>1} NLH...= 9 NLW...= 9 NDER..= 6 ITRANS= 3 NPRN..= 1
(K*W)^2..=   0.00000 DMAX....=    {DMAX:>6} RWATS...=      0.10
NQ3...= {NQ3:>2} LAT...= {LAT:>1} IPRIM.= 0 NGHBP.=13 NQR2..= 0        80
A........= {A:.7f} B.......= {B:.7f} C.......={C:.8f}
"""

    # Add lattice vectors
    for vec in lattice_vectors:
        template += f"{vec[0]:.8f}\t{vec[1]:.8f}\t{vec[2]:.8f}\n"

    # Add lattice positions
    for pos in lattice_positions:
        template += f"\t{pos[0]:.8f}\t{pos[1]:.8f}\t{pos[2]:.8f}\n"

    # Append fixed section
    for i in range(NQ3):
        template += f"a/w......= 0.70 0.70 0.70 0.70\n"

    template += f"""NL_mdl.= {2*NL + 1}
LAMDA....=    2.5000 AMAX....=    4.5000 BMAX....=    4.5000
"""
    
    with open(f"{path}/smx/{id_name}.dat", "w") as f:
        f.write(template)

    print(f"KSTR input file '{path}/smx/{id_name}.dat' created successfully.")

#######################################################################################

def create_shape_input(path, id_name, NQ3):
    """
    Create a SHAPE input file for EMTO.

    Parameters
    ----------
    filename : str
        Name of the output SHAPE file (e.g., 'fept.dat').
    job_name : str
        The JOBNAM (e.g., 'fept').
    smx_file : str
        Path to the .tfh file (e.g., '../smx/fept.tfh').
    NQ3 : int
        Number of atoms (determines number of ASR lines).
    """

    template = f"""SHAPE     HP......=N
JOBNAM...={id_name:<10} MSGL.=  1
FOR001=../smx/{id_name}.tfh
DIR002=./
DIR006=./
Lmax..= 30 NSR..=129 NFI..= 11
NPRN..=  0 IVEF.=  3
****** Relative atomic sphere radii ASR(1:NQ) ******
"""

    # Add ASR lines based on NQ3
    for i in range(1, NQ3 + 1):
        template += f"ASR({i}).= 1.0\n"

    with open(f"{path}/shp/{id_name}.dat", "w") as f:
        f.write(template)

    print(f"SHAPE input file '{path}/shp/{id_name}.dat' created successfully.")

#######################################################################################

def create_kgrn_input(path, id_namev, id_namer, SWS):
    """
    Create a KGRN (self-consistent KKR) input file for EMTO.

    Parameters
    ----------
    filename : str
        Name of the output file (e.g., 'fept_kstr.dat').
    job_name : str
        The job name (e.g., 'fept').
    smx_tfh_file : str
        Path to the .tfh file (e.g., './smx/fept.tfh').
    smx_mdl_file : str
        Path to the .mdl file (e.g., './smx/fept.mdl').
    shp_file : str
        Path to the .shp file (e.g., './shp/fept.shp').
    atoms_info : list of dict
        List of atom information dictionaries with keys:
        'symbol', 'IQ', 'IT', 'ITA', 'NRM', 'conc', 'a_scr', 'b_scr',
        'theta', 'phi', 'FXM', 'm_split'
    """

    template = f"""KGRN      HP..= 0   !                              xx xxx xx
JOBNAM...={id_namev}
MSGL.=1 STRT.=A FUNC.=SCA EXPAN=1 FCD.=Y GPM.=N FSM.=N
FOR001=./smx/{id_namer}.tfh
FOR002=./smx/{id_namer}.mdl
DIR003=./pot/
DIR006=
DIR010=./chd/
DIR011=./tmp
DIR021={id_namev}.gpm.dat
DIR022=./shp/{id_namer}.shp
FOR098=/home/x_pamca/postdoc_proj/emto/jij_EMTO/kgrn_new2020/ATOM.cfg
Self-consistent KKR calculation 
**********************************************************************
SCFP:  information for self-consistency procedure:                   *
**********************************************************************
NITER.= 99 NLIN.= 31 NCPA.=  7 NPRN....=000000000
FRC...=  N DOS..=  Y OPS..=  N AFM..=  F CRT..=  M STMP..= A
Lmaxh.=  8 Lmaxt=  4 NFI..= 31 FIXG.=  2 SHF..=  0 SOFC.=  Y
KMSH...= S IBZ..=  5 NKX..= 12 NKY..= 12 NKZ..= 12 FBZ..=  N
ZMSH...= E NZ1..= 16 NZ2..= 16 NZ3..= 16 NRES.=  4 NZD..=999
DEPTH..=  1.100 IMAGZ.=  0.005 EPS...=  0.200 ELIM..= -1.000
AMIX...=  0.010 VMIX..=   0.70 EFMIX.=  0.900 VMTZ..=  0.000
TOLE...= 1.d-07 TOLEF.= 1.d-06 TOLCPA= 1.d-06 TFERMI=  300.0 (K)
SWS....= {SWS:>6.2f} MMOM..=  0.000
EFGS...=  0.000 HX....=  0.101 NX...=  5 NZ0..= 16 KPOLE=  0
**********************************************************************
Sort:  information for alloy:                                        *
******************************SS-screeining*|***Magnetic structure ***
Symb  IQ  IT ITA NRM  CONC      a_scr b_scr |Teta    Phi    FXM  m(split)
Pt     1   1   1   1  0.500000  0.750 1.100  0.0000  0.0000  N   0.4000
Pt     2   1   1   1  0.500000  0.750 1.100  0.0000  0.0000  N   0.4000
Fe     3   2   1   1  0.500000  0.750 1.100  0.0000  0.0000  N   2.0000
Fe     4   2   1   1  0.500000  0.750 1.100  0.0000  0.0000  N   2.0000
Pt     1   1   2   1  0.500000  0.750 1.100  0.0000  0.0000  N  -0.4000
Pt     2   1   2   1  0.500000  0.750 1.100  0.0000  0.0000  N  -0.4000
Fe     3   2   2   1  0.500000  0.750 1.100  0.0000  0.0000  N  -2.0000
Fe     4   2   2   1  0.500000  0.750 1.100  0.0000  0.0000  N  -2.0000
**********************************************************************
Spin-spiral wave vector:
qx....= 0.000000 qy....= 0.000000 qz....= 0.000000
**********************************************************************
Atom:  information for atomic calculation:                           *
**********************************************************************
IEX...=  4 NES..= 15 NITER= 50 IWAT.=  0 NPRNA=  0
VMIXATM..=  0.300000 RWAT....=  3.500000 RMAX....= 20.000000
DX.......=  0.030000 DR1.....=  0.001000 TEST....=  1.00E-12
TESTE....=  1.00E-07 TESTY...=  1.00E-08 TESTV...=  1.00E-07
"""

    with open(f"{path}/{id_namev}.dat", "w") as f:
        f.write(template)

    print(f"KGRN input file '{path}/{id_namev}.dat' created successfully.")

#######################################################################################

def create_kfcd_input(path, id_namer, id_namev):
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

    template = f"""KFCD      HP......=N sno..=100                     xx xxx xx
JOBNAM...={id_namev:<10}                         MSGL.=  1
STRNAM...={id_namer}
DIR001=../smx/
DIR002=../chd/
FOR003=../shp/{id_namer}.shp
DIR004=../smx/
DIR006=
Lmaxs.= 30 NTH..= 41 NFI..= 81
OVCOR.=  Y UBG..=  N NPRN.=  0 NRM..=  0
"""

    with open(f"{path}/fcd/{id_namev}.dat", "w") as f:
        f.write(template)

    print(f"KFCD input file '{path}/fcd/{id_namev}.dat' created successfully.")

#######################################################################################

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


def create_eos_input(
    filename,
    job_name,
    comment,
    R_or_V_data,
    Energy_data,
):
    """
    Create an FCD input file for EMTO.

    Parameters
    ----------
    filename : str
        Name of the output file (e.g., 'cr50.dat').
    job_name : str
        The job name (e.g., 'cr50').
    comment : str
        Comment line describing the calculation.
    R_or_V_data : list of float
        List of R or V values (first column).
    Energy_data : list of float
        List of energy values (second column).
    """

    # Validate input lengths match
    if len(R_or_V_data) != len(Energy_data):
        raise ValueError("R_or_V_data and Energy_data must have the same length")

    N_of_Rws = len(R_or_V_data)

    template = f"""DIR_NAME.=
JOB_NAME.={job_name}
COMMENT..: {comment}
FIT_TYPE.=ALL          ! Use MO88, MU37, POLN, SPLN, ALL
N_of_Rws..= {N_of_Rws:2d}  Natm_in_uc..=   1 Polinoms_order..=  3 N_spline..=  5
R_or_V....=  R  R_or_V_in...= au. Energy_units....= Ry
"""

    # Add data lines
    for r_or_v, energy in zip(R_or_V_data, Energy_data):
        template += f"  {r_or_v:.6f}     {energy:.6f}  1\n"

    template += """PLOT.....=N
X_axis...=P X_min..=  -100.000 X_max..=  2000.000 N_Xpts.=  40
Y_axes...=V H
"""

    with open(filename, "w") as f:
        f.write(template)

    print(f"EOS input file '{filename}' created successfully.")



def create_inputs(params):

    path=params["path"]
    ratios=params["ratios"]
    name_id=params["name_id"]
    sws=params["sws"]
    NL=params["NL"]
    NQ3=params["NQ3"]
    B=params["B"]
    DMAX=params["DMAX"]
    LAT=params["LAT"]
    fractional_coors=params["fractional_coors"]

    # Subfolders to create inside each ratio folder
    subfolders = ['smx', 'shp', 'pot', 'chd', 'fcd']

    os.makedirs(path, exist_ok=True)

    for subfolder in subfolders:
        subfolder_path = os.path.join(path, subfolder)
        os.makedirs(subfolder_path, exist_ok=True)

    for r in ratios:
        lattice_vectors =  np.array([[1.0,  0.0, 0.0], [0.0,  1.0, 0.0], [0.0,  0.0, r]])
        cart_coords = fractional_coors @ lattice_vectors
        filer=f"{name_id}_{r:.2f}"

        create_kstr_input(
            path=path,
            id_name=f"{filer}",
            NL=NL, NQ3=NQ3,
            A=1, B=B, C=r,
            DMAX=DMAX, LAT=LAT,
            lattice_vectors=lattice_vectors,
            lattice_positions=cart_coords)

        create_shape_input(path=path, id_name=f"{filer}",NQ3=NQ3)

        for v in sws:
            filev=filer+f"_{v:.2f}"
        
            create_kgrn_input(path=path, id_namev=f"{filev}", id_namer=f"{filer}" ,SWS=v)

            create_kfcd_input(path=path, id_namev=f"{filev}", id_namer=f"{filer}")

    

    #         if len(sws) == 1:
                
    #             create_job_ca(
    #             folder=f"{filev}",
    #             filename=f"{path}/run_{filev}.sh")
        

    # if len(sws) > 1:
        
    #     create_job_volume(
    #     name=f"{name_id}",
    #     filename=f"run_{name_id}.sh",
    #     volumes=" ".join([f"{j:.2f}" for j in sws]))


def write_serial_sbatch(path,ratios, volumes, job_name, prcs=1, time="00:30:00", account="naiss2025-1-38", id_name="fept"):
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

id_name="{id_name}"

for r in {ratios_str}; do

    echo "c/a ratio: $r"

    cd smx

    echo "Running KSTR:"
    kstr.exe < ${{id_name}}_${{r}}.dat > smx_${{r}}.log

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
    shape.exe < ${{id_name}}_${{r}}.dat > shp_${{r}}.log

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
        mpirun -n {prcs}  kgrn_mpi.x < {id_name}_${{r}}_${{v}}.dat > kgrn_${{r}}_${{v}}.log

        if [ $? -ne 0 ]; then
            echo "KGRN failed!"
            exit 1
        else
            echo "DONE!"
        fi

        cd fcd/ 

        echo "Running KFCD:"
        kfcd.exe < {id_name}_${{r}}_${{v}}.dat > kfcd_${{r}}_${{v}}.log

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


def write_parallel_sbatch(path, ratios, volumes, job_name, prcs=1, time="00:30:00", account="naiss2025-1-38", id_name="fept"):
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

id_name="{id_name}"
r={r_fmt}

cd smx

echo "Running KSTR:"
kstr.exe < ${{id_name}}_${{r}}.dat > smx_${{r}}.log

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
shape.exe < ${{id_name}}_${{r}}.dat > shp_${{r}}.log

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

id_name="{id_name}"
r={r_fmt}
v={v_fmt}

echo "Running KGRN:"
mpirun -n {prcs} kgrn_mpi.x < {id_name}_${{r}}_${{v}}.dat > kgrn_${{r}}_${{v}}.log

if [ $? -ne 0 ]; then
    echo "KGRN failed!"
    exit 1
else
    echo "DONE!"
fi

cd fcd/ 

echo "Running KFCD:"
kfcd.exe < {id_name}_${{r}}_${{v}}.dat > kfcd_${{r}}_${{v}}.log

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