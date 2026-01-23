#!/usr/bin/env python3
"""
Analysis functions for EMTO workflow.

Handles EOS fitting, DOS analysis, and report generation.
"""

import subprocess
import os
from pathlib import Path
from typing import Union, List, Dict, Any, Optional, Tuple
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for headless environments
import matplotlib.pyplot as plt

from modules.inputs.eos_emto import create_eos_input
from modules.inputs.eos_emto import parse_eos_output, morse_energy


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
    # Note: the authoritative EOS results are written by eos.exe to
    # `filename_eos_results` (derived from JOB_NAME in the eos.dat input).
    # We still capture stdout to a separate file for debugging/logging.
    eos_stdout_file = output_path / "eos.out"

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
            with open(eos_stdout_file, 'w') as f_out:
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
    filename_eos_results = output_path / f"{job_name}.out"
    if not filename_eos_results.exists():
        raise RuntimeError(
            "EOS executable completed but did not produce the expected results file.\n"
            f"Expected: {filename_eos_results}\n"
            f"Stdout log: {eos_stdout_file}"
        )
    try:
        results = parse_eos_output(filename_eos_results)

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


def plot_eos_fit(
    eos_output_file: Union[str, Path],
    output_path: Union[str, Path],
    variable_name: str = 'R',
    variable_units: str = 'au',
    title: Optional[str] = None,
    eos_type: str = 'morse'
) -> Dict[str, Any]:
    """
    Generate EOS fit plot from EMTO EOS output.

    Creates a plot showing:
    - DFT data points (black circles)
    - Fitted curve (blue line)
    - Vertical line at optimal value (gray dashed)
    - Grid and labels

    Parameters
    ----------
    eos_output_file : str or Path
        Path to EOS results file written by `eos.exe` (e.g., '<job_name>.out')
    output_path : str or Path
        Directory where plot will be saved
    variable_name : str, optional
        Name of the independent variable (e.g., 'c/a', 'R_WS', 'V')
        Default: 'R'
    variable_units : str, optional
        Units of the independent variable (e.g., 'au', 'Bohr', 'Å³')
        Default: 'au'
    title : str, optional
        Plot title. If None, auto-generates based on EOS type
    eos_type : str, optional
        Which EOS fit to plot: 'morse', 'polynomial', 'birch_murnaghan',
        'murnaghan', 'spline'. Default: 'morse'

    Returns
    -------
    dict
        Dictionary with plot information:
        - 'plot_file': Path to saved plot
        - 'optimal_value': Optimal parameter from fit
        - 'equilibrium_energy': Equilibrium energy
        - 'eos_type': Type of EOS used

    Raises
    ------
    FileNotFoundError
        If EOS output file doesn't exist
    ValueError
        If requested EOS type not found in output
    RuntimeError
        If plotting fails

    Notes
    -----
    Based on the plotting code from files/codes_for_opt/pm_parse_percentages.ipynb
    Supports all EMTO EOS fit types.

    Examples
    --------
    >>> # Plot c/a optimization
    >>> plot_eos_fit(
    ...     'phase1_ca_optimization/myjob_ca.out',
    ...     'phase1_ca_optimization',
    ...     variable_name='c/a',
    ...     variable_units='',
    ...     title='c/a Ratio Optimization'
    ... )

    >>> # Plot SWS optimization
    >>> plot_eos_fit(
    ...     'phase2_sws_optimization/myjob_sws.out',
    ...     'phase2_sws_optimization',
    ...     variable_name='R_WS',
    ...     variable_units='Bohr',
    ...     title='Wigner-Seitz Radius Optimization'
    ... )
    """
    eos_output_file = Path(eos_output_file)
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    if not eos_output_file.exists():
        raise FileNotFoundError(f"EOS output file not found: {eos_output_file}")

    print(f"\n{'='*70}")
    print("GENERATING EOS PLOT")
    print(f"{'='*70}")
    print(f"Output file: {eos_output_file}")
    print(f"EOS type: {eos_type}")

    # Parse EOS output
    try:
        results = parse_eos_output(str(eos_output_file))
    except Exception as e:
        raise RuntimeError(f"Failed to parse EOS output: {e}")

    if not results:
        raise RuntimeError("No EOS fits found in output file")

    if eos_type not in results:
        available = ', '.join(results.keys())
        raise ValueError(
            f"EOS type '{eos_type}' not found in output. Available: {available}"
        )

    # Get the requested EOS fit
    eos_fit = results[eos_type]

    if not eos_fit.data_points:
        raise RuntimeError(f"No data points found for {eos_type} fit")

    # Extract data points
    r_data = [p.r for p in eos_fit.data_points]
    etot_data = [p.etot for p in eos_fit.data_points]
    efit_data = [p.efit for p in eos_fit.data_points]

    # Generate smooth curve for plotting
    r_min = min(r_data)
    r_max = max(r_data)
    r_smooth = np.linspace(r_min * 0.95, r_max * 1.05, 200)

    # Calculate smooth fitted curve based on EOS type
    if eos_type == 'morse':
        # Use Morse equation
        if not eos_fit.additional_params:
            raise RuntimeError("Morse parameters not found in EOS fit")

        a = eos_fit.additional_params['a']
        b = eos_fit.additional_params['b']
        c = eos_fit.additional_params['c']
        lambda_param = eos_fit.additional_params['lambda']

        # Calculate relative energies and find offset
        e_relative_data = [morse_energy(r, a, b, c, lambda_param) for r in r_data]
        offset = efit_data[0] - e_relative_data[0]

        # Generate smooth curve
        e_smooth = np.array([morse_energy(r, a, b, c, lambda_param) + offset
                             for r in r_smooth])

    else:
        # For other EOS types, use the efit values directly
        # Interpolate for smooth curve
        e_smooth = np.interp(r_smooth, r_data, efit_data)

    # Create plot
    plt.rcParams.update({'font.size': 12})
    fig, ax = plt.subplots(1, 1, figsize=(8, 6))

    # Plot data points and fitted curve
    ax.plot(r_data, etot_data, 'ko', markersize=8, label='DFT Data', zorder=5)
    ax.plot(r_smooth, e_smooth, 'b-', linewidth=2,
            label=f'{eos_fit.eos_type}', zorder=3, alpha=0.8)

    # Mark optimal value
    ax.axvline(eos_fit.rwseq, color='gray', linestyle='--', alpha=0.5,
               label=f'Optimal = {eos_fit.rwseq:.4f} {variable_units}')

    # Labels and formatting
    if variable_units:
        xlabel = f'{variable_name} ({variable_units})'
    else:
        xlabel = variable_name
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel('Total Energy (Ry)', fontsize=12)

    if title is None:
        title = f'Equation of State: {eos_fit.eos_type}'
    ax.set_title(title, fontsize=13, fontweight='bold')

    ax.legend(fontsize=10, loc='best')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    # Save plot
    plot_file = output_path / f"eos_plot_{eos_type}.png"
    plt.savefig(plot_file, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"✓ EOS plot saved: {plot_file}")
    print(f"  Optimal value: {eos_fit.rwseq:.6f} {variable_units}")
    print(f"  Equilibrium energy: {eos_fit.eeq:.6f} Ry")
    print(f"  Bulk modulus: {eos_fit.bmod:.2f} kBar")
    print(f"{'='*70}\n")

    return {
        'plot_file': str(plot_file),
        'optimal_value': eos_fit.rwseq,
        'equilibrium_energy': eos_fit.eeq,
        'bulk_modulus': eos_fit.bmod,
        'eos_type': eos_type
    }


def generate_dos_analysis(
    phase_path: Union[str, Path],
    file_id: str,
    dos_plot_range: Optional[List[float]] = None,
    dos_ylim: Optional[List[float]] = None
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
        Energy range for DOS plots [E_min, E_max] in Ry
        If None, uses default [-0.8, 0.15]
    dos_ylim : list of float, optional
        DOS range (y-axis) for plots [DOS_min, DOS_max] in states/Ry
        If None, y-axis range is auto-scaled

    Returns
    -------
    dict
        Dictionary with DOS analysis results

    Notes
    -----
    Looks for DOS files in phase_path/{file_id}.dos
    Generates plots and saves to phase_path/dos_analysis/
    """
    from modules.dos import DOSParser, DOSPlotter

    phase_path = Path(phase_path)
    dos_file = phase_path / f"{file_id}.dos"

    if not dos_file.exists():
        # List available DOS files for debugging
        dos_files = list(phase_path.glob("*.dos"))
        print(f"Warning: DOS file not found: {dos_file}")
        if dos_files:
            print(f"  Found {len(dos_files)} DOS file(s) in phase directory:")
            for f in dos_files:
                print(f"    - {f}")
        return {'status': 'not_found', 'file': str(dos_file)}

    print(f"\n{'='*70}")
    print("DOS ANALYSIS")
    print(f"{'='*70}")
    print(f"DOS file: {dos_file}")
    print(f"DOS file exists: {dos_file.exists()}")
    if dos_file.exists():
        print(f"DOS file size: {dos_file.stat().st_size} bytes")

    # Create DOS analysis directory
    dos_output_dir = phase_path / "dos_analysis"
    dos_output_dir.mkdir(parents=True, exist_ok=True)
    print(f"DOS output directory: {dos_output_dir}")
    print(f"DOS output directory exists: {dos_output_dir.exists()}")
    print(f"DOS output directory is writable: {os.access(dos_output_dir, os.W_OK)}")

    # Parse DOS
    try:
        parser = DOSParser(str(dos_file))
        print(f"✓ DOS file parsed successfully")
        print(f"  Atom info count: {len(parser.atom_info)}")
        print(f"  Has total_down: {parser.data.get('total_down') is not None}")
        print(f"  Has total_up: {parser.data.get('total_up') is not None}")
    except Exception as e:
        import traceback
        print(f"✗ Failed to parse DOS file: {e}")
        traceback.print_exc()
        return {'status': 'parse_error', 'error': str(e)}

    # Get plot ranges
    if dos_plot_range is None:
        dos_plot_range = [-0.8, 0.15]
    if len(dos_plot_range) != 2:
        raise ValueError(f"dos_plot_range must be [E_min, E_max], got: {dos_plot_range}")
    
    # Convert to tuple for plotting methods
    xlim = tuple(dos_plot_range)
    ylim = tuple(dos_ylim) if dos_ylim is not None and len(dos_ylim) == 2 else None
    if dos_ylim is not None and len(dos_ylim) != 2:
        raise ValueError(f"dos_ylim must be [DOS_min, DOS_max], got: {dos_ylim}")

    # Generate plots
    total_plot = None
    sublattice_plots = []
    
    try:
        plotter = DOSPlotter(parser)
        print(f"✓ DOSPlotter created successfully")

        # Total DOS
        total_plot = dos_output_dir / "dos_total.png"
        print(f"Attempting to create total DOS plot: {total_plot}")
        print(f"  Output directory exists: {dos_output_dir.exists()}")
        print(f"  Output directory is writable: {os.access(dos_output_dir, os.W_OK)}")
        
        fig, ax = plotter.plot_total(
            spin_polarized=True,
            save=None,
            show=False,
            xlim=xlim,
            ylim=ylim,
        )
        print(f"✓ plot_total() returned figure and axes")
        print(f"  Setting xlim to: {xlim}")
        if ylim is not None:
            print(f"  Setting ylim to: {ylim}")
        
        print(f"  Calling fig.savefig({total_plot})...")
        fig.savefig(total_plot, dpi=300, bbox_inches='tight')
        plt.close(fig)
        print(f"  savefig() completed, figure closed")
        
        # Verify file was actually created
        if total_plot.exists():
            file_size = total_plot.stat().st_size
            print(f"✓ Total DOS plot saved: {total_plot} ({file_size} bytes)")
        else:
            raise RuntimeError(f"Failed to save total DOS plot: {total_plot} (file does not exist after savefig)")

        # Sublattice DOS (if available)
        if parser.atom_info:
            # Get unique sublattices
            sublattices = sorted(set(info[2] for info in parser.atom_info))

            for sublat in sublattices:
                sublat_plot = dos_output_dir / f"dos_sublattice_{sublat}.png"
                fig, ax = plotter.plot_sublattice(
                    sublattice=sublat,
                    spin_polarized=True,
                    save=None,
                    show=False,
                    xlim=xlim,
                    ylim=ylim,
                )
                fig.savefig(sublat_plot, dpi=300, bbox_inches='tight')
                plt.close(fig)
                
                # Verify file was actually created
                if sublat_plot.exists():
                    sublattice_plots.append(str(sublat_plot))
                    print(f"✓ Sublattice {sublat} DOS plot saved: {sublat_plot}")
                else:
                    raise RuntimeError(f"Failed to save sublattice {sublat} DOS plot: {sublat_plot} (file does not exist after savefig)")
        else:
            print("Note: No atom info found, skipping sublattice DOS plots")

    except Exception as e:
        import traceback
        print(f"\n✗ Error generating DOS plots: {e}")
        print("Full traceback:")
        traceback.print_exc()
        print(f"\nDOS file was parsed successfully, but plotting failed.")
        print(f"Please check the DOS file format and try again.")

    results = {
        'status': 'success',
        'dos_file': str(dos_file),
        'total_plot': str(total_plot) if 'total_plot' in locals() else None,
        'sublattice_plots': sublattice_plots if 'sublattice_plots' in locals() else [],
        'plot_range': dos_plot_range,
        'ylim': dos_ylim,
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

        # Check for EOS plot
        phase1_path = base_path / "phase1_ca_optimization"
        if (phase1_path / "eos_plot_morse.png").exists():
            report.append(f"\n  EOS plot: phase1_ca_optimization/eos_plot_morse.png")

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

        # Check for EOS plot
        phase2_path = base_path / "phase2_sws_optimization"
        if (phase2_path / "eos_plot_morse.png").exists():
            report.append(f"\n  EOS plot: phase2_sws_optimization/eos_plot_morse.png")

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
            # Count actual plots that exist
            total_plot_path = dos.get('total_plot')
            sublattice_plots = dos.get('sublattice_plots', [])
            plot_count = (1 if total_plot_path and Path(total_plot_path).exists() else 0) + len([p for p in sublattice_plots if Path(p).exists()])
            report.append(f"DOS plots generated: {plot_count}")
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
