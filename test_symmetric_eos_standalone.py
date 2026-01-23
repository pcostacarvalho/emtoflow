#!/usr/bin/env python3
"""
Standalone test script for symmetric EOS fitting implementation.
Tests on existing calculation results in Cu100_Mg0/phase2_sws_optimization

Usage:
    python test_symmetric_eos_standalone.py [path_to_eos_executable]
    
If eos_executable is not provided, will try common paths or prompt user.
"""

import sys
import os
import re
from pathlib import Path
from typing import List, Tuple, Dict, Any
import subprocess

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import required modules
try:
    from modules.extract_results import parse_kfcd
    from modules.optimization.analysis import run_eos_fit
    from modules.inputs.eos_emto import create_eos_input, parse_eos_output
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)


def extract_sws_from_filename(filename: str) -> float:
    """Extract SWS value from filename like 'CuMg_1.00_2.52.prn'"""
    match = re.search(r'_(\d+\.\d+)\.prn$', filename)
    if match:
        return float(match.group(1))
    raise ValueError(f"Could not extract SWS from filename: {filename}")


def parse_prn_files(phase_path: Path, job_name: str, optimal_ca: float) -> Tuple[List[float], List[float]]:
    """Parse PRN files and extract SWS values and energies."""
    sws_values = []
    energy_values = []
    
    # Find all PRN files in fcd directory
    fcd_dir = phase_path / "fcd"
    if not fcd_dir.exists():
        raise FileNotFoundError(f"FCD directory not found: {fcd_dir}")
    
    prn_files = sorted(fcd_dir.glob(f"{job_name}_{optimal_ca:.2f}_*.prn"))
    
    if not prn_files:
        raise FileNotFoundError(f"No PRN files found matching pattern: {job_name}_{optimal_ca:.2f}_*.prn")
    
    print(f"\nFound {len(prn_files)} PRN files:")
    for prn_file in prn_files:
        # Extract SWS from filename
        try:
            sws = extract_sws_from_filename(prn_file.name)
        except ValueError as e:
            print(f"  Warning: {e}")
            continue
        
        # Parse PRN file
        try:
            results = parse_kfcd(str(prn_file), functional='GGA')
            if results.total_energy is None:
                print(f"  Warning: No total energy found in {prn_file.name}")
                continue
            
            energy = results.energies_by_functional['system']['GGA']
            sws_values.append(sws)
            energy_values.append(energy)
            
            print(f"  {prn_file.name}: SWS = {sws:.4f}, E = {energy:.6f} Ry")
        except Exception as e:
            print(f"  Error parsing {prn_file.name}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    return sws_values, energy_values


def find_eos_executable(user_path: str = None) -> str:
    """Find EOS executable path."""
    if user_path:
        if Path(user_path).exists():
            return user_path
        else:
            print(f"Warning: Provided path does not exist: {user_path}")
    
    # Try common paths
    common_paths = [
        "/home/x_pamca/postdoc_proj/emto/bin/eos.exe",
        "/usr/local/bin/eos.exe",
        "./eos.exe",
        "eos.exe"
    ]
    
    for path in common_paths:
        if Path(path).exists():
            return path
    
    # Prompt user
    print("\nEOS executable not found in common locations.")
    print("Please provide the path to eos.exe:")
    path = input("Path: ").strip()
    
    if Path(path).exists():
        return path
    else:
        raise FileNotFoundError(f"EOS executable not found: {path}")


def test_standard_fit(sws_values: List[float], energy_values: List[float], 
                     phase_path: Path, job_name: str, eos_executable: str) -> Dict[str, Any]:
    """Test standard EOS fit (no symmetric selection)."""
    print("\n" + "="*70)
    print("TEST 1: STANDARD EOS FIT (all points)")
    print("="*70)
    
    try:
        optimal_sws, eos_results, metadata = run_eos_fit(
            r_or_v_data=sws_values,
            energy_data=energy_values,
            output_path=phase_path,
            job_name=f"{job_name}_sws_test_std",
            comment=f"SWS optimization test (standard fit)",
            eos_executable=eos_executable,
            eos_type='MO88',
            use_symmetric_selection=False,  # Disable symmetric selection
            n_points_final=7
        )
        
        print(f"\n✓ Standard fit completed successfully")
        print(f"  Optimal SWS: {optimal_sws:.6f} Bohr")
        print(f"  Symmetric selection used: {metadata.get('symmetric_selection_used', False)}")
        print(f"  Points used: {metadata.get('final_points', len(sws_values))}")
        
        if 'morse' in eos_results:
            morse = eos_results['morse']
            print(f"\n  Morse EOS Results:")
            print(f"    Equilibrium energy: {morse.eeq:.6f} Ry")
            print(f"    Bulk modulus: {morse.bmod:.2f} kBar")
            print(f"    Fit quality: {morse.fit_quality}")
        
        return {
            'success': True,
            'optimal_sws': optimal_sws,
            'metadata': metadata,
            'eos_results': eos_results
        }
    except Exception as e:
        print(f"\n✗ Standard fit failed: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


def test_symmetric_selection(sws_values: List[float], energy_values: List[float],
                            phase_path: Path, job_name: str, eos_executable: str) -> Dict[str, Any]:
    """Test symmetric selection with extended dataset."""
    print("\n" + "="*70)
    print("TEST 2: SYMMETRIC SELECTION (simulated extended dataset)")
    print("="*70)
    
    # Create extended dataset by adding interpolated points
    import numpy as np
    
    sws_extended = []
    energy_extended = []
    
    # Add original points
    sws_extended.extend(sws_values)
    energy_extended.extend(energy_values)
    
    # Add interpolated points between existing ones
    for i in range(len(sws_values) - 1):
        sws_mid = (sws_values[i] + sws_values[i+1]) / 2
        # Simple linear interpolation for energy (approximate, good enough for testing)
        energy_mid = (energy_values[i] + energy_values[i+1]) / 2
        sws_extended.append(sws_mid)
        energy_extended.append(energy_mid)
    
    # Sort by SWS
    sorted_pairs = sorted(zip(sws_extended, energy_extended))
    sws_extended = [s for s, e in sorted_pairs]
    energy_extended = [e for s, e in sorted_pairs]
    
    print(f"Created extended dataset:")
    print(f"  Original points: {len(sws_values)}")
    print(f"  Extended points: {len(sws_extended)}")
    print(f"  SWS range: [{min(sws_extended):.4f}, {max(sws_extended):.4f}]")
    
    try:
        optimal_sws, eos_results, metadata = run_eos_fit(
            r_or_v_data=sws_extended,
            energy_data=energy_extended,
            output_path=phase_path,
            job_name=f"{job_name}_sws_test_sym",
            comment=f"SWS optimization test (symmetric selection)",
            eos_executable=eos_executable,
            eos_type='MO88',
            use_symmetric_selection=True,  # Enable symmetric selection
            n_points_final=7
        )
        
        print(f"\n✓ Symmetric selection fit completed successfully")
        print(f"  Optimal SWS: {optimal_sws:.6f} Bohr")
        print(f"  Symmetric selection used: {metadata.get('symmetric_selection_used', False)}")
        print(f"  Initial points: {metadata.get('initial_points', len(sws_extended))}")
        print(f"  Final points: {metadata.get('final_points', 7)}")
        print(f"  Equilibrium in range: {metadata.get('equilibrium_in_range', True)}")
        
        if metadata.get('selected_indices'):
            selected_sws = [sws_extended[i] for i in metadata['selected_indices']]
            print(f"  Selected SWS values: {[f'{s:.4f}' for s in selected_sws]}")
        
        if metadata.get('warnings'):
            print(f"\n  Warnings ({len(metadata['warnings'])}):")
            for warning in metadata['warnings']:
                print(f"    ⚠ {warning}")
        else:
            print(f"  No warnings")
        
        if 'morse' in eos_results:
            morse = eos_results['morse']
            print(f"\n  Morse EOS Results:")
            print(f"    Equilibrium energy: {morse.eeq:.6f} Ry")
            print(f"    Bulk modulus: {morse.bmod:.2f} kBar")
            print(f"    Fit quality: {morse.fit_quality}")
        
        return {
            'success': True,
            'optimal_sws': optimal_sws,
            'metadata': metadata,
            'eos_results': eos_results,
            'selected_indices': metadata.get('selected_indices', [])
        }
    except Exception as e:
        print(f"\n✗ Symmetric selection fit failed: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


def main():
    """Main test function."""
    print("="*70)
    print("SYMMETRIC EOS FITTING TEST")
    print("="*70)
    
    # Configuration
    phase_path = Path("/proj/snic2014-8-7/users/x_pamca/phase_diagrams/CuMg_fcc/Cu100_Mg0/phase2_sws_optimization")
    job_name = "CuMg"
    optimal_ca = 1.00
    
    # Get EOS executable path
    eos_executable = None
    if len(sys.argv) > 1:
        eos_executable = sys.argv[1]
    
    try:
        eos_executable = find_eos_executable(eos_executable)
    except FileNotFoundError as e:
        print(f"\n✗ {e}")
        sys.exit(1)
    
    print(f"\nConfiguration:")
    print(f"  Phase path: {phase_path}")
    print(f"  Job name: {job_name}")
    print(f"  Optimal c/a: {optimal_ca}")
    print(f"  EOS executable: {eos_executable}")
    
    # Check if phase path exists
    if not phase_path.exists():
        print(f"\n✗ Phase path does not exist: {phase_path}")
        sys.exit(1)
    
    # Parse PRN files
    print("\n" + "="*70)
    print("STEP 1: PARSING PRN FILES")
    print("="*70)
    
    try:
        sws_values, energy_values = parse_prn_files(phase_path, job_name, optimal_ca)
    except Exception as e:
        print(f"\n✗ Failed to parse PRN files: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    if len(sws_values) < 3:
        print(f"\n✗ Error: Need at least 3 data points, found {len(sws_values)}")
        sys.exit(1)
    
    print(f"\n✓ Parsed {len(sws_values)} data points successfully")
    print(f"  SWS range: [{min(sws_values):.4f}, {max(sws_values):.4f}] Bohr")
    print(f"  Energy range: [{min(energy_values):.6f}, {max(energy_values):.6f}] Ry")
    
    # Test 1: Standard fit
    result_std = test_standard_fit(sws_values, energy_values, phase_path, job_name, eos_executable)
    
    # Test 2: Symmetric selection (only if we have enough points to extend)
    result_sym = None
    if len(sws_values) >= 4:
        result_sym = test_symmetric_selection(sws_values, energy_values, phase_path, job_name, eos_executable)
    else:
        print("\n" + "="*70)
        print("SKIPPING SYMMETRIC SELECTION TEST")
        print("="*70)
        print("Need at least 4 points to create extended dataset for testing")
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    if result_std['success']:
        print(f"\n✓ Standard fit: SUCCESS")
        print(f"  Optimal SWS: {result_std['optimal_sws']:.6f} Bohr")
    else:
        print(f"\n✗ Standard fit: FAILED")
        print(f"  Error: {result_std.get('error', 'Unknown error')}")
    
    if result_sym and result_sym['success']:
        print(f"\n✓ Symmetric selection fit: SUCCESS")
        print(f"  Optimal SWS: {result_sym['optimal_sws']:.6f} Bohr")
        print(f"  Symmetric selection was used: {result_sym['metadata'].get('symmetric_selection_used', False)}")
        
        if result_std['success']:
            diff = abs(result_std['optimal_sws'] - result_sym['optimal_sws'])
            print(f"\n  Comparison:")
            print(f"    Difference: {diff:.6f} Bohr")
            print(f"    Relative difference: {diff/result_std['optimal_sws']*100:.4f}%")
    elif result_sym:
        print(f"\n✗ Symmetric selection fit: FAILED")
        print(f"  Error: {result_sym.get('error', 'Unknown error')}")
    
    print("\n" + "="*70)
    if result_std['success'] and (not result_sym or result_sym['success']):
        print("✓ ALL TESTS COMPLETED SUCCESSFULLY")
    else:
        print("⚠ SOME TESTS FAILED - CHECK ERRORS ABOVE")
    print("="*70)
    
    # Output file locations
    print("\nOutput files created:")
    print(f"  Standard fit: {phase_path / f'{job_name}_sws_test_std.out'}")
    if result_sym and result_sym['success']:
        print(f"  Initial fit: {phase_path / f'{job_name}_sws_test_sym.out'}")
        print(f"  Final fit: {phase_path / f'{job_name}_sws_test_sym_final.out'}")


if __name__ == "__main__":
    main()
