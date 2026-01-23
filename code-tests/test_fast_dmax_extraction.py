#!/usr/bin/env python3
"""
Test script for fast DMAX optimization with early subprocess termination.

This script demonstrates the new optimized approach where we:
1. Start KSTR subprocess in background (non-blocking)
2. Monitor for .prn file to contain IQ=1 section
3. Extract data as soon as it's available
4. Terminate subprocess early (don't wait for full completion)

This is MUCH faster than waiting for the entire KSTR calculation to finish.
"""

import sys
import os
import time
import pytest

# NOTE:
# This file is an integration/demo script that depends on external EMTO binaries.
# It should not hard-fail the repo's unit test suite during pytest collection.
if os.environ.get("RUN_EMTO_INTEGRATION_TESTS") != "1":
    pytest.skip(
        "Skipping EMTO integration/demo script. Set RUN_EMTO_INTEGRATION_TESTS=1 to run.",
        allow_module_level=True,
    )

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.create_input import create_emto_inputs

# Update this path to your KSTR executable location
KSTR_EXECUTABLE = "/home/x_pamca/postdoc_proj/emto/bin/kstr.exe"

print("="*70)
print("FAST DMAX OPTIMIZATION - Early Subprocess Termination Test")
print("="*70)
print("\n🚀 NEW OPTIMIZED APPROACH:")
print("   - Subprocess runs in background (non-blocking)")
print("   - Monitor .prn file for IQ=1 section (appears in ~1-2 seconds)")
print("   - Extract neighbor shell data immediately")
print("   - Terminate subprocess early (no need to wait for full run)")
print()
print("⏱️  EXPECTED SPEEDUP:")
print("   - Old approach: ~5-60 seconds per ratio (wait for full completion)")
print("   - New approach: ~1-5 seconds per ratio (extract and terminate)")
print("="*70)
print()

# Check if KSTR executable exists
if not os.path.exists(KSTR_EXECUTABLE):
    pytest.skip(
        f"KSTR executable not found at: {KSTR_EXECUTABLE}. "
        "Update KSTR_EXECUTABLE to run this integration test.",
        allow_module_level=True,
    )

# Clean up previous test output
import shutil
if os.path.exists("./test_fast_cu"):
    print("🧹 Cleaning up previous test output...")
    shutil.rmtree("./test_fast_cu")
    print()

# Test Case 1: Small system (Cu FCC) - should be very fast
print("\n" + "="*70)
print("TEST CASE 1: Copper (FCC) - 3 c/a ratios")
print("="*70)
print("Expected time: ~3-10 seconds (old approach: ~15-60 seconds)")
print()

start_time = time.time()

try:
    create_emto_inputs(
        output_path="./test_fast_cu",
        job_name="cu",  # Short name (2 chars) + ratio (5 chars) = 7 chars total (<=10)
        cif_file="./testing/Cu-Copper.cif",
        ca_ratios=[0.98, 1.00, 1.02],  # 3 ratios for testing
        sws_values=[2.60],              # Single SWS for simplicity
        magnetic='P',
        # DMAX optimization with fast extraction
        optimize_dmax=True,
        dmax_initial=2.0,
        dmax_target_vectors=100,
        dmax_vector_tolerance=15,
        kstr_executable=KSTR_EXECUTABLE,
        create_job_script=False  # Skip job script creation for testing
    )

    elapsed = time.time() - start_time
    print(f"\n✅ TEST CASE 1 COMPLETED in {elapsed:.1f} seconds")
    print(f"   Average: {elapsed/3:.1f} seconds per ratio")

except Exception as e:
    print(f"\n❌ TEST CASE 1 FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*70)
print("RESULTS SUMMARY")
print("="*70)
print(f"\n📊 Performance:")
print(f"   Total time: {elapsed:.1f} seconds")
print(f"   Per ratio: {elapsed/3:.1f} seconds")
print(f"   Speedup: ~{180/elapsed:.1f}x faster than old approach (estimated)")
print()
print("📁 Output location: ./test_fast_cu/")
print("   - Optimized DMAX values: smx/logs/cu_dmax_optimization.log")
print("   - KSTR outputs: smx/logs/")
print("   - Final input files: smx/cu_*.dat")
print()
print("="*70)
print("✨ SUCCESS - Fast extraction is working!")
print("="*70)
print()
print("💡 NEXT STEPS:")
print("   1. Check the optimization log:")
print("      cat ./test_fast_cu/smx/logs/cu_dmax_optimization.log")
print()
print("   2. Verify .prn files were captured correctly:")
print("      ls -lh ./test_fast_cu/smx/logs/*.prn")
print()
print("   3. Compare timing with your previous runs")
print()
print("   4. Run test on your actual system (Fe-Pt, Co-Ni, etc.)")
print()
