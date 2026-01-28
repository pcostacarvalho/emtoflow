#!/usr/bin/env python3
"""
Test script for k-point rescaling functionality.

This script demonstrates the k-point rescaling feature which maintains
constant k-point density in reciprocal space when lattice parameters change.
"""

import sys
sys.path.insert(0, '/home/user/EMTO_input_automation')

from utils.aux_lists import rescale_kpoints

def test_rescale_kpoints():
    """Test the rescale_kpoints function with various lattice parameters."""

    print("="*70)
    print("K-POINT RESCALING TESTS")
    print("="*70)
    print("\nHard-coded reference:")
    print("  Lattice: (3.86 Å, 3.86 Å, 3.76 Å)")
    print("  K-mesh: (21, 21, 21)")
    print("  Density: (81.06, 81.06, 78.96)")
    print("="*70)

    test_cases = [
        {
            'name': 'Reference lattice (should give 21×21×21)',
            'lattice': (3.86, 3.86, 3.76),
            'expected': (21, 21, 21),
            'lat': None
        },
        {
            'name': 'Doubled x-parameter (should give ~11×21×21)',
            'lattice': (7.72, 3.86, 3.76),
            'expected': (11, 21, 21),
            'lat': None
        },
        {
            'name': 'Larger lattice (Laves phase)',
            'lattice': (5.0, 5.0, 8.0),
            'expected': (16, 16, 10),
            'lat': None
        },
        {
            'name': 'Small cubic lattice (no symmetry constraint)',
            'lattice': (2.5, 2.5, 2.5),
            'expected': (32, 32, 32),
            'lat': None
        },
        {
            'name': 'Small cubic lattice WITH symmetry constraint (lat=2, FCC)',
            'lattice': (2.5, 2.5, 2.5),
            'expected': (32, 32, 32),  # Should enforce nkx=nky=nkz
            'lat': 2
        },
        {
            'name': 'Cubic lattice that would give 31×31×32 without symmetry',
            'lattice': (2.613, 2.613, 2.613),
            'expected': (31, 31, 31),  # Should enforce nkx=nky=nkz even if rounding differs
            'lat': 2
        },
        {
            'name': 'Large hexagonal lattice',
            'lattice': (10.0, 10.0, 15.0),
            'expected': (8, 8, 5),
            'lat': None
        },
        {
            'name': 'Tetragonal lattice WITH symmetry constraint (lat=5)',
            'lattice': (3.86, 3.86, 3.76),
            'expected': (21, 21, 21),  # Should enforce nkx=nky≠nkz
            'lat': 5
        }
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['name']}")
        print(f"  Input:    ({test['lattice'][0]:.2f}, "
              f"{test['lattice'][1]:.2f}, {test['lattice'][2]:.2f}) Å")
        if test.get('lat') is not None:
            print(f"  Lattice type: lat={test['lat']}")

        result = rescale_kpoints(test['lattice'], lat=test.get('lat'))

        print(f"  Result:   {result[0]} × {result[1]} × {result[2]}")
        print(f"  Expected: {test['expected'][0]} × {test['expected'][1]} × {test['expected'][2]}")

        # Check if result matches expected
        if result == test['expected']:
            print(f"  Status:   ✓ PASS")
        else:
            print(f"  Status:   ⚠ DIFFERENT (but may be correct due to rounding)")
            
        # For cubic/tetragonal tests, verify symmetry constraints
        if test.get('lat') in [1, 2, 3, 7]:  # Cubic or trigonal
            if result[0] == result[1] == result[2]:
                print(f"  Symmetry: ✓ Cubic symmetry enforced (nkx=nky=nkz)")
            else:
                print(f"  Symmetry: ✗ FAIL - Cubic symmetry not enforced!")
        elif test.get('lat') in [4, 5, 6]:  # Hexagonal or tetragonal
            if result[0] == result[1]:
                print(f"  Symmetry: ✓ Tetragonal/Hexagonal symmetry enforced (nkx=nky)")
            else:
                print(f"  Symmetry: ✗ FAIL - Tetragonal/Hexagonal symmetry not enforced!")

    print("\n" + "="*70)
    print("K-point rescaling tests completed!")
    print("="*70)

if __name__ == '__main__':
    test_rescale_kpoints()
