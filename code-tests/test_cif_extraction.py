#!/usr/bin/env python3
"""
Comprehensive test script for CIF extraction and input file generation.
Tests parse_emto_structure() and input generators across different crystal systems.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.lat_detector import parse_emto_structure
from modules.inputs.kstr import create_kstr_input
from modules.inputs.kgrn import create_kgrn_input

def print_separator(char="=", length=80):
    """Print a separator line."""
    print(char * length)

def print_section(title):
    """Print a section header."""
    print_separator()
    print(f" {title}")
    print_separator()

def test_cif_file(cif_path, expected_lat, expected_nq3, expected_nl, description):
    """
    Test a single CIF file.

    Parameters:
    -----------
    cif_path : str
        Path to CIF file
    expected_lat : int
        Expected Bravais lattice type
    expected_nq3 : int
        Expected number of atoms
    expected_nl : int
        Expected maximum angular momentum quantum number
    description : str
        Description of the material
    """
    print_section(f"Testing: {description}")
    print(f"CIF file: {cif_path}")
    print()

    # Parse the CIF file
    try:
        structure = parse_emto_structure(cif_path)
        print("✓ CIF parsing successful!")
        print()

        # Display detected parameters
        print("DETECTED STRUCTURE PARAMETERS:")
        print(f"  Bravais lattice (LAT):     {structure['lat']:2d}  {'✓' if structure['lat'] == expected_lat else '✗ Expected: ' + str(expected_lat)}")
        print(f"  Lattice name:              {structure['lattice_name']}")
        print(f"  Number of atoms (NQ3):     {structure['NQ3']:2d}  {'✓' if structure['NQ3'] == expected_nq3 else '✗ Expected: ' + str(expected_nq3)}")
        print(f"  Maximum NL:                {structure['NL']:2d}  {'✓' if structure['NL'] == expected_nl else '✗ Expected: ' + str(expected_nl)}")
        print()

        # Display lattice parameters
        print("LATTICE PARAMETERS:")
        print(f"  a = {structure['a']:.5f} Å")
        if 'b' in structure:
            print(f"  b = {structure['b']:.5f} Å")
        if 'c' in structure:
            print(f"  c = {structure['c']:.5f} Å")
        if 'boa' in structure:
            print(f"  b/a = {structure['boa']:.5f}")
        if 'coa' in structure:
            print(f"  c/a = {structure['coa']:.5f}")
        print()

        # Display primitive vectors
        print("EMTO PRIMITIVE VECTORS:")
        bsx = structure['BSX']
        bsy = structure['BSY']
        bsz = structure['BSZ']
        if isinstance(bsx, list):
            print(f"  BSX = [{bsx[0]:.6f}, {bsx[1]:.6f}, {bsx[2]:.6f}]")
            print(f"  BSY = [{bsy[0]:.6f}, {bsy[1]:.6f}, {bsy[2]:.6f}]")
            print(f"  BSZ = [{bsz[0]:.6f}, {bsz[1]:.6f}, {bsz[2]:.6f}]")
        else:
            print(f"  BSX = {bsx:.6f}")
            print(f"  BSY = {bsy:.6f}")
            print(f"  BSZ = {bsz:.6f}")
        print()

        # Display atom information
        print("ATOM INFORMATION:")
        print(f"  {'IQ':<4} {'IT':<4} {'ITA':<5} {'Symbol':<8} {'Concentration':<14} {'Moment':<8} {'Position (x, y, z)'}")
        print("  " + "-" * 75)
        for i, atom in enumerate(structure['atom_info']):
            x, y, z = structure['fractional_coords'][i]
            moment = atom.get('moment', atom.get('default_moment', 0.0))
            print(f"  {atom['IQ']:<4} {atom['IT']:<4} {atom['ITA']:<5} "
                  f"{atom['symbol']:<8} {atom['conc']:<14.6f} {moment:<8.4f} "
                  f"({x:.5f}, {y:.5f}, {z:.5f})")
        print()

        # Validation summary
        validation_passed = (
            structure['lat'] == expected_lat and
            structure['NQ3'] == expected_nq3 and
            structure['NL'] == expected_nl
        )

        if validation_passed:
            print("✓✓✓ VALIDATION PASSED ✓✓✓")
        else:
            print("✗✗✗ VALIDATION FAILED ✗✗✗")

        print()
        return structure, validation_passed

    except Exception as e:
        print(f"✗ CIF parsing FAILED!")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        print()
        return None, False

def generate_test_inputs(structure, material_name, test_output_dir):
    """
    Generate KSTR and KGRN input files for testing.

    Parameters:
    -----------
    structure : dict
        Structure dictionary from parse_emto_structure()
    material_name : str
        Name of the material (for file naming)
    test_output_dir : str
        Directory for test output files
    """
    print(f"Generating test input files for {material_name}...")

    # Create output directories
    os.makedirs(f"{test_output_dir}/smx", exist_ok=True)
    os.makedirs(f"{test_output_dir}/shp", exist_ok=True)
    os.makedirs(f"{test_output_dir}/fcd", exist_ok=True)

    try:
        # Generate KSTR input
        kstr_file = f"{test_output_dir}/smx/{material_name}_1.00.dat"
        create_kstr_input(
            structure=structure,
            output_path=f"{test_output_dir}/smx",
            id_name=f"{material_name}_1.00",
            dmax=1.5
        )
        print(f"  ✓ KSTR file created: {kstr_file}")

        # Generate KGRN input (using default SWS)
        # Calculate default SWS from volume
        import numpy as np
        sws_default = structure.get('sws_default', 2.65)

        kgrn_file = f"{test_output_dir}/{material_name}_1.00_{sws_default:.2f}.dat"
        create_kgrn_input(
            structure=structure,
            path=test_output_dir,
            id_namev=f"{material_name}_1.00_{sws_default:.2f}",
            id_namer=f"{material_name}_1.00",
            SWS=sws_default
        )
        print(f"  ✓ KGRN file created: {kgrn_file}")
        print()

        return True

    except Exception as e:
        print(f"  ✗ Input file generation FAILED!")
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False

def main():
    """Main test function."""
    print_separator("=", 80)
    print(" COMPREHENSIVE CIF EXTRACTION TEST SUITE")
    print(" Testing parse_emto_structure() and input file generators")
    print_separator("=", 80)
    print()

    # Define test cases
    test_cases = [
        {
            'cif_file': 'testing/Cu-Copper.cif',
            'expected_lat': 2,
            'expected_nq3': 4,
            'expected_nl': 2,
            'description': 'Copper (FCC, LAT 2)',
            'material_name': 'cu'
        },
        {
            'cif_file': 'testing/Fe-Iron-alpha.cif',
            'expected_lat': 3,
            'expected_nq3': 2,
            'expected_nl': 2,
            'description': 'Iron-alpha (BCC, LAT 3)',
            'material_name': 'fe'
        },
        {
            'cif_file': 'testing/Mg-Magnesium.cif',
            'expected_lat': 4,
            'expected_nq3': 2,
            'expected_nl': 1,
            'description': 'Magnesium (HCP, LAT 4)',
            'material_name': 'mg'
        },
        {
            'cif_file': 'testing/TiO2-Rutile.cif',
            'expected_lat': 5,
            'expected_nq3': 6,
            'expected_nl': 2,
            'description': 'TiO2 Rutile (Simple Tetragonal, LAT 5)',
            'material_name': 'tio2'
        },
        {
            'cif_file': 'testing/FePt.cif',
            'expected_lat': 5,
            'expected_nq3': 2,
            'expected_nl': 3,
            'description': 'FePt L10 (Simple Tetragonal, LAT 5)',
            'material_name': 'fept'
        }
    ]

    # Test output directory
    test_output_dir = "testing/test_outputs"
    os.makedirs(test_output_dir, exist_ok=True)

    # Run tests
    results = []
    structures = []

    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f" TEST {i}/{len(test_cases)}")
        print(f"{'='*80}\n")

        structure, validation_passed = test_cif_file(
            cif_path=test['cif_file'],
            expected_lat=test['expected_lat'],
            expected_nq3=test['expected_nq3'],
            expected_nl=test['expected_nl'],
            description=test['description']
        )

        if structure:
            structures.append(structure)
            input_success = generate_test_inputs(
                structure=structure,
                material_name=test['material_name'],
                test_output_dir=test_output_dir
            )
        else:
            input_success = False

        results.append({
            'description': test['description'],
            'validation_passed': validation_passed,
            'input_generated': input_success
        })

    # Print summary
    print_separator("=", 80)
    print(" TEST SUMMARY")
    print_separator("=", 80)
    print()
    print(f"{'Material':<40} {'Validation':<15} {'Input Files':<15}")
    print("-" * 80)

    total_tests = len(results)
    validation_passed = sum(1 for r in results if r['validation_passed'])
    inputs_generated = sum(1 for r in results if r['input_generated'])

    for result in results:
        val_status = "✓ PASSED" if result['validation_passed'] else "✗ FAILED"
        inp_status = "✓ GENERATED" if result['input_generated'] else "✗ FAILED"
        print(f"{result['description']:<40} {val_status:<15} {inp_status:<15}")

    print("-" * 80)
    print(f"Total tests:          {total_tests}")
    print(f"Validation passed:    {validation_passed}/{total_tests}")
    print(f"Input files created:  {inputs_generated}/{total_tests}")
    print()

    if validation_passed == total_tests and inputs_generated == total_tests:
        print("✓✓✓ ALL TESTS PASSED! ✓✓✓")
        print()
        print(f"Test output files saved to: {test_output_dir}/")
        return 0
    else:
        print("✗✗✗ SOME TESTS FAILED ✗✗✗")
        return 1

if __name__ == "__main__":
    sys.exit(main())
