"""
Test Step 2: Structure Builder Module
======================================

Tests the new structure_builder.py module with:
1. SWS conversion for various lattice types
2. Structure creation from parameters
3. Complete EMTO structure dictionary generation
"""

from pymatgen.core import Structure, Lattice
from modules.structure_builder import (
    lattice_param_to_sws,
    create_structure_from_params,
    create_emto_structure
)

def test_sws_conversion():
    """Test generalized SWS conversion using pymatgen"""

    print("\n" + "="*60)
    print("TEST 1: SWS Conversion (generalized)")
    print("="*60)

    # Test FCC structure (4 atoms per cell)
    a = 3.7  # Angstroms
    lattice = Lattice.cubic(a)
    structure_fcc = Structure(
        lattice,
        ['Fe', 'Fe', 'Fe', 'Fe'],
        [[0, 0, 0], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5]]
    )

    sws_fcc = lattice_param_to_sws(structure_fcc)
    print(f"\nFCC (a={a} Å, 4 atoms):")
    print(f"  Calculated SWS: {sws_fcc:.4f} Bohr")
    print(f"  Expected SWS:   ~2.73 Bohr")

    # Verify it's close to expected value (calculated from a=3.7, 4 atoms)
    expected_sws = 2.73
    assert abs(sws_fcc - expected_sws) < 0.01, f"FCC SWS mismatch: {sws_fcc} vs {expected_sws}"
    print(f"  ✓ Match!")

    # Test BCC structure (2 atoms per cell)
    a_bcc = 2.87
    lattice_bcc = Lattice.cubic(a_bcc)
    structure_bcc = Structure(
        lattice_bcc,
        ['Fe', 'Fe'],
        [[0, 0, 0], [0.5, 0.5, 0.5]]
    )

    sws_bcc = lattice_param_to_sws(structure_bcc)
    print(f"\nBCC (a={a_bcc} Å, 2 atoms):")
    print(f"  Calculated SWS: {sws_bcc:.4f} Bohr")
    print(f"  Expected SWS:   ~2.67 Bohr")

    expected_bcc = 2.67
    assert abs(sws_bcc - expected_bcc) < 0.01, f"BCC SWS mismatch"
    print(f"  ✓ Match!")

    # Test HCP structure
    a_hcp = 2.51
    c_hcp = 1.633 * a_hcp
    lattice_hcp = Lattice.hexagonal(a_hcp, c_hcp)
    structure_hcp = Structure(
        lattice_hcp,
        ['Co', 'Co'],
        [[1/3, 2/3, 1/4], [2/3, 1/3, 3/4]]
    )

    sws_hcp = lattice_param_to_sws(structure_hcp)
    print(f"\nHCP (a={a_hcp} Å, c={c_hcp:.3f} Å, 2 atoms):")
    print(f"  Calculated SWS: {sws_hcp:.4f} Bohr")
    print(f"  Volume per atom automatically calculated by pymatgen!")

    print(f"\n✓ All SWS calculations passed!")
    return True


def test_create_structure_from_params():
    """Test creating pymatgen structures from parameters"""

    print("\n" + "="*60)
    print("TEST 2: Create Structure from Parameters")
    print("="*60)

    # Test 1: FCC random alloy
    print("\n1. FCC Fe-Pt random alloy (50-50)")
    sites = [{'position': [0, 0, 0], 'elements': ['Fe', 'Pt'], 'concentrations': [0.5, 0.5]}]
    structure = create_structure_from_params(lat=2, a=3.7, sites=sites)

    print(f"   Created structure: {structure.composition}")
    print(f"   Number of sites: {len(structure.sites)}")
    print(f"   SWS stored: {structure.properties.get('sws', 'N/A'):.4f} Bohr")
    assert len(structure.sites) == 1, "FCC should have 1 site defined"
    assert structure.properties['sws'] > 0, "SWS should be calculated"
    print(f"   ✓ FCC alloy structure created!")

    # Test 2: Pure FCC structure
    print("\n2. Pure FCC Cu")
    sites = [{'position': [0, 0, 0], 'elements': ['Cu'], 'concentrations': [1.0]}]
    structure = create_structure_from_params(lat=2, a=3.61, sites=sites)

    print(f"   Created structure: {structure.composition}")
    print(f"   Number of sites: {len(structure.sites)}")
    print(f"   ✓ Pure structure created!")

    # Test 3: HCP with defaults
    print("\n3. HCP Co (with default c/a and gamma)")
    sites = [{'position': [0, 0, 0], 'elements': ['Co'], 'concentrations': [1.0]}]
    structure = create_structure_from_params(lat=4, a=2.51, sites=sites)

    print(f"   Created structure: {structure.composition}")
    print(f"   Lattice a: {structure.lattice.a:.3f} Å")
    print(f"   Lattice c: {structure.lattice.c:.3f} Å")
    print(f"   c/a ratio: {structure.lattice.c / structure.lattice.a:.3f}")
    print(f"   Gamma angle: {structure.lattice.gamma:.1f}°")

    # Verify HCP defaults
    expected_c_over_a = 1.633
    actual_c_over_a = structure.lattice.c / structure.lattice.a
    assert abs(actual_c_over_a - expected_c_over_a) < 0.01, "HCP c/a should be ~1.633"
    assert abs(structure.lattice.gamma - 120) < 0.1, "HCP gamma should be 120°"
    print(f"   ✓ HCP defaults correctly applied!")

    # Test 4: L10 ordered structure (tetragonal)
    print("\n4. L10 FePt (ordered, tetragonal)")
    sites = [
        {'position': [0, 0, 0], 'elements': ['Fe'], 'concentrations': [1.0]},
        {'position': [0.5, 0.5, 0.5], 'elements': ['Pt'], 'concentrations': [1.0]}
    ]
    structure = create_structure_from_params(lat=5, a=3.7, c=3.7*0.96, sites=sites)

    print(f"   Created structure: {structure.composition}")
    print(f"   Number of sites: {len(structure.sites)}")
    print(f"   c/a ratio: {structure.lattice.c / structure.lattice.a:.3f}")
    assert len(structure.sites) == 2, "L10 should have 2 sites"
    print(f"   ✓ L10 ordered structure created!")

    print(f"\n✓ All structure creation tests passed!")
    return True


def test_create_emto_structure():
    """Test the main unified interface"""

    print("\n" + "="*60)
    print("TEST 3: Unified EMTO Structure Creation")
    print("="*60)

    # Test from parameters (FCC alloy)
    print("\n1. From parameters (FCC Fe-Pt alloy)")
    sites = [{'position': [0, 0, 0], 'elements': ['Fe', 'Pt'], 'concentrations': [0.5, 0.5]}]
    emto_dict = create_emto_structure(lat=2, a=3.7, sites=sites)

    print(f"   LAT number: {emto_dict['lat']} ({emto_dict['lattice_name']})")
    print(f"   Crystal system: {emto_dict['crystal_system']}")
    print(f"   NQ3 (atoms): {emto_dict['NQ3']}")
    print(f"   NL (orbital layers): {emto_dict['NL']}")
    print(f"   a, b, c: {emto_dict['a']:.3f}, {emto_dict['b']:.3f}, {emto_dict['c']:.3f} Å")
    print(f"   b/a: {emto_dict['boa']:.3f}, c/a: {emto_dict['coa']:.3f}")

    print(f"\n   Primitive vectors:")
    print(f"   BSX = {emto_dict['BSX']}")
    print(f"   BSY = {emto_dict['BSY']}")
    print(f"   BSZ = {emto_dict['BSZ']}")

    print(f"\n   Atom info:")
    for atom in emto_dict['atom_info']:
        print(f"   IQ={atom['IQ']:2d} {atom['symbol']:2s} IT={atom['IT']:2d} "
              f"ITA={atom['ITA']:2d} conc={atom['conc']:.3f} moment={atom['default_moment']:.2f}")

    # Verify FCC structure
    assert emto_dict['lat'] == 2, "Should be FCC (LAT=2)"
    assert emto_dict['lattice_name'] == 'Face-centered cubic', "Should be FCC"
    print(f"\n   ✓ Structure dictionary complete!")

    # Test from CIF (if available)
    import os
    test_cif = 'testing/testing/Cu_fcc/Cu.cif'
    if os.path.exists(test_cif):
        print(f"\n2. From CIF file: {test_cif}")
        emto_dict_cif = create_emto_structure(cif_file=test_cif)
        print(f"   LAT: {emto_dict_cif['lat']}, NQ3: {emto_dict_cif['NQ3']}")
        print(f"   ✓ CIF loading works!")
    else:
        print(f"\n2. CIF test skipped (no test file found)")

    print(f"\n✓ Unified interface tests passed!")
    return True


def test_backward_compatibility():
    """Test that old parse_emto_structure still works"""

    print("\n" + "="*60)
    print("TEST 4: Backward Compatibility")
    print("="*60)

    from modules.lat_detector import parse_emto_structure

    # Test with pymatgen Structure
    lattice = Lattice.cubic(3.7)
    structure_pmg = Structure(lattice, ['Fe'], [[0, 0, 0]])

    try:
        result = parse_emto_structure(structure_pmg)
        print(f"\n✓ Old parse_emto_structure() still works!")
        print(f"  LAT: {result['lat']}, NQ3: {result['NQ3']}")
        return True
    except Exception as e:
        print(f"\n✗ Backward compatibility broken: {e}")
        return False


if __name__ == '__main__':
    print("\n" + "="*60)
    print("STEP 2: Test Structure Builder Module")
    print("="*60)

    results = []

    try:
        results.append(("SWS Conversion", test_sws_conversion()))
    except Exception as e:
        print(f"\n✗ SWS test failed: {e}")
        import traceback
        traceback.print_exc()
        results.append(("SWS Conversion", False))

    try:
        results.append(("Structure Creation", test_create_structure_from_params()))
    except Exception as e:
        print(f"\n✗ Structure creation test failed: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Structure Creation", False))

    try:
        results.append(("Unified Interface", test_create_emto_structure()))
    except Exception as e:
        print(f"\n✗ Unified interface test failed: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Unified Interface", False))

    try:
        results.append(("Backward Compat", test_backward_compatibility()))
    except Exception as e:
        print(f"\n✗ Backward compatibility test failed: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Backward Compat", False))

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:25s}: {status}")
    print("="*60 + "\n")

    all_passed = all(passed for _, passed in results)
    if all_passed:
        print("🎉 All Step 2 tests passed!\n")
    else:
        print("⚠️  Some tests failed. Review errors above.\n")
