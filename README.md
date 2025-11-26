# EMTO Input Automation

Python toolkit for automating the creation of input files for [EMTO](http://emto.gitlab.io/) (Exact Muffin-Tin Orbitals), a computational materials science software for electronic structure calculations.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Core Modules](#core-modules)
- [Workflows](#workflows)
- [Examples](#examples)
- [Equation of State Analysis](#equation-of-state-analysis)
- [Implementation Status](#implementation-status)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

EMTO calculations require multiple input files for different stages of the computation workflow:
- **KSTR**: Slope and Madelung matrices
- **SHAPE**: Atomic sphere radii
- **KGRN**: Self-consistent KKR calculations
- **KFCD**: Full charge density calculations

This toolkit automates the creation of these files from crystallographic information (CIF files) and enables systematic parameter sweeps for geometry optimization and equation of state fitting.

**Key Features:**
- ✅ Automatic input file generation from CIF files
- ✅ Auto-detection of Bravais lattice type (LAT 1-14)
- ✅ Automatic extraction of inequivalent atoms from symmetry analysis
- ✅ Dynamic generation of KGRN atom sections (no hardcoded values)
- ✅ Support for c/a ratio and volume (SWS) parameter sweeps
- ✅ Smart defaults for c/a ratios and SWS values
- ✅ Equation of state fitting (polynomial, Birch-Murnaghan, Murnaghan)
- ✅ SLURM job script generation (serial and parallel modes)
- ✅ Parse CIF once, use for all input generators (efficient workflow)

---

## Installation

### Prerequisites

- Python 3.7+
- [pymatgen](https://pymatgen.org/) for CIF file parsing
- NumPy
- Matplotlib (for EOS analysis)

### Setup

```bash
# Clone the repository
git clone https://github.com/pcostacarvalho/EMTO_input_automation.git
cd EMTO_input_automation

# Install dependencies
pip install pymatgen numpy matplotlib

# Add to your Python path (optional)
export PYTHONPATH="${PYTHONPATH}:/path/to/EMTO_input_automation"
```

---

## Quick Start

### Simple workflow with CIF file

```python
from modules.workflows import create_emto_inputs

# Minimal example - auto-detects LAT, uses structure's c/a and calculated SWS
create_emto_inputs(
    output_path="./fept_calc",
    job_name="fept",
    cif_file="testing/FePt.cif"
)

# Full control over parameters
create_emto_inputs(
    output_path="./fept_optimization",
    job_name="fept",
    cif_file="testing/FePt.cif",
    dmax=1.3,                              # Maximum distance parameter
    ca_ratios=[0.92, 0.96, 1.00, 1.04],   # c/a ratios to sweep
    sws_values=[2.60, 2.65, 2.70],        # Wigner-Seitz radii
    create_job_script=True,                # Generate SLURM script
    job_mode='serial'                      # 'serial' or 'parallel'
)
```

**What it does:**
- Parses CIF file once using `parse_emto_structure()`
- Auto-detects Bravais lattice type (LAT)
- Extracts atoms, symmetry, inequivalent sites
- Determines NL from electronic structure (f→3, d→2, p→1)
- Generates all input files: KSTR, SHAPE, KGRN, KFCD
- Creates SLURM job submission scripts

---

## Project Structure

```
EMTO_input_automation/
├── bin/
│   └── skr_input.py          # CLI tool for generating KSTR from CIF
├── modules/
│   ├── __init__.py
│   ├── workflows.py          # High-level workflow functions
│   ├── lat_detector.py       # CIF parsing & structure extraction
│   ├── parse_cif.py          # CIF utilities
│   ├── inputs/
│   │   ├── kstr.py           # KSTR input generator
│   │   ├── shape.py          # SHAPE input generator
│   │   ├── kgrn.py           # KGRN input generator
│   │   ├── kfcd.py           # KFCD input generator
│   │   └── sbatch.py         # SLURM job script generators
│   ├── dmax_optimizer.py     # DMAX parameter optimization
│   └── eos.py                # Equation of state analysis
├── testing/
│   ├── FePt.cif              # Example CIF files
│   ├── K6Si2O7.cif
│   └── code.ipynb            # Usage examples
├── LICENSE                   # MIT License
└── README.md                 # This file
```

---

## Core Modules

### `modules/workflows.py`

High-level workflow for complete EMTO input generation:

```python
create_emto_inputs(
    output_path,        # Base output directory
    job_name,           # Job identifier (e.g., 'fept')
    cif_file,           # Path to CIF file
    dmax=None,          # Max distance (default: 1.8)
    ca_ratios=None,     # c/a ratios (default: structure's c/a)
    sws_values=None,    # SWS values (default: calculated from volume)
    create_job_script=True,
    job_mode='serial',  # 'serial' or 'parallel'
    prcs=1,
    time="00:30:00",
    account="naiss2025-1-38"
)
```

### `modules/lat_detector.py`

Core CIF parsing and structure extraction:

```python
from modules.lat_detector import parse_emto_structure

# Parse CIF file once
structure = parse_emto_structure("FePt.cif")

# Returns comprehensive structure dictionary:
# - lat: Bravais lattice type (1-14)
# - lattice_name: e.g., "Simple tetragonal"
# - NL: Maximum angular momentum (f→3, d→2, p→1)
# - NQ3: Number of atoms
# - BSX, BSY, BSZ: EMTO primitive vectors
# - atom_info: List of dicts with IQ, IT, ITA, symbol, conc, moment
# - fractional_coords: Fractional coordinates
# - a, b, c, boa, coa: Lattice parameters
```

**Key Features:**
- Auto-detects Bravais lattice type from crystal system and centering
- Extracts inequivalent atoms using symmetry analysis
- Determines IT (inequivalent atom index) automatically
- Includes default magnetic moments database
- Uses **conventional cell** (required by EMTO, not primitive)
- Handles c/a ratio scaling for parameter sweeps

### `modules/inputs/kgrn.py`

KGRN input generator with dynamic atom section:

```python
create_kgrn_input(
    structure,      # Structure dict from parse_emto_structure()
    path,           # Output directory
    id_namev,       # Full file ID (with SWS)
    id_namer,       # Base file ID (without SWS)
    SWS             # Wigner-Seitz radius
)
```

**Atom section is auto-generated from structure:**
```
Symb  IQ  IT ITA SWS  CONC    a_scr b_scr  moment
Fe     1   1   1   1  1.000000  0.000 0.000  2.0000
Pt     2   2   1   1  1.000000  0.000 0.000  0.4000
```

### `modules/eos.py`

Equation of state fitting and analysis:

```python
from modules.eos import compute_equation_of_state, parse_energies

# Parse energies from EMTO output
ratios = [0.92, 0.96, 1.00, 1.04]
sws = [2.65]
energies_lda, energies_gga = parse_energies(ratios, sws, path="./output", id_name="fept")

# Fit equation of state
v_eq, E_eq, coeffs, fit_func = compute_equation_of_state(
    volumes=ratios,
    energies=energies_lda,
    eos_type='polynomial',
    order=3
)

print(f"Equilibrium c/a: {v_eq:.4f}")
print(f"Equilibrium energy: {E_eq:.6f} Ry")
```

**Supported EOS types:**
- `'polynomial'` (order 2 or 3)
- `'birch_murnaghan'`
- `'murnaghan'`
- `'all'` (fits all types and compares)

---

## Workflows

### Typical EMTO Calculation Workflow

1. **Prepare structure** - Start with CIF file
2. **Generate all inputs** - Use `create_emto_inputs()` with CIF file
3. **Submit calculations** - Using generated SLURM scripts
4. **(Optional) Optimize DMAX** - Find consistent neighbor shells across c/a ratios
5. **(Optional) Re-run** - With optimized DMAX
6. **Analyze results** - Extract energies and fit EOS

### Automated Parameter Sweep

```python
from modules.workflows import create_emto_inputs
import numpy as np

# Full parameter sweep
create_emto_inputs(
    output_path="./sweep_output",
    job_name="material",
    cif_file="material.cif",
    dmax=1.3,
    ca_ratios=np.linspace(0.90, 1.10, 11),  # 11 c/a ratios
    sws_values=np.linspace(2.50, 2.80, 7),  # 7 volumes
    create_job_script=True,
    job_mode='parallel'  # Parallel execution for speed
)

# Creates: 11 KSTR, 11 SHAPE, 77 KGRN, 77 KFCD files + job scripts
```

---

## Examples

### Example 1: FePt L10 Structure

Complete automated workflow:

```python
from modules.workflows import create_emto_inputs

create_emto_inputs(
    output_path="./fept_sweep",
    job_name="fept",
    cif_file="testing/FePt.cif",
    dmax=1.3,
    ca_ratios=[0.92, 0.96, 1.00, 1.04],
    sws_values=[2.60, 2.65, 2.70],
    create_job_script=True,
    job_mode='serial'
)
```

**Console output:**
```
Created directory structure in: ./fept_sweep

Parsing CIF file: testing/FePt.cif
  Detected lattice: LAT=5 (Simple tetragonal)
  Number of atoms: NQ3=2
  Maximum NL: 3

Creating input files for 4 c/a ratios and 3 SWS values...

  c/a = 0.92
KSTR input file './fept_sweep/smx/fept_0.92.dat' created successfully.
SHAPE input file './fept_sweep/shp/fept_0.92.dat' created successfully.
KGRN input file './fept_sweep/fept_0.92_2.60.dat' created successfully.
...

======================================================================
WORKFLOW COMPLETE
======================================================================
Files created:
  KSTR:  4 files in ./fept_sweep/smx/
  SHAPE: 4 files in ./fept_sweep/shp/
  KGRN:  12 files in ./fept_sweep/
  KFCD:  12 files in ./fept_sweep/fcd/
======================================================================
```

### Example 2: Using Smart Defaults

```python
# Minimal input - uses structure's c/a ratio and calculated SWS
create_emto_inputs(
    output_path="./quick_test",
    job_name="test",
    cif_file="material.cif"
)

# Auto-generates:
# - c/a ratio = structure's equilibrium c/a from CIF
# - SWS = calculated from atomic volume: (3V/4π)^(1/3)
```

### Example 3: Using the CLI Tool

```bash
# Generate KSTR input from CIF (auto-determines NL, LAT)
python bin/skr_input.py output_folder --JobName fept --DMAX 1.3

# Requires fept.cif in output_folder/
```

---

## Equation of State Analysis

The `eos` module provides tools for fitting equations of state to EMTO energy data:

**Features:**
- Parse energies from KFCD output (.prn files)
- Fit multiple EOS models
- Find equilibrium geometry
- Calculate bulk modulus (for physical EOS models)

**EOS Models:**
- **Polynomial** (2nd or 3rd order) - Simple, but unphysical at extremes
- **Birch-Murnaghan** - Standard for solid-state calculations
- **Murnaghan** - Alternative physical model
- **All** - Fits all models and compares results

---

## SLURM Job Scripts

### Serial Execution

Runs all calculations sequentially in a single job:

```python
from modules.workflows import create_emto_inputs

create_emto_inputs(
    output_path="./output",
    job_name="fept",
    cif_file="FePt.cif",
    ca_ratios=[0.92, 0.96, 1.00],
    sws_values=[2.60, 2.65, 2.70],
    create_job_script=True,
    job_mode='serial',
    prcs=4,              # Number of processors
    time="04:00:00",     # Time limit
    account="your-account"
)

# Submit with: sbatch run_fept.sh
```

### Parallel Execution

Creates multiple job scripts with SLURM dependencies for parallel execution:

```python
create_emto_inputs(
    output_path="./output",
    job_name="fept",
    cif_file="FePt.cif",
    ca_ratios=[0.92, 0.96, 1.00],
    sws_values=[2.60, 2.65, 2.70],
    create_job_script=True,
    job_mode='parallel',
    prcs=4,
    time="01:00:00",
    account="your-account"
)

# Submit with: bash submit_run_fept.sh
```

**Parallel workflow:**
1. **Stage 1:** KSTR + SHAPE (one job per c/a ratio)
2. **Stage 2:** KGRN + KFCD (one job per (c/a, volume) pair, waits for Stage 1)

---

## Implementation Status

### ✅ Completed Objectives (2/4)

#### 1. ✅ Complete CIF extraction for KSTR - **DONE**

**Implemented:**
- ✓ `parse_emto_structure()` function in `lat_detector.py` (lines 349-519)
- ✓ Auto-detection of Bravais lattice type (LAT 1-14)
- ✓ Extraction of NL, NQ3, BSX/BSY/BSZ, fractional coordinates
- ✓ Automatic NL determination from electronic structure (f→3, d→2, p→1)
- ✓ Uses conventional cell (required by EMTO, not primitive)
- ✓ Handles c/a ratio sweeps with proper z-coordinate scaling
- ✓ Integrated into `create_kstr_input()` workflow

**Files:**
- `modules/lat_detector.py`: Core CIF parser
- `modules/inputs/kstr.py`: KSTR generator using structure dict
- `modules/workflows.py`: Workflow integration (parse once, use everywhere)

---

#### 2. ✅ Use CIF to create KGRN input - **DONE**

**Implemented:**
- ✓ Refactored `create_kgrn_input()` to accept structure dict
- ✓ Dynamic atom section generation (no more hardcoded FePt atoms!)
- ✓ Auto-extraction of IQ, IT, ITA, symbols, concentrations
- ✓ Inequivalent atoms determined from symmetry analysis
- ✓ Default magnetic moments database for common elements
- ✓ Integrated into main workflow

**Example atom section generated:**
```
Symb  IQ  IT ITA SWS  CONC    a_scr b_scr  moment
Fe     1   1   1   1  1.000000  0.000 0.000  2.0000
Pt     2   2   1   1  1.000000  0.000 0.000  0.4000
```

**Files:**
- `modules/inputs/kgrn.py`: Refactored generator (lines 30-38 for atom loop)
- `modules/lat_detector.py`: Magnetic moment database (lines 15-78)

---

### ⚠️ Partial Implementation (1/4)

#### 3. ⚠️ Different concentrations for alloys - **ORDERED STRUCTURES ONLY**

**Current Status:**
- ✓ ITA (site type) and CONC (concentration) extracted from CIF
- ✓ Works perfectly for ordered structures (ITA=1, CONC=1.0)
- ❌ Disorder/alloy cases NOT implemented (by design - focus on ordered)
- ❌ Concentration sweeps NOT implemented
- ❌ Magnetic configuration handling (FM/AFM) NOT implemented

**Design Decision:**
The current implementation focuses on ordered structures as requested by the user. Disorder handling (ITA > 1, CONC < 1.0) was intentionally deferred.

**Future Work (if needed):**
- [ ] Implement disorder handling for alloy concentrations
- [ ] Support concentration sweeps for binary/ternary alloys
- [ ] Add validation for concentration constraints (sum to 1.0 per site)
- [ ] Handle ferromagnetic and antiferromagnetic configurations
- [ ] Create `create_kgrn_input_alloy()` wrapper for alloy workflows

---

### ❌ Not Started (1/4)

#### 4. ❌ Implement DMAX workflow - **NOT STARTED**

**What needs to be done:**
- [ ] Create `optimize_dmax_workflow()` function
- [ ] Integrate DMAX optimization into main workflow
- [ ] Add option to run: KSTR → optimize DMAX → update files → re-run KSTR
- [ ] Document best practices for DMAX optimization parameters
- [ ] Parse KSTR output (.prn files) to analyze neighbor shells
- [ ] Ensure consistency of neighbor shells across c/a ratios

**Note:** The `dmax_optimizer.py` module exists but is not integrated into the main workflow.

---

### Overall Progress: 50% Complete

✅ **Objectives 1-2:** CIF-based automation fully implemented
⚠️ **Objective 3:** Ordered structures supported, disorder deferred
❌ **Objective 4:** DMAX workflow automation not started

**Key Achievement:** The system now automatically extracts all structure information from CIF files and generates all input files (KSTR, SHAPE, KGRN, KFCD) with no hardcoded values or manual input required.

---

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

### Development Guidelines

1. Follow existing code style
2. Add docstrings to all functions
3. Test with multiple materials/structures
4. Update README with new features
5. Use `parse_emto_structure()` as single source of truth for structure data

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Citation

If you use this toolkit in your research, please cite:

```
EMTO Input Automation Toolkit
Author: Pamela Costa Carvalho
Year: 2025
URL: https://github.com/pcostacarvalho/EMTO_input_automation
```

---

## Acknowledgments

- [EMTO](http://emto.gitlab.io/) - The Exact Muffin-Tin Orbitals method
- [pymatgen](https://pymatgen.org/) - Materials analysis toolkit

---

## Contact

For questions or support, please open an issue on GitHub.

---

**Last Updated:** November 2025
