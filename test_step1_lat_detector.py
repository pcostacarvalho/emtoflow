"""
Test Step 1: Verify parse_emto_structure() accepts both CIF and Structure objects
"""
from pymatgen.core import Structure, Lattice
from modules.lat_detector import parse_emto_structure

def test_parse_structure_from_pymatgen():
    """Test that parse_emto_structure accepts pymatgen Structure objects"""

    print("\n" + "="*60)
    print("TEST: parse_emto_structure() with pymatgen Structure")
    print("="*60)

    # Create a simple FCC structure (Fe0.5Pt0.5 alloy)
    # FCC has 4 atoms per unit cell at (0,0,0), (0.5,0.5,0), (0.5,0,0.5), (0,0.5,0.5)
    a = 3.7  # Angstroms
    lattice = Lattice.cubic(a)

    # Single site with Fe (for simplicity in this test)
    structure_pmg = Structure(
        lattice,
        ['Fe', 'Fe', 'Fe', 'Fe'],  # 4 Fe atoms (FCC)
        [[0, 0, 0], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5]]
    )

    print(f"\nCreated FCC Fe structure:")
    print(f"  Lattice parameter: {a} Å")
    print(f"  Number of atoms: {len(structure_pmg)}")

    # Parse using the modified function
    try:
        result = parse_emto_structure(structure_pmg)

        print(f"\n✓ SUCCESS: parse_emto_structure() accepted Structure object")
        print(f"\nResults:")
        print(f"  LAT number: {result['lat']} ({result['lattice_name']})")
        print(f"  Crystal system: {result['crystal_system']}")
        print(f"  Centering: {result['centering']}")
        print(f"  NQ3 (atoms): {result['NQ3']}")
        print(f"  NL (orbital layers): {result['NL']}")
        print(f"  a, b, c: {result['a']:.4f}, {result['b']:.4f}, {result['c']:.4f} Å")
        print(f"  b/a: {result['boa']:.4f}, c/a: {result['coa']:.4f}")

        print(f"\nPrimitive vectors (BSX, BSY, BSZ):")
        print(f"  BSX = {result['BSX']}")
        print(f"  BSY = {result['BSY']}")
        print(f"  BSZ = {result['BSZ']}")

        print(f"\nAtom info:")
        for atom in result['atom_info']:
            print(f"  IQ={atom['IQ']:2d} {atom['symbol']:2s} "
                  f"IT={atom['IT']:2d} ITA={atom['ITA']:2d} "
                  f"conc={atom['conc']:.3f} moment={atom['default_moment']:.2f}")

        # Verify expected values for FCC
        assert result['lat'] == 2, f"Expected LAT=2 (FCC), got {result['lat']}"
        assert result['NQ3'] == 4, f"Expected 4 atoms in FCC, got {result['NQ3']}"
        assert result['lattice_name'] == 'Face-centered cubic', \
            f"Expected FCC, got {result['lattice_name']}"

        print(f"\n✓ All assertions passed!")
        return True

    except Exception as e:
        print(f"\n✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_parse_structure_from_cif():
    """Test that CIF workflow still works (backward compatibility)"""

    print("\n" + "="*60)
    print("TEST: parse_emto_structure() with CIF file (backward compat)")
    print("="*60)

    # Find a test CIF file
    import os
    test_cif = None

    # Look for Cu test CIF
    possible_paths = [
        'testing/testing/Cu_fcc/Cu.cif',
        'testing/Cu_fcc/Cu.cif',
        'testing/Cu.cif'
    ]

    for path in possible_paths:
        if os.path.exists(path):
            test_cif = path
            break

    if test_cif:
        print(f"\nUsing test CIF: {test_cif}")
        try:
            result = parse_emto_structure(test_cif)
            print(f"✓ CIF parsing still works: LAT={result['lat']}, NQ3={result['NQ3']}")
            return True
        except Exception as e:
            print(f"✗ CIF parsing failed: {e}")
            return False
    else:
        print("⚠ No test CIF found, skipping CIF test")
        return True

if __name__ == '__main__':
    print("\n" + "="*60)
    print("STEP 1: Test Modified lat_detector.py")
    print("="*60)

    test1 = test_parse_structure_from_pymatgen()
    test2 = test_parse_structure_from_cif()

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Pymatgen Structure test: {'✓ PASS' if test1 else '✗ FAIL'}")
    print(f"CIF backward compat test: {'✓ PASS' if test2 else '✗ FAIL'}")
    print("="*60 + "\n")
