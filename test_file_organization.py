#!/usr/bin/env python3
"""
Test script to verify KSTR output file organization.
"""

import os
import shutil
import tempfile

print("="*70)
print("Testing KSTR Output File Organization")
print("="*70)

# Create temporary directory structure
with tempfile.TemporaryDirectory() as tmpdir:
    smx_dir = os.path.join(tmpdir, "smx")
    os.makedirs(smx_dir)

    # Simulate KSTR output files for different ratios
    job_name = "test"
    ratios = [1.40, 1.50, 1.60]
    dmax_initial = 2.0
    extensions = ['.dat', '.log', '.mdl', '.prn', '.tfh', '.tfm']

    print(f"\n1. Creating test files in {smx_dir}/")
    for ratio in ratios:
        for ext in extensions:
            filename = f"{job_name}_{ratio:.2f}{ext}"
            filepath = os.path.join(smx_dir, filename)
            with open(filepath, 'w') as f:
                f.write(f"Test content for {filename}\n")
            print(f"   Created: {filename}")

        # Also create stdout log file
        stdout_filename = f"{job_name}_{ratio:.2f}_stdout.log"
        stdout_filepath = os.path.join(smx_dir, stdout_filename)
        with open(stdout_filepath, 'w') as f:
            f.write(f"KSTR stdout for {ratio:.2f}\n")
        print(f"   Created: {stdout_filename}")

    # Show initial state
    initial_files = sorted(os.listdir(smx_dir))
    print(f"\n2. Initial state: {len(initial_files)} files in smx/")

    # === Simulate the file organization logic ===
    print(f"\n3. Moving output files to smx/logs/...")

    logs_dir = os.path.join(smx_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Move KSTR output files to logs
    output_extensions = ['.log', '.mdl', '.prn', '.tfh', '.tfm']
    moved_files = 0

    for ratio in ratios:
        # Move output files
        for ext in output_extensions:
            filename = f"{job_name}_{ratio:.2f}{ext}"
            src = os.path.join(smx_dir, filename)
            dst = os.path.join(logs_dir, filename)

            if os.path.exists(src):
                os.rename(src, dst)
                moved_files += 1
                print(f"   Moved: {filename} → logs/")

        # Move stdout log file
        stdout_filename = f"{job_name}_{ratio:.2f}_stdout.log"
        stdout_src = os.path.join(smx_dir, stdout_filename)
        stdout_dst = os.path.join(logs_dir, stdout_filename)
        if os.path.exists(stdout_src):
            os.rename(stdout_src, stdout_dst)
            moved_files += 1
            print(f"   Moved: {stdout_filename} → logs/")

        # Move initial .dat file (with dmax_initial) to logs with descriptive name
        dat_filename = f"{job_name}_{ratio:.2f}.dat"
        dat_src = os.path.join(smx_dir, dat_filename)
        dat_dst = os.path.join(logs_dir, f"{job_name}_{ratio:.2f}_dmax_initial_{dmax_initial:.2f}.dat")
        if os.path.exists(dat_src):
            os.rename(dat_src, dat_dst)
            moved_files += 1
            print(f"   Moved: {dat_filename} → logs/{job_name}_{ratio:.2f}_dmax_initial_{dmax_initial:.2f}.dat")

    print(f"\n   ✓ Moved {moved_files} files to smx/logs/ (outputs + initial .dat files)")

    # Show final state
    print(f"\n4. Final state:")
    smx_files = sorted(os.listdir(smx_dir))
    logs_files = sorted(os.listdir(logs_dir)) if os.path.exists(logs_dir) else []

    print(f"   smx/ ({len(smx_files)} items):")
    for f in smx_files:
        print(f"     - {f}")

    print(f"\n   smx/logs/ ({len(logs_files)} files):")
    for f in logs_files:
        print(f"     - {f}")

    # Verify expectations
    print(f"\n5. Verification:")

    # Should have 0 .dat files in smx/ (all moved to logs/)
    dat_files = [f for f in smx_files if f.endswith('.dat')]
    if len(dat_files) == 0:
        print(f"   ✓ Correct: No .dat files in smx/ (all moved to logs/)")
    else:
        print(f"   ✗ Error: Expected 0 .dat files in smx/, found {len(dat_files)}: {dat_files}")

    # Should have 21 files in logs/
    # = 3 ratios × (5 output extensions + 1 stdout log + 1 .dat file)
    # = 3 × 7 = 21
    expected_logs = len(ratios) * (len(output_extensions) + 2)  # +1 for stdout, +1 for .dat
    if len(logs_files) == expected_logs:
        print(f"   ✓ Correct: {len(logs_files)} files in smx/logs/")
    else:
        print(f"   ✗ Error: Expected {expected_logs} files in logs/, found {len(logs_files)}")

    # Verify no output files left in smx/
    output_files_in_smx = [f for f in smx_files if any(f.endswith(ext) for ext in output_extensions)]
    if len(output_files_in_smx) == 0:
        print(f"   ✓ Correct: No output files left in smx/")
    else:
        print(f"   ✗ Error: Found {len(output_files_in_smx)} output files still in smx/: {output_files_in_smx}")

    # Verify initial .dat files are in logs with correct naming
    initial_dat_files = [f for f in logs_files if 'dmax_initial' in f]
    if len(initial_dat_files) == len(ratios):
        print(f"   ✓ Correct: {len(initial_dat_files)} initial .dat files in logs/ with dmax_initial naming")
    else:
        print(f"   ✗ Error: Expected {len(ratios)} initial .dat files in logs/, found {len(initial_dat_files)}")

    # Verify stdout log files are in logs
    stdout_files = [f for f in logs_files if 'stdout' in f]
    if len(stdout_files) == len(ratios):
        print(f"   ✓ Correct: {len(stdout_files)} stdout log files in logs/")
    else:
        print(f"   ✗ Error: Expected {len(ratios)} stdout files in logs/, found {len(stdout_files)}")

print("\n" + "="*70)
print("Test Complete")
print("="*70)
