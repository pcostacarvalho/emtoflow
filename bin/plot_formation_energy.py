#!/usr/bin/env python3
"""
Plot formation energies with phonon corrections from multiple folders.
Reads energies_raw.dat, formation_energies.dat, and phonon_energy*.dat files.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Conversion constants
RY_TO_EV = 13.6057039763
MEV_TO_RY = 1.0 / (1000.0 * RY_TO_EV)

# Reference energies (Ry/site)
ref_cu = -3310.060512  # Cu 100%
ref_mg = -400.662871   # Mg 100%


def read_energies_raw(filepath):
    """Read energies_raw.dat file."""
    data = []
    with open(filepath, 'r') as f:
        for line in f:
            if line.strip().startswith('#'):
                continue
            parts = line.split()
            if len(parts) >= 2:
                try:
                    cu_percent = float(parts[0])
                    energy_per_site = float(parts[1])
                    total_energy = float(parts[2]) if len(parts) >= 3 else None
                    data.append({
                        'Cu_percent': cu_percent,
                        'EnergyPerSite': energy_per_site,
                        'TotalEnergy': total_energy
                    })
                except (ValueError, IndexError):
                    continue
    return pd.DataFrame(data)


def read_formation_energies(filepath):
    """Read formation_energies.dat file."""
    data = []
    with open(filepath, 'r') as f:
        for line in f:
            if line.strip().startswith('#'):
                continue
            parts = line.split()
            if len(parts) >= 2:
                try:
                    cu_percent = float(parts[0])
                    formation_energy = float(parts[1])
                    data.append({
                        'Cu_percent': cu_percent,
                        'FormationEnergy_original': formation_energy
                    })
                except (ValueError, IndexError):
                    continue
    return pd.DataFrame(data)


def read_phonon_energy(filepath):
    """Read phonon_energy*.dat file.
    
    Expected format:
    # Mg_percent  composition  r_bohr  B_GPa  E_ph_meV_T300K [E_ph_meV_T0K ...]
    
    Supports files with only T300K or with multiple temperature columns.
    """
    data = []
    with open(filepath, 'r') as f:
        for line in f:
            if line.strip().startswith('#'):
                continue
            parts = line.split()
            # Need at least: Mg_percent, composition, r_bohr, B_GPa, and one temperature column
            if len(parts) >= 5:
                try:
                    mg_percent = float(parts[0])
                    cu_percent = 100.0 - mg_percent
                    r_bohr = float(parts[2])
                    b_gpa = float(parts[3])
                    
                    row_data = {
                        'Cu_percent': cu_percent,
                        'Mg_percent': mg_percent,
                        'r_bohr': r_bohr,
                        'B_GPa': b_gpa
                    }
                    
                    # Read T300K from index 4 (standard format)
                    if len(parts) >= 5:
                        row_data['E_ph_meV_T300K'] = float(parts[4])
                    
                    # Read T0K from index 5 if present
                    if len(parts) >= 6:
                        row_data['E_ph_meV_T0K'] = float(parts[5])
                    else:
                        # T0K not present, set to None
                        row_data['E_ph_meV_T0K'] = None
                    
                    data.append(row_data)
                except (ValueError, IndexError) as e:
                    continue
    return pd.DataFrame(data)


def process_folder(folder_path, folder_name):
    """Process all files in a folder and return combined dataframe."""
    folder = Path(folder_path)
    
    # Read files
    energies_raw_file = folder / 'energies_raw.dat'
    formation_energies_file = folder / 'formation_energies.dat'
    
    # Find phonon energy file (could be phonon_energy_hcp.dat or similar)
    phonon_files = list(folder.glob('phonon_energy*.dat'))
    if not phonon_files:
        print(f"Warning: No phonon_energy*.dat file found in {folder_name}")
        return None
    
    phonon_file = phonon_files[0]
    
    if not energies_raw_file.exists():
        print(f"Warning: energies_raw.dat not found in {folder_name}")
        return None
    
    # Read data
    df_raw = read_energies_raw(energies_raw_file)
    df_phonon = read_phonon_energy(phonon_file)
    
    # Start with raw data
    df = df_raw.copy()
    
    # Merge with phonon data
    df = df.merge(df_phonon, on='Cu_percent', how='outer')
    
    # Calculate Mg percentage
    df['Mg_percent'] = 100.0 - df['Cu_percent']
    
    # Always calculate formation energy from raw data
    df['FormationEnergy_original'] = (
        df['EnergyPerSite'] - 
        (df['Cu_percent'] / 100.0) * ref_cu - 
        (df['Mg_percent'] / 100.0) * ref_mg
    )
    
    # Calculate number of sites (for reference/CSV output)
    # Only calculate where we have both TotalEnergy and EnergyPerSite
    df['NumSites'] = df['TotalEnergy'] / df['EnergyPerSite']
    
    # Convert phonon energies from meV/site to Ry/site
    df['E_ph_Ry_T300K'] = df['E_ph_meV_T300K'] * MEV_TO_RY
    df['E_ph_Ry_T0K'] = df['E_ph_meV_T0K'] * MEV_TO_RY  # Will be NaN if T0K not available
    
    # Add phonon energy directly to energy per site (phonon energy is already per site)
    # Only where we have EnergyPerSite
    df['EnergyPerSite_T300K'] = df['EnergyPerSite'] + df['E_ph_Ry_T300K']
    df['EnergyPerSite_T0K'] = df['EnergyPerSite'] + df['E_ph_Ry_T0K']  # Will be NaN if T0K not available
    
    # Calculate new total energies with phonon corrections (for CSV output)
    df['TotalEnergy_T300K'] = df['EnergyPerSite_T300K'] * df['NumSites']
    df['TotalEnergy_T0K'] = df['EnergyPerSite_T0K'] * df['NumSites']  # Will be NaN if T0K not available
    
    # Calculate formation energies
    df['FormationEnergy_T300K'] = (
        df['EnergyPerSite_T300K'] - 
        (df['Cu_percent'] / 100.0) * ref_cu - 
        (df['Mg_percent'] / 100.0) * ref_mg
    )
    df['FormationEnergy_T0K'] = (
        df['EnergyPerSite_T0K'] - 
        (df['Cu_percent'] / 100.0) * ref_cu - 
        (df['Mg_percent'] / 100.0) * ref_mg
    )  # Will be NaN if T0K not available
    
    # Convert to meV/site for plotting
    df['FormationEnergy_original_meV'] = df['FormationEnergy_original'] * RY_TO_EV * 1000
    df['FormationEnergy_T0K_meV'] = df['FormationEnergy_T0K'] * RY_TO_EV * 1000
    df['FormationEnergy_T300K_meV'] = df['FormationEnergy_T300K'] * RY_TO_EV * 1000
    
    # Add folder name
    df['Folder'] = folder_name
    
    # Filter out rows without essential data (EnergyPerSite is required)
    df = df[df['EnergyPerSite'].notna()].copy()
    
    # Sort by Cu_percent
    df = df.sort_values('Cu_percent').reset_index(drop=True)
    
    return df


def main():
    # Folders to process
    folders = {
        'fcc': 'fcc',
        'hcp': 'hcp',
        'cu2mg': 'cu2mg',
        'cumg2': 'cumg2'
    }
    
    # Process each folder
    all_data = []
    for folder_name, folder_path in folders.items():
        print(f"Processing {folder_name}...")
        df = process_folder(folder_path, folder_name)
        if df is not None:
            all_data.append(df)
            
            # Save CSV for this folder
            csv_file = f'{folder_name}_formation_energies.csv'
            df.to_csv(csv_file, index=False)
            print(f"  Saved CSV: {csv_file}")
        else:
            print(f"  Skipped {folder_name}")
    
    if not all_data:
        print("No data found in any folder!")
        return
    
    # Combine all dataframes
    df_all = pd.concat(all_data, ignore_index=True)
    
    # Save combined CSV
    df_all.to_csv('all_formation_energies.csv', index=False)
    print(f"\nSaved combined CSV: all_formation_energies.csv")
    
    # Create plot
    fig, ax = plt.subplots(1, 1, figsize=(12, 7))
    
    colors = {'fcc': 'blue', 'hcp': 'red', 'cu2mg': 'green', 'cumg2': 'orange'}
    
    for folder_name in folders.keys():
        df_folder = df_all[df_all['Folder'] == folder_name]
        if len(df_folder) == 0:
            continue
        
        mg_percent = df_folder['Mg_percent'].values
        form_orig = df_folder['FormationEnergy_original_meV'].values
        form_t0 = df_folder['FormationEnergy_T0K_meV'].values
        form_t300 = df_folder['FormationEnergy_T300K_meV'].values
        
        color = colors.get(folder_name, 'black')
        
        # Plot original formation energy (T=0, no phonon)
        ax.plot(mg_percent, form_orig, 'o-', linewidth=1.5, markersize=6,
                color=color, alpha=0.7, label=f'{folder_name} (original)')
        
        # Plot formation energy with phonon correction T=0K
        ax.plot(mg_percent, form_t0, 's--', linewidth=1.5, markersize=6,
                color=color, alpha=0.7, label=f'{folder_name} (T=0K)')
        
        # Plot formation energy with phonon correction T=300K
        ax.plot(mg_percent, form_t300, '^--', linewidth=1.5, markersize=6,
                color=color, alpha=0.7, label=f'{folder_name} (T=300K)')
    
    ax.axhline(0, color='grey', linestyle='-', linewidth=1, alpha=0.5)
    ax.set_xlabel('Mg Percentage (%)', fontsize=12)
    ax.set_ylabel('Formation Energy (meV/site)', fontsize=12)
    ax.set_title('Formation Energy with Phonon Corrections', fontsize=14)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=9, loc='best', ncol=2)
    
    plt.tight_layout()
    
    # Save plot
    output_file = 'formation_energy_with_phonon.png'
    plt.savefig(output_file, dpi=300)
    print(f"\nPlot saved to: {output_file}")
    
    # Show plot
    plt.show()


if __name__ == "__main__":
    main()
