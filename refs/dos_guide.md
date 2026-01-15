# DOS Plotter Module - Quick Reference

## Overview
Module for parsing and plotting Density of States (DOS) from EMTO output files.

## Installation
Just place `dos_plotter.py` in your working directory or add to your Python path.

## Quick Start

```python
from dos_plotter import plot_dos

# Total DOS (spin polarized)
plot_dos('yourfile.dos', plot_type='total', spin_polarized=True)

# Element DOS (sums all sublattices with same element)
plot_dos('yourfile.dos', plot_type='element', element='fe', spin_polarized=True)

# Specific orbital
plot_dos('yourfile.dos', plot_type='orbital', atom='fe', sublattice=1, orbital='d')
```

## Plot Types

### 1. Total DOS
```python
plot_dos('file.dos', plot_type='total', spin_polarized=True)
```
- Shows total DOS for all atoms
- Columns from file: [E, Total_DOS, NOS, IT1, IT2, ...]

### 2. Partial DOS  
```python
plot_dos('file.dos', plot_type='partial', spin_polarized=True)
```
- Shows IT (inequivalent type) contributions
- Useful to see individual sublattice contributions to total

### 3. Atom DOS (specific sublattice)
```python
plot_dos('file.dos', plot_type='atom', atom='pt', sublattice=1, 
         orbital_resolved=True, spin_polarized=True)
```
- Shows DOS for specific atom on specific sublattice
- `orbital_resolved=True` shows s, p, d separately
- Columns: [E, Total, s, p, d]

### 4. Element DOS (summed over sublattices)
```python
plot_dos('file.dos', plot_type='element', element='fe', 
         orbital_resolved=True, spin_polarized=True)
```
- Sums DOS over all sublattices with the same element
- Useful when you have multiple Fe sites and want total Fe contribution
- `orbital_resolved=True` shows s, p, d separately

### 5. Orbital DOS
```python
plot_dos('file.dos', plot_type='orbital', atom='fe', sublattice=2, 
         orbital='d', spin_polarized=True)
```
- Shows only one specific orbital (s, p, or d)
- For specific sublattice

## Advanced Usage

### Using Classes Directly

```python
from dos_plotter import DOSParser, DOSPlotter

# Parse file
parser = DOSParser('yourfile.dos')

# Check what's available
print(parser.list_atoms())      # ['pt_1', 'fe_2']
print(parser.list_elements())   # ['pt', 'fe']

# Get data arrays
dos_down, dos_up = parser.get_total_dos(spin_polarized=True)
dos_down, dos_up = parser.get_atom_dos('pt', sublattice=1, spin_polarized=True)
dos_down, dos_up = parser.get_element_dos('fe', spin_polarized=True)
dos_down, dos_up = parser.get_orbital_dos('fe', sublattice=2, orbital='d')

# Create plots
plotter = DOSPlotter(parser)
plotter.plot_total(spin_polarized=True, save='total.png')
plotter.plot_element('fe', orbital_resolved=True, save='fe_element.png')
plotter.plot_orbital('pt', 1, 'd', save='pt_d.png')
```

### Data Array Structures

**Total DOS arrays**: `[E, Total_DOS, NOS, IT1, IT2, ...]`
- Column 0: Energy (Ry)
- Column 1: Total DOS
- Column 2: NOS (Number of States, integrated)
- Column 3+: Partial DOS for each IT (sublattice)

**Atom/Element DOS arrays**: `[E, Total, s, p, d]`
- Column 0: Energy (Ry)
- Column 1: Total DOS for this atom
- Column 2: s-orbital DOS
- Column 3: p-orbital DOS
- Column 4: d-orbital DOS

**Orbital DOS arrays**: `[E, orbital_DOS]`
- Column 0: Energy (Ry)
- Column 1: DOS for specified orbital

### Custom Plotting Example

```python
import matplotlib.pyplot as plt
from dos_plotter import DOSParser

parser = DOSParser('yourfile.dos')

fig, ax = plt.subplots()

# Plot multiple elements
for element in parser.list_elements():
    dos_down, dos_up = parser.get_element_dos(element, spin_polarized=True)
    ax.plot(dos_down[:, 0], dos_down[:, 1], label=f'{element} ↓')
    ax.plot(dos_up[:, 0], -dos_up[:, 1], label=f'{element} ↑', linestyle='--')

ax.axvline(0, color='k', linestyle='--', alpha=0.3)
ax.set_xlabel('Energy (Ry)')
ax.set_ylabel('DOS')
ax.legend()
plt.savefig('custom_plot.png')
```

## Key Differences

### Atom vs Element
- **Atom**: Specific sublattice (e.g., `atom='fe', sublattice=2`)
- **Element**: Sum of all sublattices with that element (e.g., `element='fe'`)

If you have:
- Sublattice 1: Fe
- Sublattice 2: Fe  
- Sublattice 3: Ni

Then:
- `get_atom_dos('fe', 1)` → only sublattice 1
- `get_atom_dos('fe', 2)` → only sublattice 2
- `get_element_dos('fe')` → sublattice 1 + sublattice 2

### Spin Polarized vs Non-Spin Polarized
- `spin_polarized=True`: Returns/plots spin-up and spin-down separately
- `spin_polarized=False`: Sums spin channels

## Common Parameters

- `filename`: Path to .dos file
- `spin_polarized`: True = separate spins, False = sum them
- `orbital_resolved`: True = show s,p,d separately, False = just total
- `figsize`: Tuple (width, height) in inches
- `save`: Filename to save (optional)
- `show`: Whether to display plot (default True)

## File Format

The module parses EMTO DOS files with sections:
1. Total DOS DOSDOWN (spin down)
2. Sublattice DOS for each atom (spin down)
3. Total DOS DOSUP (spin up)
4. Sublattice DOS for each atom (spin up)

Each section contains energy and DOS values. The parser automatically detects all atoms and sublattices.