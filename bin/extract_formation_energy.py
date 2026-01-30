#!/usr/bin/env python3
"""
Extract phase 3 energies from EMTO calculations and compute formation energies.
Uses energy per site from fcd calculation outputs.
"""

import os
import re
import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))
from modules.extract_results import parse_kfcd


def find_fcd_prn_file(folder_path):
    """
    Find the fcd/prn file in the folder structure.
    Looks in: phase3_optimized_calculation/fcd/*.prn or fcd/*.prn
    """
    folder = Path(folder_path)
    
    # Try phase3_optimized_calculation/fcd/*.prn first
    phase3_fcd = folder / "phase3_optimized_calculation" / "fcd"
    if phase3_fcd.exists():
        prn_files = list(phase3_fcd.glob("*.prn"))
        if prn_files:
            return prn_files[0]  # Return first .prn file found
    
    # Try fcd/*.prn
    fcd_dir = folder / "fcd"
    if fcd_dir.exists():
        prn_files = list(fcd_dir.glob("*.prn"))
        if prn_files:
            return prn_files[0]  # Return first .prn file found
    
    return None


def extract_phase3_energy(folder_path, functional='GGA'):
    """
    Extract total energy and energy per site from fcd/prn file.
    Falls back to workflow_results.json if prn file not found.
    Returns: (total_energy, energy_per_site) or (None, None) if not found
    """
    folder = Path(folder_path)
    
    # First try to get from fcd/prn file
    prn_file = find_fcd_prn_file(folder_path)
    
    if prn_file is not None:
        try:
            results = parse_kfcd(str(prn_file), functional=functional)
            
            total_energy = results.total_energy
            energy_per_site = results.energy_per_site
            
            return total_energy, energy_per_site
            
        except Exception as e:
            print(f"  Error parsing {prn_file}: {e}")
    
    # Fallback: try workflow_results.json
    json_file = folder / "workflow_results.json"
    if json_file.exists():
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            total_energy = data.get('final_energy')
            energy_per_site = data.get('final_energy_per_site')
            
            if energy_per_site is not None:
                return total_energy, energy_per_site
            elif total_energy is not None:
                # If only total energy is available, return it but warn
                print(f"  Warning: Only total energy found in {json_file}, energy per site not available")
                return total_energy, None
                
        except json.JSONDecodeError:
            print(f"  Error: Could not parse JSON in {json_file}")
        except Exception as e:
            print(f"  Error reading {json_file}: {e}")
    
    return None, None


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
    
    print("Extracting phase 3 energies from fcd/prn files...")
    print("-" * 60)
    
    # Dictionary to store energy per site: {Cu_percent: energy_per_site}
    results_per_site = {}
    # Dictionary to store total energies: {Cu_percent: total_energy}
    results_total = {}
    
    for folder in composition_folders:
        cu_percent, mg_percent = parse_composition(folder.name)
        if cu_percent is None:
            continue
        
        total_energy, energy_per_site = extract_phase3_energy(folder)
        
        if energy_per_site is not None:
            results_per_site[cu_percent] = energy_per_site
            if total_energy is not None:
                results_total[cu_percent] = total_energy
            print(f"{folder.name:15s} Cu: {cu_percent:3d}%  Total: {total_energy:12.6f} Ry  Per site: {energy_per_site:12.6f} Ry/site")
        else:
            print(f"{folder.name:15s} Cu: {cu_percent:3d}%  Energy: NOT FOUND")
    
    # Use energy per site for formation energy calculations
    results = results_per_site
    
    if not results:
        print("\nNo energies were extracted. Please check the file structure.")
        return
    
    # Calculate formation energies using energy per site
    # Use fixed reference values for pure elements (energy per site)
    # These are the fixed reference values provided by the user
    E_Cu_pure = -3310.060512  # Cu 100% (Ry/site)
    E_Mg_pure = -400.662871   # Mg 100% (Ry/site)
    
    print("\n" + "=" * 60)
    print(f"Reference energies (per site):")
    print(f"  E(Cu 100%) = {E_Cu_pure:.6f} Ry/site")
    print(f"  E(Mg 100%) = {E_Mg_pure:.6f} Ry/site")
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
        
        print(f"Cu{cu_percent:3d}_Mg{mg_percent:3d}  E_form = {E_form:12.6f} Ry/site")
    
    # Save to file
    output_file = "formation_energies.dat"
    with open(output_file, 'w') as f:
        f.write("# Cu_percent  FormationEnergy(Ry/site)\n")
        for cu_percent in sorted(formation_energies.keys()):
            f.write(f"{cu_percent:5d}  {formation_energies[cu_percent]:15.8f}\n")
    
    print(f"\nFormation energies saved to: {output_file}")
    
    # Also save raw energies (energy per site)
    output_file_raw = "energies_raw.dat"
    with open(output_file_raw, 'w') as f:
        f.write("# Cu_percent  EnergyPerSite(Ry/site)  TotalEnergy(Ry)\n")
        for cu_percent in sorted(results.keys()):
            energy_per_site = results[cu_percent]
            total_energy = results_total.get(cu_percent, None)
            if total_energy is not None:
                f.write(f"{cu_percent:5d}  {energy_per_site:15.8f}  {total_energy:15.8f}\n")
            else:
                f.write(f"{cu_percent:5d}  {energy_per_site:15.8f}  {'N/A':>15s}\n")
    
    print(f"Raw energies saved to: {output_file_raw}")
    
    # Create plot
    cu_percentages = np.array(sorted(formation_energies.keys()))
    e_form_values = np.array([formation_energies[cp] for cp in cu_percentages])
    
    plt.figure(figsize=(10, 6))
    plt.plot(cu_percentages, e_form_values, 'o-', linewidth=2, markersize=8, 
             color='royalblue', label='Formation Energy')
    plt.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    plt.xlabel('Cu Percentage (%)', fontsize=12)
    plt.ylabel('Formation Energy (Ry/site)', fontsize=12)
    plt.title('Formation Energy of Cu-Mg Alloys (per site)', fontsize=14)
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
