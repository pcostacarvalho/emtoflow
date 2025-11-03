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