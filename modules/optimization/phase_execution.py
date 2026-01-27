#!/usr/bin/env python3
"""
Phase execution functions for EMTO optimization workflow.

Handles the three main optimization phases:
- Phase 1: c/a ratio optimization
- Phase 2: SWS optimization
- Phase 3: Optimized structure calculation
"""

import json
import numpy as np
from pathlib import Path
from typing import Union, List, Dict, Any, Tuple, Callable

from modules.create_input import create_emto_inputs
from modules.extract_results import parse_kfcd, parse_kgrn
from modules.optimization.analysis import (
    detect_expansion_needed,
    estimate_morse_minimum,
    generate_parameter_vector_around_estimate,
    prepare_data_for_eos_fit,
    load_parameter_energy_data
)


def optimize_ca_ratio(
    structure: Dict[str, Any],
    ca_ratios: List[float],
    initial_sws: Union[float, List[float]],
    config: Dict[str, Any],
    base_path: Path,
    run_calculations_func: Callable,
    validate_calculations_func: Callable,
    run_eos_fit_func: Callable,
    results_dict: Dict[str, Any]
) -> Tuple[float, Dict[str, Any]]:
    """
    Phase 1: c/a ratio optimization.

    Creates EMTO inputs, runs calculations, parses energies, fits EOS,
    and extracts optimal c/a ratio.

    Parameters
    ----------
    structure : dict
        Structure dictionary from create_emto_structure()
    ca_ratios : list of float
        List of c/a ratios to test
    initial_sws : float or list of float
        Initial SWS value(s) for c/a optimization
        If float, uses same value for all c/a ratios
        If list, must have same length as ca_ratios
    config : dict
        Configuration dictionary
    base_path : Path
        Base output directory
    run_calculations_func : callable
        Function to run calculations
    validate_calculations_func : callable
        Function to validate calculations
    run_eos_fit_func : callable
        Function to run EOS fit
    results_dict : dict
        Workflow results dictionary to update

    Returns
    -------
    tuple of (float, dict)
        optimal_ca : Optimal c/a ratio from EOS fit
        results : Dictionary with EOS results and energy data

    Raises
    ------
    RuntimeError
        If calculations fail or output files not found
    """
    print(f"\n{'#'*70}")
    print("# PHASE 1: c/a RATIO OPTIMIZATION")
    print(f"{'#'*70}\n")

    # Validate initial_sws
    if isinstance(initial_sws, (int, float)):
        sws_list = [float(initial_sws)] * len(ca_ratios)
    elif isinstance(initial_sws, list):
        if len(initial_sws) != len(ca_ratios):
            raise ValueError(
                f"initial_sws list length ({len(initial_sws)}) must match "
                f"ca_ratios length ({len(ca_ratios)})"
            )
        sws_list = initial_sws
    else:
        raise TypeError("initial_sws must be float or list of float")

    # Create phase subdirectory
    phase_path = base_path / "phase1_ca_optimization"
    phase_path.mkdir(parents=True, exist_ok=True)

    print(f"Creating EMTO inputs for {len(ca_ratios)} c/a ratios...")
    print(f"  c/a ratios: {ca_ratios}")
    print(f"  SWS values: {sws_list}")
    print(f"  Output path: {phase_path}\n")

    # Create EMTO inputs
    try:
        phase_config = {
            **config,  # All validated defaults from constructor
            'output_path': str(phase_path),  # Override for this phase
            'ca_ratios': ca_ratios,
            'sws_values': sws_list,
            # Only override what's different for this phase
        }

        create_emto_inputs(phase_config)

    except Exception as e:
        raise RuntimeError(f"Failed to create EMTO inputs: {e}")

    # Run calculations
    script_name = f"run_{config['job_name']}.sh"
    run_calculations_func(
        calculation_path=phase_path,
        script_name=script_name
    )

    # Validate calculations completed successfully
    validate_calculations_func(
        phase_path=phase_path,
        ca_ratios=ca_ratios,
        sws_values=sws_list,
        job_name=config['job_name']
    )

    # Parse energies from KFCD outputs
    print("\nParsing energies from KFCD outputs...")
    ca_values = []
    energy_values = []

    for i, (ca, sws) in enumerate(zip(ca_ratios, sws_list)):
        file_id = f"{config['job_name']}_{ca:.2f}_{sws:.2f}"
        kfcd_file = phase_path / "fcd" / f"{file_id}.prn"

        if not kfcd_file.exists():
            raise RuntimeError(
                f"KFCD output not found: {kfcd_file}\n"
                f"Calculation may have failed. Check log files in {phase_path}"
            )

        try:
            results = parse_kfcd(str(kfcd_file), functional=config.get('functional', 'GGA'))
            if results.total_energy is None:
                raise RuntimeError(f"No total energy found in {kfcd_file}")

            ca_values.append(ca)
            energy_values.append(results.energies_by_functional['system']['GGA'])

            print(f"  c/a = {ca:.4f}: E = {results.energies_by_functional['system']['GGA']:.6f} Ry")

        except Exception as e:
            raise RuntimeError(f"Failed to parse {kfcd_file}: {e}")

    # Prepare data for EOS fitting
    # Always saves current workflow data to file (automatic)
    # Flag controls which data to use: all saved vs workflow only
    use_saved_data = config.get('eos_use_saved_data', False)
    ca_values_for_fit, energy_values_for_fit = prepare_data_for_eos_fit(
        ca_values, energy_values, phase_path, 'ca', use_saved_data
    )
    
    # Keep track of original workflow points (for Morse estimation after expansion)
    ca_workflow_points = list(ca_values)
    energy_workflow_points = list(energy_values)

    # Run EOS fit (with error handling for failed fits)
    # Initial fit: NO symmetric selection (fit all points to check if expansion needed)
    eos_fit_failed = False
    eos_fit_error_msg = None
    try:
        eos_fit_result = run_eos_fit_func(
            r_or_v_data=ca_values_for_fit,
            energy_data=energy_values_for_fit,
            output_path=phase_path,
            job_name=f"{config['job_name']}_ca",
            comment=f"c/a optimization for {config['job_name']}",
            eos_type=config.get('eos_type', 'MO88'),
            use_symmetric_selection=False  # No symmetric selection for initial fit
        )
        
        # Handle both old (2-tuple) and new (3-tuple) return signatures for backward compatibility
        if len(eos_fit_result) == 2:
            optimal_ca, eos_results = eos_fit_result
            symmetric_metadata = {}
        else:
            optimal_ca, eos_results, symmetric_metadata = eos_fit_result
        
        # Print warnings if any
        if symmetric_metadata.get('warnings'):
            print("\n⚠ Symmetric fit warnings:")
            for warning in symmetric_metadata['warnings']:
                print(f"  {warning}")
    
    except Exception as e:
        # EOS fit failed - proceed with expansion check using Morse estimation
        eos_fit_failed = True
        eos_fit_error_msg = str(e)
        print(f"\n⚠ EOS fit failed: {eos_fit_error_msg}")
        print("  Proceeding with expansion check using Morse estimation...")
        
        # Create dummy results for detect_expansion_needed
        from modules.inputs.eos_emto import EOSParameters
        dummy_params = EOSParameters(
            eos_type='morse',
            rwseq=float('nan'),
            v_eq=float('nan'),
            eeq=float('nan'),
            bmod=float('nan'),
            b_prime=0.0,
            gamma=0.0,
            fsumsq=float('inf'),
            fit_quality='failed'
        )
        eos_results = {'morse': dummy_params}
        optimal_ca = float('nan')
        symmetric_metadata = {}
    
    # Handle NaN values from EOS fit (always check, regardless of auto-expand setting)
    if not eos_fit_failed and np.isnan(optimal_ca):
        print(f"\n{'='*70}")
        print("⚠ WARNING: EOS fit returned NaN for optimal c/a!")
        print(f"{'='*70}")
        print(f"  The EOS executable completed but could not determine equilibrium.")
        print(f"  This often happens when the energy curve is monotonic or has insufficient curvature.")
        print(f"\n  Attempting fallback: Using Morse EOS estimation from data points...")
        
        try:
            morse_min, morse_energy, morse_info = estimate_morse_minimum(
                ca_workflow_points, energy_workflow_points
            )
            
            if morse_info['is_valid']:
                optimal_ca = morse_min
                print(f"  ✓ Morse estimation successful: optimal c/a = {optimal_ca:.6f}")
                print(f"    Fit quality (R²): {morse_info['r_squared']:.3f}")
                print(f"{'='*70}\n")
            else:
                if morse_info.get('error'):
                    print(f"  ✗ Morse estimation failed: {morse_info['error']}")
                else:
                    print(f"  ⚠ Morse fit quality is poor (R² = {morse_info['r_squared']:.3f})")
                    print(f"    Using estimated minimum: {morse_min:.6f}")
                    print(f"    (Warning: This estimate may be unreliable)")
                    optimal_ca = morse_min
                    print(f"{'='*70}\n")
        except Exception as e:
            print(f"  ✗ Morse estimation failed: {e}")
            print(f"\n  Cannot proceed without valid optimal c/a value.")
            print(f"  Suggestions:")
            print(f"    1. Check if energy values are reasonable")
            print(f"    2. Try a wider c/a range")
            print(f"    3. Enable 'eos_auto_expand_range: true' to automatically expand range")
            eos_output_file = phase_path / f"{config['job_name']}_ca.out"
            print(f"    4. Check EOS output file for details: {eos_output_file}")
            print(f"{'='*70}\n")
            raise RuntimeError(
                f"EOS fit returned NaN and Morse estimation failed.\n"
                f"Initial c/a range: [{min(ca_workflow_points):.6f}, {max(ca_workflow_points):.6f}]\n"
                f"Energy range: [{min(energy_workflow_points):.6f}, {max(energy_workflow_points):.6f}] Ry\n"
                f"Cannot determine optimal c/a value."
            )
    
    # Always check if optimal value is outside range (warn user even if auto-expansion is disabled)
    if not eos_fit_failed and not np.isnan(optimal_ca):
        ca_min = min(ca_values_for_fit)
        ca_max = max(ca_values_for_fit)
        if optimal_ca < ca_min or optimal_ca > ca_max:
            print(f"\n{'='*70}")
            print("⚠ WARNING: Optimal c/a is outside the initial range!")
            print(f"{'='*70}")
            print(f"  Initial c/a range: [{ca_min:.6f}, {ca_max:.6f}]")
            print(f"  Optimal c/a from EOS: {optimal_ca:.6f}")
            if optimal_ca < ca_min:
                print(f"  → Optimal value is {ca_min - optimal_ca:.6f} BELOW minimum")
            else:
                print(f"  → Optimal value is {optimal_ca - ca_max:.6f} ABOVE maximum")
            print(f"\n  The EOS fit suggests the true minimum is outside your initial range.")
            print(f"  Consider:")
            print(f"    1. Enabling 'eos_auto_expand_range: true' in config to automatically expand")
            print(f"    2. Re-running with a wider initial c/a range")
            print(f"    3. Using ca_ratios centered around {optimal_ca:.6f}")
            print(f"{'='*70}\n")
    
    # Check if expansion is needed (similar to optimize_sws)
    expansion_metadata = {}
    if config.get('eos_auto_expand_range', False):
        # If EOS fit failed, we definitely need expansion
        if eos_fit_failed:
            needs_expansion = True
            reason = f"EOS fit failed: {eos_fit_error_msg}"
        else:
            needs_expansion, reason = detect_expansion_needed(
                eos_results, ca_values_for_fit, energy_values_for_fit, optimal_ca
            )
        
        if needs_expansion:
            print(f"\n⚠ Expansion needed: {reason}")
            
            # Estimate Morse EOS minimum (use workflow points, not merged with saved data)
            morse_min, morse_energy, morse_info = estimate_morse_minimum(
                ca_workflow_points, energy_workflow_points
            )
            
            # Always use the calculated Morse minimum (global minimum of curve)
            # Warn if fit quality is poor, but still use the calculated value
            if not morse_info['is_valid']:
                if morse_info.get('error'):
                    print(f"  ⚠ Morse fit failed: {morse_info['error']}")
                    print(f"  Using minimum from data: {morse_min:.6f}")
                else:
                    print(f"  ⚠ Morse fit quality is poor (R² = {morse_info['r_squared']:.3f})")
                    print(f"  Using calculated Morse minimum: {morse_min:.6f}")
                    print(f"  (Fit quality is low - estimate may be unreliable)")
            else:
                print(f"  Morse EOS estimate: minimum at {morse_min:.6f} "
                      f"(R² = {morse_info['r_squared']:.3f})")
            
            # Generate new parameter vector (use same number of points as initial)
            initial_n_points = len(ca_values_for_fit)
            new_ca_values = generate_parameter_vector_around_estimate(
                estimated_minimum=morse_min,
                step_size=config.get('ca_step', 0.02),
                n_points=initial_n_points
            )
            
            # Identify which points need calculation
            existing_set = set(ca_values_for_fit)
            new_points_to_calculate = [v for v in new_ca_values if v not in existing_set]
            
            print(f"  Generating new vector with {len(new_ca_values)} points "
                  f"centered around {morse_min:.6f}")
            print(f"  New points to calculate: {len(new_points_to_calculate)}")
            print(f"  New range: [{min(new_ca_values):.4f}, {max(new_ca_values):.4f}]")
            
            # Dictionary to map c/a values to energies (for lookup)
            ca_to_energy = dict(zip(ca_workflow_points, energy_workflow_points))
            
            if new_points_to_calculate:
                print(f"  Calculating {len(new_points_to_calculate)} new points...")
                # Run calculations for new points
                new_ca_calculated, new_energy_values = run_calculations_for_parameter_values(
                    parameter_values=new_points_to_calculate,
                    parameter_name='ca',
                    other_params={'initial_sws': initial_sws},
                    phase_path=phase_path,
                    config=config,
                    structure=structure,
                    run_calculations_func=run_calculations_func,
                    validate_calculations_func=validate_calculations_func
                )
                
                # Update dictionary with new calculated values
                for ca, energy in zip(new_ca_calculated, new_energy_values):
                    ca_to_energy[ca] = energy
            else:
                print(f"  All points already calculated, using existing data")
            
            # For final fit, use ONLY the expanded parameter vector (new_ca_values)
            # Extract energies for these specific c/a values
            expanded_ca_values = []
            expanded_energy_values = []
            for ca in new_ca_values:
                if ca in ca_to_energy:
                    expanded_ca_values.append(ca)
                    expanded_energy_values.append(ca_to_energy[ca])
                else:
                    print(f"  ⚠ Warning: No energy found for c/a={ca:.4f}, skipping")
            
            # Sort by parameter value
            sorted_pairs = sorted(zip(expanded_ca_values, expanded_energy_values))
            expanded_ca_values = [c for c, e in sorted_pairs]
            expanded_energy_values = [e for c, e in sorted_pairs]
            
            # ALWAYS save all workflow data to file (automatic, no option)
            # Save combined data (original + expanded) for future use
            all_ca_values = ca_workflow_points + expanded_ca_values
            all_energy_values = energy_workflow_points + expanded_energy_values
            from modules.optimization.analysis import save_parameter_energy_data
            save_parameter_energy_data(phase_path, 'ca', all_ca_values, all_energy_values)
            
            # Choose data source for final fit based on user flag
            use_all_saved_for_final_fit = config.get('eos_use_all_saved_for_final_fit', False)
            if use_all_saved_for_final_fit:
                # Use all saved data from file (may include previous runs)
                saved_ca, saved_energy = load_parameter_energy_data(phase_path, 'ca')
                if saved_ca:
                    print(f"  Using all {len(saved_ca)} saved points for final fit")
                    final_ca_values = saved_ca
                    final_energy_values = saved_energy
                else:
                    print(f"  No saved file found, using expanded parameter vector")
                    final_ca_values = expanded_ca_values
                    final_energy_values = expanded_energy_values
            else:
                # Use ONLY the expanded parameter vector (default)
                print(f"  Using expanded parameter vector only ({len(expanded_ca_values)} points) for final fit")
                final_ca_values = expanded_ca_values
                final_energy_values = expanded_energy_values
            
            # Re-fit EOS with selected data (symmetric selection only if user enabled it)
            try:
                eos_fit_result = run_eos_fit_func(
                    r_or_v_data=final_ca_values,
                    energy_data=final_energy_values,
                    output_path=phase_path,
                    job_name=f"{config['job_name']}_ca",
                    comment=f"c/a optimization (after expansion) for {config['job_name']}",
                    eos_type=config.get('eos_type', 'MO88'),
                    use_symmetric_selection=config.get('symmetric_fit', False)  # Use config setting after expansion
                )
                
                # Handle return signature
                if len(eos_fit_result) == 2:
                    optimal_ca, eos_results = eos_fit_result
                    symmetric_metadata = {}
                else:
                    optimal_ca, eos_results, symmetric_metadata = eos_fit_result
                
                # Check if converged after expansion
                # Don't check monotonicity after expansion - only check if equilibrium is within range
                needs_expansion_again, reason_again = detect_expansion_needed(
                    eos_results, final_ca_values, final_energy_values, optimal_ca,
                    check_monotonic=False  # Skip monotonic check after expansion
                )
            except Exception as e:
                # Post-expansion fit also failed - estimate and suggest value
                print(f"\n⚠ Post-expansion EOS fit failed: {e}")
                needs_expansion_again = True
                reason_again = f"Post-expansion EOS fit failed: {e}"
                # Create dummy results for estimation
                from modules.inputs.eos_emto import EOSParameters
                dummy_params = EOSParameters(
                    eos_type='morse',
                    rwseq=float('nan'),
                    v_eq=float('nan'),
                    eeq=float('nan'),
                    bmod=float('nan'),
                    b_prime=0.0,
                    gamma=0.0,
                    fsumsq=float('inf'),
                    fit_quality='failed'
                )
                eos_results = {'morse': dummy_params}
                optimal_ca = float('nan')
                symmetric_metadata = {}
            
            if needs_expansion_again:
                # Estimate Morse EOS from final fit data and suggest value
                morse_min2, _, morse_info2 = estimate_morse_minimum(
                    final_ca_values, final_energy_values
                )
                
                print(f"\n⚠ EOS fit still not adequate after expansion")
                print(f"  Estimated equilibrium from final fit data: {morse_min2:.6f}")
                if morse_info2.get('morse_params'):
                    print(f"  Morse fit R²: {morse_info2['r_squared']:.3f}")
                
                suggested_initial = morse_min2 if morse_info2['is_valid'] else optimal_ca
                
                raise RuntimeError(
                    f"Failed to find equilibrium after expansion.\n\n"
                    f"Initial range: [{min(ca_values_for_fit):.6f}, {max(ca_values_for_fit):.6f}]\n"
                    f"Expanded range: [{min(expanded_ca_values):.6f}, {max(expanded_ca_values):.6f}]\n"
                    f"Final fit used: {len(final_ca_values)} points\n"
                    f"Reason: {reason_again}\n\n"
                    f"Estimated equilibrium from final fit data: {morse_min2:.6f}\n"
                    f"Fit quality (R²): {morse_info2['r_squared']:.3f}\n\n"
                    f"SUGGESTION: Re-run optimization with:\n"
                    f"  ca_ratios centered around {suggested_initial:.6f}"
                )
            
            # Update for results - use final fit values
            ca_values_for_fit = final_ca_values
            energy_values_for_fit = final_energy_values
            
            expansion_metadata = {
                'expansion_used': True,
                'morse_estimate': morse_min,
                'expanded_range': (min(expanded_ca_values), max(expanded_ca_values)),
                'points_added': len(new_points_to_calculate) if new_points_to_calculate else 0,
                'converged_after_expansion': not needs_expansion_again
            }

    # Generate EOS plot
    try:
        from modules.optimization.analysis import plot_eos_fit

        # Determine which EOS fit to plot (default to morse).
        # Supported EOS fit flags from eos.exe: MO88, MU37, POLN, SPLN, ALL.
        eos_type_map = {
            'MO88': 'morse',
            'POLN': 'polynomial',
            'SPLN': 'spline',
            'MU37': 'murnaghan',
            'ALL': 'morse'  # Default to morse if ALL was used
        }
        plot_eos_type = eos_type_map.get(config.get('eos_type', 'MO88'), 'morse')

        # Use final fit output if symmetric selection was used, otherwise use initial fit
        if symmetric_metadata.get('symmetric_selection_used'):
            eos_output_file = phase_path / f"{config['job_name']}_ca_final.out"
        else:
            eos_output_file = phase_path / f"{config['job_name']}_ca.out"
        plot_eos_fit(
            eos_output_file=eos_output_file,
            output_path=phase_path,
            variable_name='c/a',
            variable_units='',
            title=f"c/a Ratio Optimization - {config['job_name']}",
            eos_type=plot_eos_type
        )
    except Exception as e:
        print(f"Warning: Failed to generate EOS plot: {e}")

    # Extract final selected values if symmetric selection was used
    ca_values_final = None
    energy_values_final = None
    if symmetric_metadata.get('symmetric_selection_used'):
        selected_indices = symmetric_metadata.get('selected_indices', [])
        ca_values_final = [ca_values_for_fit[i] for i in selected_indices]
        energy_values_final = [energy_values_for_fit[i] for i in selected_indices]
    
    # Save results
    phase_results = {
        'optimal_ca': optimal_ca,
        'ca_values': ca_values_for_fit,
        'energy_values': energy_values_for_fit,
        'eos_type': config.get('eos_type', 'MO88'),
        'eos_fits': {
            name: {
                'rwseq': params.rwseq,
                'v_eq': params.v_eq,
                'eeq': params.eeq,
                'bulk_modulus': params.bmod * 0.1  # Convert kBar to GPa
            }
            for name, params in eos_results.items()
        }
    }
    
    # Add symmetric fit metadata if available
    if symmetric_metadata:
        phase_results['symmetric_fit_metadata'] = symmetric_metadata
        if ca_values_final is not None:
            phase_results['ca_values_final'] = ca_values_final
        if energy_values_final is not None:
            phase_results['energy_values_final'] = energy_values_final
    
    # Add expansion metadata if available
    if expansion_metadata:
        phase_results['expansion_metadata'] = expansion_metadata

    results_file = phase_path / "ca_optimization_results.json"
    with open(results_file, 'w') as f:
        json.dump(phase_results, f, indent=2)

    print(f"\n✓ c/a optimization results saved to: {results_file}")
    print(f"✓ Optimal c/a ratio: {optimal_ca:.6f}")

    # Store in workflow results
    results_dict['phase1_ca_optimization'] = phase_results

    return optimal_ca, phase_results


def run_calculations_for_parameter_values(
    parameter_values: List[float],
    parameter_name: str,
    other_params: Dict[str, Any],
    phase_path: Path,
    config: Dict[str, Any],
    structure: Dict[str, Any],
    run_calculations_func: Callable,
    validate_calculations_func: Callable
) -> Tuple[List[float], List[float]]:
    """
    Run calculations for given parameter values.
    
    Parameters
    ----------
    parameter_values : List[float]
        New parameter values to calculate
    parameter_name : str
        'sws' or 'ca' (determines which parameter is varying)
    other_params : dict
        Other parameters (e.g., optimal_ca for SWS optimization, initial_sws for c/a optimization)
    phase_path : Path
        Phase output directory
    config : dict
        Configuration dictionary
    structure : dict
        Structure dictionary
    run_calculations_func : callable
        Function to run calculations
    validate_calculations_func : callable
        Function to validate calculations
    
    Returns
    -------
    tuple of (calculated_params, energy_values)
        calculated_params : List of parameter values that were successfully calculated
        energy_values : Corresponding energy values
    """
    if parameter_name == 'sws':
        # SWS optimization: vary SWS, keep c/a fixed
        optimal_ca = other_params.get('optimal_ca')
        if optimal_ca is None:
            raise ValueError("optimal_ca required for SWS optimization")
        
        # Create EMTO inputs
        phase_config = {
            **config,
            'output_path': str(phase_path),
            'ca_ratios': [optimal_ca],
            'sws_values': parameter_values,
        }
        
        create_emto_inputs(phase_config)
        
        # Run calculations
        script_name = f"run_{config['job_name']}.sh"
        run_calculations_func(
            calculation_path=phase_path,
            script_name=script_name
        )
        
        # Validate calculations
        validate_calculations_func(
            phase_path=phase_path,
            ca_ratios=[optimal_ca],
            sws_values=parameter_values,
            job_name=config['job_name']
        )
        
        # Parse energies
        calculated_params = []
        energy_values = []
        
        for sws in parameter_values:
            file_id = f"{config['job_name']}_{optimal_ca:.2f}_{sws:.2f}"
            kfcd_file = phase_path / "fcd" / f"{file_id}.prn"
            
            if kfcd_file.exists():
                try:
                    results = parse_kfcd(str(kfcd_file), functional=config.get('functional', 'GGA'))
                    if results.total_energy is not None:
                        calculated_params.append(sws)
                        energy_values.append(results.energies_by_functional['system']['GGA'])
                        print(f"  SWS = {sws:.4f}: E = {results.energies_by_functional['system']['GGA']:.6f} Ry")
                except Exception as e:
                    print(f"  Warning: Failed to parse {kfcd_file}: {e}")
            else:
                print(f"  Warning: KFCD output not found: {kfcd_file}")
        
    elif parameter_name == 'ca':
        # c/a optimization: vary c/a, keep SWS fixed
        initial_sws = other_params.get('initial_sws')
        if initial_sws is None:
            raise ValueError("initial_sws required for c/a optimization")
        
        if isinstance(initial_sws, list):
            initial_sws = initial_sws[0]  # Use first value if list
        
        # Create EMTO inputs
        phase_config = {
            **config,
            'output_path': str(phase_path),
            'ca_ratios': parameter_values,
            'sws_values': [initial_sws],
        }
        
        create_emto_inputs(phase_config)
        
        # Run calculations
        script_name = f"run_{config['job_name']}.sh"
        run_calculations_func(
            calculation_path=phase_path,
            script_name=script_name
        )
        
        # Validate calculations
        validate_calculations_func(
            phase_path=phase_path,
            ca_ratios=parameter_values,
            sws_values=[initial_sws],
            job_name=config['job_name']
        )
        
        # Parse energies
        calculated_params = []
        energy_values = []
        
        for ca in parameter_values:
            file_id = f"{config['job_name']}_{ca:.2f}_{initial_sws:.2f}"
            kfcd_file = phase_path / "fcd" / f"{file_id}.prn"
            
            if kfcd_file.exists():
                try:
                    results = parse_kfcd(str(kfcd_file), functional=config.get('functional', 'GGA'))
                    if results.total_energy is not None:
                        calculated_params.append(ca)
                        energy_values.append(results.energies_by_functional['system']['GGA'])
                        print(f"  c/a = {ca:.4f}: E = {results.energies_by_functional['system']['GGA']:.6f} Ry")
                except Exception as e:
                    print(f"  Warning: Failed to parse {kfcd_file}: {e}")
            else:
                print(f"  Warning: KFCD output not found: {kfcd_file}")
    else:
        raise ValueError(f"Unknown parameter_name: {parameter_name}. Must be 'sws' or 'ca'")
    
    if not calculated_params:
        raise RuntimeError(f"No successful calculations for {parameter_name} values")
    
    return calculated_params, energy_values


def optimize_sws(
    structure: Dict[str, Any],
    sws_values: List[float],
    optimal_ca: float,
    config: Dict[str, Any],
    base_path: Path,
    run_calculations_func: Callable,
    validate_calculations_func: Callable,
    run_eos_fit_func: Callable,
    results_dict: Dict[str, Any]
) -> Tuple[float, Dict[str, Any]]:
    """
    Phase 2: SWS optimization at optimal c/a ratio.

    Creates EMTO inputs, runs calculations, parses energies, fits EOS,
    extracts optimal SWS, and calculates derived parameters.

    Parameters
    ----------
    structure : dict
        Structure dictionary from create_emto_structure()
    sws_values : list of float
        List of SWS values to test
    optimal_ca : float
        Optimal c/a ratio from Phase 1
    config : dict
        Configuration dictionary
    base_path : Path
        Base output directory
    run_calculations_func : callable
        Function to run calculations
    validate_calculations_func : callable
        Function to validate calculations
    run_eos_fit_func : callable
        Function to run EOS fit
    results_dict : dict
        Workflow results dictionary to update

    Returns
    -------
    tuple of (float, dict)
        optimal_sws : Optimal SWS value from EOS fit
        results : Dictionary with EOS results, energy data, and derived parameters

    Raises
    ------
    RuntimeError
        If calculations fail or output files not found
    """
    print(f"\n{'#'*70}")
    print("# PHASE 2: SWS OPTIMIZATION")
    print(f"{'#'*70}\n")

    # Create phase subdirectory
    phase_path = base_path / "phase2_sws_optimization"
    phase_path.mkdir(parents=True, exist_ok=True)

    print(f"Creating EMTO inputs for {len(sws_values)} SWS values...")
    print(f"  Optimal c/a: {optimal_ca:.6f}")
    print(f"  SWS values: {sws_values}")
    print(f"  Output path: {phase_path}\n")

    # Create EMTO inputs with optimal c/a
    try:
        phase_config = {
            **config,  # All validated defaults from constructor
            'output_path': str(phase_path),  # Override for this phase
            'ca_ratios': [optimal_ca],
            'sws_values': sws_values,
            # Only override what's different for this phase
        }

        create_emto_inputs(phase_config)
    except Exception as e:
        raise RuntimeError(f"Failed to create EMTO inputs: {e}")

    # Run calculations
    script_name = f"run_{config['job_name']}.sh"
    run_calculations_func(
        calculation_path=phase_path,
        script_name=script_name
    )

    # Validate calculations completed successfully
    validate_calculations_func(
        phase_path=phase_path,
        ca_ratios=[optimal_ca],
        sws_values=sws_values,
        job_name=config['job_name']
    )

    # Parse energies from KFCD outputs
    print("\nParsing energies from KFCD outputs...")
    sws_parsed = []
    energy_values = []

    for sws in sws_values:
        file_id = f"{config['job_name']}_{optimal_ca:.2f}_{sws:.2f}"
        kfcd_file = phase_path / "fcd" / f"{file_id}.prn"

        if not kfcd_file.exists():
            raise RuntimeError(
                f"KFCD output not found: {kfcd_file}\n"
                f"Calculation may have failed. Check log files in {phase_path}"
            )

        try:
            results = parse_kfcd(str(kfcd_file), functional=config.get('functional', 'GGA'))
            if results.total_energy is None:
                raise RuntimeError(f"No total energy found in {kfcd_file}")

            sws_parsed.append(sws)
            energy_values.append(results.energies_by_functional['system']['GGA'])

            print(f"  SWS = {sws:.4f}: E = {results.energies_by_functional['system']['GGA']:.6f} Ry")

        except Exception as e:
            raise RuntimeError(f"Failed to parse {kfcd_file}: {e}")

    # Prepare data for EOS fitting
    # Always saves current workflow data to file (automatic)
    # Flag controls which data to use: all saved vs workflow only
    use_saved_data = config.get('eos_use_saved_data', False)
    sws_values_for_fit, energy_values_for_fit = prepare_data_for_eos_fit(
        sws_parsed, energy_values, phase_path, 'sws', use_saved_data
    )
    
    # Keep track of original workflow points (for Morse estimation after expansion)
    sws_workflow_points = list(sws_parsed)
    energy_workflow_points = list(energy_values)

    # Run EOS fit (with error handling for failed fits)
    # Initial fit: NO symmetric selection (fit all points to check if expansion needed)
    eos_fit_failed = False
    eos_fit_error_msg = None
    try:
        eos_fit_result = run_eos_fit_func(
            r_or_v_data=sws_values_for_fit,
            energy_data=energy_values_for_fit,
            output_path=phase_path,
            job_name=f"{config['job_name']}_sws",
            comment=f"SWS optimization for {config['job_name']} at c/a={optimal_ca:.4f}",
            eos_type=config.get('eos_type', 'MO88'),
            use_symmetric_selection=False  # No symmetric selection for initial fit
        )
        
        # Handle both old (2-tuple) and new (3-tuple) return signatures for backward compatibility
        if len(eos_fit_result) == 2:
            optimal_sws, eos_results = eos_fit_result
            symmetric_metadata = {}
        else:
            optimal_sws, eos_results, symmetric_metadata = eos_fit_result
        
        # Print warnings if any
        if symmetric_metadata.get('warnings'):
            print("\n⚠ Symmetric fit warnings:")
            for warning in symmetric_metadata['warnings']:
                print(f"  {warning}")
    
    except Exception as e:
        # EOS fit failed - proceed with expansion check using Morse estimation
        eos_fit_failed = True
        eos_fit_error_msg = str(e)
        print(f"\n⚠ EOS fit failed: {eos_fit_error_msg}")
        print("  Proceeding with expansion check using Morse estimation...")
        
        # Create dummy results for detect_expansion_needed
        from modules.inputs.eos_emto import EOSParameters
        dummy_params = EOSParameters(
            eos_type='morse',
            rwseq=float('nan'),
            v_eq=float('nan'),
            eeq=float('nan'),
            bmod=float('nan'),
            b_prime=0.0,
            gamma=0.0,
            fsumsq=float('inf'),
            fit_quality='failed'
        )
        eos_results = {'morse': dummy_params}
        optimal_sws = float('nan')
        symmetric_metadata = {}
    
    # Handle NaN values from EOS fit (always check, regardless of auto-expand setting)
    if not eos_fit_failed and np.isnan(optimal_sws):
        print(f"\n{'='*70}")
        print("⚠ WARNING: EOS fit returned NaN for optimal SWS!")
        print(f"{'='*70}")
        print(f"  The EOS executable completed but could not determine equilibrium.")
        print(f"  This often happens when the energy curve is monotonic or has insufficient curvature.")
        print(f"\n  Attempting fallback: Using Morse EOS estimation from data points...")
        
        try:
            morse_min, morse_energy, morse_info = estimate_morse_minimum(
                sws_workflow_points, energy_workflow_points
            )
            
            if morse_info['is_valid']:
                optimal_sws = morse_min
                print(f"  ✓ Morse estimation successful: optimal SWS = {optimal_sws:.6f} Bohr")
                print(f"    Fit quality (R²): {morse_info['r_squared']:.3f}")
                print(f"{'='*70}\n")
            else:
                if morse_info.get('error'):
                    print(f"  ✗ Morse estimation failed: {morse_info['error']}")
                else:
                    print(f"  ⚠ Morse fit quality is poor (R² = {morse_info['r_squared']:.3f})")
                    print(f"    Using estimated minimum: {morse_min:.6f} Bohr")
                    print(f"    (Warning: This estimate may be unreliable)")
                    optimal_sws = morse_min
                    print(f"{'='*70}\n")
        except Exception as e:
            print(f"  ✗ Morse estimation failed: {e}")
            print(f"\n  Cannot proceed without valid optimal SWS value.")
            print(f"  Suggestions:")
            print(f"    1. Check if energy values are reasonable")
            print(f"    2. Try a wider SWS range")
            print(f"    3. Enable 'eos_auto_expand_range: true' to automatically expand range")
            print(f"    4. Check EOS output file for details: {phase_path / f'{config[\"job_name\"]}_sws.out'}")
            print(f"{'='*70}\n")
            raise RuntimeError(
                f"EOS fit returned NaN and Morse estimation failed.\n"
                f"Initial SWS range: [{min(sws_workflow_points):.6f}, {max(sws_workflow_points):.6f}] Bohr\n"
                f"Energy range: [{min(energy_workflow_points):.6f}, {max(energy_workflow_points):.6f}] Ry\n"
                f"Cannot determine optimal SWS value."
            )
    
    # Always check if optimal value is outside range (warn user even if auto-expansion is disabled)
    if not eos_fit_failed and not np.isnan(optimal_sws):
        sws_min = min(sws_values_for_fit)
        sws_max = max(sws_values_for_fit)
        if optimal_sws < sws_min or optimal_sws > sws_max:
            print(f"\n{'='*70}")
            print("⚠ WARNING: Optimal SWS is outside the initial range!")
            print(f"{'='*70}")
            print(f"  Initial SWS range: [{sws_min:.6f}, {sws_max:.6f}] Bohr")
            print(f"  Optimal SWS from EOS: {optimal_sws:.6f} Bohr")
            if optimal_sws < sws_min:
                print(f"  → Optimal value is {sws_min - optimal_sws:.6f} Bohr BELOW minimum")
            else:
                print(f"  → Optimal value is {optimal_sws - sws_max:.6f} Bohr ABOVE maximum")
            print(f"\n  The EOS fit suggests the true minimum is outside your initial range.")
            print(f"  Consider:")
            print(f"    1. Enabling 'eos_auto_expand_range: true' in config to automatically expand")
            print(f"    2. Re-running with a wider initial SWS range")
            print(f"    3. Using initial_sws: {optimal_sws:.6f} as starting point")
            print(f"{'='*70}\n")
    
    # Check if expansion is needed
    expansion_metadata = {}
    expansion_used = False
    if config.get('eos_auto_expand_range', False):
        # If EOS fit failed, we definitely need expansion
        if eos_fit_failed:
            needs_expansion = True
            reason = f"EOS fit failed: {eos_fit_error_msg}"
        else:
            needs_expansion, reason = detect_expansion_needed(
                eos_results, sws_values_for_fit, energy_values_for_fit, optimal_sws
            )
        
        if needs_expansion:
            print(f"\n⚠ Expansion needed: {reason}")
            
            # Estimate Morse EOS minimum (use workflow points, not merged with saved data)
            morse_min, morse_energy, morse_info = estimate_morse_minimum(
                sws_workflow_points, energy_workflow_points
            )
            
            # Always use the calculated Morse minimum (global minimum of curve)
            # Warn if fit quality is poor, but still use the calculated value
            if not morse_info['is_valid']:
                if morse_info.get('error'):
                    print(f"  ⚠ Morse fit failed: {morse_info['error']}")
                    print(f"  Using minimum from data: {morse_min:.6f}")
                else:
                    print(f"  ⚠ Morse fit quality is poor (R² = {morse_info['r_squared']:.3f})")
                    print(f"  Using calculated Morse minimum: {morse_min:.6f}")
                    print(f"  (Fit quality is low - estimate may be unreliable)")
            else:
                print(f"  Morse EOS estimate: minimum at {morse_min:.6f} "
                      f"(R² = {morse_info['r_squared']:.3f})")
            
            # Generate new parameter vector (use same number of points as initial)
            initial_n_points = len(sws_values_for_fit)
            new_sws_values = generate_parameter_vector_around_estimate(
                estimated_minimum=morse_min,
                step_size=config.get('sws_step', 0.05),
                n_points=initial_n_points
            )
            
            # Identify which points need calculation
            existing_set = set(sws_values_for_fit)
            new_points_to_calculate = [v for v in new_sws_values if v not in existing_set]
            
            print(f"  Generating new vector with {len(new_sws_values)} points "
                  f"centered around {morse_min:.6f}")
            print(f"  New points to calculate: {len(new_points_to_calculate)}")
            print(f"  New range: [{min(new_sws_values):.4f}, {max(new_sws_values):.4f}]")
            
            # Dictionary to map SWS values to energies (for lookup)
            sws_to_energy = dict(zip(sws_workflow_points, energy_workflow_points))
            
            if new_points_to_calculate:
                print(f"  Calculating {len(new_points_to_calculate)} new points...")
                # Run calculations for new points
                new_sws_calculated, new_energy_values = run_calculations_for_parameter_values(
                    parameter_values=new_points_to_calculate,
                    parameter_name='sws',
                    other_params={'optimal_ca': optimal_ca},
                    phase_path=phase_path,
                    config=config,
                    structure=structure,
                    run_calculations_func=run_calculations_func,
                    validate_calculations_func=validate_calculations_func
                )
                
                # Update dictionary with new calculated values
                for sws, energy in zip(new_sws_calculated, new_energy_values):
                    sws_to_energy[sws] = energy
            else:
                print(f"  All points already calculated, using existing data")
            
            # For final fit, use ONLY the expanded parameter vector (new_sws_values)
            # Extract energies for these specific SWS values
            expanded_sws_values = []
            expanded_energy_values = []
            for sws in new_sws_values:
                if sws in sws_to_energy:
                    expanded_sws_values.append(sws)
                    expanded_energy_values.append(sws_to_energy[sws])
                else:
                    print(f"  ⚠ Warning: No energy found for SWS={sws:.4f}, skipping")
            
            # Sort by parameter value
            sorted_pairs = sorted(zip(expanded_sws_values, expanded_energy_values))
            expanded_sws_values = [s for s, e in sorted_pairs]
            expanded_energy_values = [e for s, e in sorted_pairs]
            
            # ALWAYS save all workflow data to file (automatic, no option)
            # Save combined data (original + expanded) for future use
            all_sws_values = sws_workflow_points + expanded_sws_values
            all_energy_values = energy_workflow_points + expanded_energy_values
            from modules.optimization.analysis import save_parameter_energy_data
            save_parameter_energy_data(phase_path, 'sws', all_sws_values, all_energy_values)
            
            # Choose data source for final fit based on user flag
            use_all_saved_for_final_fit = config.get('eos_use_all_saved_for_final_fit', False)
            if use_all_saved_for_final_fit:
                # Use all saved data from file (may include previous runs)
                saved_sws, saved_energy = load_parameter_energy_data(phase_path, 'sws')
                if saved_sws:
                    print(f"  Using all {len(saved_sws)} saved points for final fit")
                    final_sws_values = saved_sws
                    final_energy_values = saved_energy
                else:
                    print(f"  No saved file found, using expanded parameter vector")
                    final_sws_values = expanded_sws_values
                    final_energy_values = expanded_energy_values
            else:
                # Use ONLY the expanded parameter vector (default)
                print(f"  Using expanded parameter vector only ({len(expanded_sws_values)} points) for final fit")
                final_sws_values = expanded_sws_values
                final_energy_values = expanded_energy_values
            
            # Re-fit EOS with selected data (symmetric selection only if user enabled it)
            try:
                eos_fit_result = run_eos_fit_func(
                    r_or_v_data=final_sws_values,
                    energy_data=final_energy_values,
                    output_path=phase_path,
                    job_name=f"{config['job_name']}_sws",
                    comment=f"SWS optimization (after expansion) for {config['job_name']} at c/a={optimal_ca:.4f}",
                    eos_type=config.get('eos_type', 'MO88'),
                    use_symmetric_selection=config.get('symmetric_fit', False)  # Use config setting after expansion
                )
                
                # Handle return signature
                if len(eos_fit_result) == 2:
                    optimal_sws, eos_results = eos_fit_result
                    symmetric_metadata = {}
                else:
                    optimal_sws, eos_results, symmetric_metadata = eos_fit_result
                
                # Check if converged after expansion
                # Don't check monotonicity after expansion - only check if equilibrium is within range
                needs_expansion_again, reason_again = detect_expansion_needed(
                    eos_results, final_sws_values, final_energy_values, optimal_sws,
                    check_monotonic=False  # Skip monotonic check after expansion
                )
            except Exception as e:
                # Post-expansion fit also failed - estimate and suggest value
                print(f"\n⚠ Post-expansion EOS fit failed: {e}")
                needs_expansion_again = True
                reason_again = f"Post-expansion EOS fit failed: {e}"
                # Create dummy results for estimation
                from modules.inputs.eos_emto import EOSParameters
                dummy_params = EOSParameters(
                    eos_type='morse',
                    rwseq=float('nan'),
                    v_eq=float('nan'),
                    eeq=float('nan'),
                    bmod=float('nan'),
                    b_prime=0.0,
                    gamma=0.0,
                    fsumsq=float('inf'),
                    fit_quality='failed'
                )
                eos_results = {'morse': dummy_params}
                optimal_sws = float('nan')
                symmetric_metadata = {}
            
            if needs_expansion_again:
                # Estimate Morse EOS from final fit data and suggest value
                morse_min2, _, morse_info2 = estimate_morse_minimum(
                    final_sws_values, final_energy_values
                )
                
                print(f"\n⚠ EOS fit still not adequate after expansion")
                print(f"  Estimated equilibrium from final fit data: {morse_min2:.6f}")
                if morse_info2.get('morse_params'):
                    print(f"  Morse fit R²: {morse_info2['r_squared']:.3f}")
                
                suggested_initial = morse_min2 if morse_info2['is_valid'] else optimal_sws
                
                raise RuntimeError(
                    f"Failed to find equilibrium after expansion.\n\n"
                    f"Initial range: [{min(sws_values_for_fit):.6f}, {max(sws_values_for_fit):.6f}]\n"
                    f"Expanded range: [{min(expanded_sws_values):.6f}, {max(expanded_sws_values):.6f}]\n"
                    f"Final fit used: {len(final_sws_values)} points\n"
                    f"Reason: {reason_again}\n\n"
                    f"Estimated equilibrium from final fit data: {morse_min2:.6f}\n"
                    f"Fit quality (R²): {morse_info2['r_squared']:.3f}\n\n"
                    f"SUGGESTION: Re-run optimization with:\n"
                    f"  initial_sws: {suggested_initial:.6f}\n"
                    f"  (or sws_values centered around {suggested_initial:.6f})"
                )
            
            # Update for results - use final fit values
            sws_values_for_fit = final_sws_values
            energy_values_for_fit = final_energy_values
            
            expansion_metadata = {
                'expansion_used': True,
                'morse_estimate': morse_min,
                'expanded_range': (min(expanded_sws_values), max(expanded_sws_values)),
                'points_added': len(new_points_to_calculate) if new_points_to_calculate else 0,
                'converged_after_expansion': not needs_expansion_again
            }
            expansion_used = True
    
    # If no expansion was needed and symmetric_fit is enabled, run final symmetric fit
    if not expansion_used and config.get('symmetric_fit', False):
        # Initial fit was done without symmetric selection - now run final fit with symmetric selection
        print(f"\n{'='*70}")
        print(f"RUNNING FINAL SYMMETRIC FIT")
        print(f"{'='*70}")
        print(f"Selecting {config.get('n_points_final', 7)} points centered around equilibrium...")
        
        try:
            eos_fit_result = run_eos_fit_func(
                r_or_v_data=sws_values_for_fit,
                energy_data=energy_values_for_fit,
                output_path=phase_path,
                job_name=f"{config['job_name']}_sws",
                comment=f"SWS optimization (final symmetric fit) for {config['job_name']} at c/a={optimal_ca:.4f}",
                eos_type=config.get('eos_type', 'MO88'),
                use_symmetric_selection=True  # Enable symmetric selection for final fit
            )
            
            # Handle return signature
            if len(eos_fit_result) == 2:
                optimal_sws, eos_results = eos_fit_result
                symmetric_metadata = {}
            else:
                optimal_sws, eos_results, symmetric_metadata = eos_fit_result
            
            # Print warnings if any
            if symmetric_metadata.get('warnings'):
                print("\n⚠ Symmetric fit warnings:")
                for warning in symmetric_metadata['warnings']:
                    print(f"  {warning}")
            
            print(f"\n✓ Final symmetric fit completed: optimal value = {optimal_sws:.6f}")
            print(f"{'='*70}\n")
            
        except Exception as e:
            print(f"\n⚠ Final symmetric fit failed: {e}")
            print("  Using initial fit results instead.")
            # Keep the initial fit results (already set above)

    # Generate EOS plot
    try:
        from modules.optimization.analysis import plot_eos_fit

        # Determine which EOS fit to plot (default to morse).
        # Supported EOS fit flags from eos.exe: MO88, MU37, POLN, SPLN, ALL.
        eos_type_map = {
            'MO88': 'morse',
            'POLN': 'polynomial',
            'SPLN': 'spline',
            'MU37': 'murnaghan',
            'ALL': 'morse'  # Default to morse if ALL was used
        }
        plot_eos_type = eos_type_map.get(config.get('eos_type', 'MO88'), 'morse')

        # Use final fit output if symmetric selection was used, otherwise use initial fit
        if symmetric_metadata.get('symmetric_selection_used'):
            eos_output_file = phase_path / f"{config['job_name']}_sws_final.out"
        else:
            eos_output_file = phase_path / f"{config['job_name']}_sws.out"
        plot_eos_fit(
            eos_output_file=eos_output_file,
            output_path=phase_path,
            variable_name='R_WS',
            variable_units='Bohr',
            title=f"Wigner-Seitz Radius Optimization - {config['job_name']}",
            eos_type=plot_eos_type
        )
    except Exception as e:
        print(f"Warning: Failed to generate EOS plot: {e}")

    # Calculate derived parameters
    # SWS is in atomic units (Bohr), convert to lattice parameters in Angstroms
    bohr_to_angstrom = 0.529177210903

    # Volume per atom in Bohr^3
    volume_per_atom = (4/3) * np.pi * optimal_sws**3

    # Total unit cell volume in Bohr^3
    total_volume_bohr = volume_per_atom * structure['NQ3']

    # Convert to Angstrom^3
    total_volume_angstrom = total_volume_bohr * (bohr_to_angstrom**3)

    # Calculate lattice parameters based on lattice type
    lat_type = structure['lat']

    if lat_type in [1, 2, 3]:  # SC, FCC, BCC (cubic)
        # For cubic: V = a^3
        a_optimal = total_volume_angstrom ** (1/3)
        c_optimal = a_optimal
    elif lat_type == 4:  # HCP
        # For HCP: V = a^2 * c * sqrt(3)/2
        # With c/a ratio: c = a * c/a
        # V = a^3 * c/a * sqrt(3)/2
        # a = (V * 2 / (c/a * sqrt(3)))^(1/3)
        a_optimal = (total_volume_angstrom * 2 / (optimal_ca * np.sqrt(3))) ** (1/3)
        c_optimal = a_optimal * optimal_ca
    elif lat_type == 5:  # BCT
        # For BCT: V = a^2 * c
        # With c/a ratio: c = a * c/a
        # V = a^3 * c/a
        # a = (V / c/a)^(1/3)
        a_optimal = (total_volume_angstrom / optimal_ca) ** (1/3)
        c_optimal = a_optimal * optimal_ca
    else:
        # Generic tetragonal approximation
        a_optimal = (total_volume_angstrom / optimal_ca) ** (1/3)
        c_optimal = a_optimal * optimal_ca

    derived_params = {
        'optimal_sws_bohr': optimal_sws,
        'optimal_ca': optimal_ca,
        'volume_per_atom_bohr3': volume_per_atom,
        'total_volume_angstrom3': total_volume_angstrom,
        'a_angstrom': a_optimal,
        'c_angstrom': c_optimal,
        'lattice_type': lat_type,
        'lattice_name': structure.get('lattice_name', 'Unknown')
    }

    # Extract final selected values if symmetric selection was used
    sws_values_final = None
    energy_values_final = None
    if symmetric_metadata.get('symmetric_selection_used'):
        selected_indices = symmetric_metadata.get('selected_indices', [])
        sws_values_final = [sws_values_for_fit[i] for i in selected_indices]
        energy_values_final = [energy_values_for_fit[i] for i in selected_indices]
    
    # Save results
    phase_results = {
        'optimal_sws': optimal_sws,
        'optimal_ca': optimal_ca,
        'sws_values': sws_values_for_fit,
        'energy_values': energy_values_for_fit,
        'eos_type': config.get('eos_type', 'MO88'),
        'eos_fits': {
            name: {
                'rwseq': params.rwseq,
                'v_eq': params.v_eq,
                'eeq': params.eeq,
                'bulk_modulus': params.bmod * 0.1  # Convert kBar to GPa
            }
            for name, params in eos_results.items()
        },
        'derived_parameters': derived_params
    }
    
    # Add symmetric fit metadata if available
    if symmetric_metadata:
        phase_results['symmetric_fit_metadata'] = symmetric_metadata
        if sws_values_final is not None:
            phase_results['sws_values_final'] = sws_values_final
        if energy_values_final is not None:
            phase_results['energy_values_final'] = energy_values_final
    
    # Add expansion metadata if available
    if expansion_metadata:
        phase_results['expansion_metadata'] = expansion_metadata

    results_file = phase_path / "sws_optimization_results.json"
    with open(results_file, 'w') as f:
        json.dump(phase_results, f, indent=2)

    print(f"\n✓ SWS optimization results saved to: {results_file}")
    print(f"✓ Optimal SWS: {optimal_sws:.6f} Bohr")
    print(f"\nDerived lattice parameters:")
    print(f"  a = {a_optimal:.6f} Å")
    print(f"  c = {c_optimal:.6f} Å")
    print(f"  c/a = {optimal_ca:.6f}")
    print(f"  Volume = {total_volume_angstrom:.6f} Å³")

    # Store in workflow results
    results_dict['phase2_sws_optimization'] = phase_results

    return optimal_sws, phase_results


def run_optimized_calculation(
    structure: Dict[str, Any],
    optimal_ca: float,
    optimal_sws: float,
    config: Dict[str, Any],
    base_path: Path,
    run_calculations_func: Callable,
    validate_calculations_func: Callable,
    results_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Phase 3: Run final calculation with optimized parameters.

    Creates EMTO inputs with optimal c/a and SWS, runs calculation,
    and parses results.

    Parameters
    ----------
    structure : dict
        Structure dictionary from create_emto_structure()
    optimal_ca : float
        Optimal c/a ratio from Phase 1
    optimal_sws : float
        Optimal SWS value from Phase 2
    config : dict
        Configuration dictionary
    base_path : Path
        Base output directory
    run_calculations_func : callable
        Function to run calculations
    validate_calculations_func : callable
        Function to validate calculations
    results_dict : dict
        Workflow results dictionary to update

    Returns
    -------
    dict
        Dictionary with final calculation results

    Raises
    ------
    RuntimeError
        If calculation fails or output files not found
    """
    print(f"\n{'#'*70}")
    print("# PHASE 3: OPTIMIZED STRUCTURE CALCULATION")
    print(f"{'#'*70}\n")

    # Create phase subdirectory
    phase_path = base_path / "phase3_optimized_calculation"
    phase_path.mkdir(parents=True, exist_ok=True)

    print(f"Creating EMTO inputs with optimized parameters...")
    print(f"  Optimal c/a: {optimal_ca:.6f}")
    print(f"  Optimal SWS: {optimal_sws:.6f} Bohr")
    print(f"  Output path: {phase_path}\n")

    # Create EMTO inputs with optimal parameters
    try:
        phase_config = {
            **config,  # All validated defaults from constructor
            'output_path': str(phase_path),  # Override for this phase
            'ca_ratios': [optimal_ca],
            'sws_values': [optimal_sws],
            # Only override what's different for this phase
        }

        create_emto_inputs(phase_config)
    except Exception as e:
        raise RuntimeError(f"Failed to create EMTO inputs: {e}")

    # Run calculation
    script_name = f"run_{config['job_name']}.sh"
    run_calculations_func(
        calculation_path=phase_path,
        script_name=script_name
    )

    # Validate calculations completed successfully
    validate_calculations_func(
        phase_path=phase_path,
        ca_ratios=[optimal_ca],
        sws_values=[optimal_sws],
        job_name=config['job_name']
    )

    # Parse results from KFCD and KGRN outputs
    print("\nParsing optimized calculation results...")

    file_id = f"{config['job_name']}_{optimal_ca:.2f}_{optimal_sws:.2f}"
    kfcd_file = phase_path / "fcd" / f"{file_id}.prn"
    kgrn_file = phase_path / "pot" / f"{file_id}.prn"

    if not kfcd_file.exists():
        raise RuntimeError(
            f"KFCD output not found: {kfcd_file}\n"
            f"Calculation may have failed. Check log files in {phase_path}"
        )

    # Parse KFCD
    try:
        kfcd_results = parse_kfcd(str(kfcd_file), functional=config.get('functional', 'GGA'))
        print(f"\n✓ KFCD results parsed")
        print(f"  Total energy: {kfcd_results.energies_by_functional['system']['GGA']:.6f} Ry")
    except Exception as e:
        raise RuntimeError(f"Failed to parse {kfcd_file}: {e}")

    # Parse KGRN if available
    kgrn_results = None
    if kgrn_file.exists():
        try:
            kgrn_results = parse_kgrn(
                str(kgrn_file),
                kfcd_results.concentrations,
                kfcd_results.iq_to_element,
                kfcd_results.atoms
            )
            print(f"✓ KGRN results parsed")
            if kgrn_results.energies_by_functional['system']['GGA']:
                print(f"  Total energy: {kgrn_results.energies_by_functional['system']['GGA']:.6f} Ry")
        except Exception as e:
            print(f"Warning: Failed to parse KGRN output: {e}")

    # Save results
    phase_results = {
        'optimal_ca': optimal_ca,
        'optimal_sws': optimal_sws,
        'kfcd_total_energy': kfcd_results.energies_by_functional['system']['GGA'],
        'kgrn_total_energy': kgrn_results.energies_by_functional['system']['GGA'] if kgrn_results else None,
        'magnetic_moments': {
            f"IQ{iq}_ITA{ita}_{atom}": moment
            for (iq, ita, atom), moment in kfcd_results.magnetic_moments.items()
        } if kfcd_results.magnetic_moments else {},
        'total_magnetic_moment': kfcd_results.total_magnetic_moment,
        'file_id': file_id
    }

    results_file = phase_path / "optimized_results.json"
    with open(results_file, 'w') as f:
        json.dump(phase_results, f, indent=2)

    print(f"\n✓ Optimized calculation results saved to: {results_file}")

    # Store in workflow results
    results_dict['phase3_optimized_calculation'] = phase_results

    return phase_results
