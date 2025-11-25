#!/usr/bin/env python3
"""
Test script for the new parse_emto_structure() function
"""

from modules.lat_detector import parse_emto_structure
import json

# Test with FePt CIF file
cif_file = './testing/K6Si2O7.cif'

print("="*70)
print("Testing parse_emto_structure() with FePt.cif")
print("="*70)

# Parse the structure
structure = parse_emto_structure(cif_file)

# Display basic lattice info
print("\n--- LATTICE INFORMATION ---")
print(f"LAT number:      {structure['lat']} ({structure['lattice_name']})")
print(f"Crystal system:  {structure['crystal_system']}")
print(f"Centering:       {structure['centering']}")
print(f"Lattice params:  a={structure['a']:.4f} Å, b={structure['b']:.4f} Å, c={structure['c']:.4f} Å")
print(f"Ratios:          b/a={structure['boa']:.4f}, c/a={structure['coa']:.4f}")
print(f"Angles:          α={structure['alpha']:.2f}°, β={structure['beta']:.2f}°, γ={structure['gamma']:.2f}°")

# Display primitive vectors
print("\n--- PRIMITIVE VECTORS (normalized to a) ---")
print(f"BSX = {structure['BSX']}")
print(f"BSY = {structure['BSY']}")
print(f"BSZ = {structure['BSZ']}")

# Display atomic information
print("\n--- ATOMIC INFORMATION ---")
print(f"Total atoms (NQ3):       {structure['NQ3']}")
print(f"Angular layers (NL):     {structure['NL']}")
print(f"Unique elements:         {structure['unique_elements']}")
print(f"Atoms in unit cell:      {structure['atoms']}")

# Display detailed atom info (KGRN-specific)
print("\n--- ATOM INFO (KGRN-SPECIFIC) ---")
print(f"{'IQ':>3} {'Symbol':<6} {'IT':>3} {'ITA':>4} {'Conc':>6} {'Moment':>8} {'a_scr':>7} {'b_scr':>7}")
print("-" * 60)
for atom in structure['atom_info']:
    print(f"{atom['IQ']:>3} {atom['symbol']:<6} {atom['IT']:>3} {atom['ITA']:>4} "
          f"{atom['conc']:>6.3f} {atom['default_moment']:>8.3f} "
          f"{atom['a_scr']:>7.3f} {atom['b_scr']:>7.3f}")

# Display fractional coordinates
print("\n--- FRACTIONAL COORDINATES ---")
for i, frac in enumerate(structure['fractional_coords']):
    symbol = structure['atoms'][i]
    print(f"{i+1:>3} {symbol:<3} [{frac[0]:8.5f}, {frac[1]:8.5f}, {frac[2]:8.5f}]")

print("\n" + "="*70)
print("Test completed successfully!")
print("="*70)
