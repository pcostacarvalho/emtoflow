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
    extensions = ['.dat', '.log', '.mdl', '.prn', '.tfh', '.tfm']

    print(f"\n1. Creating test files in {smx_dir}/")
    for ratio in ratios:
        for ext in extensions:
            filename = f"{job_name}_{ratio:.2f}{ext}"
            filepath = os.path.join(smx_dir, filename)
            with open(filepath, 'w') as f:
                f.write(f"Test content for {filename}\n")
            print(f"   Created: {filename}")

    # Show initial state
    initial_files = sorted(os.listdir(smx_dir))
    print(f"\n2. Initial state: {len(initial_files)} files in smx/")

    # === Simulate the file organization logic ===
    print(f"\n3. Moving output files to smx/logs/...")

    logs_dir = os.path.join(smx_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Move KSTR output files to logs (keep .dat input files in smx/)
    output_extensions = ['.log', '.mdl', '.prn', '.tfh', '.tfm']
    moved_files = 0

    for ratio in ratios:
        for ext in output_extensions:
            filename = f"{job_name}_{ratio:.2f}{ext}"
            src = os.path.join(smx_dir, filename)
            dst = os.path.join(logs_dir, filename)

            if os.path.exists(src):
                os.rename(src, dst)
                moved_files += 1
                print(f"   Moved: {filename} → logs/")

    print(f"\n   ✓ Moved {moved_files} output files to smx/logs/")

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

    # Should have 3 .dat files in smx/ + 1 logs directory
    dat_files = [f for f in smx_files if f.endswith('.dat')]
    if len(dat_files) == len(ratios):
        print(f"   ✓ Correct: {len(dat_files)} .dat files in smx/")
    else:
        print(f"   ✗ Error: Expected {len(ratios)} .dat files, found {len(dat_files)}")

    # Should have 15 output files in logs/ (3 ratios × 5 extensions)
    expected_logs = len(ratios) * len(output_extensions)
    if len(logs_files) == expected_logs:
        print(f"   ✓ Correct: {len(logs_files)} output files in smx/logs/")
    else:
        print(f"   ✗ Error: Expected {expected_logs} files in logs/, found {len(logs_files)}")

    # Verify no output files left in smx/
    output_files_in_smx = [f for f in smx_files if any(f.endswith(ext) for ext in output_extensions)]
    if len(output_files_in_smx) == 0:
        print(f"   ✓ Correct: No output files left in smx/")
    else:
        print(f"   ✗ Error: Found {len(output_files_in_smx)} output files still in smx/: {output_files_in_smx}")

print("\n" + "="*70)
print("Test Complete")
print("="*70)
