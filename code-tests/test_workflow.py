#!/usr/bin/env python3
"""
Test script to verify the refactored workflow with parse-once CIF logic.
"""

import os
import sys
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.create_input import create_emto_inputs

# Clean up previous test output
test_output = "./test_output"
if os.path.exists(test_output):
    shutil.rmtree(test_output)

print("="*70)
print("Testing refactored workflow with FePt.cif")
print("="*70)

# Test the workflow with CIF mode
create_emto_inputs(
    output_path=test_output,
    job_name="fept",
    cif_file="./testing/FePt.cif",
    dmax=1.3,
    ca_ratios=[0.96],  # Just one ratio for quick test
    sws_values=[2.65],  # Just one SWS for quick test
    magnetic='F',
    create_job_script=False  # Skip job script for test
)

print("\n" + "="*70)
print("Test completed! Checking generated files...")
print("="*70)

# Verify files were created
expected_files = [
    f"{test_output}/smx/fept_0.96.dat",  # KSTR
    f"{test_output}/shp/fept_0.96.dat",  # SHAPE
    f"{test_output}/fept_0.96_2.65.dat",  # KGRN
    f"{test_output}/fcd/fept_0.96_2.65.dat",  # KFCD
]

all_exist = True
for file in expected_files:
    exists = os.path.exists(file)
    status = "✓" if exists else "✗"
    print(f"{status} {file}")
    if not exists:
        all_exist = False

if all_exist:
    print("\n✓ All expected files created successfully!")

    # Show a sample of KGRN file to verify atom section
    print("\n" + "="*70)
    print("Sample from KGRN file (atom section):")
    print("="*70)
    with open(f"{test_output}/fept_0.96_2.65.dat", "r") as f:
        lines = f.readlines()
        # Find and print atom section (around line 70)
        in_atom_section = False
        for i, line in enumerate(lines):
            if "Symb  IQ  IT ITA" in line:
                in_atom_section = True
            if in_atom_section:
                print(line.rstrip())
                if i > 72:  # Print a few lines after header
                    break
else:
    print("\n✗ Some files are missing!")
    sys.exit(1)
