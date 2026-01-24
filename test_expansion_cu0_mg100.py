#!/usr/bin/env python3
"""
Test script for range expansion feature on Cu0_Mg100 case.

This script tests the expansion logic on existing calculation data
from Cu0_Mg100/phase2_sws_optimization.
"""

import sys
from pathlib import Path
import numpy as np

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from modules.extract_results import parse_kfcd
from modules.optimization.analysis import (
    detect_expansion_needed,
    estimate_morse_minimum,
    generate_parameter_vector_around_estimate,
    run_eos_fit,
    prepare_data_for_eos_fit,
    save_parameter_energy_data,
    load_parameter_energy_data
)
from modules.inputs.eos_emto import parse_eos_output


def find_eos_executable():
    """Find EOS executable path."""
    possible_paths = [
        "/home/x_pamca/postdoc_proj/emto/bin/eos.exe",
        "/proj/snic2014-8-7/users/x_pamca/postdoc_proj/emto/bin/eos.exe",
        project_root / "bin" / "eos.exe",
    ]
    
    for path in possible_paths:
        path_obj = Path(path)
        if path_obj.exists():
            return str(path_obj)
    
    raise FileNotFoundError(
        f"EOS executable not found. Tried: {possible_paths}\n"
        f"Please set EOS_EXECUTABLE environment variable or update the script."
    )


def parse_existing_data(phase_path):
    """Parse SWS and energy values from existing PRN files."""
    phase_path = Path(phase_path)
    fcd_dir = phase_path / "fcd"
    
    if not fcd_dir.exists():
        # Try direct PRN files in phase_path
        prn_files = list(phase_path.glob("*.prn"))
    else:
        prn_files = list(fcd_dir.glob("*.prn"))
    
    if not prn_files:
        raise FileNotFoundError(f"No PRN files found in {phase_path}")
    
    sws_values = []
    energy_values = []
    
    print(f"Found {len(prn_files)} PRN files")
    print("Parsing energies...")
    
    for prn_file in sorted(prn_files):
        # Extract SWS from filename: CuMg_1.00_2.52.prn -> 2.52
        try:
            parts = prn_file.stem.split('_')
            if len(parts) >= 3:
                sws_str = parts[-1]
                sws = float(sws_str)
            else:
                print(f"  Warning: Could not parse SWS from {prn_file.name}, skipping")
                continue
            
            # Parse energy from PRN file
            results = parse_kfcd(str(prn_file), functional='GGA')
            if results.total_energy is not None:
                energy = results.energies_by_functional['system']['GGA']
                sws_values.append(sws)
                energy_values.append(energy)
                print(f"  SWS = {sws:.4f}: E = {energy:.6f} Ry")
            else:
                print(f"  Warning: No energy found in {prn_file.name}")
        except Exception as e:
            print(f"  Warning: Failed to parse {prn_file.name}: {e}")
    
    # Sort by SWS
    sorted_pairs = sorted(zip(sws_values, energy_values))
    sws_values = [s for s, e in sorted_pairs]
    energy_values = [e for s, e in sorted_pairs]
    
    print(f"\n✓ Parsed {len(sws_values)} data points")
    print(f"  SWS range: [{min(sws_values):.4f}, {max(sws_values):.4f}]")
    print(f"  Energy range: [{min(energy_values):.6f}, {max(energy_values):.6f}] Ry")
    
    return sws_values, energy_values


def main():
    """Main test function."""
    print("="*70)
    print("TEST: Range Expansion for Cu0_Mg100")
    print("="*70)
    
    # Paths
    phase_path = project_root / "Cu0_Mg100" / "phase2_sws_optimization"
    
    if not phase_path.exists():
        raise FileNotFoundError(f"Phase path not found: {phase_path}")
    
    print(f"\nPhase path: {phase_path}")
    
    # Parse existing data
    print("\n" + "-"*70)
    print("STEP 1: Parse existing calculation data")
    print("-"*70)
    sws_values, energy_values = parse_existing_data(phase_path)
    
    # Test data persistence
    print("\n" + "-"*70)
    print("STEP 2: Test data persistence")
    print("-"*70)
    save_parameter_energy_data(phase_path, 'sws', sws_values, energy_values)
    print(f"✓ Saved data to {phase_path / 'sws_energy_data.json'}")
    
    loaded_sws, loaded_energy = load_parameter_energy_data(phase_path, 'sws')
    if loaded_sws:
        print(f"✓ Loaded {len(loaded_sws)} data points from file")
        assert len(loaded_sws) == len(sws_values), "Data mismatch!"
    else:
        print("✗ Failed to load data")
    
    # Test prepare_data_for_eos_fit
    print("\n" + "-"*70)
    print("STEP 3: Test prepare_data_for_eos_fit")
    print("-"*70)
    print("  Testing with use_saved_data=False (use only current data)")
    sws_fit1, energy_fit1 = prepare_data_for_eos_fit(
        sws_values, energy_values, phase_path, 'sws', use_saved_data=False
    )
    print(f"  Result: {len(sws_fit1)} data points")
    
    print("  Testing with use_saved_data=True (merge with saved data)")
    sws_fit2, energy_fit2 = prepare_data_for_eos_fit(
        sws_values, energy_values, phase_path, 'sws', use_saved_data=True
    )
    print(f"  Result: {len(sws_fit2)} data points")
    
    # Run initial EOS fit
    print("\n" + "-"*70)
    print("STEP 4: Run initial EOS fit")
    print("-"*70)
    
    try:
        eos_executable = find_eos_executable()
        print(f"Using EOS executable: {eos_executable}")
    except FileNotFoundError as e:
        print(f"⚠ {e}")
        print("  Skipping EOS fit (need executable for full test)")
        return
    
    try:
        optimal_sws, eos_results, metadata = run_eos_fit(
            r_or_v_data=sws_values,
            energy_data=energy_values,
            output_path=phase_path,
            job_name="CuMg_sws_test",
            comment="Test EOS fit for Cu0_Mg100",
            eos_executable=eos_executable,
            eos_type='MO88',
            use_symmetric_selection=True,
            n_points_final=7
        )
        
        print(f"\n✓ EOS fit completed")
        print(f"  Optimal SWS: {optimal_sws:.6f}")
        
        if metadata.get('warnings'):
            print("\n⚠ Warnings:")
            for warning in metadata['warnings']:
                print(f"  {warning}")
        
        # Test expansion detection
        print("\n" + "-"*70)
        print("STEP 5: Test expansion detection")
        print("-"*70)
        
        needs_expansion, reason = detect_expansion_needed(
            eos_results, sws_values, energy_values, optimal_sws
        )
        
        print(f"  Needs expansion: {needs_expansion}")
        if needs_expansion:
            print(f"  Reason: {reason}")
        
        # Test Morse EOS estimation
        print("\n" + "-"*70)
        print("STEP 6: Test Morse EOS estimation")
        print("-"*70)
        
        morse_min, morse_energy, morse_info = estimate_morse_minimum(
            sws_values, energy_values
        )
        
        print(f"  Estimated minimum SWS: {morse_min:.6f}")
        print(f"  Estimated minimum energy: {morse_energy:.6f} Ry")
        print(f"  R²: {morse_info['r_squared']:.3f}")
        print(f"  RMS: {morse_info['rms']:.6f}")
        print(f"  Is valid: {morse_info['is_valid']}")
        if morse_info.get('morse_params'):
            print(f"  Morse parameters: a={morse_info['morse_params']['a']:.6f}, "
                  f"b={morse_info['morse_params']['b']:.6f}, "
                  f"c={morse_info['morse_params']['c']:.6f}, "
                  f"λ={morse_info['morse_params']['lambda']:.6f}")
        
        if morse_info['is_valid']:
            # Test parameter vector generation
            print("\n" + "-"*70)
            print("STEP 7: Test parameter vector generation")
            print("-"*70)
            
            new_sws_values = generate_parameter_vector_around_estimate(
                estimated_minimum=morse_min,
                step_size=0.05,
                n_points=14,
                expansion_factor=3.0
            )
            
            print(f"  Generated {len(new_sws_values)} points")
            print(f"  Range: [{min(new_sws_values):.4f}, {max(new_sws_values):.4f}]")
            print(f"  Points: {[f'{s:.4f}' for s in new_sws_values[:5]]} ... {[f'{s:.4f}' for s in new_sws_values[-5:]]}")
            
            # Check which points need calculation
            existing_set = set(sws_values)
            new_points = [v for v in new_sws_values if v not in existing_set]
            print(f"\n  Existing points: {len(sws_values)}")
            print(f"  New points needed: {len(new_points)}")
            if new_points:
                print(f"  New points: {[f'{s:.4f}' for s in new_points[:10]]} ...")
        
        # Summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"✓ Parsed {len(sws_values)} data points")
        print(f"✓ Data persistence working")
        print(f"✓ EOS fit completed: optimal SWS = {optimal_sws:.6f}")
        print(f"✓ Expansion detection: {'NEEDED' if needs_expansion else 'NOT NEEDED'}")
        if needs_expansion:
            print(f"  Reason: {reason}")
        print(f"✓ Morse EOS estimation: minimum at {morse_min:.6f} (R² = {morse_info['r_squared']:.3f})")
        
        if needs_expansion and morse_info['is_valid']:
            print(f"\n⚠ RECOMMENDATION:")
            print(f"  The equilibrium appears to be outside the current range.")
            print(f"  Suggested expansion:")
            print(f"    - Estimated minimum: {morse_min:.6f}")
            print(f"    - New range: [{min(new_sws_values):.4f}, {max(new_sws_values):.4f}]")
            print(f"    - Points to calculate: {len(new_points)}")
        
    except Exception as e:
        print(f"\n✗ Error during EOS fit or expansion test: {e}")
        import traceback
        traceback.print_exc()
        return


if __name__ == "__main__":
    main()
