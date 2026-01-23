# DOS Module

## Overview

The `modules/dos.py` module provides parsing and plotting functionality for Density of States (DOS) data from EMTO output files.

## Supported DOS File Formats

The parser supports two DOS file formats:

1. **Spin-polarized (magnetic)**: Contains separate `DOSDOWN` and `DOSUP` sections
   - Header: `"Total DOS and NOS and partial (IT) DOSDOWN"` and `"Total DOS and NOS and partial (IT) DOSUP"`
   - Sublattices: `"Sublattice X Atom YY spin DOWN"` and `"Sublattice X Atom YY spin UP"`

2. **Paramagnetic (non-magnetic)**: Contains combined `DOSUP+DOWN` sections
   - Header: `"Total DOS and NOS and partial (IT) DOSUP+DOWN"`
   - Sublattices: `"Sublattice X Atom YY spin UP+DOWN"`
   - For paramagnetic files, `get_dos()` returns `(dos_data, None)` instead of separate spin channels

The parser automatically detects the file format and handles both cases transparently.

## Key Concepts

- **Energy unit**: Ry. \(E_F\) is plotted as **0** (vertical line)
- **IT (sublattice)**: Pre-weighted DOS columns in the *Total DOS* section (`IT1`, `IT2`, ...). No orbital resolution.
- **ITA**: Repeated "Sublattice X Atom <element>" blocks (CPA components). Has orbital columns (total/s/p/d).

## Quick Usage

```python
from modules.dos import plot_dos

# Total DOS
plot_dos("mycalc.dos", plot_type="total", save="dos_total.png", show=False)

# Sublattice/IT DOS (plots one IT index)
plot_dos("mycalc.dos", plot_type="sublattice", sublattice=1, save="dos_it1.png", show=False)

# ITA DOS (plots one component on a sublattice)
plot_dos("mycalc.dos", plot_type="ITA", sublattice=1, ITA_index=1, save="dos_ita1.png", show=False)

# ITA orbital-resolved (s/p/d curves)
plot_dos("mycalc.dos", plot_type="ITA", sublattice=1, ITA_index=1, orbital_resolved=True,
         save="dos_ita1_spd.png", show=False)
```

Supported `plot_type`: **`total`**, **`sublattice`**, **`ITA`**.

## Programmatic Usage

```python
from modules.dos import DOSParser, DOSPlotter

parser = DOSParser("mycalc.dos")
plotter = DOSPlotter(parser)

# Inspect available ITAs: [(ita_number, element, sublattice), ...]
ITAs = parser.list_ITAs()

# IT (Total-DOS section): total / NOS / sublattice columns
it1_down, it1_up = parser.get_dos("sublattice", sublattice=1, spin_polarized=True)

# ITA blocks (orbital-resolved)
ita_down, ita_up = parser.get_ITA_dos(sublattice=1, ITA_index=1, orbital="d", spin_polarized=True)

# Optional consistency check (CPA weighting)
check = parser.verify_ITA_sum(sublattice=1, concentrations=[0.7, 0.3])
```

## Classes

### `DOSParser`
Parses DOS files and extracts:
- Total DOS (spin up and down for magnetic, combined for paramagnetic)
- Sublattice DOS (IT-resolved)
- ITA DOS (component-resolved with orbital resolution)

**Attributes:**
- `is_paramagnetic`: Boolean flag indicating if the DOS file is paramagnetic (non-magnetic)
- `atom_info`: List of tuples `(atom_number, element, sublattice)` for all ITAs
- `data`: Dictionary containing parsed DOS data

**Methods:**
- `get_dos(data_type, sublattice=None, spin_polarized=True)`: Extract DOS data
  - For paramagnetic files, `dos_up` will be `None` even if `spin_polarized=True`
- `get_ITA_dos(sublattice, ITA_index, orbital, ...)`: Extract ITA-specific DOS
- `list_ITAs()`: Return list of all ITAs in the file
- `verify_ITA_sum(sublattice, concentrations)`: Verify CPA weighting consistency

### `DOSPlotter`
Creates publication-quality plots:
- Total DOS plots (automatically handles paramagnetic vs spin-polarized)
- Sublattice DOS plots
- ITA DOS plots (with optional orbital resolution)

**Plotting behavior:**
- For **spin-polarized** files: Plots spin-up and spin-down separately (up positive, down negative)
- For **paramagnetic** files: Plots single combined DOS curve
- The plotter automatically detects the file type and adjusts the plot style accordingly

## Plot Range Control

Both x-axis (energy) and y-axis (DOS) ranges can be controlled:

```python
from modules.dos import DOSParser, DOSPlotter

parser = DOSParser("dos_file.dos")
plotter = DOSPlotter(parser)

# Plot with custom ranges
fig, ax = plotter.plot_total(
    xlim=(-0.8, 0.15),  # Energy range in Ry
    ylim=(0, 10)        # DOS range in states/Ry (optional)
)
```

**In configuration files:**
```yaml
dos_plot_range: [-0.8, 0.15]  # Energy range (x-axis) in Ry
dos_ylim: [0, 10]              # DOS range (y-axis) in states/Ry (optional, auto-scales if not specified)
```

## Integration

Used by `modules/optimization_workflow.py` for automated DOS analysis in optimization workflows.

## Examples

### Paramagnetic DOS File

```python
from modules.dos import DOSParser, DOSPlotter

# Parse paramagnetic DOS file
parser = DOSParser("paramagnetic_calc.dos")

# Check if file is paramagnetic
if parser.is_paramagnetic:
    print("This is a paramagnetic (non-magnetic) calculation")

# Get total DOS (dos_up will be None for paramagnetic)
dos_down, dos_up = parser.get_dos('total', spin_polarized=True)
# dos_up is None for paramagnetic files

# Plotting automatically handles paramagnetic case
plotter = DOSPlotter(parser)
fig, ax = plotter.plot_total(
    spin_polarized=True,
    xlim=(-0.8, 0.15),  # Energy range
    ylim=(0, 10),       # DOS range (optional)
    save="dos_total.png",
    show=False
)
```

### Spin-Polarized DOS File

```python
from modules.dos import DOSParser, DOSPlotter

# Parse spin-polarized DOS file
parser = DOSParser("magnetic_calc.dos")

# Get total DOS (both spin channels available)
dos_down, dos_up = parser.get_dos('total', spin_polarized=True)
# Both dos_down and dos_up contain data

# Plotting shows separate spin channels
plotter = DOSPlotter(parser)
fig, ax = plotter.plot_total(
    spin_polarized=True,
    xlim=(-0.8, 0.15),  # Energy range
    ylim=(-5, 5),       # DOS range for spin-polarized (optional)
    save="dos_total.png",
    show=False
)
```

## Notes

- The parser automatically detects the DOS file format (paramagnetic vs spin-polarized)
- For paramagnetic files, `get_dos()` and `get_ITA_dos()` return `(dos_data, None)` instead of separate spin channels
- Plotting methods automatically adjust based on available data (no separate spin channels for paramagnetic)
- All methods maintain backward compatibility with existing spin-polarized DOS files
