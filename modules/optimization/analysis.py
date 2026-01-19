#!/usr/bin/env python3
"""
Analysis functions for EMTO workflow.

Handles EOS fitting, DOS analysis, and report generation.
"""

import subprocess
from pathlib import Path
from typing import Union, List, Dict, Any, Optional, Tuple

from modules.create_input import create_eos_input
from modules.parse import parse_eos_output


def run_eos_fit(
    r_or_v_data: List[float],
    energy_data: List[float],
    output_path: Union[str, Path],
    job_name: str,
    comment: str,
    eos_executable: str,
    eos_type: str = 'MO88'
) -> Tuple[float, Dict[str, Any]]:
    """
    Run EMTO EOS executable and parse results.

    Steps:
    1. Create EOS input file using create_eos_input()
    2. Run EOS executable: subprocess.run(eos_executable + ' < eos.dat')
    3. Parse output using parse_eos_output()
    4. Extract optimal parameter (rwseq)

    Parameters
    ----------
    r_or_v_data : list of float
        R or V values (independent variable)
    energy_data : list of float
        Energy values (dependent variable)
    output_path : str or Path
        Directory where EOS files will be created
    job_name : str
        Job identifier
    comment : str
        Comment for EOS input
    eos_executable : str
        Path to EOS executable
    eos_type : str, optional
        EOS fit type (MO88, POLN, SPLN, MU37, ALL)
        Default: 'MO88'

    Returns
    -------
    tuple of (float, dict)
        optimal_value : Optimal parameter (rwseq) from primary fit
        results : Dictionary of all EOS fit results

    Raises
    ------
    RuntimeError
        If EOS executable fails or parsing fails
    """

    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    eos_input_file = output_path / "eos.dat"
    eos_output_file = output_path / "eos.out"

    print(f"\n{'='*70}")
    print(f"RUNNING EOS FIT")
    print(f"{'='*70}")
    print(f"Type: {eos_type}")
    print(f"Data points: {len(r_or_v_data)}")
    print(f"Output: {output_path}")
    print(f"{'='*70}\n")

    # Step 1: Create EOS input file
    try:
        create_eos_input(
            filename=str(eos_input_file),
            job_name=job_name,
            comment=comment,
            R_or_V_data=r_or_v_data,
            Energy_data=energy_data,
            fit_type=eos_type
        )
    except Exception as e:
        raise RuntimeError(f"Failed to create EOS input: {e}")

    # Step 2: Run EOS executable
    try:
        print(f"Running EOS executable: {eos_executable}")

        with open(eos_input_file, 'r') as f_in:
            with open(eos_output_file, 'w') as f_out:
                result = subprocess.run(
                    [eos_executable],
                    stdin=f_in,
                    stdout=f_out,
                    stderr=subprocess.PIPE,
                    cwd=str(output_path),
                    text=True,
                    timeout=300  # 5 minute timeout
                )

        if result.returncode != 0:
            raise RuntimeError(
                f"EOS executable failed with return code {result.returncode}\n"
                f"stderr: {result.stderr}"
            )

        print(f"✓ EOS executable completed successfully")

    except subprocess.TimeoutExpired:
        raise RuntimeError("EOS executable timed out after 5 minutes")
    except Exception as e:
        raise RuntimeError(f"Failed to run EOS executable: {e}")

    # Step 3: Parse EOS output
    try:
        results = parse_eos_output(str(eos_output_file))

        if not results:
            raise RuntimeError("No results found in EOS output")

        print(f"\nParsed {len(results)} EOS fit(s):")
        for fit_name, params in results.items():
            print(f"  {fit_name}: rwseq = {params.rwseq:.6f}, eeq = {params.eeq:.6f} Ry")

    except Exception as e:
        raise RuntimeError(f"Failed to parse EOS output: {e}")

    # Step 4: Extract optimal parameter from primary fit
    # Priority: morse > birch_murnaghan > murnaghan > polynomial > spline
    if 'morse' in results:
        primary_fit = 'morse'
    elif 'birch_murnaghan' in results:
        primary_fit = 'birch_murnaghan'
    elif 'murnaghan' in results:
        primary_fit = 'murnaghan'
    elif 'polynomial' in results:
        primary_fit = 'polynomial'
    elif 'spline' in results:
        primary_fit = 'spline'
    else:
        raise RuntimeError("No valid EOS fit found in results")

    optimal_value = results[primary_fit].rwseq

    print(f"\n✓ Using {primary_fit} fit: optimal value = {optimal_value:.6f}")
    print(f"{'='*70}\n")

    return optimal_value, results


def generate_dos_analysis(
    phase_path: Union[str, Path],
    file_id: str,
    dos_plot_range: Optional[List[float]] = None
) -> Dict[str, Any]:
    """
    Generate DOS analysis and plots.

    Parameters
    ----------
    phase_path : str or Path
        Path to calculation directory
    file_id : str
        File identifier for DOS files
    dos_plot_range : list of float, optional
        Energy range for DOS plots [E_min, E_max] in eV
        If None, uses default [-0.8, 0.15]

    Returns
    -------
    dict
        Dictionary with DOS analysis results

    Notes
    -----
    Looks for DOS files in phase_path/pot/{file_id}.dos
    Generates plots and saves to phase_path/dos_analysis/
    """
    from modules.dos import DOSParser

    phase_path = Path(phase_path)
    dos_file = phase_path / "pot" / f"{file_id}.dos"

    if not dos_file.exists():
        print(f"Warning: DOS file not found: {dos_file}")
        return {'status': 'not_found', 'file': str(dos_file)}

    print(f"\n{'='*70}")
    print("DOS ANALYSIS")
    print(f"{'='*70}")
    print(f"DOS file: {dos_file}")

    # Create DOS analysis directory
    dos_output_dir = phase_path / "dos_analysis"
    dos_output_dir.mkdir(parents=True, exist_ok=True)

    # Parse DOS
    try:
        parser = DOSParser(str(dos_file))
        print(f"✓ DOS file parsed successfully")
    except Exception as e:
        print(f"✗ Failed to parse DOS file: {e}")
        return {'status': 'parse_error', 'error': str(e)}

    # Get plot range
    if dos_plot_range is None:
        dos_plot_range = [-0.8, 0.15]

    # Generate plots
    try:
        # Total DOS
        total_plot = dos_output_dir / "dos_total.png"
        parser.plot_total(
            spin_polarized=True,
            save=str(total_plot),
            show=False
        )
        print(f"✓ Total DOS plot saved: {total_plot}")

        # Sublattice DOS (if available)
        sublattice_plots = []
        if parser.atom_info:
            # Get unique sublattices
            sublattices = sorted(set(info[2] for info in parser.atom_info))

            for sublat in sublattices:
                sublat_plot = dos_output_dir / f"dos_sublattice_{sublat}.png"
                parser.plot_sublattice(
                    sublattice=sublat,
                    spin_polarized=True,
                    save=str(sublat_plot),
                    show=False
                )
                sublattice_plots.append(str(sublat_plot))
                print(f"✓ Sublattice {sublat} DOS plot saved")

    except Exception as e:
        print(f"Warning: Failed to generate some DOS plots: {e}")

    results = {
        'status': 'success',
        'dos_file': str(dos_file),
        'total_plot': str(total_plot) if 'total_plot' in locals() else None,
        'sublattice_plots': sublattice_plots if 'sublattice_plots' in locals() else [],
        'plot_range': dos_plot_range,
        'atom_info': [
            {'atom_number': num, 'element': elem, 'sublattice': sublat}
            for num, elem, sublat in parser.atom_info
        ]
    }

    print(f"{'='*70}\n")

    return results


def generate_summary_report(
    config: Dict[str, Any],
    base_path: Path,
    results: Dict[str, Any]
) -> str:
    """
    Generate comprehensive summary report of optimization workflow.

    Parameters
    ----------
    config : dict
        Configuration dictionary
    base_path : Path
        Base output directory
    results : dict
        Results dictionary from workflow execution

    Returns
    -------
    str
        Formatted summary report

    Notes
    -----
    Report includes all phases executed and their results.
    Saved to workflow_summary.txt in base_path.
    """
    report = []
    report.append("=" * 80)
    report.append("OPTIMIZATION WORKFLOW SUMMARY")
    report.append("=" * 80)
    report.append(f"\nJob name: {config['job_name']}")
    report.append(f"Output path: {base_path}")
    report.append(f"Run mode: {config.get('run_mode', 'sbatch')}")

    # Configuration
    report.append("\n" + "-" * 80)
    report.append("CONFIGURATION")
    report.append("-" * 80)
    report.append(f"Lattice type: {config.get('lat')}")
    report.append(f"DMAX: {config.get('dmax')}")
    report.append(f"Magnetic: {config.get('magnetic')}")
    report.append(f"EOS type: {config.get('eos_type', 'MO88')}")

    # Phase 1: c/a optimization
    if 'phase1_ca_optimization' in results:
        phase1 = results['phase1_ca_optimization']
        report.append("\n" + "-" * 80)
        report.append("PHASE 1: c/a RATIO OPTIMIZATION")
        report.append("-" * 80)
        report.append(f"Optimal c/a: {phase1['optimal_ca']:.6f}")
        report.append(f"Number of c/a points: {len(phase1['ca_values'])}")
        report.append(f"c/a range: [{min(phase1['ca_values']):.4f}, {max(phase1['ca_values']):.4f}]")
        report.append(f"Energy range: [{min(phase1['energy_values']):.6f}, {max(phase1['energy_values']):.6f}] Ry")

        # EOS fit info
        if 'eos_fits' in phase1:
            for fit_name, params in phase1['eos_fits'].items():
                report.append(f"\n  {fit_name.upper()} fit:")
                report.append(f"    Equilibrium energy: {params['eeq']:.6f} Ry")
                report.append(f"    Bulk modulus: {params['bulk_modulus']:.3f} GPa")

    # Phase 2: SWS optimization
    if 'phase2_sws_optimization' in results:
        phase2 = results['phase2_sws_optimization']
        report.append("\n" + "-" * 80)
        report.append("PHASE 2: SWS OPTIMIZATION")
        report.append("-" * 80)
        report.append(f"Optimal SWS: {phase2['optimal_sws']:.6f} Bohr")
        report.append(f"Number of SWS points: {len(phase2['sws_values'])}")
        report.append(f"SWS range: [{min(phase2['sws_values']):.4f}, {max(phase2['sws_values']):.4f}] Bohr")
        report.append(f"Energy range: [{min(phase2['energy_values']):.6f}, {max(phase2['energy_values']):.6f}] Ry")

        # Derived parameters
        if 'derived_parameters' in phase2:
            params = phase2['derived_parameters']
            report.append("\n  Derived lattice parameters:")
            report.append(f"    a = {params['a_angstrom']:.6f} Å")
            report.append(f"    c = {params['c_angstrom']:.6f} Å")
            report.append(f"    c/a = {params['optimal_ca']:.6f}")
            report.append(f"    Volume = {params['total_volume_angstrom3']:.6f} Å³")
            report.append(f"    Lattice: {params['lattice_name']} (type {params['lattice_type']})")

    # Phase 3: Optimized calculation
    if 'phase3_optimized_calculation' in results:
        phase3 = results['phase3_optimized_calculation']
        report.append("\n" + "-" * 80)
        report.append("PHASE 3: OPTIMIZED STRUCTURE CALCULATION")
        report.append("-" * 80)
        report.append(f"Optimal c/a: {phase3['optimal_ca']:.6f}")
        report.append(f"Optimal SWS: {phase3['optimal_sws']:.6f} Bohr")
        report.append(f"KFCD total energy: {phase3['kfcd_total_energy']:.6f} Ry")

        if phase3['kgrn_total_energy'] is not None:
            report.append(f"KGRN total energy: {phase3['kgrn_total_energy']:.6f} Ry")

        if phase3.get('total_magnetic_moment') is not None:
            report.append(f"Total magnetic moment: {phase3['total_magnetic_moment']:.4f} μB")

        if phase3.get('magnetic_moments'):
            report.append("\n  Magnetic moments:")
            for site, moment in phase3['magnetic_moments'].items():
                report.append(f"    {site}: {moment:.4f} μB")

    # DOS analysis
    if 'dos_analysis' in results:
        dos = results['dos_analysis']
        if dos.get('status') == 'success':
            report.append("\n" + "-" * 80)
            report.append("DOS ANALYSIS")
            report.append("-" * 80)
            report.append(f"DOS plots generated: {len(dos.get('sublattice_plots', [])) + 1}")
            report.append(f"Plot range: {dos.get('plot_range')} eV")

    report.append("\n" + "=" * 80)
    report.append("END OF REPORT")
    report.append("=" * 80)

    # Save report
    report_text = "\n".join(report)
    report_file = base_path / "workflow_summary.txt"
    with open(report_file, 'w') as f:
        f.write(report_text)

    print(f"\n✓ Summary report saved to: {report_file}\n")

    return report_text
