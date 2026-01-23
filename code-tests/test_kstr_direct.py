#!/usr/bin/env python3
"""
Direct KSTR execution test to diagnose subprocess issues.

This script tests KSTR execution without the optimization wrapper
to identify any basic issues with the executable or file I/O.
"""

import sys
import os
import subprocess
import time
import pytest

# NOTE:
# This file is an integration/debug script that depends on external EMTO binaries.
# It should not hard-fail the repo's unit test suite during pytest collection.
if os.environ.get("RUN_EMTO_INTEGRATION_TESTS") != "1":
    pytest.skip(
        "Skipping EMTO integration/debug script. Set RUN_EMTO_INTEGRATION_TESTS=1 to run.",
        allow_module_level=True,
    )

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

KSTR_EXECUTABLE = "/home/x_pamca/postdoc_proj/emto/bin/kstr.exe"

print("="*70)
print("KSTR Direct Execution Test")
print("="*70)
print()

# Check if KSTR executable exists
if not os.path.exists(KSTR_EXECUTABLE):
    pytest.skip(
        f"KSTR executable not found at: {KSTR_EXECUTABLE}. "
        "Update KSTR_EXECUTABLE to run this integration test.",
        allow_module_level=True,
    )

print(f"✓ KSTR executable found: {KSTR_EXECUTABLE}")

# Check for existing test data
test_input = "./testing/testing/Cu_fcc/smx/Cu_1.00.dat"
if not os.path.exists(test_input):
    print(f"❌ ERROR: Test input file not found: {test_input}")
    sys.exit(1)

print(f"✓ Test input file found: {test_input}")
print()

# Create a temporary output directory
os.makedirs("./test_kstr_debug", exist_ok=True)

# Copy input file to test directory
import shutil
shutil.copy(test_input, "./test_kstr_debug/test.dat")

print("Testing Method 1: Blocking subprocess.run()")
print("-" * 70)

try:
    with open("./test_kstr_debug/test.dat", 'r') as stdin_f:
        result = subprocess.run(
            [KSTR_EXECUTABLE],
            stdin=stdin_f,
            capture_output=True,
            text=True,
            cwd="./test_kstr_debug",
            timeout=10
        )

    print(f"Return code: {result.returncode}")
    print(f"Stdout length: {len(result.stdout)} chars")
    print(f"Stderr length: {len(result.stderr)} chars")

    # Check for .prn file
    prn_file = "./test_kstr_debug/test.prn"
    if os.path.exists(prn_file):
        with open(prn_file, 'r') as f:
            prn_content = f.read()
        print(f"✓ PRN file created: {len(prn_content)} chars")
        if "IQ =  1" in prn_content:
            print("✓ PRN file contains IQ=1 section")
    else:
        print("✗ PRN file not created")

    print("\nFirst 500 chars of stdout:")
    print(result.stdout[:500])

except Exception as e:
    print(f"✗ Error: {e}")

print()
print("="*70)
print("Testing Method 2: Non-blocking Popen with file handles")
print("-" * 70)

# Clean up previous test
import glob
for f in glob.glob("./test_kstr_debug/*"):
    if not f.endswith(".dat"):
        os.remove(f)

# Copy input again
shutil.copy(test_input, "./test_kstr_debug/test2.dat")

try:
    stdin_file = open("./test_kstr_debug/test2.dat", 'r')
    stdout_file = open("./test_kstr_debug/test2_stdout.log", 'w')

    process = subprocess.Popen(
        [KSTR_EXECUTABLE],
        stdin=stdin_file,
        stdout=stdout_file,
        stderr=subprocess.PIPE,
        cwd="./test_kstr_debug",
        text=True
    )

    print(f"Process started with PID: {process.pid}")

    # Poll for a few seconds
    for i in range(50):  # 5 seconds max
        poll_result = process.poll()

        # Check for .prn file
        prn_file = "./test_kstr_debug/test2.prn"
        if os.path.exists(prn_file):
            with open(prn_file, 'r') as f:
                prn_content = f.read()
            if "IQ =  1" in prn_content:
                print(f"✓ PRN file with IQ=1 found after {i*0.1:.1f}s")
                print(f"  PRN file size: {len(prn_content)} chars")
                break

        if poll_result is not None:
            print(f"Process ended with return code {poll_result} after {i*0.1:.1f}s")
            break

        time.sleep(0.1)

    # Clean up
    if process.poll() is None:
        process.terminate()
        process.wait(timeout=2)

    stdin_file.close()
    stdout_file.close()

    # Check stdout file
    with open("./test_kstr_debug/test2_stdout.log", 'r') as f:
        stdout_content = f.read()

    print(f"Stdout file size: {len(stdout_content)} chars")

    if stdout_content:
        print("\nFirst 500 chars of stdout:")
        print(stdout_content[:500])
    else:
        print("✗ Stdout file is empty!")

    # Get stderr
    _, stderr = process.communicate(timeout=1)
    if stderr:
        print(f"\nStderr: {stderr[:500]}")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

print()
print("="*70)
print("Diagnostic Complete")
print("="*70)
