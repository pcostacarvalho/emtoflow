import os

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