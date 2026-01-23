# EMTO Input Automation

Python toolkit for automating EMTO (Exact Muffin-Tin Orbitals) input file generation and optimization workflows for electronic structure calculations.

---

## Overview

EMTO requires multiple input files (KSTR, SHAPE, KGRN, KFCD) for each calculation. This toolkit:
- Generates all input files from CIF structures or lattice parameters
- Automates c/a ratio and volume (SWS) optimization workflows
- Supports both ordered structures and random alloys (CPA)
- Provides equation of state fitting and analysis
- Generates SLURM job scripts for HPC clusters

---

## Key Features

- ✅ **Automatic input generation** from CIF files or lattice parameters
- ✅ **Complete optimization workflow** - c/a + SWS optimization with EOS fitting
- ✅ **Alloy support** - CPA random alloys (binary/ternary) and ordered intermetallics
- ✅ **All 14 EMTO lattice types** - Auto-detection from CIF or manual specification
- ✅ **DMAX optimization** - Automatic cutoff distance optimization
- ✅ **K-point rescaling** - Maintains constant reciprocal-space density across structures
- ✅ **Smart defaults** - Auto-generates c/a ratios and SWS values from structure
- ✅ **SLURM integration** - Serial and parallel job script generation
- ✅ **YAML configuration** - Reproducible workflows with configuration files

---

## Installation

```bash
# Clone repository
git clone https://github.com/pcostacarvalho/EMTO_input_automation.git
cd EMTO_input_automation

# Install dependencies
pip install pymatgen numpy matplotlib
```

**Requirements:** Python 3.7+, pymatgen, numpy, matplotlib

---

## Quick Start

### Optimization Workflow (Recommended)

The optimization workflow is the main entry point for automated c/a and SWS optimization:

**1. Create configuration file** (copy from template):
```bash
cp refs/optimization_config_template.yaml my_structure.yaml
```

**2. Edit configuration** (minimal example):
```yaml
# Basic settings
output_path: "./Cu2Mg_calc"
job_name: "cu2mg"

# Structure (choose one)
cif_file: "files/systems/Cu2Mg_laves.cif"  # From CIF
# OR
lat: 2                                      # From parameters (2=FCC)
a: 7.2                                      # Lattice parameter (Å)
sites: [{'position': [0,0,0], 'elements': ['Cu','Mg'], 'concentrations': [0.67, 0.33]}]

# EMTO parameters
dmax: 1.8
magnetic: "P"

# K-mesh (optional - rescales automatically based on lattice size)
rescale_k: true

# Optimization flags
optimize_ca: false   # Enable c/a optimization
optimize_sws: false  # Enable SWS optimization
prepare_only: true   # Just create inputs, don't run calculations

# Ranges (auto-generated if single values provided)
ca_ratios: [1.0]
sws_values: [2.6]
```

**3. Run workflow**:
```bash
python bin/run_optimization.py my_structure.yaml
```

**Output structure**:
```
Cu2Mg_calc/
├── cu2mg_structure.json           # Structure information
├── smx/                            # KSTR inputs
├── shp/                            # SHAPE inputs
├── pot/                            # Potential directory
├── chd/                            # Charge density directory
├── fcd/                            # KFCD outputs
├── cu2mg_1.00_2.60.dat            # KGRN input
└── run_cu2mg.sh                   # SLURM job script
```

---

## Configuration Options

### Structure Input (Choose One)

**Option 1: CIF File**
```yaml
cif_file: "path/to/structure.cif"

# Optional: Replace elements with alloys
substitutions:
  Fe:
    elements: ['Fe', 'Co']
    concentrations: [0.7, 0.3]
```

**Option 2: Lattice Parameters**
```yaml
lat: 2              # EMTO lattice type (1-14, see LATTICE_TYPES.md)
a: 3.7              # Lattice parameter a (Å)
b: 3.7              # Lattice parameter b (default: a)
c: 3.7              # Lattice parameter c (default: a for cubic, 1.633*a for HCP)

# Site specifications
sites:
  - position: [0, 0, 0]
    elements: ['Fe', 'Pt']
    concentrations: [0.5, 0.5]
```

### EMTO Calculation Parameters

```yaml
dmax: 1.8                            # Neighbor shell cutoff distance
magnetic: "P"                        # P=Paramagnetic, F=Ferromagnetic, A=Antiferromagnetic
user_magnetic_moments: {'Fe': 2.2}  # Custom magnetic moments (optional)
functional: "GGA"                    # GGA, LDA, or LAG

# K-mesh
nkx: 21                              # K-points along x-axis
nky: 21                              # K-points along y-axis
nkz: 21                              # K-points along z-axis
rescale_k: false                     # Auto-rescale k-points based on lattice size
```

**K-point rescaling** maintains constant reciprocal-space density when lattice parameters change. Uses reference convergence: (3.86 Å, 3.86 Å, 3.76 Å) with k-mesh (21, 21, 21).

### Optimization Settings

```yaml
# Optimization phases
optimize_ca: false                   # Enable c/a ratio optimization (Phase 1)
optimize_sws: false                  # Enable SWS volume optimization (Phase 2)
prepare_only: false                  # Create inputs only, don't run calculations

# Parameter ranges
ca_ratios: [0.96, 1.00, 1.04]       # c/a ratios to test
sws_values: [2.60, 2.65, 2.70]      # SWS values to test

# Auto-generation from single values
auto_generate: true                  # Generate range around single value
ca_step: 0.02                        # c/a step size
sws_step: 0.05                       # SWS step size
n_points: 7                          # Number of points in range

# DMAX optimization
optimize_dmax: false                 # Auto-optimize cutoff distance
dmax_initial: 2.0                    # Starting guess
dmax_target_vectors: 100             # Target k-vectors
dmax_vector_tolerance: 15            # Tolerance (±N vectors)
```

### Execution Settings

```yaml
# Run mode
run_mode: "local"                    # "local" or "sbatch"
prcs: 8                              # Processors per job

# SLURM settings (for run_mode="sbatch")
slurm_account: "your-account"
slurm_partition: "main"
slurm_time: "02:00:00"               # HH:MM:SS

# Job scripts
create_job_script: true              # Generate SLURM scripts
job_mode: "serial"                   # "serial" or "parallel"
```

### Analysis Settings

```yaml
# Equation of state
eos_type: "MO88"                     # MO88, POLN, SPLN, MU37, ALL

# DOS analysis
generate_dos: false                  # Generate DOS files (supports paramagnetic and spin-polarized)
dos_plot_range: [-0.8, 0.15]        # Energy range (Ry)

# Output
generate_plots: true
export_csv: true
plot_format: "png"
```

**Full template**: `refs/optimization_config_template.yaml`

---

## Workflow Phases

The optimization workflow runs in phases:

### Phase 1: c/a Optimization (Optional)
- Sweep c/a ratios at fixed SWS
- Fit equation of state
- Find optimal c/a ratio

### Phase 2: SWS Optimization (Optional)
- Sweep SWS values at optimal c/a
- Fit equation of state
- Find optimal SWS (volume)

### Phase 3: Final Calculation
- Run calculation with optimized parameters
- Parse results (energies, magnetic moments)

### Phase 4-6: Analysis
- DOS analysis (optional) - Supports both paramagnetic and spin-polarized DOS files
- Summary report generation
- Export results to JSON/CSV

**Disable optimizations** for single-point calculations:
```yaml
optimize_ca: false
optimize_sws: false
prepare_only: true
ca_ratios: [1.0]      # Single value
sws_values: [2.65]    # Single value
```

---

## Alloy Workflows

### Random Alloys (CPA)

**Binary FCC alloy:**
```yaml
lat: 2
a: 3.7
sites:
  - position: [0, 0, 0]
    elements: ['Cu', 'Mg']
    concentrations: [0.67, 0.33]
```

**Ternary alloy:**
```yaml
sites:
  - position: [0, 0, 0]
    elements: ['Fe', 'Co', 'Ni']
    concentrations: [0.5, 0.3, 0.2]
```

### Ordered Intermetallics

**L10 FePt:**
```yaml
lat: 5              # Body-centered tetragonal
a: 3.7
c: 3.552           # Tetragonal distortion (c/a = 0.96)
sites:
  - position: [0, 0, 0]
    elements: ['Fe']
    concentrations: [1.0]
  - position: [0.5, 0.5, 0.5]
    elements: ['Pt']
    concentrations: [1.0]
```

**See**: `ALLOY_WORKFLOW_GUIDE.md` for detailed examples

---

## Project Structure

```
EMTO_input_automation/
├── bin/
│   ├── run_optimization.py          # Main CLI tool for optimization workflow
│   └── generate_percentages.py      # Generate YAML files for composition loops
├── modules/
│   ├── optimization_workflow.py     # Main optimization workflow orchestrator
│   ├── optimization/                # Optimization submodules
│   │   ├── execution.py              # Calculation execution
│   │   ├── phase_execution.py       # Phase 1-3 execution
│   │   ├── analysis.py               # EOS fitting, DOS analysis
│   │   └── prepare_only.py          # Input generation only
│   ├── structure_builder.py         # Unified structure creation (CIF/parameters)
│   ├── create_input.py              # EMTO input file generation
│   ├── dmax_optimizer.py            # DMAX cutoff optimization
│   ├── dos.py                       # DOS parsing and plotting
│   ├── extract_results.py           # Results parsing (KGRN/KFCD)
│   ├── alloy_loop.py                # Legacy composition loop (automatic)
│   ├── generate_percentages/        # Composition YAML generation
│   │   ├── generator.py
│   │   ├── composition.py
│   │   └── yaml_writer.py
│   ├── inputs/                      # Input file generators
│   │   ├── kstr.py                  # KSTR (structure)
│   │   ├── kgrn.py                  # KGRN (Green's function)
│   │   ├── shape.py                 # SHAPE (shape functions)
│   │   ├── kfcd.py                  # KFCD (charge density)
│   │   ├── eos_emto.py              # EOS input/output
│   │   └── jobs_tetralith.py        # SLURM script generation
│   ├── lat_detector.py              # Lattice type detection
│   └── element_database.py          # Element properties
├── utils/
│   ├── config_parser.py             # Configuration validation and defaults
│   ├── aux_lists.py                 # K-point rescaling
│   ├── file_io.py                   # File utilities
│   └── running_bash.py               # Job execution (SLURM/local)
├── refs/
│   ├── optimization_config_template.yaml  # Complete config template
│   ├── DEVELOPMENT_GUIDELINES.md          # Development guidelines
│   ├── LATTICE_TYPES.md                    # Lattice type reference
│   └── [module summaries]                  # Brief summaries of each module
├── files/systems/                   # Example configurations
└── code-tests/                     # Test suite
```

---

## Examples

### Example 1: Cu-Mg Laves Phase (Single Point)

```yaml
output_path: "./Cu2Mg_calc"
job_name: "cu2mg"
cif_file: "files/systems/Cu2Mg_laves.cif"
dmax: 1.8
magnetic: "P"
rescale_k: true                      # Auto-rescale k-points
prepare_only: true
ca_ratios: [1.0]
sws_values: [2.6]
```

### Example 2: FePt with c/a Optimization

```yaml
output_path: "./FePt_opt"
job_name: "fept"
cif_file: "testing/FePt.cif"
dmax: 1.3
magnetic: "F"
optimize_ca: true                    # Enable c/a optimization
optimize_sws: true                   # Enable SWS optimization
ca_ratios: [0.96]                    # Auto-generates range around this value
sws_values: [2.65]                   # Auto-generates range around this value
auto_generate: true
```

### Example 3: Fe-Co Random Alloy

```yaml
output_path: "./FeCo_alloy"
job_name: "feco"
lat: 2                               # FCC
a: 3.6
sites:
  - position: [0, 0, 0]
    elements: ['Fe', 'Co']
    concentrations: [0.7, 0.3]
dmax: 1.5
magnetic: "F"
optimize_sws: true
sws_values: [2.6]
```

---

## Documentation

All documentation is in the `refs/` directory:

- **`optimization_config_template.yaml`** - Complete configuration template with all options
- **`DEVELOPMENT_GUIDELINES.md`** - Code development guidelines and best practices
- **`LATTICE_TYPES.md`** - EMTO lattice type reference (LAT 1-14) with primitive vectors
- **`WORKFLOW_DIAGRAMS.md`** - Visual workflow diagrams showing module connections

### Module Summaries

- **`OPTIMIZATION_WORKFLOW.md`** - Optimization workflow module (`modules/optimization_workflow.py`)
- **`STRUCTURE_BUILDER.md`** - Structure builder module (`modules/structure_builder.py`)
- **`INPUT_GENERATION.md`** - Input file generation (`modules/create_input.py`)
- **`DMAX_OPTIMIZATION.md`** - DMAX optimizer module (`modules/dmax_optimizer.py`)
- **`DOS.md`** - DOS module (`modules/dos.py`)
- **`EOS.md`** - EOS module (`modules/inputs/eos_emto.py`)
- **`ALLOY_COMPOSITION_LOOPS.md`** - Alloy composition loops (`modules/alloy_loop.py`, `modules/generate_percentages/`)
- **`GENERATE_PERCENTAGES.md`** - Generate percentages module
- **`CIF_SUBSTITUTIONS.md`** - CIF element substitutions feature
- **`OPTIMIZATION_REFACTORING.md`** - Optimization module refactoring notes

---

## Advanced Features

### DMAX Optimization

Automatically find optimal cutoff distances for consistent neighbor shells:

```yaml
optimize_dmax: true
dmax_initial: 2.5
dmax_target_vectors: 100
dmax_vector_tolerance: 15
kstr_executable: "/path/to/kstr.exe"
```

### Composition Loops

Systematic composition variation for alloys (see template for details):

```yaml
loop_perc:
  enabled: true
  start: 0
  end: 100
  step: 10
  site_index: 0
  element_index: 0
```

### Parallel Execution

Generate SLURM scripts with job dependencies:

```yaml
create_job_script: true
job_mode: "parallel"                 # Creates dependency chain
run_mode: "sbatch"
```

---

## Development

### Development Guidelines

See `refs/DEVELOPMENT_GUIDELINES.md` for:
- Centralized validation and defaults
- Modular code organization
- Template synchronization
- Configuration best practices

### Testing

```bash
# Test k-point rescaling
python tests/test_rescale_k.py

# Test DMAX optimization
python tests/test_fast_dmax_extraction.py
```

---

## Contributing

Contributions welcome! Please:
1. Follow existing code style
2. Add docstrings to functions
3. Update configuration template for new parameters
4. See `DEVELOPMENT_GUIDELINES.md` for detailed guidelines

---

## Citation

```
EMTO Input Automation Toolkit
Author: Pamela Costa Carvalho
Year: 2025
URL: https://github.com/pcostacarvalho/EMTO_input_automation
```

---

## License

MIT License - See [LICENSE](LICENSE) file

---

## Contact

For questions or support, please open an issue on GitHub.

**Last Updated:** January 2026
