#!/usr/bin/env python3
"""
Quick function to plot energies from JSON parameter optimization files
"""
import json
import matplotlib.pyplot as plt
import numpy as np


def plot_energy_from_json(json_file, output_file=None, show_plot=True):
    """
    Plot parameter vs energy from a JSON file.
    
    Parameters
    ----------
    json_file : str
        Path to JSON file with 'parameter_name', 'data_points' fields
    output_file : str, optional
        Path to save the plot (e.g., 'plot.png'). If None, doesn't save.
    show_plot : bool, optional
        Whether to display the plot. Default: True
    
    Returns
    -------
    dict
        Dictionary with minimum information: {'parameter': value, 'energy': value, 'index': idx}
    
    Example
    -------
    >>> plot_energy_from_json('sws_data.json', 'sws_plot.png')
    """
    # Load data
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # Extract data
    param_name = data.get('parameter_name', 'parameter')
    data_points = data['data_points']
    
    parameters = np.array([point['parameter'] for point in data_points])
    energies = np.array([point['energy'] for point in data_points])
    
    # Find minimum
    min_idx = np.argmin(energies)
    min_param = parameters[min_idx]
    min_energy = energies[min_idx]
    
    # Create plot
    fig, ax = plt.subplots(figsize=(10, 6))
    
    ax.plot(parameters, energies, 'o-', linewidth=1.5, markersize=6, 
            alpha=0.7, label='DFT Data')
    ax.plot(min_param, min_energy, 'r*', markersize=15, 
            label=f'Minimum: {param_name}={min_param:.4f}, E={min_energy:.6f} Ry')
    
    ax.set_xlabel(f'{param_name.upper()} (Bohr)' if param_name == 'sws' else f'{param_name}', 
                  fontsize=12, fontweight='bold')
    ax.set_ylabel('Energy (Ry)', fontsize=12, fontweight='bold')
    ax.set_title(f'{param_name.upper()} Optimization', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(fontsize=10)
    
    # Add statistics
    stats_text = f'Points: {len(parameters)}\nRange: [{parameters.min():.4f}, {parameters.max():.4f}]\nΔE: {energies.max()-energies.min():.6f} Ry'
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
            fontsize=9, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    
    # Save if requested
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Plot saved to: {output_file}")
    
    # Show if requested
    if show_plot:
        plt.show()
    
    # Return minimum info
    return {
        'parameter': min_param,
        'energy': min_energy,
        'index': min_idx
    }


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python plot_json_energy.py <json_file> [output_file]")
        print("\nExample:")
        print("  python plot_json_energy.py sws_data.json")
        print("  python plot_json_energy.py sws_data.json sws_plot.png")
        sys.exit(1)
    
    json_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    min_info = plot_energy_from_json(json_file, output_file)
    
    print(f"\nMinimum found:")
    print(f"  Index: {min_info['index']}")
    print(f"  Parameter: {min_info['parameter']:.6f}")
    print(f"  Energy: {min_info['energy']:.6f} Ry")
