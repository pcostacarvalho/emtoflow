#!/usr/bin/env python3
"""
Quick script to analyze the Cu0_Mg100 case where equilibrium is outside range.
"""

import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).parent))

from modules.extract_results import parse_kfcd

def extract_sws_from_filename(filename: str) -> float:
    """Extract SWS value from filename."""
    match = re.search(r'_(\d+\.\d+)\.prn$', filename)
    if match:
        return float(match.group(1))
    raise ValueError(f"Could not extract SWS from filename: {filename}")

def main():
    phase_path = Path("/Users/pamco116/Documents/GitHub/EMTO_input_automation/Cu0_Mg100/phase2_sws_optimization")
    job_name = "CuMg"
    optimal_ca = 1.00
    
    # Find all PRN files
    fcd_dir = phase_path / "fcd"
    prn_files = sorted(fcd_dir.glob(f"{job_name}_{optimal_ca:.2f}_*.prn"))
    
    print("="*70)
    print("ANALYZING Cu0_Mg100 - Equilibrium Outside Range Case")
    print("="*70)
    print(f"\nFound {len(prn_files)} PRN files:\n")
    
    sws_values = []
    energy_values = []
    
    for prn_file in prn_files:
        sws = extract_sws_from_filename(prn_file.name)
        try:
            results = parse_kfcd(str(prn_file), functional='GGA')
            if results.total_energy is None:
                continue
            energy = results.energies_by_functional['system']['GGA']
            sws_values.append(sws)
            energy_values.append(energy)
            print(f"  SWS = {sws:.4f}: E = {energy:.6f} Ry")
        except Exception as e:
            print(f"  Error parsing {prn_file.name}: {e}")
    
    if len(sws_values) < 2:
        print("Not enough data points")
        return
    
    print(f"\n" + "="*70)
    print("ANALYSIS")
    print("="*70)
    print(f"SWS range: [{min(sws_values):.4f}, {max(sws_values):.4f}]")
    print(f"Energy range: [{min(energy_values):.6f}, {max(energy_values):.6f}]")
    print(f"\nEnergy trend:")
    
    # Check if energy is still decreasing at the end
    if len(energy_values) >= 3:
        last_three = energy_values[-3:]
        if last_three[0] > last_three[1] > last_three[2]:
            print("  ⚠ Energy is STILL DECREASING at the end of the range!")
            print(f"  Last 3 energies: {[f'{e:.6f}' for e in last_three]}")
            print(f"  This suggests equilibrium is BEYOND the maximum SWS value")
        else:
            print("  Energy appears to have reached a minimum")
    
    # Check if energy is increasing at the beginning
    if len(energy_values) >= 3:
        first_three = energy_values[:3]
        if first_three[0] < first_three[1] < first_three[2]:
            print("  ⚠ Energy is INCREASING at the beginning of the range!")
            print(f"  First 3 energies: {[f'{e:.6f}' for e in first_three]}")
            print(f"  This suggests equilibrium is BELOW the minimum SWS value")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    main()
