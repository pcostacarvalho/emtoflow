"""
CLI entry point for generating alloy composition YAML files.

Usage (after installation):

    emtoflow-generate-percentages master_config.yaml [output_dir] [--preview]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from emtoflow.modules.generate_percentages import (
    generate_percentage_configs,
    preview_compositions,
)
from emtoflow import load_and_validate_config


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="emtoflow-generate-percentages",
        description="Generate YAML files for alloy composition loops.",
    )
    parser.add_argument(
        "master_config",
        help="Path to master YAML configuration with loop_perc settings.",
    )
    parser.add_argument(
        "output_dir",
        nargs="?",
        default=None,
        help="Optional output directory for generated YAML files "
        "(default: same directory as master config).",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Preview compositions without generating files.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    master_config = Path(args.master_config)

    if not master_config.exists():
        print(f"✗ Error: Config file not found: {master_config}", file=sys.stderr)
        print("\nPlease provide a valid path to the master YAML configuration.")
        return 1

    if args.preview:
        try:
            preview_compositions(str(master_config))
            return 0
        except Exception as exc:  # pragma: no cover - defensive logging
            print("\n✗ Error during preview:", file=sys.stderr)
            print(f"  {exc}", file=sys.stderr)
            import traceback

            print("\nFull traceback:", file=sys.stderr)
            traceback.print_exc()
            return 1

    output_dir = args.output_dir

    try:
        print("=" * 80)
        print("GENERATE YAML FILES FOR ALLOY COMPOSITIONS")
        print("=" * 80)
        print(f"\nMaster config: {master_config}")

        if output_dir:
            print(f"Output directory: {output_dir}")
        else:
            print(f"Output directory: {master_config.parent} (same as master)")

        print()

        generated_files = generate_percentage_configs(str(master_config), output_dir)

        print("=" * 80)
        print("✓ GENERATION COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print(f"\nGenerated {len(generated_files)} YAML files")

        if output_dir:
            output_location = Path(output_dir)
        else:
            output_location = master_config.parent

        print(f"Location: {output_location}")
        print("\n" + "-" * 80)
        print("NEXT STEPS:")
        print("-" * 80)
        print("\n1. Review the generated YAML files to verify compositions")

        config_dict = load_and_validate_config(str(master_config))
        if config_dict.get("create_master_job_script", False):
            if generated_files:
                scripts_dir = Path(generated_files[0]).parent
                print("\n2. Submit all jobs at once using the master script:")
                print(f"\n   bash {scripts_dir / 'master_job_script.sh'}")
                print("\n   Or submit individual jobs:")
                print(f"\n   sbatch {scripts_dir / 'job_COMPOSITION.sh'}")
                print("\n   Examples:")
                for filepath in generated_files[:3]:
                    filename = Path(filepath).stem
                    print(f"     sbatch {scripts_dir / f'job_{filename}.sh'}")
                if len(generated_files) > 3:
                    print(f"     ... ({len(generated_files) - 3} more jobs)")
            else:
                print("\n2. No files generated, cannot create job scripts")
        else:
            print("\n2. Submit each composition individually:")
            print(f"\n   emtoflow-opt {output_location / 'COMPOSITION.yaml'}")
            print("\n   Examples:")
            for filepath in generated_files[:3]:
                filename = Path(filepath).name
                print(f"     emtoflow-opt {output_location / filename}")
            if len(generated_files) > 3:
                print(f"     ... ({len(generated_files) - 3} more files)")

        print("\n" + "=" * 80 + "\n")
        return 0

    except KeyboardInterrupt:
        print("\n\n✗ Generation interrupted by user.")
        return 1

    except ValueError as exc:
        print("\n✗ Configuration Error:", file=sys.stderr)
        print(f"  {exc}", file=sys.stderr)
        print("\nPlease fix the configuration and try again.", file=sys.stderr)
        return 1

    except Exception as exc:  # pragma: no cover - defensive logging
        print("\n✗ Error during YAML generation:", file=sys.stderr)
        print(f"  {exc}", file=sys.stderr)
        import traceback

        print("\nFull traceback:", file=sys.stderr)
        traceback.print_exc()
        print("\nIf this is unexpected, please report this issue.", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

