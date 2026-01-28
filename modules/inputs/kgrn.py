
def create_kgrn_input(structure, path, id_full, id_ratio, SWS, magnetic, nkx, nky, nkz, depth=1.100, efmix=0.900, tolcpa=1e-06, tolef=1e-08, efgs=0.000, hx=0.101, nx=5, amix=0.010, vmix=0.70, imagz=0.005, eps=0.200, nz0=16):
    """
    Create a KGRN (self-consistent KKR) input file for EMTO from structure dict.

    Supports both ordered structures and random alloys (CPA).

    Parameters
    ----------
    structure : dict
        Structure dictionary from create_emto_structure()
        containing atom_info with IQ, IT, ITA, conc for each atom
    path : str
        Output directory path
    id_full : str
        Full job ID with volume (e.g., 'fept_0.96_2.65')
    id_ratio : str
        Job ID with ratio only (e.g., 'fept_0.96')
    SWS : float
        Wigner-Seitz radius
    magnetic : str
        'P' for paramagnetic or 'F' for ferromagnetic
    kpoints : list of lists, optional
        Custom k-points in format [[kx, ky, kz], ...] or [[kx, ky, kz, weight], ...]
        If provided, uses explicit k-points instead of automatic mesh.
        Default: None (uses automatic Monkhorst-Pack mesh)
    nkx : int, optional
        K-mesh divisions along x-axis (default: 21, ignored if kpoints provided)
    nky : int, optional
        K-mesh divisions along y-axis (default: 21, ignored if kpoints provided)
    nkz : int, optional
        K-mesh divisions along z-axis (default: 21, ignored if kpoints provided)
    depth : float, optional
        DEPTH parameter for KGRN (default: 1.100)
    efmix : float, optional
        EFMIX parameter for KGRN (default: 0.900)
    tolcpa : float, optional
        TOLCPA parameter for KGRN in Fortran scientific notation (default: 1e-06 = 1.d-06)
    tolef : float, optional
        TOLEF parameter for KGRN in Fortran scientific notation (default: 1e-08 = 1.d-08)
    efgs : float, optional
        EFGS parameter for KGRN (default: 0.000)
    hx : float, optional
        HX parameter for KGRN (default: 0.101)
    nx : int, optional
        NX parameter for KGRN (default: 5)
    amix : float, optional
        AMIX parameter for KGRN (default: 0.010)
    vmix : float, optional
        VMIX parameter for KGRN (default: 0.70)
    imagz : float, optional
        IMAGZ parameter for KGRN (default: 0.005)
    eps : float, optional
        EPS parameter for KGRN (default: 0.200)
    nz0 : int, optional
        NZ0 parameter for KGRN (default: 16)

    Notes
    -----
    The structure_builder module automatically sets correct values:

    For ordered structures (L10, L12, pure elements):
    - Each distinct site has unique IQ (1, 2, 3, ...)
    - Each site has ITA=1, CONC=1.0
    - IT determined from symmetry

    For random alloys (CPA - Fe-Pt 50-50, ternary alloys):
    - All atoms on same site have same IQ (typically 1)
    - Different components have ITA=1,2,3...
    - Concentrations sum to 1.0 per site
    - IT determined from symmetry

    The atom section format is:
    Symb  IQ  IT ITA NRM  CONC      a_scr b_scr |Teta    Phi    FXM  m(split)
    """

    lat = structure['lat']

    # Format tolerance values in Fortran scientific notation (e.g., 1.d-08)
    def format_fortran_sci(value):
        """Convert scientific notation to Fortran format (1.d-XX)"""
        if value == 0:
            return "0.d+00"
        # Convert to scientific notation
        exp = int(f"{value:.2e}".split('e')[1])
        return f"1.d{exp:+03d}"

    tolef_str = format_fortran_sci(tolef)
    tolcpa_str = format_fortran_sci(tolcpa)

    # Build atom section dynamically from structure
    # Works for both ordered structures (CIF) and random alloys (CPA)
    # The structure_builder module sets correct IQ, IT, ITA, and conc values
    atom_lines = []
    for atom in structure['atom_info']:
        line = (f"{atom['symbol']:<5} {atom['IQ']:>2} {atom['IT']:>3} {atom['ITA']:>3} "
                f"{1:>3}  {atom['conc']:.6f}  {atom['a_scr']:.3f} {atom['b_scr']:.3f}  "
                f"0.0000  0.0000  N  {atom['default_moment']:>7.4f}")
        atom_lines.append(line)

    atoms_section = "\n".join(atom_lines)

    template = f"""KGRN      HP..= 0   !                              xx xxx xx
JOBNAM...={id_full}
MSGL.=1 STRT.=A FUNC.=SCA EXPAN=1 FCD.=Y GPM.=N FSM.=N
FOR001=./smx/{id_ratio}.tfh
FOR002=./smx/{id_ratio}.mdl
DIR003=./pot/
DIR006=
DIR010=./chd/
DIR011=./tmp
DIR021={id_full}.gpm.dat
DIR022=./shp/{id_ratio}.shp
FOR098=/home/x_pamca/postdoc_proj/emto/jij_EMTO/kgrn_new2020/ATOM.cfg
Self-consistent KKR calculation
**********************************************************************
SCFP:  information for self-consistency procedure:                   *
**********************************************************************
NITER.= 99 NLIN.= 31 NCPA.=  7 NPRN....=000000000
FRC...=  N DOS..=  Y OPS..=  N AFM..=  {magnetic:>1} CRT..=  M STMP..= A
Lmaxh.=  8 Lmaxt=  4 NFI..= 31 FIXG.=  2 SHF..=  0 SOFC.=  Y
KMSH...= S IBZ..={lat:>3} NKX..={nkx:>3} NKY..={nky:>3} NKZ..={nkz:>3} FBZ..=  N
ZMSH...= E NZ1..= 16 NZ2..= 16 NZ3..= 16 NRES.=  4 NZD..=999
DEPTH..= {depth:>6.3f} IMAGZ.= {imagz:>6.3f} EPS...= {eps:>6.3f} ELIM..= -1.000
AMIX...= {amix:>6.3f} VMIX..= {vmix:>6.2f} EFMIX.= {efmix:>6.3f} VMTZ..=  0.000
TOLE...= 1.d-07 TOLEF.= {tolef_str} TOLCPA= {tolcpa_str} TFERMI=  300.0 (K)
SWS....= {SWS:>6.3f} MMOM..=  0.000
EFGS...= {efgs:>6.3f} HX....= {hx:>6.3f} NX...={nx:>3} NZ0..={nz0:>3} KPOLE=  0
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

    with open(f"{path}/{id_full}.dat", "w") as f:
        f.write(template)

    print(f"KGRN input file '{path}/{id_full}.dat' created successfully.")
