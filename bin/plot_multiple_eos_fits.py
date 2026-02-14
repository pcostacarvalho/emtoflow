#!/usr/bin/env python3
"""
Plot multiple EOS final fits together on a single figure.

Reads JSON files containing EOS fit results (like sws_optimization_results.json),
extracts the final fit data and parameters, and plots all fits together with
both data points and smooth fitted curves.
"""

import json
import argparse
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import numpy as np
import matplotlib.pyplot as plt

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.inputs.eos_emto import parse_eos_output, morse_energy


def read_json_file(filepath: Path) -> Optional[Dict]:
    """
    Read JSON file and extract final fit data.
    
    Parameters
    ----------
    filepath : Path
        Path to JSON file
        
    Returns
    -------
    dict or None
        Dictionary with extracted data:
        - 'sws_values_final': List of SWS values
        - 'energy_values_final': List of energy values
        - 'optimal_sws': Optimal SWS value
        - 'eos_fits': Dictionary of EOS fit parameters
        - 'eos_type': Type of EOS (e.g., 'MO88')
        - 'filepath': Original file path
        - 'label': Label for plotting (filename without extension)
        Returns None if file cannot be read or doesn't contain required data
    """
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Could not read {filepath}: {e}")
        return None
    
    # Extract required fields - try final values first, then fall back to regular values
    sws_values_final = data.get('sws_values_final')
    energy_values_final = data.get('energy_values_final')
    
    # Fallback to sws_values and energy_values if final values not found
    if sws_values_final is None or energy_values_final is None:
        print(f"Warning: {filepath} does not contain 'sws_values_final' or 'energy_values_final'")
        sws_values_final = data.get('sws_values')
        energy_values_final = data.get('energy_values')
        if sws_values_final is None or energy_values_final is None:
            print(f"  Also missing 'sws_values' or 'energy_values'. Skipping file.")
            return None
        print(f"  Using 'sws_values' and 'energy_values' instead")
    
    result = {
        'filepath': filepath,
        'label': filepath.stem,
        'sws_values_final': sws_values_final,
        'energy_values_final': energy_values_final,
        'optimal_sws': data.get('optimal_sws'),
        'eos_fits': data.get('eos_fits', {}),
        'eos_type': data.get('eos_type')
    }
    
    # Check array lengths match
    if len(result['sws_values_final']) != len(result['energy_values_final']):
        print(f"Warning: {filepath} has mismatched array lengths")
        return None
    
    return result


def find_eos_output_file(json_path: Path, label: str) -> Optional[Path]:
    """
    Find corresponding EOS output file (.out) for a JSON file.
    
    Assumes the EOS output file is named: {label}_eos_fit.out
    
    Parameters
    ----------
    json_path : Path
        Path to JSON file
    label : str
        Label for the fit
        
    Returns
    -------
    Path or None
        Path to EOS output file if found, None otherwise
    """
    json_dir = json_path.parent
    
    # EOS output file is named: {label}_eos_fit.out
    eos_output_file = json_dir / f"{label}_eos_fit.out"
    
    if eos_output_file.exists():
        return eos_output_file
    
    return None


def get_morse_parameters_from_eos_output(eos_output_file: Path) -> Dict:
    """
    Parse EOS output file to extract Morse parameters.
    
    Parameters
    ----------
    eos_output_file : Path
        Path to EOS output file
        
    Returns
    -------
    dict
        Dictionary with Morse parameters:
        - 'a': float
        - 'b': float
        - 'c': float
        - 'lambda': float
        
    Raises
    ------
    RuntimeError
        If file cannot be parsed or parameters not found
    """
    results = parse_eos_output(str(eos_output_file))
    
    # Look for Morse fit (try 'morse' or 'MO88')
    morse_fit = None
    if 'morse' in results:
        morse_fit = results['morse']
    elif 'MO88' in results:
        morse_fit = results['MO88']
    
    if morse_fit is None:
        raise RuntimeError(f"No Morse fit found in EOS output file: {eos_output_file}")
    
    # Extract parameters from additional_params
    if not morse_fit.additional_params:
        raise RuntimeError(f"No additional_params in Morse fit: {eos_output_file}")
    
    params = {}
    for key in ['a', 'b', 'c', 'lambda']:
        if key not in morse_fit.additional_params:
            raise RuntimeError(f"Missing required Morse parameter '{key}' in {eos_output_file}")
        params[key] = morse_fit.additional_params[key]
    
    return params


def evaluate_morse_fit(sws_values: List[float], morse_params: Dict, 
                       equilibrium_energy: Optional[float] = None,
                       energy_values: Optional[List[float]] = None,
                       optimal_sws: Optional[float] = None) -> Tuple[np.ndarray, np.ndarray]:
    """
    Evaluate Morse EOS function to create smooth curve.
    
    Parameters
    ----------
    sws_values : list of float
        SWS values for data points
    morse_params : dict
        Dictionary with Morse parameters: 'a', 'b', 'c', 'lambda'
    equilibrium_energy : float, optional
        Equilibrium energy (eeq) to use for offset. If None, uses data points.
    energy_values : list of float, optional
        Actual energy values from data points (used for offset if equilibrium_energy is None)
    optimal_sws : float, optional
        Optimal SWS value (used with equilibrium_energy for offset calculation)
        
    Returns
    -------
    tuple of (np.ndarray, np.ndarray)
        (sws_smooth, energy_smooth) - smooth arrays for plotting
    """
    a = morse_params['a']
    b = morse_params['b']
    c = morse_params['c']
    lambda_param = morse_params['lambda']
    
    # Create smooth SWS range
    sws_min = min(sws_values)
    sws_max = max(sws_values)
    sws_range = sws_max - sws_min
    sws_smooth = np.linspace(sws_min - 0.05 * sws_range, sws_max + 0.05 * sws_range, 200)
    
    # Evaluate Morse function (returns relative energy)
    energy_relative = np.array([morse_energy(r, a, b, c, lambda_param) for r in sws_smooth])
    
    # Calculate offset to match equilibrium energy or data points
    if equilibrium_energy is not None and optimal_sws is not None:
        # Use equilibrium energy at optimal SWS
        energy_at_optimal = morse_energy(optimal_sws, a, b, c, lambda_param)
        offset = equilibrium_energy - energy_at_optimal
    elif energy_values is not None and len(energy_values) > 0:
        # Use first data point to determine offset
        energy_at_first_sws = morse_energy(sws_values[0], a, b, c, lambda_param)
        offset = energy_values[0] - energy_at_first_sws
    else:
        # Fallback: use minimum energy from relative curve
        # This is less accurate but better than nothing
        min_idx = np.argmin(energy_relative)
        min_sws = sws_smooth[min_idx]
        energy_at_min = energy_relative[min_idx]
        # Estimate offset from data if available
        if energy_values is not None:
            min_energy_data = min(energy_values)
            offset = min_energy_data - energy_at_min
        else:
            offset = 0.0
    
    energy_smooth = energy_relative + offset
    
    return sws_smooth, energy_smooth


def plot_all_fits(json_data_list: List[Dict], output_file: str, 
                  labels: Optional[List[str]] = None,
                  show_data_points: bool = True,
                  show_curves: bool = True) -> None:
    """
    Plot all EOS fits together on a single figure.
    
    Parameters
    ----------
    json_data_list : list of dict
        List of data dictionaries from read_json_file()
    output_file : str
        Output filename for plot
    labels : list of str, optional
        Custom labels for each fit. If None, uses file names.
    show_data_points : bool
        Whether to plot data points
    show_curves : bool
        Whether to plot smooth curves
    """
    if not json_data_list:
        print("Error: No data to plot!")
        return
    
    # Set up colors
    colors = plt.cm.tab10(np.linspace(0, 1, len(json_data_list)))
    
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    
    for i, data in enumerate(json_data_list):
        sws_values = data['sws_values_final']
        energy_values = data['energy_values_final']
        optimal_sws = data.get('optimal_sws')
        label = labels[i] if labels and i < len(labels) else data['label']
        color = colors[i]
        
        # Plot data points
        if show_data_points:
            ax.plot(sws_values, energy_values, 'o', markersize=8, 
                   color=color, alpha=0.7, label=f'{label}', zorder=5)
        
        # Plot smooth curve
        if show_curves:
            # Get Morse parameters from EOS output file
            eos_output_file = find_eos_output_file(data['filepath'], data['label'])
            if not eos_output_file or not eos_output_file.exists():
                expected_file = data['filepath'].parent / f"{data['label']}_eos_fit.out"
                raise RuntimeError(f"EOS output file not found for {data['filepath']}. Expected: {expected_file}")
            
            morse_params = get_morse_parameters_from_eos_output(eos_output_file)
            
            # Use Morse EOS function
            eos_fits = data.get('eos_fits', {})
            morse_fit = eos_fits.get('morse', {})
            equilibrium_energy = morse_fit.get('eeq')
            
            sws_smooth, energy_smooth = evaluate_morse_fit(
                sws_values, morse_params, 
                equilibrium_energy=equilibrium_energy,
                energy_values=energy_values,
                optimal_sws=optimal_sws
            )
            ax.plot(sws_smooth, energy_smooth, '-', linewidth=2, 
                   color=color, alpha=0.8, label=f'{label}', zorder=3)
        
        # Mark optimal SWS
        if optimal_sws is not None and not np.isnan(optimal_sws):
            ax.axvline(optimal_sws, color=color, linestyle=':', linewidth=1.5, 
                      alpha=0.5, zorder=2)
    
    ax.set_xlabel('SWS (Bohr)', fontsize=12)
    ax.set_ylabel('Total Energy (Ry)', fontsize=12)
    ax.set_title('EOS Final Fits Comparison', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=9, loc='best', ncol=2)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\nPlot saved to: {output_file}")
    plt.close()


def main():
    parser = argparse.ArgumentParser(
        description='Plot multiple EOS final fits together',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Plot files from a list of labels
  python bin/plot_multiple_eos_fits.py --labels Cu50Mg50 Cu70Mg30 Cu30Mg70
  
  # Labels can also be provided in a file (one per line)
  python bin/plot_multiple_eos_fits.py --file-list labels.txt
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--labels', '-l', nargs='+', type=str,
                      help='List of labels (files will be {label}_sws_optimization.json)')
    group.add_argument('--file-list', type=str,
                      help='File containing list of labels (one per line)')
    
    parser.add_argument('--output', '-o', type=str, default='all_eos_fits.png',
                      help='Output filename (default: all_eos_fits.png)')
    parser.add_argument('--directory', '-d', type=str, default='./',
                      help='Directory containing JSON files (default: current directory)')
    parser.add_argument('--no-data-points', action='store_true',
                      help='Plot only curves, not data points')
    parser.add_argument('--no-curves', action='store_true',
                      help='Plot only data points, not curves')
    
    args = parser.parse_args()
    
    # Get labels from command line or file
    if args.labels:
        labels = args.labels
    else:
        # Read labels from file
        file_list_path = Path(args.file_list)
        if not file_list_path.exists():
            print(f"Error: File list not found: {file_list_path}")
            return 1
        try:
            with open(file_list_path, 'r') as f:
                labels = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
        except IOError as e:
            print(f"Error: Could not read file list: {e}")
            return 1
    
    if not labels:
        print("Error: No labels provided!")
        return 1
    
    # Construct file paths from labels
    directory = Path(args.directory)
    if not directory.exists():
        print(f"Error: Directory not found: {directory}")
        return 1
    
    json_files = []
    for label in labels:
        json_file = directory / f"{label}_sws_optimization.json"
        if not json_file.exists():
            print(f"Error: File not found: {json_file}")
            return 1
        json_files.append(json_file)
    
    if not json_files:
        print("Error: No JSON files found!")
        return 1
    
    print(f"Found {len(json_files)} JSON file(s)")
    
    # Read JSON files
    json_data_list = []
    for json_file, label in zip(json_files, labels):
        print(f"Reading {json_file}...")
        data = read_json_file(json_file)
        if data:
            # Override the label with the provided label
            data['label'] = label
            json_data_list.append(data)
            print(f"  ✓ Loaded {len(data['sws_values_final'])} data points")
        else:
            print(f"  ✗ Skipped")
    
    if not json_data_list:
        print("Error: No valid data found in any JSON file!")
        return 1
    
    # Extract labels from data
    plot_labels = [data['label'] for data in json_data_list]
    
    # Plot
    plot_all_fits(
        json_data_list,
        args.output,
        labels=plot_labels,
        show_data_points=not args.no_data_points,
        show_curves=not args.no_curves
    )
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
