#!/usr/bin/env python3
"""
Create master job script for batch submission of multiple optimization runs.

This script generates a master SLURM script that submits separate jobs
for each YAML config file listed in a file.

Usage:
    python create_master_job_script.py <config_file.yaml>

The master script will:
1. Read list of YAML files from master_job_list_file
2. For each YAML file, create a job script that runs run_optimization.py
3. Submit each job script to SLURM

Example:
    python create_master_job_script.py config.yaml
    # Creates master_job_script.sh
    # Run: bash master_job_script.sh
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config_parser import load_and_validate_config


def create_master_job_script(config_file: str):
    """
    Create master job script for batch submission.
    
    Parameters
    ----------
    config_file : str
        Path to YAML config file containing master job settings
    """
    # Load config
    config = load_and_validate_config(config_file)
    
    # Get settings
    list_file = config.get('master_job_list_file', 'yaml_list.txt')
    account = config.get('slurm_account', 'naiss2025-1-38')
    prcs = config.get('prcs', 8)
    time_limit = config.get('slurm_time', '02:00:00')
    
    # Get path to run_optimization.py (relative to where script will be run)
    script_dir = Path(__file__).parent
    run_optimization_script = script_dir / "run_optimization.py"
    
    # Check if list file exists
    list_file_path = Path(list_file)
    if not list_file_path.exists():
        print(f"Error: List file not found: {list_file}")
        print(f"Please create {list_file} with one YAML file path per line")
        sys.exit(1)
    
    # Read YAML files from list
    yaml_files = []
    with open(list_file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                yaml_files.append(line)
    
    if not yaml_files:
        print(f"Error: No YAML files found in {list_file}")
        sys.exit(1)
    
    print(f"Found {len(yaml_files)} YAML files in {list_file}")
    
    # Get absolute path to run_optimization.py
    run_optimization_abs = run_optimization_script.resolve()
    
    # Create master script content
    master_script = f"""#!/bin/bash -l
# Master job script for batch submission
# Generated automatically - do not edit manually
# Submits separate jobs for each YAML config file

# Read YAML files from list file: {list_file}
while IFS= read -r i; do
    # Skip empty lines and comments
    [[ -z "$i" || "$i" =~ ^# ]] && continue
    
    # Extract job name from filename (remove extension)
    name=$(echo "$i" | cut -d '.' -f 1 | xargs basename)
    
    # Create job script for this YAML file
    cat > job_${{name}}.sh << EOF
#!/bin/bash -l
#SBATCH -A {account}
#SBATCH --exclusive
#SBATCH -n {prcs}
#SBATCH -t {time_limit}
#SBATCH -J ${{name}}_optimization

module load buildenv-intel/2023a-eb
module load Mambaforge/23.3.1-1-hpc1 

conda activate env

# Run optimization with this YAML file
python {run_optimization_abs} "$i"
EOF

    # Submit the job
    echo "Submitting job for $i (name: ${{name}})..."
    sbatch job_${{name}}.sh
    
    # Small delay to avoid overwhelming the scheduler
    sleep 1
    
done < {list_file_path.resolve()}

echo ""
echo "All jobs submitted!"
echo "Check status with: squeue -u $USER"
"""
    
    # Write master script
    master_script_path = Path("master_job_script.sh")
    with open(master_script_path, 'w') as f:
        f.write(master_script)
    
    # Make executable
    os.chmod(master_script_path, 0o755)
    
    print(f"\n✓ Master job script created: {master_script_path}")
    print(f"  Will submit {len(yaml_files)} jobs")
    print(f"  Account: {account}")
    print(f"  Processors per job: {prcs}")
    print(f"  Time limit: {time_limit}")
    print(f"\nTo submit all jobs, run:")
    print(f"  bash {master_script_path}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    config_file = sys.argv[1]
    
    if not Path(config_file).exists():
        print(f"Error: Config file not found: {config_file}")
        sys.exit(1)
    
    create_master_job_script(config_file)


if __name__ == "__main__":
    main()
