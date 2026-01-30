#!/usr/bin/env python3
"""
Plot energies_raw.dat files from multiple folders together.
Points marked with * in the data file will be plotted differently.
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import re


def read_energies_raw(filepath):
    """
    Read energies_raw.dat file.
    Returns: (cu_percentages, energy_per_site, total_energy, marked_points)
    where marked_points is a set of Cu percentages that have * marker
    """
    cu_percentages = []
    energy_per_site = []
    total_energy = []
    marked_points = set()
    
    with open(filepath, 'r') as f:
        for line in f:
            # Skip comments
            if line.strip().startswith('#'):
                continue
            
            # Check if line has * marker
            if '*' in line:
                # Remove * and add to marked set
                line = line.replace('*', '')
                parts = line.split()
                if len(parts) >= 2:
                    cu_percent = int(float(parts[0]))
                    marked_points.add(cu_percent)
            
            # Parse data
            parts = line.split()
            if len(parts) >= 2:
                try:
                    cu_percent = int(float(parts[0]))
                    e_per_site = float(parts[1])
                    e_total = float(parts[2]) if len(parts) >= 3 else None
                    
                    cu_percentages.append(cu_percent)
                    energy_per_site.append(e_per_site)
                    total_energy.append(e_total)
                except (ValueError, IndexError):
                    continue
    
    return cu_percentages, energy_per_site, total_energy, marked_points


def main():
    # Current directory
    data_files = ['/proj/snic2014-8-7/users/x_pamca/phase_diagrams/all_results/fcc/energies_raw.dat', 
                  '/proj/snic2014-8-7/users/x_pamca/phase_diagrams/all_results/hcp/energies_raw.dat',
                  '/proj/snic2014-8-7/users/x_pamca/phase_diagrams/all_results/cu2mg/energies_raw.dat']
        

    names = ['CuMg_FCC', 'CuMg_HCP', 'Cu2Mg']

    if not data_files:
        print("No energies_raw.dat files found in subdirectories!")
        return
    
    print(f"Found {len(data_files)} energies_raw.dat files")

    ref_cu = -3310.060512  # Cu 100% (Ry/site)
    ref_mg = -400.662871   # Mg 100% (Ry/site)
    
    # Create figure with two subplots
    fig, ax1 = plt.subplots(1, 1, figsize=(14, 6))
    
    # Plot each file
    for index,data_file in enumerate(data_files):
        folder_name = names[index]
        cu_percentages, energy_per_site, total_energy, marked_points = read_energies_raw(data_file)
        mg_percentages = [100-x for x in cu_percentages]
        formation_energies = [conc - (cu_percentages[index]/100)*ref_cu - (mg_percentages[index]/100)*ref_mg for index, conc in enumerate(energy_per_site)]
        
        if not cu_percentages:
            print(f"  Warning: No data found in {data_file}")
            continue
        
        mg_percentages = np.array(mg_percentages)
        formation_energies = np.array(formation_energies)
        
        # Separate marked and unmarked points
        marked_mask = np.array([cp in marked_points for cp in cu_percentages])
        unmarked_mask = ~marked_mask
        
        # Plot formation energy - all points connected
        line = ax1.plot(mg_percentages, formation_energies, '-', linewidth=1.5, alpha=0.7, 
                        label=f'{folder_name}')
        line_color = line[0].get_color()
        
        # Overlay markers for unmarked points with same color as line
        if np.any(unmarked_mask):
            ax1.plot(mg_percentages[unmarked_mask], formation_energies[unmarked_mask], 
                    'o', markersize=6, alpha=0.7, color=line_color, linestyle='')
        # Overlay different markers for marked points with same line color
        if np.any(marked_mask):
            ax1.plot(mg_percentages[marked_mask], formation_energies[marked_mask], 
                    's', markersize=10, alpha=0.9, markeredgewidth=2, 
                    markeredgecolor='red', markerfacecolor='none', 
                    linestyle='', color=line_color)
    
    
    # Format energy per site plot
    ax1.axhline(0, color='grey')
    ax1.set_xlabel('Mg Percentage (%)', fontsize=12)
    ax1.set_ylabel('Formation energy (Ry/site)', fontsize=12)
    ax1.set_title('Energy per Site vs Mg Percentage', fontsize=14)
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=9, loc='best')

    
    plt.tight_layout()
    
    # Save plot
    output_file = 'energies_raw_comparison.png'
    plt.savefig(output_file, dpi=300)
    print(f"\nPlot saved to: {output_file}")
    
    # Show plot
    plt.show()


if __name__ == "__main__":
    main()
