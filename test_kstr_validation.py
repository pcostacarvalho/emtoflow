#!/usr/bin/env python3
"""
Test script to validate KSTR success/failure detection.
"""

import os

def _check_kstr_success(stdout, stderr, log_file=None):
    """Check if KSTR execution succeeded."""
    output = stdout + "\n" + stderr

    if log_file and os.path.exists(log_file):
        with open(log_file, 'r') as f:
            output += "\n" + f.read()

    # Check for success indicator
    if "KSTR: OK" in output and "Finished at:" in output:
        return True, None

    # Check for failure indicators
    if "Stop:" in output:
        lines = output.split('\n')
        error_lines = []
        for i, line in enumerate(lines):
            if "Stop:" in line:
                error_lines = lines[i:min(i+5, len(lines))]
                break
        error_msg = "\n".join(error_lines)

        if "DMAX" in error_msg and "too small" in error_msg:
            return False, "DMAX_TOO_SMALL: " + error_msg
        else:
            return False, "KSTR_ERROR: " + error_msg

    return False, "KSTR did not complete successfully (no 'KSTR: OK' found)"

# Test with Co_hcp examples
print("="*70)
print("Testing KSTR Success/Failure Detection")
print("="*70)

test_cases = [
    ("Co_1.40 (SUCCESS)", "testing/testing/Co_hcp/smx/Co_1.40.log"),
    ("Co_1.70 (FAIL)", "testing/testing/Co_hcp/smx/Co_1.70.log"),
    ("Co_1.80 (FAIL)", "testing/testing/Co_hcp/smx/Co_1.80.log"),
    ("Cu_1.00 (SUCCESS)", "testing/testing/Cu_fcc/smx/Cu_1.00.log"),
]

for name, log_path in test_cases:
    print(f"\nTest: {name}")
    print("-" * 70)

    if not os.path.exists(log_path):
        print(f"  ✗ File not found: {log_path}")
        continue

    # Read log file content
    with open(log_path, 'r') as f:
        log_content = f.read()

    # Test the validation function
    success, error_msg = _check_kstr_success("", "", log_path)

    if success:
        print(f"  ✓ DETECTED AS: SUCCESS")
    else:
        print(f"  ✗ DETECTED AS: FAILURE")
        if error_msg:
            print(f"  Error: {error_msg[:150]}")

    # Show first few lines of log for context
    lines = log_content.split('\n')[:8]
    print(f"\n  Log preview:")
    for line in lines:
        if line.strip():
            print(f"    {line}")

print("\n" + "="*70)
print("Test Complete")
print("="*70)
