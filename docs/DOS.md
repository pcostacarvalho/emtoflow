# DOS Module

## Overview

The `modules/dos.py` module provides parsing and plotting functionality for Density of States (DOS) data from EMTO output files.

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
- Total DOS (spin up and down)
- Sublattice DOS (IT-resolved)
- ITA DOS (component-resolved with orbital resolution)

### `DOSPlotter`
Creates publication-quality plots:
- Total DOS plots
- Sublattice DOS plots
- ITA DOS plots (with optional orbital resolution)

## Integration

Used by `modules/optimization_workflow.py` for automated DOS analysis in optimization workflows.
