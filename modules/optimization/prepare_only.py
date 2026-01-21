#!/usr/bin/env python3
"""
Prepare-only mode for EMTO workflow.

Creates input files for Phase 1 and Phase 2 without running calculations.
"""

from pathlib import Path
from typing import Dict, Any, List, Callable, Tuple


def run_prepare_only_mode(
    config: Dict[str, Any],
    base_path: Path,
    prepare_ranges_func: Callable[[Any, Any, Dict[str, Any]], Tuple[List[float], List[float]]]
) -> Dict[str, Any]:
    """
    Prepare-only mode: Create input files for Phase 1 & 2, skip Phase 3.

    Creates EMTO input files for exploratory calculations (c/a and SWS sweeps)
    without running any calculations. Phase 3 (final optimized calculation) is
    skipped entirely - no inputs created.

    Parameters
    ----------
    config : dict
        Configuration dictionary with all workflow settings
    base_path : Path
        Base output directory for the workflow
    prepare_ranges_func : callable
        Function to prepare c/a and SWS ranges
        Signature: (ca_ratios, sws_values, structure) -> (ca_list, sws_list)

    Returns
    -------
    dict
        Empty results dictionary with prepare_only flag set

    Notes
    -----
    This mode is useful for:
    - Validating configurations before expensive calculations
    - Generating inputs to run manually or on different systems
    - Debugging input file generation
    """
    print("\n" + "#" * 80)
    print("# PREPARE-ONLY MODE: Creating Input Files")
    print("#" * 80)
    print(f"\nJob: {config['job_name']}")
    print(f"Output: {base_path}")
    print(f"Mode: Input file generation only (no calculations)")
    print("#" * 80)

    # Step 1: Create structure
    print("\n" + "=" * 80)
    print("STEP 1: STRUCTURE CREATION")
    print("=" * 80)

    try:
        from modules.structure_builder import create_emto_structure

        if config.get('cif_file'):
            print(f"Creating structure from CIF: {config['cif_file']}")
            structure_pmg, structure = create_emto_structure(
                cif_file=config['cif_file'],
                user_magnetic_moments=config.get('user_magnetic_moments')
            )
        else:
            print(f"Creating structure from parameters...")
            structure_pmg, structure = create_emto_structure(
                lat=config['lat'],
                a=config['a'],
                sites=config['sites'],
                b=config.get('b'),
                c=config.get('c'),
                alpha=config.get('alpha', 90),
                beta=config.get('beta', 90),
                gamma=config.get('gamma', 90),
                user_magnetic_moments=config.get('user_magnetic_moments')
            )

        structure['structure_pmg'] = structure_pmg

        print(f"✓ Structure created")
        print(f"  Lattice: {structure['lattice_name']} (type {structure['lat']})")
        print(f"  Atoms: {structure['NQ3']}")

    except Exception as e:
        raise RuntimeError(f"Failed to create structure: {e}")

    # Step 2: Prepare parameter ranges
    print("\n" + "=" * 80)
    print("STEP 2: PARAMETER PREPARATION")
    print("=" * 80)

    try:
        ca_list, sws_list = prepare_ranges_func(
            config.get('ca_ratios'),
            config.get('sws_values'),
            structure
        )
    except Exception as e:
        raise RuntimeError(f"Failed to prepare parameter ranges: {e}")

    # Phase 1: Create c/a optimization inputs (if enabled)
    if config.get('optimize_ca', False):
        print("\n" + "=" * 80)
        print("PHASE 1: Creating c/a optimization inputs")
        print("=" * 80)

        try:
            initial_sws = config.get('initial_sws', [sws_list[len(sws_list)//2]])

            # Create Phase 1 directory
            phase_path = base_path / "phase1_ca_optimization"
            phase_path.mkdir(parents=True, exist_ok=True)

            print(f"Creating inputs for {len(ca_list)} c/a values...")
            print(f"  c/a values: {ca_list}")
            print(f"  initial SWS: {initial_sws}")
            print(f"  Output path: {phase_path}\n")

            # Create inputs
            from modules.create_input import create_emto_inputs

            phase_config = {
                **config,
                'output_path': str(phase_path),
                'ca_ratios': ca_list,
                'sws_values': initial_sws,
            }

            create_emto_inputs(phase_config)

            print(f"\n✓ Phase 1 input files created in: {phase_path}")

        except Exception as e:
            raise RuntimeError(f"Failed to create Phase 1 inputs: {e}")
    else:
        print("\n✓ Phase 1 (c/a optimization) skipped (optimize_ca=False)")

    # Phase 2: Create SWS optimization inputs (if enabled)
    if config.get('optimize_sws', False):
        print("\n" + "=" * 80)
        print("PHASE 2: Creating SWS optimization inputs")
        print("=" * 80)

        try:
            # Use first c/a value for SWS sweep (force 1.0 for cubic lattices)
            if structure.get('lat') in [1, 2, 3]:  # SC, FCC, BCC
                optimal_ca = 1.0
                print(f"Cubic lattice detected (LAT={structure.get('lat')}): c/a forced to 1.0")
            else:
                # Prioritize actual input value from structure/CIF over auto-generated list
                optimal_ca = structure.get('coa') if structure.get('coa') is not None else (ca_list[0] if ca_list else 1.0)

            # Create Phase 2 directory
            phase_path = base_path / "phase2_sws_optimization"
            phase_path.mkdir(parents=True, exist_ok=True)

            print(f"Creating inputs for {len(sws_list)} SWS values...")
            print(f"  c/a: {optimal_ca:.6f}")
            print(f"  SWS values: {sws_list}")
            print(f"  Output path: {phase_path}\n")

            # Create inputs
            from modules.create_input import create_emto_inputs

            phase_config = {
                **config,
                'output_path': str(phase_path),
                'ca_ratios': [optimal_ca],
                'sws_values': sws_list,
            }

            create_emto_inputs(phase_config)

            print(f"\n✓ Phase 2 input files created in: {phase_path}")

        except Exception as e:
            raise RuntimeError(f"Failed to create Phase 2 inputs: {e}")
    else:
        print("\n✓ Phase 2 (SWS optimization) skipped (optimize_sws=False)")

    # Phase 3: Explicitly skip
    print("\n" + "=" * 80)
    print("PHASE 3: Skipping final optimized calculation (prepare_only mode)")
    print("=" * 80)
    print("✓ Phase 3 inputs NOT created (by design in prepare_only mode)")

    # Summary
    print("\n" + "#" * 80)
    print("# PREPARE-ONLY MODE COMPLETED")
    print("#" * 80)
    print(f"\n✓ Input files created for:")
    if config.get('optimize_ca'):
        print(f"  - Phase 1 (c/a optimization): {len(ca_list)} calculations")
    if config.get('optimize_sws'):
        print(f"  - Phase 2 (SWS optimization): {len(sws_list)} calculations")
    print(f"\n✓ Phase 3 (final calculation) intentionally skipped")
    print(f"\n✓ All files saved in: {base_path}")
    print(f"\n✓ No calculations were executed (prepare_only=True)")
    print("#" * 80 + "\n")

    return {'prepare_only': True}
