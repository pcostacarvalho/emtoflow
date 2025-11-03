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
- ✅ Support for c/a ratio and volume (SWS) parameter sweeps
- ✅ Equation of state fitting (polynomial, Birch-Murnaghan, Murnaghan)
- ✅ SLURM job script generation (serial and parallel modes)

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

### Generate KSTR input from CIF file

```python
from modules.parse_cif import get_LatticeVectors

# Parse CIF file
lattice_vectors, atomic_positions, a, b, c, atoms = get_LatticeVectors("FePt.cif")

# Use with create_files functions to generate inputs
```

### Complete workflow for geometry optimization

```python
import numpy as np
from modules.create_files import create_inputs, write_serial_sbatch

# Define parameters
params = {
    "path": "./fept_optimization",
    "name_id": "fept",
    "ratios": [0.92, 0.96, 1.00, 1.04],  # c/a ratios to sweep
    "sws": [2.60, 2.65, 2.70],            # Wigner-Seitz radii
    "NL": 2,                               # Orbital layers (auto-detect with bin/skr_input.py)
    "NQ3": 4,                              # Number of atoms
    "B": 1.0,                              # b/a ratio
    "DMAX": 1.3,                           # Maximum distance parameter
    "LAT": 5,                              # Bravais lattice type
    "fractional_coors": np.array([         # Fractional coordinates
        [0.0, 0.5, 0.5],
        [0.5, 0.0, 0.5],
        [0.0, 0.0, 0.0],
        [0.5, 0.5, 0.0]
    ])
}

# Create all input files
create_inputs(params)

# Generate SLURM job script
write_serial_sbatch(
    path="./fept_optimization",
    ratios=params["ratios"],
    volumes=params["sws"],
    job_name="run_fept",
    prcs=4,
    time="02:00:00",
    account="your-account",
    id_name="fept"
)
```

---

## Project Structure

```
EMTO_input_automation/
├── bin/
│   └── skr_input.py          # CLI tool for generating KSTR from CIF
├── modules/
│   ├── __init__.py
│   ├── create_files.py       # Input file generators (KSTR, SHAPE, KGRN, KFCD, jobs)
│   ├── parse_cif.py          # CIF file parsing with pymatgen
│   ├── dmax_optimizer.py     # DMAX parameter optimization
│   └── eos.py                # Equation of state analysis
├── utils/
│   └── file_io.py            # File I/O utilities
├── testing/
│   ├── FePt.cif              # Example CIF file
│   └── code.ipynb            # Usage examples
├── LICENSE                   # MIT License
└── README.md                 # This file
```

---

## Core Modules

### `modules/create_files.py`

Provides functions to generate all EMTO input files:

**Input File Generators:**
- `create_kstr_input()` - KSTR input 
- `create_shape_input()` - SHAPE input 
- `create_kgrn_input()` - KGRN input 
- `create_kfcd_input()` - KFCD input 
- `create_eos_input()` - EOS input file for equation of state fitting

**Job Script Generators:**
- `write_serial_sbatch()` - Serial SLURM job script (sequential execution)
- `write_parallel_sbatch()` - Parallel SLURM job scripts with dependencies

**High-Level Workflow:**
- `create_inputs(params)` - Complete workflow for parameter sweeps

### `modules/parse_cif.py`

Parse crystallographic information from CIF files:

```python
from modules.parse_cif import get_LatticeVectors

matrix, cart_coords, a, b, c, atoms = get_LatticeVectors("structure.cif")
```

**Returns:**
- `matrix`: 3×3 lattice matrix (Å)
- `cart_coords`: Cartesian atomic coordinates (Å)
- `a, b, c`: Lattice parameters (Å)
- `atoms`: List of atom species (pymatgen Species objects)


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
2. **Generate KSTR input** - With initial DMAX guess
3. **Run KSTR** - Generates neighbor information (.prn file)
4. **Optimize DMAX** - Find consistent neighbor shells across c/a ratios
5. **Update KSTR files** - With optimized DMAX
6. **Generate remaining inputs** - SHAPE, KGRN, KFCD
7. **Submit calculations** - Using generated SLURM scripts
8. **Analyze results** - Extract energies and fit EOS

### Automated Parameter Sweep

```python
from modules.create_files import create_inputs, write_serial_sbatch
import numpy as np

# Define sweep parameters
params = {
    "path": "./sweep_output",
    "name_id": "material",
    "ratios": np.linspace(0.90, 1.10, 11),  # 11 c/a ratios
    "sws": np.linspace(2.50, 2.80, 7),      # 7 volumes
    "NL": 2,
    "NQ3": 4,
    "B": 1.0,
    "DMAX": 1.3,
    "LAT": 5,
    "fractional_coors": your_coords
}

# Creates: 11 KSTR, 11 SHAPE, 77 KGRN, 77 KFCD files
create_inputs(params)

# Generate job script
write_serial_sbatch(
    path=params["path"],
    ratios=params["ratios"],
    volumes=params["sws"],
    job_name="run_material",
    id_name=params["name_id"]
)
```

---

## Examples

### Example 1: FePt L10 Structure

See `testing/code.ipynb` for a complete example using the FePt CIF file.

### Example 2: Using the CLI Tool

```bash
# Generate KSTR input from CIF (auto-determines NL)
python bin/skr_input.py output_folder --JobName fept --DMAX 1.3 --LAT 5

# Requires fept.cif in output_folder/
```


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
write_serial_sbatch(
    path="./output",
    ratios=[0.92, 0.96, 1.00],
    volumes=[2.60, 2.65, 2.70],
    job_name="run_serial",
    prcs=4,              # Number of processors
    time="04:00:00",     # Time limit
    account="your-account",
    id_name="fept"
)

# Submit with: sbatch run_serial.sh
```

### Parallel Execution

Creates multiple job scripts with SLURM dependencies for parallel execution:

```python
write_parallel_sbatch(
    path="./output",
    ratios=[0.92, 0.96, 1.00],
    volumes=[2.60, 2.65, 2.70],
    job_name="run_parallel",
    prcs=4,
    time="01:00:00",
    account="your-account",
    id_name="fept"
)

# Submit with: bash submit_run_parallel.sh
```

**Parallel workflow:**
1. **Stage 1:** KSTR + SHAPE (one job per c/a ratio)
2. **Stage 2:** KGRN + KFCD (one job per (c/a, volume) pair, waits for Stage 1)

---

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

### Development Guidelines

1. Follow existing code style
2. Add docstrings to all functions
3. Test with multiple materials/structures
4. Update README with new features

## TODO

### Pending Implementations

- [ ] **Complete the extraction of the structure from CIF for KSTR**
  - Enhance `create_kstr_input_from_cif()` to handle more crystal systems
  - Add validation for lattice parameters
  - Improve error handling for malformed CIF files

- [ ] **Use CIF to create KGRN input file**
  - Implement `create_kgrn_input_from_cif()` wrapper function
  - Auto-extract atom information from CIF
  - Generate KGRN atom section automatically (currently hardcoded)

- [ ] **Consider different concentrations for alloys**
  - Implement `create_kgrn_input_alloy()` for flexible alloy compositions
  - Support concentration sweeps for binary/ternary alloys
  - Add validation for concentration constraints (sum to 1.0 per site)
  - Handle ferromagnetic and antiferromagnetic configurations

- [ ] **Implement DMAX workflow**
  - Create automated workflow: `optimize_dmax_workflow()`
  - Integrate DMAX optimization into main `create_emto_inputs()` function
  - Add option to run KSTR → optimize DMAX → update files → re-run KSTR
  - Document best practices for DMAX optimization parameters

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
