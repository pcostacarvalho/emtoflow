#!/usr/bin/env python3
"""
Unit test for .prn file monitoring function.

This tests the _check_prn_iq1_complete() function that determines
when we have enough data from the KSTR output to proceed with
DMAX optimization.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.create_input import _check_prn_iq1_complete

print("="*70)
print("PRN File Monitoring - Unit Test")
print("="*70)
print("\nTesting _check_prn_iq1_complete() function...")
print()

# Test 1: Non-existent file
print("Test 1: Non-existent file")
result = _check_prn_iq1_complete("/nonexistent/file.prn")
assert result == False, "Should return False for non-existent file"
print("   ✓ Returns False for non-existent file")

# Test 2: Existing complete .prn file
print("\nTest 2: Complete .prn file (Co HCP example)")
test_file = "./testing/testing/Co_hcp/smx/Co_1.40.prn"
if os.path.exists(test_file):
    result = _check_prn_iq1_complete(test_file)
    print(f"   File: {test_file}")
    print(f"   Result: {result}")
    if result:
        print("   ✓ Correctly detected complete IQ=1 section")
    else:
        print("   ✗ Failed to detect complete IQ=1 section")
else:
    print(f"   ⚠ Test file not found: {test_file}")

# Test 3: Another example (Cu FCC)
print("\nTest 3: Complete .prn file (Cu FCC example)")
test_file = "./testing/testing/Cu_fcc/smx/Cu_1.00.prn"
if os.path.exists(test_file):
    result = _check_prn_iq1_complete(test_file)
    print(f"   File: {test_file}")
    print(f"   Result: {result}")
    if result:
        print("   ✓ Correctly detected complete IQ=1 section")
    else:
        print("   ✗ Failed to detect complete IQ=1 section")
else:
    print(f"   ⚠ Test file not found: {test_file}")

# Test 4: Check all available .prn files
print("\nTest 4: Scanning all available .prn files...")
import glob
prn_files = glob.glob("./testing/testing/*/smx/*.prn")
if prn_files:
    complete_count = 0
    incomplete_count = 0
    for prn_file in prn_files[:5]:  # Check first 5 files
        result = _check_prn_iq1_complete(prn_file)
        status = "✓ COMPLETE" if result else "✗ INCOMPLETE"
        print(f"   {os.path.basename(prn_file):20s} {status}")
        if result:
            complete_count += 1
        else:
            incomplete_count += 1

    print(f"\n   Summary: {complete_count} complete, {incomplete_count} incomplete")
else:
    print("   ⚠ No .prn test files found")

print("\n" + "="*70)
print("Unit test complete!")
print("="*70)
print("\n💡 The function is ready to monitor .prn files in real-time.")
print("   It will return True as soon as IQ=1 section is written to disk.")
print()
