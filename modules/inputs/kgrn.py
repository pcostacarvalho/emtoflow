import os

def create_kgrn_input(structure, path, id_namev, id_namer, SWS):
    """
    Create a KGRN (self-consistent KKR) input file for EMTO from structure dict.

    Supports both ordered structures (CIF) and random alloys (CPA).

    Parameters
    ----------
    structure : dict
        Structure dictionary from parse_emto_structure() or create_alloy_structure()
        containing atom_info and is_alloy flag
    path : str
        Output directory path
    id_namev : str
        Full job ID with volume (e.g., 'fept_0.96_2.65')
    id_namer : str
        Job ID with ratio only (e.g., 'fept_0.96')
    SWS : float
        Wigner-Seitz radius

    Notes
    -----
    For ordered structures (CIF, is_alloy=False):
    - Each atom has ITA=1, CONC=1.0
    - Different sites have different IQ values
    - No magnetic disorder (single configuration)

    For random alloys (CPA, is_alloy=True):
    - All atoms on same site: IQ=1 for all
    - Different components: IT=ITA=1,2,3...
    - Concentrations sum to 1.0
    - Magnetic disorder via CPA

    The atom section format is:
    Symb  IQ  IT ITA NRM  CONC      a_scr b_scr |Teta    Phi    FXM  m(split)
    """

    lat = structure['lat']
    is_alloy = structure.get('is_alloy', False)

    # Build atom section dynamically from structure
    atom_lines = []

    if is_alloy:
        # CPA alloy: all atoms have IQ=1, IT=ITA increment (1,2,3...)
        # The structure dict from create_alloy_structure() already has correct IT/ITA
        for atom in structure['atom_info']:
            line = (f"{atom['symbol']:<5} {atom['IQ']:>2} {atom['IT']:>3} {atom['ITA']:>3} "
                    f"{1:>3}  {atom['conc']:.6f}  {atom['a_scr']:.3f} {atom['b_scr']:.3f}  "
                    f"0.0000  0.0000  N  {atom['default_moment']:>7.4f}")
            atom_lines.append(line)
    else:
        # Ordered structure (CIF): use IT/ITA from structure dict
        for atom in structure['atom_info']:
            line = (f"{atom['symbol']:<5} {atom['IQ']:>2} {atom['IT']:>3} {atom['ITA']:>3} "
                    f"{1:>3}  {atom['conc']:.6f}  {atom['a_scr']:.3f} {atom['b_scr']:.3f}  "
                    f"0.0000  0.0000  N  {atom['default_moment']:>7.4f}")
            atom_lines.append(line)

    atoms_section = "\n".join(atom_lines)

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
KMSH...= S IBZ..={lat:>3} NKX..= 21 NKY..= 21 NKZ..= 21 FBZ..=  N
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
{atoms_section}
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
