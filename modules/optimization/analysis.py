#!/usr/bin/env python3
"""
Analysis functions for EMTO workflow.

Handles EOS fitting, DOS analysis, and report generation.
"""

import subprocess
import os
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Union, List, Dict, Any, Optional, Tuple
import numpy as np
from scipy.optimize import curve_fit
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for headless environments
import matplotlib.pyplot as plt

from modules.inputs.eos_emto import create_eos_input
from modules.inputs.eos_emto import parse_eos_output, morse_energy


def select_symmetric_points(
    param_values: List[float],
    equilibrium_value: float,
    n_points: int = 7
) -> Tuple[List[int], List[str]]:
    """
    Select N points centered around equilibrium value for symmetric fitting.
    
    Parameters
    ----------
    param_values : list of float
        Parameter values (must be sorted)
    equilibrium_value : float
        Equilibrium value around which to center selection
    n_points : int, optional
        Number of points to select (default: 7)
    
    Returns
    -------
    tuple of (list, list)
        indices : List of indices of selected points
        warnings : List of warning messages (empty if no warnings)
    
    Notes
    -----
    - Finds the point closest to equilibrium
    - Selects N points centered around that closest point
    - Handles edge cases: equilibrium outside range, insufficient points
    """
    warnings = []
    param_values = np.array(param_values)
    
    # Ensure param_values is sorted
    if not np.all(np.diff(param_values) >= 0):
        # Sort and track original indices
        sorted_indices = np.argsort(param_values)
        param_values_sorted = param_values[sorted_indices]
    else:
        sorted_indices = np.arange(len(param_values))
        param_values_sorted = param_values
    
    # Find index of point closest to equilibrium
    closest_idx = np.argmin(np.abs(param_values_sorted - equilibrium_value))
    closest_value = param_values_sorted[closest_idx]
    
    # Calculate how many points needed on each side
    n_side = (n_points - 1) // 2
    
    # Check if we have enough points
    if len(param_values_sorted) < n_points:
        warnings.append(
            f"WARNING: Only {len(param_values_sorted)} points available, "
            f"fewer than requested {n_points}. Using all available points for final fit."
        )
        # Use all available points
        indices_sorted = list(range(len(param_values_sorted)))
    else:
        # Try to select symmetric points
        start_idx = closest_idx - n_side
        end_idx = closest_idx + n_side + 1
        
        # Check if we have enough points on both sides
        if start_idx < 0:
            # Not enough points on left side
            start_idx = 0
            end_idx = min(n_points, len(param_values_sorted))
            n_left = closest_idx
            n_right = end_idx - closest_idx - 1
            warnings.append(
                f"WARNING: Equilibrium value {equilibrium_value:.6f} is too close to the "
                f"range boundary. Cannot select {n_points} symmetric points. "
                f"Using best available selection with {end_idx - start_idx} points "
                f"({n_left} left, {n_right} right of equilibrium)."
            )
        elif end_idx > len(param_values_sorted):
            # Not enough points on right side
            end_idx = len(param_values_sorted)
            start_idx = max(0, end_idx - n_points)
            n_left = closest_idx - start_idx
            n_right = end_idx - closest_idx - 1
            warnings.append(
                f"WARNING: Equilibrium value {equilibrium_value:.6f} is too close to the "
                f"range boundary. Cannot select {n_points} symmetric points. "
                f"Using best available selection with {end_idx - start_idx} points "
                f"({n_left} left, {n_right} right of equilibrium)."
            )
        
        indices_sorted = list(range(start_idx, end_idx))
    
    # Map back to original indices if we sorted
    if not np.all(np.diff(param_values) >= 0):
        indices = [int(sorted_indices[i]) for i in indices_sorted]
    else:
        indices = indices_sorted
    
    return indices, warnings


def check_equilibrium_position(
    equilibrium_value: float,
    param_values: List[float],
    tolerance: Optional[float] = None
) -> Tuple[bool, str]:
    """
    Check if equilibrium value is within the parameter range.
    
    Parameters
    ----------
    equilibrium_value : float
        Equilibrium value to check
    param_values : list of float
        Parameter values
    tolerance : float, optional
        Tolerance for boundary check. If None, checks exact range.
    
    Returns
    -------
    tuple of (bool, str)
        in_range : True if equilibrium is within range
        warning_message : Warning message if not in range, empty string otherwise
    """
    min_val = min(param_values)
    max_val = max(param_values)
    
    if tolerance is None:
        # Exact range check
        if equilibrium_value < min_val or equilibrium_value > max_val:
            return False, (
                f"WARNING: Equilibrium value {equilibrium_value:.6f} is outside the "
                f"input range [{min_val:.6f}, {max_val:.6f}]. "
                f"The fit may be extrapolated."
            )
    else:
        # Check with tolerance
        if equilibrium_value < min_val - tolerance or equilibrium_value > max_val + tolerance:
            return False, (
                f"WARNING: Equilibrium value {equilibrium_value:.6f} is outside the "
                f"input range [{min_val:.6f}, {max_val:.6f}] (tolerance: {tolerance:.6f}). "
                f"The fit may be extrapolated."
            )
    
    return True, ""


def run_eos_fit(
    r_or_v_data: List[float],
    energy_data: List[float],
    output_path: Union[str, Path],
    job_name: str,
    comment: str,
    eos_executable: str,
    eos_type: str = 'MO88',
    use_symmetric_selection: bool = True,
    n_points_final: int = 7
) -> Tuple[float, Dict[str, Any], Dict[str, Any]]:
    """
    Run EMTO EOS executable and parse results.

    Steps:
    1. Create EOS input file using create_eos_input()
    2. Run EOS executable: subprocess.run(eos_executable + ' < eos.dat')
    3. Parse output using parse_eos_output()
    4. Extract optimal parameter (rwseq)

    If use_symmetric_selection=True and more than n_points_final points are provided:
    - Performs initial fit with all points to find equilibrium
    - Selects n_points_final symmetric points around equilibrium
    - Performs final fit with selected points (used for optimization)

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
    use_symmetric_selection : bool, optional
        If True and len(r_or_v_data) > n_points_final, performs two-stage fitting
        with symmetric point selection. Default: True
    n_points_final : int, optional
        Number of points to use for final symmetric fit. Default: 7

    Returns
    -------
    tuple of (float, dict, dict)
        optimal_value : Optimal parameter (rwseq) from primary fit
        results : Dictionary of all EOS fit results
        metadata : Dictionary with symmetric fit metadata and warnings

    Raises
    ------
    RuntimeError
        If EOS executable fails or parsing fails
    """

    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    # Initialize metadata dictionary
    metadata = {
        'symmetric_selection_used': False,
        'initial_points': len(r_or_v_data),
        'final_points': len(r_or_v_data),
        'equilibrium_value': None,
        'equilibrium_in_range': True,
        'selected_indices': list(range(len(r_or_v_data))),
        'warnings': [],
        'initial_fit_equilibrium': None
    }

    # Check if we should use symmetric selection
    use_symmetric = use_symmetric_selection and len(r_or_v_data) > n_points_final

    if use_symmetric:
        print(f"\n{'='*70}")
        print(f"RUNNING EOS FIT WITH SYMMETRIC SELECTION")
        print(f"{'='*70}")
        print(f"Initial points: {len(r_or_v_data)}")
        print(f"Target final points: {n_points_final}")
        print(f"Type: {eos_type}")
        print(f"Output: {output_path}")
        print(f"{'='*70}\n")

        # Step 1: Initial fit with all points
        print("Step 1: Initial fit with all points to find equilibrium...")
        initial_optimal, initial_results = _run_single_eos_fit(
            r_or_v_data=r_or_v_data,
            energy_data=energy_data,
            output_path=output_path,
            job_name=job_name,
            comment=comment,
            eos_executable=eos_executable,
            eos_type=eos_type
        )
        
        metadata['initial_fit_equilibrium'] = initial_optimal
        metadata['equilibrium_value'] = initial_optimal

        # Step 2: Check equilibrium position
        print("\nStep 2: Checking equilibrium position...")
        in_range, range_warning = check_equilibrium_position(
            initial_optimal, r_or_v_data
        )
        metadata['equilibrium_in_range'] = in_range
        if range_warning:
            metadata['warnings'].append(range_warning)
            print(f"  {range_warning}")

        # Step 3: Select symmetric points
        print("\nStep 3: Selecting symmetric points around equilibrium...")
        selected_indices, selection_warnings = select_symmetric_points(
            r_or_v_data, initial_optimal, n_points_final
        )
        metadata['selected_indices'] = selected_indices
        metadata['warnings'].extend(selection_warnings)
        
        if selection_warnings:
            for warning in selection_warnings:
                print(f"  {warning}")
        else:
            print(f"  INFO: Selected {len(selected_indices)} symmetric points "
                  f"around equilibrium {initial_optimal:.6f}")

        # Step 4: Final fit with selected points
        print(f"\nStep 4: Final fit with {len(selected_indices)} selected points...")
        r_or_v_final = [r_or_v_data[i] for i in selected_indices]
        energy_final = [energy_data[i] for i in selected_indices]
        
        # Verify we have enough points and they're sorted
        if len(r_or_v_final) < 3:
            raise RuntimeError(
                f"Not enough points selected for final fit: {len(r_or_v_final)}. "
                f"Need at least 3 points for EOS fitting."
            )
        
        # Ensure points are sorted (should be, but double-check)
        sorted_pairs = sorted(zip(r_or_v_final, energy_final))
        r_or_v_final = [r for r, e in sorted_pairs]
        energy_final = [e for r, e in sorted_pairs]
        
        print(f"  Selected SWS values: {[f'{r:.4f}' for r in r_or_v_final]}")
        
        metadata['symmetric_selection_used'] = True
        metadata['final_points'] = len(selected_indices)

        # Use shorter job name for final fit to avoid EOS truncation issues
        # EOS limits job names to ~20 characters, so use a shorter suffix
        final_job_name = f"{job_name}_fin" if len(f"{job_name}_final") > 20 else f"{job_name}_final"
        optimal_value, eos_results = _run_single_eos_fit(
            r_or_v_data=r_or_v_final,
            energy_data=energy_final,
            output_path=output_path,
            job_name=final_job_name,
            comment=f"{comment} (final symmetric fit)",
            eos_executable=eos_executable,
            eos_type=eos_type
        )

        print(f"\n✓ Final fit completed: optimal value = {optimal_value:.6f}")
        if metadata['warnings']:
            print(f"\n⚠ Warnings:")
            for warning in metadata['warnings']:
                print(f"  {warning}")
        print(f"{'='*70}\n")

    else:
        # Original behavior: single fit with all points
        print(f"\n{'='*70}")
        print(f"RUNNING EOS FIT")
        print(f"{'='*70}")
        print(f"Type: {eos_type}")
        print(f"Data points: {len(r_or_v_data)}")
        print(f"Output: {output_path}")
        print(f"{'='*70}\n")

        optimal_value, eos_results = _run_single_eos_fit(
            r_or_v_data=r_or_v_data,
            energy_data=energy_data,
            output_path=output_path,
            job_name=job_name,
            comment=comment,
            eos_executable=eos_executable,
            eos_type=eos_type
        )
        metadata['equilibrium_value'] = optimal_value

    return optimal_value, eos_results, metadata


def _run_single_eos_fit(
    r_or_v_data: List[float],
    energy_data: List[float],
    output_path: Union[str, Path],
    job_name: str,
    comment: str,
    eos_executable: str,
    eos_type: str = 'MO88'
) -> Tuple[float, Dict[str, Any]]:
    """
    Internal function to run a single EOS fit.
    
    This is the core EOS fitting logic, extracted to be reusable
    for both initial and final fits in symmetric selection mode.
    
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
    # Use unique filenames based on job_name to avoid conflicts when running multiple fits
    eos_input_file = output_path / f"eos_{job_name}.dat"
    eos_stdout_file = output_path / f"eos_{job_name}.out"

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
    # EOS executable may truncate job names to ~20 characters, so check for both full and truncated names
    filename_eos_results = output_path / f"{job_name}.out"
    
    # First, try to find output file from stdout log (most reliable)
    if not filename_eos_results.exists() and eos_stdout_file.exists():
        try:
            with open(eos_stdout_file, 'r') as f:
                stdout_content = f.read()
                # Look for "Output file" pattern in stdout
                import re
                match = re.search(r'Output file\s+(\S+)', stdout_content, re.IGNORECASE)
                if match:
                    output_file_from_stdout = match.group(1)
                    potential_file = output_path / output_file_from_stdout
                    if potential_file.exists():
                        filename_eos_results = potential_file
                        print(f"  Note: Found output file from stdout: {output_file_from_stdout}")
                        if output_file_from_stdout != f"{job_name}.out":
                            print(f"       (EOS truncated job name from '{job_name}' to '{output_file_from_stdout[:-4]}')")
        except Exception:
            pass
    
    # If still not found, check for truncated version (EOS limits job names to ~20 chars)
    if not filename_eos_results.exists():
        # Check for truncated job name (first 20 characters)
        truncated_job_name = job_name[:20] if len(job_name) > 20 else job_name
        filename_truncated = output_path / f"{truncated_job_name}.out"
        
        if filename_truncated.exists():
            # Use the truncated filename
            filename_eos_results = filename_truncated
            print(f"  Note: EOS truncated job name to '{truncated_job_name}' (original: '{job_name}')")
        else:
            # Check what .out files were actually created
            created_files = list(output_path.glob("*.out"))
            created_files_str = "\n".join([f"  - {f.name}" for f in created_files])
            
            # Read stdout log for error messages
            stdout_content = ""
            if eos_stdout_file.exists():
                try:
                    with open(eos_stdout_file, 'r') as f:
                        stdout_content = f.read()
                        # Show last 20 lines if file is long
                        lines = stdout_content.split('\n')
                        if len(lines) > 20:
                            stdout_content = '\n'.join(lines[-20:])
                except Exception:
                    pass
            
            if not filename_eos_results.exists():
                error_msg = (
                    "EOS executable completed but did not produce the expected results file.\n"
                    f"Expected: {output_path / f'{job_name}.out'}\n"
                    f"Also checked truncated: {filename_truncated}\n"
                    f"Files created in output directory:\n{created_files_str if created_files_str else '  (none)'}\n"
                )
                if stdout_content:
                    error_msg += f"\nLast lines from stdout log ({eos_stdout_file}):\n{stdout_content}"
                else:
                    error_msg += f"\nStdout log: {eos_stdout_file}"
                
                raise RuntimeError(error_msg)
    try:
        results = parse_eos_output(filename_eos_results)

        if not results:
            raise RuntimeError("No results found in EOS output")

        print(f"\nParsed {len(results)} EOS fit(s):")
        for fit_name, params in results.items():
            rwseq_str = f"{params.rwseq:.6f}" if not np.isnan(params.rwseq) else "NaN"
            eeq_str = f"{params.eeq:.6f}" if not np.isnan(params.eeq) else "NaN"
            print(f"  {fit_name}: rwseq = {rwseq_str}, eeq = {eeq_str} Ry")

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
    # If optimal_value is NaN, we'll let detect_expansion_needed handle it

    optimal_str = f"{optimal_value:.6f}" if not np.isnan(optimal_value) else "NaN"
    print(f"\n✓ Using {primary_fit} fit: optimal value = {optimal_str}")
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


# ============================================================================
# Range Expansion Functions
# ============================================================================

def detect_expansion_needed(
    eos_results: Dict[str, Any],
    param_values: List[float],
    energy_values: List[float],
    equilibrium_value: float
) -> Tuple[bool, str]:
    """
    Determine if parameter range expansion is needed.
    
    Simplified detection: checks for NaN values, equilibrium outside range,
    or energy monotonic at boundaries.
    
    Parameters
    ----------
    eos_results : dict
        EOS fit results from parse_eos_output
    param_values : List[float]
        Parameter values used in fit
    energy_values : List[float]
        Energy values used in fit
    equilibrium_value : float
        Equilibrium value from EOS fit (may be NaN)
    
    Returns
    -------
    tuple of (needs_expansion, reason)
        needs_expansion : bool
        reason : str (reason for expansion, empty if not needed)
    """
    if not param_values or not energy_values:
        return False, ""
    
    param_values = np.array(param_values)
    energy_values = np.array(energy_values)
    
    # Sort by parameter value
    sort_idx = np.argsort(param_values)
    param_values = param_values[sort_idx]
    energy_values = energy_values[sort_idx]
    
    # Check 1: NaN values in EOS results
    for name, params in eos_results.items():
        if (np.isnan(params.rwseq) or np.isnan(params.eeq) or 
            np.isnan(params.bmod) or np.isnan(params.v_eq)):
            return True, f"EOS fit returned NaN values in {name} fit"
    
    # Check 2: Equilibrium outside range
    if np.isnan(equilibrium_value):
        return True, "Equilibrium value is NaN"
    
    param_min = np.min(param_values)
    param_max = np.max(param_values)
    if equilibrium_value < param_min:
        return True, f"Equilibrium ({equilibrium_value:.6f}) below minimum parameter ({param_min:.6f})"
    if equilibrium_value > param_max:
        return True, f"Equilibrium ({equilibrium_value:.6f}) above maximum parameter ({param_max:.6f})"
    
    # Check 3: Energy monotonic at boundaries
    # Check if energy still decreasing at maximum
    if len(energy_values) >= 2:
        energy_at_max = energy_values[-1]
        energy_before_max = energy_values[-2]
        if energy_at_max < energy_before_max:
            return True, f"Energy still decreasing at maximum parameter ({param_max:.6f})"
        
        # Check if energy still increasing at minimum
        energy_at_min = energy_values[0]
        energy_after_min = energy_values[1]
        if energy_at_min > energy_after_min:
            return True, f"Energy still increasing at minimum parameter ({param_min:.6f})"
    
    return False, ""


def estimate_morse_minimum(
    param_values: List[float],
    energy_values: List[float]
) -> Tuple[float, float, Dict[str, Any]]:
    """
    Estimate minimum using Modified Morse EOS fitting.
    
    Fits Modified Morse equation: E(R) = a + b·exp(-λ·R) + c·exp(-2λ·R)
    Equilibrium found from: x0 = -b/(2c), R_eq = -log(x0)/λ
    
    Based on fitmo88.for (V.L.Moruzzi et al. Phys.Rev.B, 37, 790-799 (1988))
    
    Parameters
    ----------
    param_values : List[float]
        Parameter values (R_WS for SWS optimization, c/a for c/a optimization)
        Will be sorted
    energy_values : List[float]
        Corresponding energy values
    
    Returns
    -------
    tuple of (estimated_min_param, estimated_min_energy, fit_info)
        estimated_min_param : float
            Estimated parameter value at minimum (R_eq or c/a_eq)
        estimated_min_energy : float
            Estimated energy at minimum
        fit_info : dict
            - morse_params: {'a': float, 'b': float, 'c': float, 'lambda': float}
            - r_squared: float (fit quality, 0-1)
            - is_valid: bool (fit converged and R² > 0.7)
            - rms: float (root mean square error)
    
    Note
    ----
    Currently only implements Modified Morse EOS. Other EOS types (Birch-Murnaghan,
    Murnaghan, Polynomial) need to be implemented for full support.
    """
    if len(param_values) < 4:
        raise ValueError("Need at least 4 points to fit Morse EOS")
    
    param_values = np.array(param_values)
    energy_values = np.array(energy_values)
    
    # Sort by parameter value
    sort_idx = np.argsort(param_values)
    param_values = param_values[sort_idx]
    energy_values = energy_values[sort_idx]
    
    # Define Morse function for fitting
    def morse_func(r, a, b, c, lam):
        """Modified Morse: E(R) = a + b·exp(-λ·R) + c·exp(-2λ·R)"""
        x = np.exp(-lam * r)
        return a + b * x + c * x * x
    
    # Initial guess for parameters
    # Use simple estimates based on data
    energy_min = np.min(energy_values)
    energy_max = np.max(energy_values)
    energy_range = energy_max - energy_min
    param_range = np.max(param_values) - np.min(param_values)
    
    # Initial guesses
    a_init = energy_min  # Offset
    lam_init = 2.0 / param_range  # Rough estimate for lambda
    # For b and c, we need b < 0 and c > 0 for a minimum
    b_init = -energy_range * 0.5
    c_init = energy_range * 0.3
    
    try:
        # Fit Morse equation
        popt, pcov = curve_fit(
            morse_func,
            param_values,
            energy_values,
            p0=[a_init, b_init, c_init, lam_init],
            maxfev=5000,
            bounds=(
                [-np.inf, -np.inf, 1e-10, 1e-10],  # Lower bounds
                [np.inf, np.inf, np.inf, np.inf]    # Upper bounds
            )
        )
        
        a, b, c, lam = popt
        
        # Calculate equilibrium from Morse parameters (fitmo88.for:222-224)
        # x0 = -b/(2c)
        # alx0 = log(x0)
        # R_eq = -alx0/λ
        if abs(c) < 1e-10:
            raise ValueError("c parameter too small, cannot calculate equilibrium")
        
        x0_eq = -b / (2.0 * c)
        if x0_eq <= 0:
            raise ValueError("x0_eq is non-positive, invalid Morse parameters")
        
        alx0_eq = np.log(x0_eq)
        estimated_min_param = -alx0_eq / lam
        
        # Calculate energy at equilibrium
        estimated_min_energy = morse_func(estimated_min_param, a, b, c, lam)
        
        # Calculate R²
        energy_predicted = morse_func(param_values, a, b, c, lam)
        ss_res = np.sum((energy_values - energy_predicted)**2)
        ss_tot = np.sum((energy_values - np.mean(energy_values))**2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        
        # Calculate RMS
        rms = np.sqrt(np.mean((energy_values - energy_predicted)**2))
        
        # Validate: reasonable fit (R² > 0.7) and valid parameters
        is_valid = (r_squared > 0.7) and np.all(np.isfinite([a, b, c, lam])) and (c > 0)
        
        fit_info = {
            'morse_params': {
                'a': float(a),
                'b': float(b),
                'c': float(c),
                'lambda': float(lam)
            },
            'r_squared': float(r_squared),
            'rms': float(rms),
            'is_valid': bool(is_valid)
        }
        
    except Exception as e:
        # Fallback: use minimum from data
        min_idx = np.argmin(energy_values)
        estimated_min_param = float(param_values[min_idx])
        estimated_min_energy = float(energy_values[min_idx])
        
        fit_info = {
            'morse_params': None,
            'r_squared': 0.0,
            'rms': np.inf,
            'is_valid': False,
            'error': str(e)
        }
    
    return float(estimated_min_param), float(estimated_min_energy), fit_info


def generate_parameter_vector_around_estimate(
    estimated_minimum: float,
    step_size: float,
    n_points: int = 14
) -> List[float]:
    """
    Generate parameter vector centered around estimated minimum.
    
    The range width is automatically calculated from the number of points and step_size:
    - Total range width = (n_points - 1) * step_size
    - Range = [estimate - half_width, estimate + half_width]
    
    Parameters
    ----------
    estimated_minimum : float
        Morse EOS-estimated minimum parameter value
    step_size : float
        Step size for parameter spacing (from config: ca_step or sws_step)
    n_points : int
        Number of points to generate (uses same as initial user input)
    
    Returns
    -------
    List[float]
        Sorted list of parameter values centered around estimate
    """
    # Calculate range width automatically: (n_points - 1) * step_size
    # This ensures the spacing between points matches the step_size
    total_range_width = (n_points - 1) * step_size
    range_half_width = total_range_width / 2.0
    
    min_val = estimated_minimum - range_half_width
    max_val = estimated_minimum + range_half_width
    
    param_values = np.linspace(min_val, max_val, n_points)
    return sorted(param_values.tolist())


# ============================================================================
# Data Persistence Functions
# ============================================================================

def save_parameter_energy_data(
    phase_path: Path,
    parameter_name: str,
    parameter_values: List[float],
    energy_values: List[float]
) -> Path:
    """
    Save parameter values and energies to JSON file.
    Merges with existing data if file exists (avoids duplicates).
    
    Parameters
    ----------
    phase_path : Path
        Phase directory (e.g., phase2_sws_optimization)
    parameter_name : str
        'sws' or 'ca'
    parameter_values : List[float]
        Parameter values
    energy_values : List[float]
        Corresponding energy values
    
    Returns
    -------
    Path
        Path to saved file
    """
    if len(parameter_values) != len(energy_values):
        raise ValueError("parameter_values and energy_values must have same length")
    
    filename = f"{parameter_name}_energy_data.json"
    file_path = phase_path / filename
    
    # Load existing data if file exists
    existing_data = {}
    if file_path.exists():
        try:
            with open(file_path, 'r') as f:
                existing_data = json.load(f)
        except (json.JSONDecodeError, IOError):
            # If file is corrupted or can't be read, start fresh
            existing_data = {}
    
    # Create data points dictionary (use parameter as key for deduplication)
    new_data_points = {
        float(p): float(e) for p, e in zip(parameter_values, energy_values)
    }
    
    # Merge with existing data (new values take precedence)
    if 'data_points' in existing_data:
        existing_data_points = {
            float(p['parameter']): float(p['energy'])
            for p in existing_data['data_points']
        }
        existing_data_points.update(new_data_points)
        merged_data_points = existing_data_points
    else:
        merged_data_points = new_data_points
    
    # Convert back to list format
    data_points_list = [
        {'parameter': p, 'energy': e}
        for p, e in sorted(merged_data_points.items())
    ]
    
    # Save to file
    output_data = {
        'parameter_name': parameter_name,
        'data_points': data_points_list,
        'last_updated': datetime.now().isoformat(),
        'source': str(phase_path.name)
    }
    
    with open(file_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    return file_path


def load_parameter_energy_data(
    phase_path: Path,
    parameter_name: str
) -> Tuple[Optional[List[float]], Optional[List[float]]]:
    """
    Load parameter values and energies from saved file.
    
    Parameters
    ----------
    phase_path : Path
        Phase directory
    parameter_name : str
        'sws' or 'ca'
    
    Returns
    -------
    tuple of (parameter_values, energy_values) or (None, None) if not found
    """
    filename = f"{parameter_name}_energy_data.json"
    file_path = phase_path / filename
    
    if not file_path.exists():
        return None, None
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        if 'data_points' not in data or not data['data_points']:
            return None, None
        
        parameter_values = [p['parameter'] for p in data['data_points']]
        energy_values = [p['energy'] for p in data['data_points']]
        
        return parameter_values, energy_values
    except (json.JSONDecodeError, IOError, KeyError):
        return None, None


def prepare_data_for_eos_fit(
    current_param_values: List[float],
    current_energy_values: List[float],
    phase_path: Path,
    parameter_name: str,
    use_saved_data: bool
) -> Tuple[List[float], List[float]]:
    """
    Prepare data for EOS fitting based on user preference.
    
    IMPORTANT: Always saves current workflow data to file (automatic, no option).
    The flag controls which data to use for EOS fitting:
    - If use_saved_data=True: Use ALL points from saved file (accumulated over time)
    - If use_saved_data=False: Use ONLY current workflow's array (just generated)
    
    Parameters
    ----------
    current_param_values : List[float]
        Current workflow's parameter values
    current_energy_values : List[float]
        Current workflow's energy values
    phase_path : Path
        Phase directory
    parameter_name : str
        'sws' or 'ca'
    use_saved_data : bool
        Whether to use all saved data (true) or only current workflow (false)
    
    Returns
    -------
    tuple of (final_param_values, final_energy_values) sorted by parameter
    """
    if len(current_param_values) != len(current_energy_values):
        raise ValueError("current_param_values and current_energy_values must have same length")
    
    # ALWAYS save current workflow data to file (automatic, no option)
    save_parameter_energy_data(phase_path, parameter_name, current_param_values, current_energy_values)
    
    # Choose data source for EOS fitting based on user flag
    if use_saved_data:
        # Use ALL points from saved file (accumulated over multiple runs)
        saved_params, saved_energies = load_parameter_energy_data(phase_path, parameter_name)
        if saved_params:
            print(f"  Using all {len(saved_params)} points from saved file for EOS fit")
            final_param_values = list(saved_params)
            final_energy_values = list(saved_energies)
        else:
            # Fallback to current workflow if no saved file exists
            print("  No saved file found, using current workflow data only")
            final_param_values = list(current_param_values)
            final_energy_values = list(current_energy_values)
    else:
        # Use ONLY current workflow's array (just generated)
        print(f"  Using current workflow data only ({len(current_param_values)} points)")
        final_param_values = list(current_param_values)
        final_energy_values = list(current_energy_values)
    
    # Sort by parameter value
    sorted_pairs = sorted(zip(final_param_values, final_energy_values))
    final_param_values = [p for p, e in sorted_pairs]
    final_energy_values = [e for p, e in sorted_pairs]
    
    return final_param_values, final_energy_values
