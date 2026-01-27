#!/usr/bin/env python3
"""
Generate YAML Files for Alloy Percentage Loop
==============================================

This script generates multiple YAML configuration files from a master YAML,
each representing a different alloy composition percentage.

After generating the files, users can manually submit each composition
to run_optimization.py when ready.

If create_master_job_script is enabled in the master config, the script
will automatically create individual SLURM job scripts for each YAML file
and a master script to submit them all.

Usage:
    python bin/generate_percentages.py <master_config.yaml> [output_dir]

    Arguments:
        master_config.yaml : Master YAML with loop_perc configuration
        output_dir         : Optional directory for generated files
                            (default: same directory as master YAML)

Options:
    --preview : Preview compositions without generating files

Examples:
    # Generate YAML files in same directory as master
    python bin/generate_percentages.py configs/FePt_master.yaml

    # Generate YAML files in specific directory
    python bin/generate_percentages.py configs/FePt_master.yaml ./generated_configs/

    # Preview compositions before generating
    python bin/generate_percentages.py configs/FePt_master.yaml --preview

Next Steps:
    After generating files, submit each composition individually:

    python bin/run_optimization.py Fe50_Pt50.yaml
    python bin/run_optimization.py Fe60_Pt40.yaml
    ...

    Or if create_master_job_script is enabled, submit all jobs at once:

    bash <output_dir>/master_job_script.sh

    Or submit individual jobs to SLURM:
    sbatch job_Fe50_Pt50.sh
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.generate_percentages import (
    generate_percentage_configs,
    preview_compositions
)


def print_usage():
    """Print usage information."""
    print(__doc__)


def main():
    """Main entry point for CLI."""

    # Parse arguments
    if len(sys.argv) < 2 or '--help' in sys.argv or '-h' in sys.argv:
        print_usage()
        sys.exit(0 if '--help' in sys.argv or '-h' in sys.argv else 1)

    master_config = sys.argv[1]

    # Check if master config exists
    if not Path(master_config).exists():
        print(f"✗ Error: Config file not found: {master_config}")
        print(f"\nPlease provide a valid path to the master YAML configuration.")
        sys.exit(1)

    # Check for preview mode
    if '--preview' in sys.argv:
        try:
            preview_compositions(master_config)
            sys.exit(0)
        except Exception as e:
            print(f"\n✗ Error during preview:")
            print(f"  {e}")
            import traceback
            print("\nFull traceback:")
            traceback.print_exc()
            sys.exit(1)

    # Get output directory
    output_dir = None
    if len(sys.argv) > 2 and not sys.argv[2].startswith('--'):
        output_dir = sys.argv[2]

    try:
        print("=" * 80)
        print("GENERATE YAML FILES FOR ALLOY COMPOSITIONS")
        print("=" * 80)
        print(f"\nMaster config: {master_config}")

        if output_dir:
            print(f"Output directory: {output_dir}")
        else:
            print(f"Output directory: {Path(master_config).parent} (same as master)")

        print()

        # Generate files
        generated_files = generate_percentage_configs(master_config, output_dir)

        # Print success summary
        print("=" * 80)
        print("✓ GENERATION COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print(f"\nGenerated {len(generated_files)} YAML files")

        if output_dir:
            output_location = output_dir
        else:
            output_location = Path(master_config).parent

        print(f"Location: {output_location}")
        print("\n" + "-" * 80)
        print("NEXT STEPS:")
        print("-" * 80)
        print("\n1. Review the generated YAML files to verify compositions")
        
        # Check if job scripts were created
        from utils.config_parser import load_and_validate_config
        config_dict = load_and_validate_config(master_config)
        if config_dict.get('create_master_job_script', False):
            # Job scripts are created in the same directory as YAML files
            # Use the directory of the first generated file
            if generated_files:
                scripts_dir = Path(generated_files[0]).parent
                print("\n2. Submit all jobs at once using the master script:")
                print(f"\n   bash {scripts_dir / 'master_job_script.sh'}")
                print("\n   Or submit individual jobs:")
                print(f"\n   sbatch {scripts_dir / 'job_COMPOSITION.sh'}")
                print("\n   Examples:")
                for i, filepath in enumerate(generated_files[:3], 1):
                    filename = Path(filepath).stem
                    print(f"     sbatch {scripts_dir / f'job_{filename}.sh'}")
                if len(generated_files) > 3:
                    print(f"     ... ({len(generated_files) - 3} more jobs)")
            else:
                print("\n2. No files generated, cannot create job scripts")
        else:
            print("\n2. Submit each composition individually:")
            print(f"\n   python bin/run_optimization.py {Path(output_location) / 'COMPOSITION.yaml'}")
            print("\n   Examples:")
            # Show first 3 files as examples
            for i, filepath in enumerate(generated_files[:3], 1):
                filename = Path(filepath).name
                print(f"     python bin/run_optimization.py {Path(output_location) / filename}")
            if len(generated_files) > 3:
                print(f"     ... ({len(generated_files) - 3} more files)")
        
        print("\n" + "=" * 80 + "\n")

        sys.exit(0)

    except KeyboardInterrupt:
        print("\n\n✗ Generation interrupted by user.")
        sys.exit(1)

    except ValueError as e:
        # Configuration validation errors (user-friendly)
        print(f"\n✗ Configuration Error:")
        print(f"  {e}")
        print(f"\nPlease fix the configuration and try again.")
        sys.exit(1)

    except Exception as e:
        # Unexpected errors (with traceback)
        print(f"\n✗ Error during YAML generation:")
        print(f"  {e}")

        import traceback
        print("\nFull traceback:")
        traceback.print_exc()

        print(f"\nIf this is unexpected, please report this issue.")
        sys.exit(1)


if __name__ == '__main__':
    main()
