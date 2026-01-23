#!/usr/bin/env python3
"""
Test script for symmetric EOS fitting implementation.
Tests on existing calculation results in Cu100_Mg0/phase2_sws_optimization
"""

import sys
from pathlib import Path
import re
from typing import List, Tuple

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import only what we need, avoiding module __init__ imports
from modules.extract_results import parse_kfcd
# Import analysis module directly
import importlib.util
spec = importlib.util.spec_from_file_location(
    "analysis", 
    project_root / "modules" / "optimization" / "analysis.py"
)
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)
run_eos_fit = analysis.run_eos_fit

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
    prn_files = sorted(fcd_dir.glob(f"{job_name}_{optimal_ca:.2f}_*.prn"))
    
    print(f"\nFound {len(prn_files)} PRN files:")
    for prn_file in prn_files:
        # Extract SWS from filename
        sws = extract_sws_from_filename(prn_file.name)
        
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
            continue
    
    return sws_values, energy_values

def main():
    """Test symmetric EOS fitting on existing results."""
    phase_path = Path("/Users/pamco116/Documents/GitHub/EMTO_input_automation/Cu100_Mg0/phase2_sws_optimization")
    job_name = "CuMg"
    optimal_ca = 1.00
    
    print("="*70)
    print("TESTING SYMMETRIC EOS FITTING")
    print("="*70)
    print(f"Phase path: {phase_path}")
    print(f"Job name: {job_name}")
    print(f"Optimal c/a: {optimal_ca}")
    
    # Parse PRN files
    print("\n" + "="*70)
    print("STEP 1: PARSING PRN FILES")
    print("="*70)
    sws_values, energy_values = parse_prn_files(phase_path, job_name, optimal_ca)
    
    if len(sws_values) < 3:
        print(f"\nError: Need at least 3 data points, found {len(sws_values)}")
        return
    
    print(f"\n✓ Parsed {len(sws_values)} data points")
    print(f"  SWS range: [{min(sws_values):.4f}, {max(sws_values):.4f}]")
    print(f"  Energy range: [{min(energy_values):.6f}, {max(energy_values):.6f}] Ry")
    
    # Test 1: Standard fit (no symmetric selection since we have exactly 7 points)
    print("\n" + "="*70)
    print("STEP 2: STANDARD EOS FIT (7 points, no symmetric selection)")
    print("="*70)
    
    eos_executable = "/home/x_pamca/postdoc_proj/emto/bin/eos.exe"
    if not Path(eos_executable).exists():
        print(f"Warning: EOS executable not found at {eos_executable}")
        print("Please update the path in the script")
        return
    
    try:
        optimal_sws_std, eos_results_std, metadata_std = run_eos_fit(
            r_or_v_data=sws_values,
            energy_data=energy_values,
            output_path=phase_path,
            job_name=f"{job_name}_sws_test_std",
            comment=f"SWS optimization test (standard fit)",
            eos_executable=eos_executable,
            eos_type='MO88',
            use_symmetric_selection=True,
            n_points_final=7
        )
        
        print(f"\n✓ Standard fit completed")
        print(f"  Optimal SWS: {optimal_sws_std:.6f} Bohr")
        print(f"  Symmetric selection used: {metadata_std.get('symmetric_selection_used', False)}")
        print(f"  Points used: {metadata_std.get('final_points', len(sws_values))}")
        if metadata_std.get('warnings'):
            print(f"  Warnings: {len(metadata_std['warnings'])}")
            for warning in metadata_std['warnings']:
                print(f"    - {warning}")
    except Exception as e:
        print(f"\n✗ Standard fit failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test 2: Simulate having more points by duplicating some (to test symmetric selection)
    print("\n" + "="*70)
    print("STEP 3: TESTING SYMMETRIC SELECTION (simulated 14 points)")
    print("="*70)
    
    # Create extended dataset by interpolating between points
    import numpy as np
    sws_extended = []
    energy_extended = []
    
    # Add original points
    sws_extended.extend(sws_values)
    energy_extended.extend(energy_values)
    
    # Add interpolated points between existing ones
    for i in range(len(sws_values) - 1):
        sws_mid = (sws_values[i] + sws_values[i+1]) / 2
        # Simple linear interpolation for energy (not accurate, but good for testing)
        energy_mid = (energy_values[i] + energy_values[i+1]) / 2
        sws_extended.append(sws_mid)
        energy_extended.append(energy_mid)
    
    # Sort by SWS
    sorted_pairs = sorted(zip(sws_extended, energy_extended))
    sws_extended = [s for s, e in sorted_pairs]
    energy_extended = [e for s, e in sorted_pairs]
    
    print(f"Created extended dataset with {len(sws_extended)} points")
    print(f"  SWS range: [{min(sws_extended):.4f}, {max(sws_extended):.4f}]")
    
    try:
        optimal_sws_sym, eos_results_sym, metadata_sym = run_eos_fit(
            r_or_v_data=sws_extended,
            energy_data=energy_extended,
            output_path=phase_path,
            job_name=f"{job_name}_sws_test_sym",
            comment=f"SWS optimization test (symmetric selection)",
            eos_executable=eos_executable,
            eos_type='MO88',
            use_symmetric_selection=True,
            n_points_final=7
        )
        
        print(f"\n✓ Symmetric selection fit completed")
        print(f"  Optimal SWS: {optimal_sws_sym:.6f} Bohr")
        print(f"  Symmetric selection used: {metadata_sym.get('symmetric_selection_used', False)}")
        print(f"  Initial points: {metadata_sym.get('initial_points', len(sws_extended))}")
        print(f"  Final points: {metadata_sym.get('final_points', 7)}")
        print(f"  Equilibrium in range: {metadata_sym.get('equilibrium_in_range', True)}")
        print(f"  Selected indices: {metadata_sym.get('selected_indices', [])}")
        if metadata_sym.get('warnings'):
            print(f"  Warnings ({len(metadata_sym['warnings'])}):")
            for warning in metadata_sym['warnings']:
                print(f"    - {warning}")
        else:
            print(f"  No warnings")
    except Exception as e:
        print(f"\n✗ Symmetric selection fit failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Standard fit (7 points):")
    print(f"  Optimal SWS: {optimal_sws_std:.6f} Bohr")
    print(f"  Symmetric selection: {metadata_std.get('symmetric_selection_used', False)}")
    print(f"\nSymmetric selection fit ({len(sws_extended)} points → 7 points):")
    print(f"  Optimal SWS: {optimal_sws_sym:.6f} Bohr")
    print(f"  Symmetric selection: {metadata_sym.get('symmetric_selection_used', False)}")
    print(f"  Difference: {abs(optimal_sws_std - optimal_sws_sym):.6f} Bohr")
    
    print("\n" + "="*70)
    print("✓ TEST COMPLETED SUCCESSFULLY")
    print("="*70)

if __name__ == "__main__":
    main()
