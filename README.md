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
- ✅ **DMAX optimization** - automatic cutoff distance optimization with early subprocess termination (~300x speedup)
- ✅ Equation of state fitting (polynomial, Birch-Murnaghan, Murnaghan)
- ✅ SLURM job script generation (serial and parallel modes)
- ✅ Parse CIF once, use for all input generators (efficient workflow)
- ✅ Complete alloy support with pymatgen-based structure generation
  - CPA random alloys (binary, ternary, higher-order)
  - Ordered intermetallics (L10, L12, B2, Heusler, etc.)
  - All 14 EMTO lattice types
  - Unified workflow with CIF-based calculations

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

### Workflow 1: CIF File (Ordered Structures)

```python
from modules.workflows import create_emto_inputs

# Minimal example - auto-detects LAT, uses structure's c/a and calculated SWS
create_emto_inputs(
    output_path="./fept_calc",
    job_name="fept",
    cif_file="testing/FePt.cif",
    dmax=1.3,
    magnetic='F'
)

# Full control over parameters
create_emto_inputs(
    output_path="./fept_optimization",
    job_name="fept",
    cif_file="testing/FePt.cif",
    dmax=1.3,                              # Maximum distance parameter
    ca_ratios=[0.92, 0.96, 1.00, 1.04],   # c/a ratios to sweep
    sws_values=[2.60, 2.65, 2.70],        # Wigner-Seitz radii
    magnetic='F',                          # Ferromagnetic
    create_job_script=True,                # Generate SLURM script
    job_mode='serial'                      # 'serial' or 'parallel'
)
```

### Workflow 2: Parameter Input (Alloys & Custom Structures)

```python
# FCC Fe-Pt random alloy (CPA)
sites = [{'position': [0, 0, 0],
          'elements': ['Fe', 'Pt'],
          'concentrations': [0.5, 0.5]}]

create_emto_inputs(
    output_path="./fept_alloy",
    job_name="fept",
    lat=2,  # FCC
    a=3.7,  # Lattice parameter (Angstroms)
    sites=sites,
    dmax=1.3,
    sws_values=[2.60, 2.65, 2.70],  # Required for parameter workflow
    magnetic='F'
)

# L10 FePt ordered structure
sites = [
    {'position': [0, 0, 0], 'elements': ['Fe'], 'concentrations': [1.0]},
    {'position': [0.5, 0.5, 0.5], 'elements': ['Pt'], 'concentrations': [1.0]}
]

create_emto_inputs(
    output_path="./fept_l10",
    job_name="fept_l10",
    lat=5,  # Body-centered tetragonal
    a=3.7,
    c=3.7 * 0.96,  # Tetragonal distortion
    sites=sites,
    dmax=1.3,
    ca_ratios=[0.96],
    sws_values=[2.60, 2.65],
    magnetic='F'
)
```

**📖 For lattice type reference (LAT 1-14), see:** [LATTICE_TYPES.md](LATTICE_TYPES.md)

---

### Workflow 3: DMAX Optimization

Automatically find optimal cutoff distances for consistent neighbor shells across c/a ratios:

```python
create_emto_inputs(
    output_path="./fept_optimized",
    job_name="fept",
    cif_file="./FePt.cif",
    ca_ratios=[0.92, 0.96, 1.00, 1.04],
    sws_values=[2.60, 2.65, 2.70],
    magnetic='F',
    optimize_dmax=True,
    dmax_initial=2.5,
    dmax_target_vectors=100,
    kstr_executable="/path/to/kstr.exe"
)
```

The optimizer runs KSTR calculations with early termination (~0.1s per ratio instead of ~30-60s), extracting neighbor data as soon as it's written. Typical speedup: **300-600x**.

**📖 For detailed documentation, see:** [DMAX_OPTIMIZATION.md](DMAX_OPTIMIZATION.md)

---

### Workflow 4: Complete Optimization Workflow (c/a + SWS)

Automated optimization workflow for finding equilibrium structural parameters:

```python
# From YAML configuration file
python bin/run_optimization.py config.yaml

# Or programmatically
from modules.optimization_workflow import OptimizationWorkflow

workflow = OptimizationWorkflow(config_file='optimization_config.yaml')
results = workflow.run_complete_workflow()

# Access optimized parameters
print(f"Optimal c/a: {results['phase2_sws_optimization']['optimal_ca']:.6f}")
print(f"Optimal SWS: {results['phase2_sws_optimization']['optimal_sws']:.6f}")
print(f"Lattice a: {results['phase2_sws_optimization']['derived_parameters']['a_angstrom']:.6f} Å")
```

**The workflow automatically performs:**
1. **Phase 1**: c/a ratio optimization (if enabled)
2. **Phase 2**: SWS (volume) optimization (if enabled)
3. **Phase 3**: Final calculation with optimized parameters
4. **Phase 4**: Results parsing (energies, magnetic moments)
5. **Phase 5**: DOS analysis (if enabled)
6. **Phase 6**: Summary report generation

**Features:**
- Smart parameter auto-generation (single value → range, null → calculate from structure)
- YAML configuration files for reproducibility
- Equation of state fitting with multiple methods (Morse, Birch-Murnaghan, Murnaghan)
- Organized output with JSON results per phase
- Human-readable summary reports
- Optional DOS analysis and plotting

**Configuration template**: `refs/optimization_config_template.yaml`

**📖 For complete documentation, see:** [OPTIMIZATION_WORKFLOW.md](OPTIMIZATION_WORKFLOW.md)

---

**What the workflows do:**
- **CIF workflow:** Auto-detects LAT, extracts atoms and symmetry
- **Parameter workflow:** Creates structure from lattice parameters and site specifications
- **DMAX optimization:** Finds optimal cutoffs with early subprocess termination
- All workflows use unified `create_emto_structure()` function
- Generates all input files: KSTR, SHAPE, KGRN, KFCD
- Creates SLURM job submission scripts

**📖 For alloy workflows and examples, see:** [ALLOY_WORKFLOW_GUIDE.md](ALLOY_WORKFLOW_GUIDE.md)

---

## Project Structure

```
EMTO_input_automation/
├── bin/
│   ├── run_optimization.py   # CLI tool for optimization workflow
│   └── skr_input.py          # CLI tool for generating KSTR from CIF
├── modules/
│   ├── __init__.py
│   ├── workflows.py          # High-level workflow functions (CIF + Parameter)
│   ├── optimization_workflow.py  # Complete c/a + SWS optimization workflow
│   ├── structure_builder.py  # Unified structure creation module
│   ├── lat_detector.py       # Structure analysis & symmetry detection
│   ├── parse_cif.py          # CIF utilities
│   ├── element_database.py   # Default magnetic moments database
│   ├── inputs/
│   │   ├── kstr.py           # KSTR input generator
│   │   ├── shape.py          # SHAPE input generator
│   │   ├── kgrn.py           # KGRN input generator
│   │   ├── kfcd.py           # KFCD input generator
│   │   └── sbatch.py         # SLURM job script generators
│   ├── dmax_optimizer.py     # DMAX parameter optimization
│   ├── dos.py                # DOS parser and plotter
│   └── eos.py                # Equation of state analysis
├── refs/
│   └── optimization_config_template.yaml  # Complete config template
├── tests/
│   ├── test_fast_dmax_extraction.py  # DMAX optimization integration test
│   └── test_prn_monitoring.py        # Unit test for .prn file monitoring
├── testing/
│   ├── FePt.cif              # Example CIF files
│   ├── K6Si2O7.cif
│   └── code.ipynb            # Usage examples
├── DMAX_OPTIMIZATION.md      # DMAX optimization documentation
├── OPTIMIZATION_WORKFLOW.md  # Complete c/a + SWS optimization workflow
├── LATTICE_TYPES.md          # Reference table for LAT parameter (1-14)
├── ALLOY_WORKFLOW_GUIDE.md   # Detailed alloy workflow documentation
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

### `modules/dos.py`

**Available in `test/dmax-optimization` branch**

DOS (Density of States) parser and plotter for EMTO calculations using proper ITA terminology:

```python
from modules.dos import DOSParser, DOSPlotter

# Parse DOS file
parser = DOSParser("fept_0.96_2.86.dos")

# Get total DOS from Total DOS sections
dos_down, dos_up = parser.get_dos('total', spin_polarized=True)

# Get Number of States (NOS)
nos_down, nos_up = parser.get_dos('nos', spin_polarized=True)

# Get sublattice DOS from Total DOS sections
dos_it1_down, dos_it1_up = parser.get_dos('sublattice', sublattice=1, spin_polarized=True)

# Get ITA-specific orbital-resolved DOS
# First ITA on sublattice 1, d-orbital
dos_d_down, dos_d_up = parser.get_ITA_dos(
    sublattice=1, ITA_index=1, orbital='d', spin_polarized=True
)

# Second ITA on same sublattice (e.g., for alloys)
dos_d2_down, dos_d2_up = parser.get_ITA_dos(
    sublattice=1, ITA_index=2, orbital='d', spin_polarized=True
)

# Concentration-weighted sum over all ITAs on a sublattice (for alloys)
# Example: 70% element1 + 30% element2
dos_weighted_down, dos_weighted_up = parser.get_ITA_dos(
    sublattice=1,
    orbital='d',
    sum_ITAs=True,
    concentrations=[0.7, 0.3],
    spin_polarized=True
)

# Verify concentration sum (should equal 1.0)
parser.verify_ITA_sum(sublattice=1, concentrations=[0.7, 0.3])

# List available ITAs
itas = parser.list_ITAs()  # Returns [(1, 'pt', 1), (2, 'fe', 2)]

# Plotting
plotter = DOSPlotter(parser)
plotter.plot_total(spin_polarized=True)
plotter.plot_sublattice(sublattice=1, spin_polarized=True)
plotter.plot_ITA(sublattice=1, ITA_index=1, orbital='d', spin_polarized=True)
```

**Key features:**
- **Unified `get_dos()`**: Access total DOS, NOS, or sublattice DOS from Total DOS sections
- **ITA-specific `get_ITA_dos()`**: Orbital-resolved DOS (s, p, d) with proper ITA handling
- **Multiple ITAs per sublattice**: Handle alloys with different concentration components
- **Concentration weighting**: Compute weighted orbital-resolved sublattice DOS
- **EMTO terminology**: Uses IT (sublattice) and ITA (Inequivalent Type Atom) nomenclature
- **Automatic spin handling**: Returns spin-polarized or summed data
- **Robust parsing**: Handles Fortran overflow markers (****) gracefully

### `modules/dmax_optimizer.py`

**Available in `test/dmax-optimization` branch**

DMAX parameter optimization for consistent neighbor shells:

```python
from modules.dmax_optimizer import find_optimal_dmax, parse_prn_file

# Parse .prn files from KSTR runs
prn_files = {
    0.92: "./fept_calc/smx/fept_0.92.prn",
    0.96: "./fept_calc/smx/fept_0.96.prn",
    1.00: "./fept_calc/smx/fept_1.00.prn",
}

# Find optimal DMAX for each c/a ratio
optimal_dmax = find_optimal_dmax(
    prn_files,
    target_vectors=100,
    vector_tolerance=10
)

# Returns: {0.92: 2.65, 0.96: 2.70, 1.00: 2.75}
```

**Key functions:**
- `parse_prn_file(filepath)` - Extract neighbor shell data from KSTR .prn output
- `find_optimal_dmax(prn_files, target_vectors, tolerance)` - Optimize DMAX values
- `print_optimization_summary(results)` - Display optimization results
- `save_dmax_optimization_log(results, output_file)` - Save detailed log

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

### CIF-based Workflow (Ordered Structures)

1. **Prepare structure** - Start with CIF file
2. **Generate all inputs** - Use `create_emto_inputs()` with CIF file
3. **Submit calculations** - Using generated SLURM scripts
4. **(Optional) Optimize DMAX** - Find consistent neighbor shells across c/a ratios
5. **(Optional) Re-run** - With optimized DMAX
6. **Analyze results** - Extract energies and fit EOS

### Optimization Workflow (c/a + SWS) - ✅ Complete

**Automated multi-phase optimization** (see `OPTIMIZATION_WORKFLOW.md` for details):

1. **Structure input** - CIF file or lattice parameters
2. **Phase 1** - c/a ratio optimization (optional)
3. **Phase 2** - SWS (volume) optimization (optional)
4. **Phase 3** - Optimized structure calculation
5. **Phase 4** - Results parsing and analysis
6. **Phase 5** - DOS analysis (optional)
7. **Phase 6** - Summary report generation

**Key features:**
- YAML configuration files (`refs/optimization_config_template.yaml`)
- Smart parameter auto-generation
- EOS fitting (Morse, Birch-Murnaghan, Murnaghan)
- Organized JSON results per phase
- Command-line tool: `python bin/run_optimization.py config.yaml`

### Alloy Workflow (CPA Disorder) - ✅ Complete

**Pymatgen-based implementation** (see `ALLOY_WORKFLOW_GUIDE.md` and `ALLOY_IMPLEMENTATION_PLAN.md`):

1. **Specify structure** - Provide lattice type, lattice parameters, and site specifications
2. **Build pymatgen Structure** - Create Structure object with partial occupancies
3. **Parse structure** - Use existing `parse_emto_structure()` (unified with CIF workflow)
4. **Generate inputs** - Same input generators as CIF mode (KSTR, SHAPE, KGRN, KFCD)
5. **Run calculations** - SWS optimization for cubic structures (no c/a sweep)
6. **Analyze results** - Extract energies and fit EOS

**Key features:**
- Unified code path for both CIF and alloy modes
- Automatic IT/ITA assignment via symmetry analysis
- Support for multi-sublattice disorder and ordered intermetallics
- All 14 EMTO lattice types supported
- No template files needed

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

### DMAX Optimization Workflow

**Available in `test/dmax-optimization` branch**

The DMAX parameter controls the maximum distance for neighbor shell calculations in KSTR. The optimizer ensures consistent neighbor shells across different c/a ratios, which is critical for accurate geometry optimization.

**Basic usage:**

```python
from modules.workflows import _run_dmax_optimization
from modules.lat_detector import parse_emto_structure

# Parse structure
structure = parse_emto_structure("FePt.cif")

# Run DMAX optimization
optimal_dmax = _run_dmax_optimization(
    output_path="./fept_calc",
    job_name="fept",
    structure=structure,
    ca_ratios=[0.92, 0.96, 1.00, 1.04],
    dmax_initial=1.3,              # Starting guess
    target_vectors=100,             # Target number of k-vectors
    vector_tolerance=10,            # Acceptable deviation (±10 vectors)
    kstr_executable="/path/to/kstr"
)

# Returns: {0.92: 2.65, 0.96: 2.70, 1.00: 2.75, 1.04: 2.80}
```

**Workflow steps:**
1. Creates KSTR inputs with `dmax_initial` for all c/a ratios
2. Runs KSTR executable for each ratio
3. Parses `.prn` files to extract neighbor shell information
4. Optimizes DMAX to achieve target k-vectors within tolerance
5. Saves optimization log with shell consistency analysis

**Output example:**

```
Step 1: Creating initial KSTR inputs (DMAX=1.3)...
✓ Created 4 KSTR input files

Step 2: Running KSTR calculations...
  Running KSTR for c/a = 0.92... ✓
  Running KSTR for c/a = 0.96... ✓
  Running KSTR for c/a = 1.00... ✓
  Running KSTR for c/a = 1.04... ✓

Step 3: Analyzing neighbor shells and optimizing DMAX...
  c/a = 0.92: 98 vectors (within tolerance) → DMAX = 2.65
  c/a = 0.96: 102 vectors (within tolerance) → DMAX = 2.70

✓ Optimization log saved: ./fept_calc/smx/logs/fept_dmax_optimization.log
```

**Note:** See "Performance Optimization: Early KSTR Termination" section below for proposed speed improvements.

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

### ✅ Recently Completed (1/4)

#### 3. ✅ Alloy support (CPA + Ordered Structures) - **COMPLETED**

**Pymatgen-based Implementation:**
The alloy implementation is now complete with full support for:
- ✅ Unified workflow for both CIF and parameter inputs
- ✅ Automatic IT/ITA determination via symmetry analysis
- ✅ All 14 EMTO lattice types (not just FCC/BCC/SC)
- ✅ Native handling of multi-sublattice disorder
- ✅ Support for ordered intermetallics (L10, L12, Heusler, etc.)
- ✅ Binary, ternary, and higher-order alloys
- ✅ Proper CPA with correct ITA and concentration handling
- ✅ Smart defaults for cubic (a=b=c) and HCP (c=1.633*a, γ=120°)
- ✅ Custom magnetic moments per element

**Implementation Status:**
- ✅ Step 1: Modified `lat_detector.py` (backward compatibility)
- ✅ Step 2: Created `structure_builder.py` (unified interface)
- ✅ Step 3: Updated `workflows.py` (integrated structure builder)
- ✅ Step 4: Cleanup (removed 453 lines of obsolete code)
- ✅ Step 5: Documentation (workflow guide and examples)
- ✅ Step 6: Testing (FCC, L10, ternary alloys verified)

**Current Interface:**
```python
# Binary FCC random alloy (single-site disorder)
sites = [{'position': [0,0,0], 'elements': ['Fe','Pt'],
          'concentrations': [0.5, 0.5]}]
create_emto_inputs(
    output_path="./fept_alloy",
    job_name="fept",
    lat=2,  # FCC
    a=3.7,  # lattice parameter in Angstroms
    sites=sites,
    dmax=1.3,
    sws_values=[2.60, 2.65, 2.70],
    magnetic='F'
)

# L10 FePt (ordered, two sublattices)
sites = [
    {'position': [0,0,0], 'elements': ['Fe'], 'concentrations': [1.0]},
    {'position': [0.5,0.5,0.5], 'elements': ['Pt'], 'concentrations': [1.0]}
]
create_emto_inputs(
    output_path="./fept_l10",
    job_name="fept_l10",
    lat=5,  # Body-centered tetragonal
    a=3.7,
    c=3.7*0.96,
    sites=sites,
    dmax=1.3,
    sws_values=[2.65],
    magnetic='F'
)
```

**See:** `ALLOY_WORKFLOW_GUIDE.md` for detailed workflow diagrams and examples.
**See:** `ALLOY_IMPLEMENTATION_PLAN.md` for complete implementation details.

---

### ⚠️ Mostly Complete (1/4)

#### 4. ⚠️ Implement DMAX workflow - **80% COMPLETE**

**Implemented (in `test/dmax-optimization` branch):**
- ✓ `_run_dmax_optimization()` function in `workflows.py`
- ✓ Full automation: KSTR → parse .prn → optimize DMAX → log results
- ✓ Parse KSTR output (.prn files) to analyze neighbor shells
- ✓ Ensure consistency of neighbor shells across c/a ratios
- ✓ Error handling when target vectors not achievable
- ✓ Working example: `test_dmax_optimization.py` with FePt
- ✓ Complete calculation outputs in `fept_calc/`

**Still missing:**
- [ ] Integration into `create_emto_inputs()` main workflow
- [ ] Documentation and usage examples in README
- [ ] Comprehensive test suite
- [ ] **Performance optimization: Early KSTR termination** (see below)

**Note:** The DMAX workflow is functional but runs as a separate function. It requires `kstr_executable` path as input.

---

### Performance Optimization: Early KSTR Termination

**Problem:** DMAX optimization only needs the neighbor shell table for IQ=1 from `.prn` files, which appears in the first few seconds of KSTR execution, but we currently wait for full completion (~2 minutes).

**Proposed Solution:** Monitor `.prn` file and terminate KSTR once IQ=1 section is complete (~95% time savings).

```python
def _run_kstr_for_dmax_early_stop(kstr_executable, input_file, output_dir, timeout=30):
    """
    Run KSTR and terminate once IQ=1 neighbor data is written to .prn file.

    Parameters:
    -----------
    kstr_executable : str
        Path to KSTR executable
    input_file : str
        Path to KSTR input .dat file
    output_dir : str
        Directory where .prn file will be written
    timeout : int
        Max seconds to wait before force-terminating (default: 30)

    Returns:
    --------
    str : Path to the .prn file

    Raises:
    -------
    TimeoutError : If KSTR exceeds timeout
    """
    import subprocess
    import time
    import re
    from pathlib import Path

    base_name = Path(input_file).stem
    prn_file = Path(output_dir) / f"{base_name}.prn"

    # Start KSTR process
    with open(input_file, 'r') as f:
        process = subprocess.Popen(
            [kstr_executable],
            stdin=f,
            cwd=output_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

    # Monitor .prn file incrementally
    start_time = time.time()

    while process.poll() is None:  # While process is running
        # Check timeout (safety mechanism)
        if time.time() - start_time > timeout:
            process.terminate()
            process.wait(timeout=5)
            raise TimeoutError(f"KSTR exceeded {timeout}s timeout")

        # Check if .prn has complete IQ=1 section
        if prn_file.exists():
            try:
                with open(prn_file, 'r') as f:
                    content = f.read()
                    # Found both IQ=1 start AND IQ=2 start (IQ=1 section complete)
                    if 'IQ =  1' in content and re.search(r'IQ\s*=\s*2', content):
                        time.sleep(0.2)  # Allow final writes to complete
                        process.terminate()
                        process.wait(timeout=5)
                        return str(prn_file)
            except (IOError, PermissionError):
                pass  # File might be locked, retry next iteration

        time.sleep(0.1)  # Check every 100ms

    # Process ended naturally (shouldn't happen, but handle gracefully)
    return str(prn_file)
```

**Usage in workflow:**

```python
# Replace current subprocess.run call in _run_dmax_optimization():
# OLD:
result = subprocess.run([kstr_executable], stdin=f, cwd=smx_dir, ...)

# NEW:
try:
    prn_file = _run_kstr_for_dmax_early_stop(
        kstr_executable, input_path, smx_dir, timeout=30
    )
    print("✓ (early stop)")
except TimeoutError:
    print("✗ (timeout)")
```

**Benefits:**
- ~95% time savings (3 seconds vs 120 seconds per KSTR run)
- Safe termination with timeout protection
- No changes to parsing logic
- Particularly valuable when optimizing across many c/a ratios

---

### Overall Progress: 90% Complete

✅ **Objective 1:** CIF-based automation fully implemented
✅ **Objective 2:** Dynamic KGRN generation with symmetry analysis
✅ **Objective 3:** Alloy support (CPA + ordered structures) complete
⚠️ **Objective 4:** DMAX workflow functional, needs integration and optimization

**Key Achievement:** Unified workflow for both CIF and parameter-based structure creation. The system now supports:
- **CIF workflow:** Automatic extraction of structure information from crystallographic files
- **Parameter workflow:** Creation of alloy structures (random CPA, ordered intermetallics)
- **All 14 lattice types:** Not limited to simple cubic lattices
- **No hardcoded values:** All parameters determined automatically or specified by user

**What's New (January 2026):**
- ✅ **Complete optimization workflow** - Automated c/a + SWS optimization with EOS fitting
- ✅ **Refactored structure creation** - Centralized structure creation in workflow initialization, removed 20+ lines of duplicated conditional logic from parameter preparation methods
- ✅ Complete alloy implementation with pymatgen-based structure builder
- ✅ Zero-concentration element support in KGRN inputs
- ✅ 453 lines of obsolete code removed (simplified architecture)
- ✅ Unified code path for all structure types
- ✅ Comprehensive testing and documentation
- ✅ YAML configuration support for workflows

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

**Last Updated:** January 2026
