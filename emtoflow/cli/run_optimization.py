"""
CLI entry point for running the full optimization workflow.

Usage (after installation):

    emtoflow-opt path/to/config.yaml
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from emtoflow import OptimizationWorkflow, load_and_validate_config


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="emtoflow-opt",
        description="Run the full EMTOFlow optimization workflow from a YAML/JSON configuration.",
    )
    parser.add_argument(
        "config",
        help="Path to YAML or JSON configuration file.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config_path = Path(args.config)

    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        return 1

    try:
        config = load_and_validate_config(config_path)
        workflow = OptimizationWorkflow(config=config_path)
        results = workflow.run()

        print("\n" + "=" * 80)
        print("WORKFLOW COMPLETED SUCCESSFULLY")
        print("=" * 80)

        if "phase1_ca_optimization" in results:
            print("\n✓ Phase 1 (c/a optimization):")
            print(
                f"  Optimal c/a = "
                f"{results['phase1_ca_optimization']['optimal_ca']:.6f}"
            )

        if "phase2_sws_optimization" in results:
            print("\n✓ Phase 2 (SWS optimization):")
            sws_results = results["phase2_sws_optimization"]
            print(f"  Optimal SWS = {sws_results['optimal_sws']:.6f} Bohr")

            if "derived_parameters" in sws_results:
                params = sws_results["derived_parameters"]
                print("  Lattice parameters:")
                print(f"    a = {params['a_angstrom']:.6f} Å")
                print(f"    c = {params['c_angstrom']:.6f} Å")
                print(f"    V = {params['total_volume_angstrom3']:.6f} Å³")

        if "phase3_optimized_calculation" in results:
            print("\n✓ Phase 3 (optimized calculation):")
            final = results["phase3_optimized_calculation"]
            print(f"  Total energy = {final['kfcd_total_energy']:.6f} Ry")

            if final.get("total_magnetic_moment"):
                print(
                    f"  Total magnetic moment = "
                    f"{final['total_magnetic_moment']:.4f} μB"
                )

        print(f"\n✓ All results saved in: {workflow.base_path}")
        print(f"✓ Summary report: {workflow.base_path}/workflow_summary.txt")
        print("=" * 80 + "\n")
        return 0

    except KeyboardInterrupt:
        print("\n\nWorkflow interrupted by user.")
        return 1

    except Exception as exc:  # pragma: no cover - defensive logging
        print("\n✗ Error during workflow execution:", file=sys.stderr)
        print(f"  {exc}", file=sys.stderr)
        import traceback

        print("\nFull traceback:", file=sys.stderr)
        traceback.print_exc()
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

