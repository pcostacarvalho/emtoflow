#!/usr/bin/env python3
"""
Example script demonstrating DMAX optimization workflow.

This script shows how to use the integrated DMAX optimization feature
to find consistent neighbor shells across different c/a ratios.

Requirements:
- KSTR executable must be available
- Update kstr_executable path below to match your system
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.workflows import create_emto_inputs

# Update this path to your KSTR executable location
KSTR_EXECUTABLE = "/path/to/your/kstr.exe"

print("="*70)
print("DMAX Optimization Workflow Example")
print("="*70)
print("\nThis workflow will:")
print("1. Create initial KSTR inputs with dmax_initial=2.5")
print("2. Run KSTR for each c/a ratio")
print("3. Parse .prn files to analyze neighbor shells")
print("4. Optimize DMAX values for consistent shells")
print("5. Generate final input files with optimized DMAX")
print()

# Check if KSTR executable path is updated
if KSTR_EXECUTABLE == "/path/to/your/kstr.exe":
    print("⚠ WARNING: Please update KSTR_EXECUTABLE path in this script!")
    print("   Edit the KSTR_EXECUTABLE variable to point to your kstr.exe")
    sys.exit(1)

# Run workflow with DMAX optimization
create_emto_inputs(
    output_path="./fept_dmax_optimized",
    job_name="fept",
    cif_file="./testing/FePt.cif",
    ca_ratios=[0.92, 0.96, 1.00, 1.04],
    sws_values=[2.60, 2.65, 2.70],
    magnetic='F',
    # DMAX optimization parameters
    optimize_dmax=True,
    dmax_initial=2.5,              # Initial DMAX guess (should be large enough)
    dmax_target_vectors=100,       # Target number of k-vectors
    dmax_vector_tolerance=15,      # Acceptable deviation from target
    kstr_executable=KSTR_EXECUTABLE,
    # Job script
    create_job_script=True,
    job_mode='serial'
)

print("\n" + "="*70)
print("Example completed!")
print("="*70)
print("\nCheck the optimization log:")
print("  ./fept_dmax_optimized/smx/logs/fept_dmax_optimization.log")
print("\nGenerated files include:")
print("  - KSTR files with optimized DMAX (smx/)")
print("  - SHAPE files (shp/)")
print("  - KGRN files (root)")
print("  - KFCD files (fcd/)")
print("  - Job submission script")
