#!/usr/bin/env python3
"""
Extract phase 3 energies from EMTO calculations and compute formation energies.
"""

import os
import re
import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


def extract_phase3_energy(folder_path):
    """
    Extract final energy from workflow_results.json in the folder.
    """
    folder = Path(folder_path)
    
    # Look for workflow_results.json
    json_file = folder / "workflow_results.json"
    
    if json_file.exists():
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            # Primary: Check for final_energy (standard key in workflow results)
            if 'final_energy' in data:
                return float(data['final_energy'])
            
            # Fallback: Try other possible keys
            possible_keys = [
                'total_energy',
                'energy',
                'phase_3_energy',
                'phase3_energy',
            ]
            
            for key in possible_keys:
                if key in data:
                    return float(data[key])
            
            print(f"  Warning: Could not find energy in {json_file}")
            print(f"  Available keys: {list(data.keys())}")
            
        except json.JSONDecodeError:
            print(f"  Error: Could not parse JSON in {json_file}")
        except Exception as e:
            print(f"  Error reading {json_file}: {e}")
    
    return None


def parse_composition(folder_name):
    """
    Parse composition from folder name like 'Cu30_Mg70'.
    Returns: (Cu_percent, Mg_percent)
    """
    match = re.match(r'Cu(\d+)_Mg(\d+)', folder_name)
    if match:
        cu_percent = int(match.group(1))
        mg_percent = int(match.group(2))
        return cu_percent, mg_percent
    return None, None


def main():
    # Current directory
    current_dir = Path.cwd()
    
    # Dictionary to store results: {Cu_percent: energy}
    results = {}
    
    # Find all composition folders
    composition_folders = sorted([d for d in current_dir.iterdir() 
                                 if d.is_dir() and re.match(r'Cu\d+_Mg\d+', d.name)])
    
    if not composition_folders:
        print("No composition folders found (Cu*_Mg* pattern)")
        return
    
    print("Extracting phase 3 energies from workflow_results.json files...")
    print("-" * 60)
    
    for folder in composition_folders:
        cu_percent, mg_percent = parse_composition(folder.name)
        if cu_percent is None:
            continue
        
        energy = extract_phase3_energy(folder)
        
        if energy is not None:
            results[cu_percent] = energy
            print(f"{folder.name:15s} Cu: {cu_percent:3d}%  Energy: {energy:12.6f} Ry")
        else:
            print(f"{folder.name:15s} Cu: {cu_percent:3d}%  Energy: NOT FOUND")
    
    if not results:
        print("\nNo energies were extracted. Please check the file structure.")
        return
    
    # Check if we have pure elements
    if 0 not in results or 100 not in results:
        print("\nWarning: Missing pure element energies (Cu0_Mg100 or Cu100_Mg0)")
        print("Cannot calculate formation energies without reference states.")
        
        # Just save raw energies
        output_file = "energies_raw.dat"
        with open(output_file, 'w') as f:
            f.write("# Cu_percent  Energy(Ry)\n")
            for cu_percent in sorted(results.keys()):
                f.write(f"{cu_percent:5d}  {results[cu_percent]:15.8f}\n")
        
        print(f"\nRaw energies saved to: {output_file}")
        
        # Plot raw energies
        cu_percentages = np.array(sorted(results.keys()))
        energies = np.array([results[cp] for cp in cu_percentages])
        
        plt.figure(figsize=(10, 6))
        plt.plot(cu_percentages, energies, 'o-', linewidth=2, markersize=8)
        plt.xlabel('Cu Percentage (%)', fontsize=12)
        plt.ylabel('Total Energy (Ry)', fontsize=12)
        plt.title('Total Energy vs Cu Percentage', fontsize=14)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig('energy_vs_composition.png', dpi=300)
        print(f"Plot saved to: energy_vs_composition.png")
        
        return
    
    # Calculate formation energies
    E_Cu_pure = -3310.060512 #results[100]  # Cu100_Mg0
    E_Mg_pure = -400.662871 #results[0]    # Cu0_Mg100
    
    print("\n" + "=" * 60)
    print(f"Reference energies:")
    print(f"  E(Cu 100%) = {E_Cu_pure:.6f} Ry")
    print(f"  E(Mg 100%) = {E_Mg_pure:.6f} Ry")
    print("=" * 60)
    
    formation_energies = {}
    
    print("\nFormation Energies:")
    print("-" * 60)
    
    for cu_percent in sorted(results.keys()):
        mg_percent = 100 - cu_percent
        conc_Cu = cu_percent / 100.0
        conc_Mg = mg_percent / 100.0
        
        E_alloy = results[cu_percent]
        
        # Formation energy formula
        E_form = E_alloy - E_Cu_pure * conc_Cu - E_Mg_pure * conc_Mg
        
        formation_energies[cu_percent] = E_form
        
        print(f"Cu{cu_percent:3d}_Mg{mg_percent:3d}  E_form = {E_form:12.6f} Ry")
    
    # Save to file
    output_file = "formation_energies.dat"
    with open(output_file, 'w') as f:
        f.write("# Cu_percent  FormationEnergy(Ry)\n")
        for cu_percent in sorted(formation_energies.keys()):
            f.write(f"{cu_percent:5d}  {formation_energies[cu_percent]:15.8f}\n")
    
    print(f"\nFormation energies saved to: {output_file}")
    
    # Also save raw energies
    output_file_raw = "energies_raw.dat"
    with open(output_file_raw, 'w') as f:
        f.write("# Cu_percent  Energy(Ry)\n")
        for cu_percent in sorted(results.keys()):
            f.write(f"{cu_percent:5d}  {results[cu_percent]:15.8f}\n")
    
    print(f"Raw energies saved to: {output_file_raw}")
    
    # Create plot
    cu_percentages = np.array(sorted(formation_energies.keys()))
    e_form_values = np.array([formation_energies[cp] for cp in cu_percentages])
    
    plt.figure(figsize=(10, 6))
    plt.plot(cu_percentages, e_form_values, 'o-', linewidth=2, markersize=8, 
             color='royalblue', label='Formation Energy')
    plt.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    plt.xlabel('Cu Percentage (%)', fontsize=12)
    plt.ylabel('Formation Energy (Ry)', fontsize=12)
    plt.title('Formation Energy of Cu-Mg Alloys', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=10)
    plt.tight_layout()
    
    # Save plot
    plt.savefig('formation_energy_vs_composition.png', dpi=300)
    print(f"Plot saved to: formation_energy_vs_composition.png")
    
    # Show plot
    plt.show()


if __name__ == "__main__":
    main()
