#!/usr/bin/env python3
"""
Plot formation energies from data file.
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys


def plot_formation_energy(data_file="formation_energies.dat"):
    """
    Plot formation energy from data file.
    """
    if not Path(data_file).exists():
        print(f"Error: {data_file} not found!")
        print("Run extract_formation_energy.py or extract_formation_energy.sh first.")
        return
    
    # Load data
    data = np.loadtxt(data_file, comments='#')
    
    if len(data) == 0:
        print("Error: No data found in file")
        return
    
    cu_percentages = data[:, 0]
    formation_energies = data[:, 1]
    
    # Create plot
    plt.figure(figsize=(10, 6))
    plt.plot(cu_percentages, formation_energies, 'o-', linewidth=2, markersize=8, 
             color='royalblue', label='Formation Energy')
    plt.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    plt.xlabel('Cu Percentage (%)', fontsize=12)
    plt.ylabel('Formation Energy (Ry)', fontsize=12)
    plt.title('Formation Energy of Cu-Mg Alloys', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=10)
    plt.tight_layout()
    
    # Save plot
    output_file = 'formation_energy_vs_composition.png'
    plt.savefig(output_file, dpi=300)
    print(f"Plot saved to: {output_file}")
    
    # Show plot
    plt.show()


def plot_raw_energy(data_file="energies_raw.dat"):
    """
    Plot raw energies from data file.
    """
    if not Path(data_file).exists():
        print(f"Error: {data_file} not found!")
        return
    
    # Load data
    data = np.loadtxt(data_file, comments='#')
    
    if len(data) == 0:
        print("Error: No data found in file")
        return
    
    cu_percentages = data[:, 0]
    energies = data[:, 1]
    
    # Create plot
    plt.figure(figsize=(10, 6))
    plt.plot(cu_percentages, energies, 'o-', linewidth=2, markersize=8, 
             color='forestgreen', label='Total Energy')
    plt.xlabel('Cu Percentage (%)', fontsize=12)
    plt.ylabel('Total Energy (Ry)', fontsize=12)
    plt.title('Total Energy vs Cu Percentage', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=10)
    plt.tight_layout()
    
    # Save plot
    output_file = 'energy_vs_composition.png'
    plt.savefig(output_file, dpi=300)
    print(f"Plot saved to: {output_file}")
    
    # Show plot
    plt.show()


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--raw':
        plot_raw_energy()
    else:
        plot_formation_energy()


if __name__ == "__main__":
    main()
