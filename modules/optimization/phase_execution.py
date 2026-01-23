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

    # Run EOS fit
    optimal_ca, eos_results = run_eos_fit_func(
        r_or_v_data=ca_values,
        energy_data=energy_values,
        output_path=phase_path,
        job_name=f"{config['job_name']}_ca",
        comment=f"c/a optimization for {config['job_name']}",
        eos_type=config.get('eos_type', 'MO88')
    )

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

    # Save results
    phase_results = {
        'optimal_ca': optimal_ca,
        'ca_values': ca_values,
        'energy_values': energy_values,
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

    results_file = phase_path / "ca_optimization_results.json"
    with open(results_file, 'w') as f:
        json.dump(phase_results, f, indent=2)

    print(f"\n✓ c/a optimization results saved to: {results_file}")
    print(f"✓ Optimal c/a ratio: {optimal_ca:.6f}")

    # Store in workflow results
    results_dict['phase1_ca_optimization'] = phase_results

    return optimal_ca, phase_results


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

    # Run EOS fit
    optimal_sws, eos_results = run_eos_fit_func(
        r_or_v_data=sws_parsed,
        energy_data=energy_values,
        output_path=phase_path,
        job_name=f"{config['job_name']}_sws",
        comment=f"SWS optimization for {config['job_name']} at c/a={optimal_ca:.4f}",
        eos_type=config.get('eos_type', 'MO88')
    )

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

    # Save results
    phase_results = {
        'optimal_sws': optimal_sws,
        'optimal_ca': optimal_ca,
        'sws_values': sws_parsed,
        'energy_values': energy_values,
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
