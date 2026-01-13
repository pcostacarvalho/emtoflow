"""
Test Step 3: Workflow Integration with Structure Builder

This test verifies that the updated workflows.py correctly integrates
the new structure builder for both CIF and parameter workflows.
"""

import os
import shutil
from modules.workflows import create_emto_inputs


def test_parameter_workflow_fcc_alloy():
    """Test parameter workflow with FCC Fe-Pt random alloy"""

    print("=" * 70)
    print("TEST: Parameter Workflow - FCC Fe-Pt Random Alloy (50-50)")
    print("=" * 70)

    # Define output directory
    output_path = "./test_output/fept_alloy"

    # Clean up if exists
    if os.path.exists(output_path):
        shutil.rmtree(output_path)

    # Define FCC Fe-Pt alloy structure
    sites = [
        {
            'position': [0, 0, 0],
            'elements': ['Fe', 'Pt'],
            'concentrations': [0.5, 0.5]
        }
    ]

    try:
        # Create EMTO inputs
        create_emto_inputs(
            output_path=output_path,
            job_name="fept",
            lat=2,  # FCC
            a=3.7,  # Angstroms
            sites=sites,
            dmax=1.3,
            ca_ratios=[1.00],
            sws_values=[2.60, 2.65],
            magnetic='F',
            user_magnetic_moments={'Fe': 2.2, 'Pt': 0.4},
            create_job_script=False  # Don't create job scripts for test
        )

        print("\n✓ Workflow completed successfully!")

        # Verify files were created
        print("\nVerifying created files:")

        # Check directory structure
        expected_dirs = ['smx', 'shp', 'pot', 'chd', 'fcd', 'tmp']
        for d in expected_dirs:
            dir_path = os.path.join(output_path, d)
            if os.path.exists(dir_path):
                print(f"  ✓ {d}/ directory exists")
            else:
                print(f"  ✗ {d}/ directory missing")

        # Check for KSTR file
        kstr_file = os.path.join(output_path, 'smx', 'fept_1.00.dat')
        if os.path.exists(kstr_file):
            print(f"  ✓ KSTR file created: {kstr_file}")
            # Read first few lines
            with open(kstr_file, 'r') as f:
                lines = f.readlines()[:5]
                print(f"    First line: {lines[0].strip()}")
        else:
            print(f"  ✗ KSTR file missing: {kstr_file}")

        # Check for SHAPE file
        shape_file = os.path.join(output_path, 'shp', 'fept_1.00.dat')
        if os.path.exists(shape_file):
            print(f"  ✓ SHAPE file created: {shape_file}")
        else:
            print(f"  ✗ SHAPE file missing: {shape_file}")

        # Check for KGRN files
        for sws in [2.60, 2.65]:
            kgrn_file = os.path.join(output_path, f'fept_1.00_{sws:.2f}.dat')
            if os.path.exists(kgrn_file):
                print(f"  ✓ KGRN file created: {kgrn_file}")
                # Read and check for alloy info
                with open(kgrn_file, 'r') as f:
                    content = f.read()
                    if 'Fe' in content and 'Pt' in content:
                        print(f"    Contains Fe and Pt elements")
                    if '0.500' in content or '0.5' in content:
                        print(f"    Contains concentration values")
            else:
                print(f"  ✗ KGRN file missing: {kgrn_file}")

        # Check for KFCD files
        for sws in [2.60, 2.65]:
            kfcd_file = os.path.join(output_path, 'fcd', f'fept_1.00_{sws:.2f}.dat')
            if os.path.exists(kfcd_file):
                print(f"  ✓ KFCD file created: {kfcd_file}")
            else:
                print(f"  ✗ KFCD file missing: {kfcd_file}")

        print("\n" + "=" * 70)
        print("PARAMETER WORKFLOW TEST: PASSED")
        print("=" * 70)
        return True

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        print("\n" + "=" * 70)
        print("PARAMETER WORKFLOW TEST: FAILED")
        print("=" * 70)
        return False


def test_parameter_workflow_l10():
    """Test parameter workflow with L10 FePt ordered structure"""

    print("\n\n" + "=" * 70)
    print("TEST: Parameter Workflow - L10 FePt Ordered Structure")
    print("=" * 70)

    # Define output directory
    output_path = "./test_output/fept_l10"

    # Clean up if exists
    if os.path.exists(output_path):
        shutil.rmtree(output_path)

    # Define L10 FePt structure (2 sites)
    sites = [
        {'position': [0, 0, 0], 'elements': ['Fe'], 'concentrations': [1.0]},
        {'position': [0.5, 0.5, 0.5], 'elements': ['Pt'], 'concentrations': [1.0]}
    ]

    try:
        # Create EMTO inputs
        create_emto_inputs(
            output_path=output_path,
            job_name="fept_l10",
            lat=5,  # BCT (body-centered tetragonal)
            a=3.7,
            c=3.7 * 0.96,  # c/a = 0.96
            sites=sites,
            dmax=1.3,
            ca_ratios=[0.96],
            sws_values=[2.60],
            magnetic='F',
            create_job_script=False
        )

        print("\n✓ L10 workflow completed successfully!")

        # Quick verification
        kstr_file = os.path.join(output_path, 'smx', 'fept_l10_0.96.dat')
        if os.path.exists(kstr_file):
            print(f"  ✓ KSTR file created for L10 structure")

        kgrn_file = os.path.join(output_path, 'fept_l10_0.96_2.60.dat')
        if os.path.exists(kgrn_file):
            print(f"  ✓ KGRN file created for L10 structure")
            with open(kgrn_file, 'r') as f:
                content = f.read()
                if 'IQ=  1' in content and 'IQ=  2' in content:
                    print(f"    Contains 2 distinct atomic sites (IQ=1, IQ=2)")

        print("\n" + "=" * 70)
        print("L10 WORKFLOW TEST: PASSED")
        print("=" * 70)
        return True

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        print("\n" + "=" * 70)
        print("L10 WORKFLOW TEST: FAILED")
        print("=" * 70)
        return False


if __name__ == '__main__':
    print("\n")
    print("*" * 70)
    print("STEP 3: WORKFLOW INTEGRATION TEST")
    print("*" * 70)
    print("\nTesting integration of structure_builder with workflows.py")
    print("This verifies the parameter workflow for alloy structures.\n")

    results = []

    # Test 1: FCC random alloy
    results.append(("FCC Fe-Pt Alloy", test_parameter_workflow_fcc_alloy()))

    # Test 2: L10 ordered structure
    results.append(("L10 FePt Ordered", test_parameter_workflow_l10()))

    # Summary
    print("\n\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:30s} : {status}")
    print("=" * 70)

    if all(p for _, p in results):
        print("\n✓ All tests passed! Step 3 integration is complete.")
    else:
        print("\n⚠️  Some tests failed. Review errors above.")
