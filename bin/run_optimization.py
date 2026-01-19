#!/usr/bin/env python3
"""
Complete Optimization Workflow Example

This script demonstrates how to run the complete EMTO optimization workflow
for c/a ratio and SWS optimization.

Usage:
    python run_optimization.py <config_file.yaml>

Example:
    python run_optimization.py ../files/systems/optimization_CuMg_fcc.yaml

The workflow will:
1. Create structure from CIF or parameters
2. Auto-generate or use provided c/a and SWS ranges
3. Optimize c/a ratio (if enabled)
4. Optimize SWS at optimal c/a (if enabled)
5. Run final calculation with optimized parameters
6. Generate DOS analysis (if enabled)
7. Create comprehensive summary report

All results are saved in organized subdirectories with JSON files
for easy post-processing and analysis.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.optimization_workflow import OptimizationWorkflow
from modules.alloy_loop import run_with_percentage_loop
from utils.config_parser import load_and_validate_config


def run_single_workflow(config):
    """
    Run workflow for a single configuration.

    Parameters
    ----------
    config : dict or str
        Configuration dictionary or path to config file

    Returns
    -------
    dict
        Workflow results
    """
    workflow = OptimizationWorkflow(config=config)
    return workflow.run()


def main():
    """Run complete optimization workflow from command line."""

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    config_file = sys.argv[1]

    if not Path(config_file).exists():
        print(f"Error: Config file not found: {config_file}")
        sys.exit(1)

    try:
        # Load and validate config
        config = load_and_validate_config(config_file)

        # Check if loop mode is enabled
        if config['loop_perc'] is not None and config['loop_perc'].get('enabled') is True:
            # Run with percentage loop
            results = run_with_percentage_loop(config, run_single_workflow)

            # Print summary
            print("\n" + "="*80)
            print("ALLOY LOOP COMPLETED SUCCESSFULLY")
            print("="*80)
            print(f"\nProcessed {len(results)} compositions")
            print(f"Results saved in: {config['output_path']}_alloy_loop")
            print("="*80 + "\n")

        else:
            # Run single workflow
            workflow = OptimizationWorkflow(config=config)
            results = workflow.run()

            # Print final summary for single workflow
            print("\n" + "="*80)
            print("WORKFLOW COMPLETED SUCCESSFULLY")
            print("="*80)

            if 'phase1_ca_optimization' in results:
                print(f"\n✓ Phase 1 (c/a optimization):")
                print(f"  Optimal c/a = {results['phase1_ca_optimization']['optimal_ca']:.6f}")

            if 'phase2_sws_optimization' in results:
                print(f"\n✓ Phase 2 (SWS optimization):")
                sws_results = results['phase2_sws_optimization']
                print(f"  Optimal SWS = {sws_results['optimal_sws']:.6f} Bohr")

                if 'derived_parameters' in sws_results:
                    params = sws_results['derived_parameters']
                    print(f"  Lattice parameters:")
                    print(f"    a = {params['a_angstrom']:.6f} Å")
                    print(f"    c = {params['c_angstrom']:.6f} Å")
                    print(f"    V = {params['total_volume_angstrom3']:.6f} Å³")

            if 'phase3_optimized_calculation' in results:
                print(f"\n✓ Phase 3 (optimized calculation):")
                final = results['phase3_optimized_calculation']
                print(f"  Total energy = {final['kfcd_total_energy']:.6f} Ry")

                if final.get('total_magnetic_moment'):
                    print(f"  Total magnetic moment = {final['total_magnetic_moment']:.4f} μB")

            print(f"\n✓ All results saved in: {workflow.base_path}")
            print(f"✓ Summary report: {workflow.base_path}/workflow_summary.txt")
            print("="*80 + "\n")

        sys.exit(0)

    except KeyboardInterrupt:
        print("\n\nWorkflow interrupted by user.")
        sys.exit(1)

    except Exception as e:
        print(f"\n✗ Error during workflow execution:")
        print(f"  {e}")

        import traceback
        print("\nFull traceback:")
        traceback.print_exc()

        sys.exit(1)


if __name__ == '__main__':
    main()
