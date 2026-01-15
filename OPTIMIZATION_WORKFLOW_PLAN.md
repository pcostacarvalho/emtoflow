# EMTO Optimization Workflow Implementation Plan

## Overview

This document outlines the plan to implement an automated workflow for EMTO calculations that performs:
1. **c/a ratio optimization** - Find equilibrium c/a ratio for any structure with c≠a (not just tetragonal)
2. **SWS (volume) optimization** - Find equilibrium Wigner-Seitz radius
3. **Optimized structure calculation** - Run final calculation with optimized parameters
4. **Results parsing and analysis** - Extract energies, magnetic moments, DOS
5. **Visualization and reporting** - Generate plots and summary reports

The workflow will support running **only c/a optimization**, **only SWS optimization**, or **both in sequence**.

This workflow is based on the notebook `files/codes_for_opt/pm_parse_percentages.ipynb` and will integrate with the existing repo structure.

---

## Key Features

### 1. Flexible Structure Input
- **CIF file**: Auto-detect lattice type and parameters
- **Lattice parameters**: Manually specify lat, a, c, sites (for alloys)

### 2. Smart Parameter Auto-generation
- Single value → auto-generate range (±3×step, 7 points)
- List → use as-is
- None → calculate from structure, then generate range
- **Steps**: 0.02 for c/a, 0.05 for SWS (user-configurable)

### 3. Modular Optimization Workflow
- Run c/a only: `optimize_ca=True, optimize_sws=False`
- Run SWS only: `optimize_ca=False, optimize_sws=True`
- Run both: `optimize_ca=True, optimize_sws=True`

### 4. Automated Execution
- **SLURM**: `run_mode="sbatch"` (submit jobs with sbatch)
- **Local**: `run_mode="local"` (run with ./script.sh)
- Integrated with `utils/running_bash.py`

### 5. Configuration File Support
- YAML or JSON configuration files
- Alternative: Python dict for simple cases
- Example config provided below

### 6. Complete Analysis Pipeline
- EOS fitting with EMTO's Fortran executable
- Results parsing (energies, magnetic moments)
- DOS generation and plotting
- Comprehensive results reporting

---

## Configuration File Example

### YAML Format (Recommended)
```yaml
# Basic settings
base_path: "fept_optimization"
job_name: "fept_p0.0"

# Structure input (choose one approach)
cif_file: "FePt.cif"
# OR for alloys/custom structures:
# lat: 5
# a: 3.86
# c: 3.76
# sites:
#   - position: [0.0, 0.5, 0.5]
#     elements: ["Fe", "Pt"]
#     concentrations: [0.5, 0.5]

# Optimization settings
optimize_ca: true
optimize_sws: true

# Parameter ranges (three options for each):
# Option 1: Single value (auto-generate range)
ca_ratios: 0.95
sws_values: 2.86

# Option 2: List of values (use as-is)
# ca_ratios: [0.89, 0.91, 0.93, 0.95, 0.97, 0.99, 1.01]
# sws_values: [2.77, 2.80, 2.83, 2.86, 2.89, 2.92, 2.95]

# Option 3: Null (calculate from structure)
# ca_ratios: null
# sws_values: null

initial_sws: [2.82]  # For c/a optimization

# Range generation parameters (optional)
ca_step: 0.02        # Step for c/a range generation (default: 0.02)
sws_step: 0.05       # Step for SWS range generation (default: 0.05)
n_points: 7          # Number of points in range (default: 7)

# EMTO parameters
dmax: 1.52
magnetic: "P"  # Paramagnetic
NL: 3
NQ3: 4

# Execution settings
run_mode: "sbatch"  # or "local"
slurm_account: "naiss2025-1-38"
slurm_time: "02:00:00"
slurm_partition: "main"
prcs: 8

# EOS settings
eos_executable: "/home/user/emto/bin/eos.exe"
eos_type: "MO88"  # MO88, POLN, SPLN, ALL

# Analysis settings
generate_plots: true
export_csv: true
```

---

## Input Parameter Handling

### Structure Input (Same as `create_emto_inputs()`)
Users provide either:
- **CIF file**: `cif_file='structure.cif'`
- **Lattice parameters**: `lat=5, a=3.86, sites=[...], c=3.76, ...`

### c/a Ratio and SWS Input (New Smart Behavior)

#### Option 1: User provides lists (explicit sweep)
```python
ca_ratios = [0.89, 0.91, 0.93, 0.95, 0.97, 0.99, 1.01]  # 7 points
sws_values = [2.77, 2.80, 2.83, 2.86, 2.89, 2.92, 2.95]  # 7 points
```

#### Option 2: User provides single value (auto-generate range)
```python
ca_ratios = 0.95       # Experimental value
sws_values = 2.86      # Experimental value
```
→ Workflow will auto-generate:
- `ca_ratios = np.linspace(0.95 - 3*0.02, 0.95 + 3*0.02, 7)` = `[0.89, 0.91, 0.93, 0.95, 0.97, 0.99, 1.01]`
- `sws_values = np.linspace(2.86 - 3*0.05, 2.86 + 3*0.05, 7)` = `[2.71, 2.76, 2.81, 2.86, 2.91, 2.96, 3.01]`

**Steps**: 0.02 for c/a, 0.05 for SWS, total of 7 points (user-configurable via `ca_step`, `sws_step`, `n_points`)

#### Option 3: Not provided (auto-calculate from structure)
```python
ca_ratios = None
sws_values = None
```
→ Workflow will:
- Calculate `ca_ratios` from structure's c/a ratio (if c≠a), otherwise 1.0 for cubic
- Calculate `sws_values` from structure using `lattice_param_to_sws()` function
- Then create ranges around these calculated values (same as Option 2)

### Optimization Modes (Flags)

Users can choose which optimization to run:
```python
optimize_ca = True      # Run c/a ratio optimization
optimize_sws = True     # Run SWS optimization
optimize_both = True    # Run both in sequence (ca → sws)
```

**Examples**:
- `optimize_ca=True, optimize_sws=False` → Only Phase 1 (c/a optimization)
- `optimize_ca=False, optimize_sws=True` → Only Phase 2 (SWS optimization, requires `ca_ratios` input)
- `optimize_ca=True, optimize_sws=True` → Full workflow (Phase 1 → Phase 2)

---

## Current Workflow (from Notebook)

### Phase 1: c/a Ratio Optimization
```python
# For each percentage/composition:
1. Define c/a ratio range (e.g., [0.89, 0.91, 0.93, 0.95, 0.97, 0.99, 1.01])
2. Use initial SWS guess (e.g., [2.82])
3. Create EMTO inputs using create_emto_inputs()
4. Run EMTO calculations (KSTR, SHAPE, KGRN, KFCD)
5. Parse energies from KFCD output files
6. Create EOS input file with Morse fit (MO88)
7. Run EMTO EOS executable
8. Parse EOS output to extract optimal c/a ratio
9. Store results and plot EOS curves
```

### Phase 2: SWS (Volume) Optimization
```python
# Using optimized c/a from Phase 1:
1. Define SWS range (e.g., [2.77, 2.80, 2.83, 2.86, 2.89, 2.92, 2.95])
2. Use optimized c/a ratio from Phase 1
3. Create EMTO inputs for SWS sweep
4. Run EMTO calculations
5. Parse energies from KFCD output
6. Create EOS input and run EOS fit
7. Parse optimal SWS value
8. Calculate derived parameters: a, c, volume
9. Store results and plot EOS curves
```

### Phase 3: Optimized Structure Calculation
```python
# Using optimized c/a and SWS:
1. Create single EMTO input with optimal parameters
2. Run full EMTO calculation (KSTR, SHAPE, KGRN, KFCD, DOS)
3. Wait for convergence
```

### Phase 4: Results Parsing
```python
1. Parse KGRN output (.prn file):
   - Total energy convergence
   - Magnetic moments per iteration
   - Fermi energy

2. Parse KFCD output (.prn file):
   - Final total energy (LDA and GGA)
   - Final magnetic moments per element
   - Weighted magnetic moments

3. Generate text summary report
```

### Phase 5: DOS Analysis
```python
1. Parse DOS files (.dos)
2. Extract:
   - Total DOS (spin up and down)
   - Sublattice DOS for each element
   - Orbital-resolved DOS (s, p, d)
3. Create multi-panel plots:
   - Total DOS
   - Element-specific PDOS
```

### Phase 6: Results Analysis and Visualization
```python
1. Collect results across all compositions/percentages
2. Calculate percentage changes relative to reference
3. Generate comparison plots:
   - Magnetic moments vs composition
   - Lattice parameters (a, c, c/a) vs composition
   - Volume and SWS vs composition
4. Export summary CSV with all results
```

---

## Proposed Implementation Structure

### New Module: `modules/optimization_workflow.py`

Main workflow orchestration module with high-level functions:

```python
class OptimizationWorkflow:
    """
    Manages complete optimization workflow for EMTO calculations.

    Workflow (configurable):
    1. c/a ratio optimization (optional)
    2. SWS optimization (optional)
    3. Optimized structure calculation
    4. Results parsing
    5. DOS analysis
    6. Visualization and reporting
    """

    def __init__(self, config_file=None, config_dict=None, eos_executable=None):
        """
        Parameters:
        -----------
        config_file : str, optional
            Path to YAML/JSON configuration file
        config_dict : dict, optional
            Configuration dictionary (alternative to file)
        eos_executable : str
            Path to EMTO EOS executable (user must provide)

        Configuration file structure (YAML example):
        -------------------------------------------
        base_path: "fept_optimization"
        job_name: "fept"

        # Structure input (choose one)
        cif_file: "FePt.cif"
        # OR
        lat: 5
        a: 3.86
        c: 3.76
        sites: [...]

        # Optimization settings
        optimize_ca: true
        optimize_sws: true
        ca_ratios: 0.95           # Single value or list
        sws_values: 2.86          # Single value or list
        initial_sws: [2.82]       # For c/a optimization

        # EMTO parameters
        dmax: 1.52
        magnetic: "P"
        NL: 3
        NQ3: 4

        # Execution settings
        run_mode: "sbatch"        # "sbatch" or "local"
        slurm_account: "naiss2025-1-38"
        slurm_time: "02:00:00"
        prcs: 8

        # EOS settings
        eos_type: "MO88"          # MO88, POLN, SPLN, ALL
        """
        pass

    def _prepare_ranges(self, ca_ratios, sws_values, structure):
        """
        Auto-generate c/a and SWS ranges if needed.

        Handles three cases:
        1. List provided → use as-is
        2. Single value → create range around it (±3*step, 7 points)
        3. None → calculate from structure, then create range

        Steps: 0.02 for c/a, 0.05 for SWS (defaults, user-configurable)
        """
        pass

    def _run_calculations(self, calculation_path, run_mode="sbatch"):
        """
        Execute EMTO calculations using utils/running_bash.py.

        Parameters:
        -----------
        calculation_path : str
            Directory containing run script
        run_mode : str
            "sbatch" → run with sbatch (SLURM)
            "local" → run locally with ./run_script.sh

        Uses:
        - run_sbatch() from utils/running_bash.py for SLURM
        - chmod_and_run() from utils/running_bash.py for local execution
        """
        pass

    def _run_eos_fit(self, r_or_v_data, energy_data, output_path,
                     job_name, comment, eos_type='MO88'):
        """
        Run EMTO EOS executable and parse results.

        Steps:
        1. Create EOS input file using create_eos_input()
        2. Run EOS executable: subprocess.run(eos_executable + ' < eos.dat')
        3. Parse output using parse_eos_output()
        4. Extract optimal parameter (rwseq)

        Similar to notebook cell that runs:
        result = subprocess.run('/path/to/eos.exe < eos.dat', ...)
        """
        pass

    def run_ca_optimization(self, ca_ratios, initial_sws, eos_type='MO88'):
        """
        Phase 1: Optimize c/a ratio.

        Steps:
        1. Create EMTO inputs for c/a sweep using create_emto_inputs()
        2. Run EMTO calculations:
           - If run_mode='sbatch': use run_sbatch()
           - If run_mode='local': use chmod_and_run()
        3. Wait for calculations to complete (poll with timeout)
        4. Parse energies from KFCD outputs using parse_energies()
        5. Run EOS fit using _run_eos_fit()
        6. Extract optimal c/a from EOS results
        7. Save results:
           - EOS plot (e.g., 'ca_optimization/eos_ca.png')
           - Parsed EOS results with optimal c/a (e.g., 'ca_optimization/eos_ca_results.json')
        8. Return results for use in Phase 2

        Returns:
        --------
        optimal_ca : float
            Optimized c/a ratio
        results : dict
            Full EOS fitting results
        """
        pass

    def run_sws_optimization(self, optimal_ca, sws_range, eos_type='MO88'):
        """
        Phase 2: Optimize SWS (volume).

        Steps:
        1. Create EMTO inputs for SWS sweep at optimal c/a
        2. Run EMTO calculations (sbatch or local)
        3. Wait for calculations to complete (poll with timeout)
        4. Parse energies from KFCD outputs
        5. Run EOS fit
        6. Extract optimal SWS
        7. Calculate derived parameters (a, c, volume) using:
           volume = 4*π*((sws*bohr_to_angstrom)**3)*4/3
           a = (volume/ca)**(1/3)
           c = a*ca
        8. Save results:
           - EOS plot (e.g., 'sws_optimization/eos_sws.png')
           - Parsed EOS results with optimal SWS (e.g., 'sws_optimization/eos_sws_results.json')
           - Derived parameters: a, c, volume (e.g., 'sws_optimization/derived_params.json')
        9. Return results for use in Phase 3

        Returns:
        --------
        optimal_sws : float
            Optimized Wigner-Seitz radius
        derived_params : dict
            a, c, volume, percentage changes
        results : dict
            Full EOS fitting results
        """
        pass

    def run_optimized_calculation(self, optimal_ca, optimal_sws):
        """
        Phase 3: Run calculation with optimized parameters.

        Steps:
        1. Create EMTO input with optimal c/a and SWS
        2. Run full calculation including DOS
        3. Monitor convergence

        Returns:
        --------
        calculation_path : str
            Path to calculation directory
        """
        pass

    def parse_results(self, calculation_path):
        """
        Phase 4: Parse calculation results.

        Steps:
        1. Parse KGRN output (convergence, iterations)
        2. Parse KFCD output (final energies, magnetic moments)
        3. Generate summary report

        Returns:
        --------
        kgrn_results : EMTOResults
        kfcd_results : EMTOResults
        report : str
        """
        pass

    def analyze_dos(self, calculation_path, plot=True):
        """
        Phase 5: Analyze density of states.

        Steps:
        1. Parse DOS file
        2. Extract total and element-specific DOS
        3. Generate plots if requested

        Returns:
        --------
        dos_data : dict
            Parsed DOS data
        """
        pass

    def generate_report(self, output_file='summary.txt'):
        """
        Generate comprehensive summary report.

        Includes:
        - Optimal parameters (c/a, SWS, a, c, volume)
        - Final energies (LDA, GGA)
        - Magnetic moments per element
        - Convergence information
        """
        pass

    def run_complete_workflow(self, ca_ratios, sws_range, initial_sws):
        """
        Execute entire workflow from start to finish.

        Returns:
        --------
        results : dict
            Complete workflow results
        """
        pass
```

### Enhanced Module: `modules/eos.py`

Add integration with EMTO's EOS executable:

```python
def run_emto_eos_fit(data_file, eos_executable, fit_type='MO88',
                     job_name='eos', comment='EOS fit'):
    """
    Create EOS input, run EMTO EOS executable, and parse results.

    Parameters:
    -----------
    data_file : str
        Path where EOS input file will be created
    eos_executable : str
        Path to EMTO EOS executable
    fit_type : str
        EOS fit type (MO88, POLN, SPLN, MU37, ALL)
    job_name : str
        Job name for output files
    comment : str
        Comment for EOS input

    Returns:
    --------
    results : dict
        Parsed EOS results from all fit types
    optimal_value : float
        Optimized parameter (c/a or SWS)
    """
    pass

def compare_eos_methods(r_or_v_data, energy_data, methods=['MO88', 'POLN', 'SPLN']):
    """
    Compare different EOS fitting methods.

    Returns:
    --------
    comparison : dict
        Results from each method
    plot : matplotlib.Figure
        Comparison plot
    """
    pass
```

---

## Integration with Existing Code

### Leverage Existing Modules

1. **`modules/workflows.py`** - Use `create_emto_inputs()` for generating input files
2. **`modules/eos.py`** - Use `parse_energies()` for extracting energies from KFCD
3. **`modules/inputs/eos_emto.py`** - Use `create_eos_input()` and `parse_eos_output()`
4. **`modules/extract_results.py`** - Use `parse_emto_output()` for parsing KGRN/KFCD
5. **`modules/dos.py`** - Use `DOSParser` and `DOSPlotter` for DOS analysis

### New Dependencies

The workflow will need:
- Subprocess management for running EMTO calculations
- File system operations for organizing output directories
- Progress tracking and logging
- Error handling for failed calculations

---

## Directory Structure

Proposed organization for workflow outputs:

```
base_path/                    # User-specified output directory
├── ca_optimization/          # Phase 1: c/a ratio optimization
│   ├── smx/                  # KSTR files (structural data)
│   ├── shp/                  # SHAPE files
│   ├── fcd/                  # KFCD files (energy outputs)
│   ├── *.dat                 # KGRN input files
│   ├── *.prn                 # KGRN/KFCD output files
│   ├── run_*.sh              # Job submission scripts
│   ├── eos.dat               # EOS input file
│   ├── eos.out               # EOS output file
│   ├── eos_ca.png            # EOS plot
│   └── eos_ca_results.json   # Parsed EOS results with optimal c/a
├── sws_optimization/         # Phase 2: SWS optimization
│   ├── smx/
│   ├── shp/
│   ├── fcd/
│   ├── *.dat
│   ├── *.prn
│   ├── run_*.sh
│   ├── eos.dat
│   ├── eos.out
│   ├── eos_sws.png           # EOS plot
│   ├── eos_sws_results.json  # Parsed EOS results with optimal SWS
│   └── derived_params.json   # Derived parameters (a, c, volume)
├── optimized/                # Phase 3: Final calculation with optimal parameters
│   ├── smx/
│   ├── shp/
│   ├── fcd/
│   ├── *.dat
│   ├── *.prn
│   ├── *.dos                 # DOS files
│   ├── run_*.sh
│   ├── convergence.png       # Convergence plot
│   ├── dos_plot.png          # DOS plot
│   └── summary.txt           # Summary report
└── workflow_results.json     # Complete workflow results
```

---

## Key Features to Implement

### 1. **Robust Error Handling**
- Check for failed EMTO calculations
- Validate EOS fitting convergence
- Handle missing output files gracefully
- Provide informative error messages

### 2. **Progress Tracking**
- Visual progress bars for long calculations
- Logging of all steps
- Time estimation
- Checkpoint saving

### 3. **Flexible Configuration**
- YAML or JSON configuration files
- Command-line interface
- Sensible defaults
- Validation of input parameters

### 4. **Parallel Execution**
- Parallel EMTO calculations within phases (future enhancement)
- Efficient resource utilization
- Sequential phase execution (Phase 1 → Phase 2 → Phase 3)

### 5. **Visualization**
- Consistent plot styling
- Automatic figure sizing
- Export to multiple formats (PNG, PDF, SVG)
- Interactive plots (optional)

### 6. **Data Management**
- JSON export of all results
- CSV export for spreadsheet analysis
- HDF5 format for large datasets (optional)
- Metadata tracking

---

## Implementation Tasks

### 1. Update Existing Functions to Support YAML Configuration ✅ COMPLETED
- [x] Update `create_emto_inputs()` to accept configuration from YAML file
- [x] Add YAML/JSON parser utility function
- [x] Add configuration validation
- [x] Support both file and dict input

### 2. Implement Smart Parameter Auto-generation ✅ COMPLETED
- [x] Implement `_prepare_ranges()` method with three modes:
  - Single value → auto-generate range (±3×step, n_points)
  - List → use as-is
  - None → calculate from structure, then generate range
- [x] Make `ca_step`, `sws_step`, `n_points` user-configurable (with defaults)
- [x] Use `lattice_param_to_sws()` for SWS calculation from structure

### 3. Implement Calculation Execution ✅ COMPLETED
- [x] Implement `_run_calculations()` using `utils/running_bash.py`:
  - Support `run_mode="sbatch"` using `run_sbatch()`
  - Support `run_mode="local"` using `chmod_and_run()`
- [x] Implement job monitoring with polling and timeout
- [x] Add progress reporting during calculations

### 4. Implement EOS Integration ✅ COMPLETED
- [x] Implement `_run_eos_fit()` method:
  - Create EOS input using `create_eos_input()`
  - Run EOS executable: `subprocess.run(eos_executable + ' < eos.dat')`
  - Parse results using `parse_eos_output()`
  - Extract optimal parameter (rwseq)
- [x] Add error handling for EOS executable failures

### 5. Implement Phase 1: c/a Optimization ✅ COMPLETED
- [x] Create EMTO inputs for c/a sweep
- [x] Run calculations and wait for completion
- [x] Parse energies from KFCD outputs using parse_kfcd()
- [x] Run EOS fit and extract optimal c/a
- [x] Save results to ca_optimization_results.json with:
  - Optimal c/a ratio
  - Energy vs c/a data
  - EOS fit parameters (rwseq, v_eq, eeq, bulk_modulus)
- [x] Return results for Phase 2

### 6. Implement Phase 2: SWS Optimization ✅ COMPLETED
- [x] Create EMTO inputs for SWS sweep at optimal c/a
- [x] Run calculations and wait for completion
- [x] Parse energies from KFCD outputs using parse_kfcd()
- [x] Run EOS fit and extract optimal SWS
- [x] Calculate derived parameters (a, c, volume) based on lattice type
- [x] Save results to sws_optimization_results.json with:
  - Optimal SWS value
  - Energy vs SWS data
  - EOS fit parameters
  - Derived lattice parameters (a, c, c/a, volume)
- [x] Return results for Phase 3

### 7. Implement Phase 3: Optimized Structure Calculation ✅ COMPLETED
- [x] Create EMTO inputs with optimal c/a and SWS
- [x] Run final calculation
- [x] Parse results from KFCD and KGRN using parse_kfcd() and parse_kgrn()
- [x] Save results to optimized_results.json with:
  - Optimal parameters (c/a, SWS)
  - Final energies (KFCD and KGRN)
  - Magnetic moments
  - File identifier

### 8. Implement Phase 4: Results Parsing
- [ ] Parse KGRN output (convergence, iterations)
- [ ] Parse KFCD output (final energies, magnetic moments)
- [ ] Generate summary report

### 9. Implement Phase 5: DOS Analysis
- [ ] Parse DOS files using existing `DOSParser`
- [ ] Generate DOS plots
- [ ] Save plots and data

### 10. Implement Complete Workflow
- [ ] Implement `run_complete_workflow()` orchestrating all phases
- [ ] Handle optimization mode flags (optimize_ca, optimize_sws)
- [ ] Save workflow-level results summary

### 11. Error Handling and Validation
- [ ] Add configuration validation
- [ ] Handle EMTO calculation failures
- [ ] Provide informative error messages
- [ ] Preserve intermediate results on failure

### 12. Create YAML Configuration Template
- [ ] Create complete template with all possible flags
- [ ] Add comments explaining each parameter
- [ ] Provide examples for different use cases

### 13. Documentation
- [ ] Add docstrings to all functions
- [ ] Create user guide
- [ ] Add example usage scripts
- [ ] Update README with workflow documentation

### 14. Testing
- [ ] Unit tests for parameter auto-generation
- [ ] Integration tests for each phase
- [ ] End-to-end workflow test
- [ ] Test with different structures (cubic, tetragonal, hexagonal)

---

## Complete YAML Configuration Template

Create a file named `optimization_config.yaml` with all possible parameters:

```yaml
# ==============================================================================
# EMTO Optimization Workflow Configuration Template
# ==============================================================================
# This file contains ALL possible configuration options.
# Uncomment and modify as needed for your calculation.

# ------------------------------------------------------------------------------
# Basic Settings (REQUIRED)
# ------------------------------------------------------------------------------
base_path: "my_optimization"           # Output directory
job_name: "material_opt"               # Job identifier

# ------------------------------------------------------------------------------
# Structure Input (REQUIRED - choose ONE approach)
# ------------------------------------------------------------------------------
# Option A: CIF file (recommended for known structures)
cif_file: "structure.cif"

# Option B: Lattice parameters (for alloys or custom structures)
# lat: 5                               # EMTO lattice type (1-14)
# a: 3.86                              # Lattice parameter a (Angstroms)
# b: null                              # Lattice parameter b (default: a)
# c: 3.76                              # Lattice parameter c
# alpha: 90                            # Lattice angle alpha (degrees)
# beta: 90                             # Lattice angle beta (degrees)
# gamma: 90                            # Lattice angle gamma (degrees)
# sites:                               # Atomic sites
#   - position: [0.0, 0.5, 0.5]
#     elements: ["Fe"]
#     concentrations: [1.0]
#   - position: [0.5, 0.0, 0.5]
#     elements: ["Fe"]
#     concentrations: [1.0]
#   - position: [0.0, 0.0, 0.0]
#     elements: ["Pt"]
#     concentrations: [1.0]
#   - position: [0.5, 0.5, 0.0]
#     elements: ["Pt"]
#     concentrations: [1.0]

# ------------------------------------------------------------------------------
# Optimization Settings (REQUIRED)
# ------------------------------------------------------------------------------
optimize_ca: true                      # Run c/a ratio optimization
optimize_sws: true                     # Run SWS optimization

# DMAX optimization settings (optional)
optimize_dmax: false                   # Enable DMAX optimization
dmax_initial: 2.0                      # Initial DMAX guess for optimization
dmax_target_vectors: 100               # Target number of k-vectors
dmax_vector_tolerance: 15              # Acceptable deviation (±N vectors)
kstr_executable: null                  # Path to KSTR executable (required if optimize_dmax=true)
                                       # Example: "/home/user/emto/bin/kstr.exe"

# ------------------------------------------------------------------------------
# Parameter Ranges (choose ONE option for each)
# ------------------------------------------------------------------------------
# Option 1: Single value (auto-generate range around it)
ca_ratios: 0.95                        # Experimental c/a ratio
sws_values: 2.86                       # Experimental SWS

# Option 2: List of values (use as-is)
# ca_ratios: [0.89, 0.91, 0.93, 0.95, 0.97, 0.99, 1.01]
# sws_values: [2.77, 2.80, 2.83, 2.86, 2.89, 2.92, 2.95]

# Option 3: Auto-calculate from structure
# ca_ratios: null
# sws_values: null

# Initial SWS for c/a optimization (required if optimize_ca=true)
initial_sws: [2.82]

# ------------------------------------------------------------------------------
# Range Generation Parameters (OPTIONAL - for auto-generation)
# ------------------------------------------------------------------------------
ca_step: 0.02                          # Step size for c/a range (default: 0.02)
sws_step: 0.05                         # Step size for SWS range (default: 0.05)
n_points: 7                            # Number of points in range (default: 7)

# ------------------------------------------------------------------------------
# EMTO Calculation Parameters (REQUIRED)
# ------------------------------------------------------------------------------
dmax: 1.52                             # Maximum distance parameter
magnetic: "P"                          # Magnetic type: "P" (paramagnetic) or "F" (ferromagnetic)

# Optional EMTO parameters (usually auto-detected from structure)
# NL: 3                                # Maximum angular momentum
# NQ3: 4                               # Number of atoms
# fractional_coords:                   # Fractional coordinates (if not from CIF)
#   - [0.0, 0.5, 0.5]
#   - [0.5, 0.0, 0.5]
#   - [0.0, 0.0, 0.0]
#   - [0.5, 0.5, 0.0]

# Custom magnetic moments (optional)
# user_magnetic_moments:
#   Fe: 2.5
#   Pt: 0.4

# ------------------------------------------------------------------------------
# Execution Settings (REQUIRED)
# ------------------------------------------------------------------------------
run_mode: "sbatch"                     # "sbatch" (SLURM) or "local"

# SLURM settings (required if run_mode="sbatch")
slurm_account: "naiss2025-1-38"        # SLURM account
slurm_time: "02:00:00"                 # Time limit (HH:MM:SS)
slurm_partition: "main"                # SLURM partition
prcs: 8                                # Number of processors

# Job script settings
# job_script_name: "run_calc.sh"       # Name of generated job script
# job_mode: "serial"                   # "serial" or "parallel"

# ------------------------------------------------------------------------------
# EOS Settings (REQUIRED)
# ------------------------------------------------------------------------------
eos_executable: "/home/user/emto/bin/eos.exe"  # Path to EOS executable
eos_type: "MO88"                       # EOS fit type: MO88, POLN, SPLN, MU37, ALL

# ------------------------------------------------------------------------------
# Analysis Settings (OPTIONAL)
# ------------------------------------------------------------------------------
generate_plots: true                   # Generate EOS and DOS plots
export_csv: true                       # Export results to CSV
plot_format: "png"                     # Plot format: png, pdf, svg

# DOS analysis settings
# generate_dos: true                   # Generate DOS files
# dos_plot_range: [-0.8, 0.15]        # Energy range for DOS plots (eV)

# Reference values for percentage calculations (optional)
# reference_ca: null                   # Reference c/a ratio
# reference_sws: null                  # Reference SWS
# reference_volume: null               # Reference volume

# ------------------------------------------------------------------------------
# Advanced Settings (OPTIONAL)
# ------------------------------------------------------------------------------
# skip_existing: false                 # Skip calculations if output exists
# save_intermediate: true              # Save intermediate results
# cleanup_temp: false                  # Remove temporary files after completion
# log_level: "INFO"                    # Logging level: DEBUG, INFO, WARNING, ERROR
# max_iterations: 100                  # Maximum SCF iterations
# convergence_tolerance: 1e-6          # SCF convergence tolerance

# Job monitoring settings
# poll_interval: 30                    # Check job status every N seconds
# max_wait_time: 7200                  # Maximum wait time (seconds)
# timeout_action: "stop"               # Action on timeout: stop, continue, retry
```

Save this template as `optimization_config.yaml` and modify the values as needed for your calculation.

---

## Example Usage

### Single Material Optimization
Complete optimization workflow using YAML configuration file:

```python
from modules.optimization_workflow import OptimizationWorkflow

# Load configuration from YAML file
workflow = OptimizationWorkflow(
    config_file='fept_optimization.yaml',
    eos_executable='/home/user/emto/bin/eos.exe'
)

# Run complete workflow (c/a → SWS → optimized calculation)
results = workflow.run_complete_workflow()

# Results automatically saved to files:
# - ca_optimization/eos_ca.png
# - ca_optimization/eos_ca_results.json (includes optimal c/a)
# - sws_optimization/eos_sws.png
# - sws_optimization/eos_sws_results.json (includes optimal SWS)
# - sws_optimization/derived_params.json (a, c, volume)
# - optimized/summary.txt
# - optimized/convergence.png

# Access results programmatically
print(f"Optimal c/a: {results['optimal_ca']:.6f}")
print(f"Optimal SWS: {results['optimal_sws']:.6f}")
print(f"Optimal a: {results['derived']['a']:.6f} Å")
print(f"Optimal c: {results['derived']['c']:.6f} Å")
print(f"Optimal volume: {results['derived']['volume']:.6f} Å³")
```

### Step-by-Step Execution (Manual Control)

```python
# Initialize workflow
workflow = OptimizationWorkflow(
    config_file='config.yaml',
    eos_executable='/path/to/eos.exe'
)

# Phase 1: c/a optimization only
if workflow.config['optimize_ca']:
    optimal_ca, ca_results = workflow.run_ca_optimization()
    print(f"Phase 1 complete: optimal c/a = {optimal_ca:.6f}")
else:
    optimal_ca = workflow.config['ca_ratios']  # Use provided value

# Phase 2: SWS optimization only
if workflow.config['optimize_sws']:
    optimal_sws, sws_results, derived = workflow.run_sws_optimization(optimal_ca)
    print(f"Phase 2 complete: optimal SWS = {optimal_sws:.6f}")
else:
    optimal_sws = workflow.config['sws_values']  # Use provided value

# Phase 3: Final calculation with optimized parameters
calc_path = workflow.run_optimized_calculation(optimal_ca, optimal_sws)

# Phase 4: Parse and analyze results
kgrn, kfcd, report = workflow.parse_results(calc_path)
dos_data = workflow.analyze_dos(calc_path, plot=True)
workflow.generate_report(output_file='final_summary.txt')
```

---

## Design Decisions

### ✅ Decided

1. **Calculation Management**: ✅ **Full automation with execution mode choice**
   - Workflow will actually run EMTO calculations
   - User chooses execution mode: `run_mode="sbatch"` or `run_mode="local"`
   - Uses utilities from `utils/running_bash.py`

2. **Configuration Format**: ✅ **Configuration file (YAML/JSON preferred) + dict support**
   - Primary: YAML/JSON configuration file (easier for complex workflows)
   - Alternative: Python dict for simple cases
   - Constructor accepts both: `config_file=` or `config_dict=`

3. **EOS Executable**: ✅ **User must provide path**
   - Required parameter: `eos_executable="/path/to/eos.exe"`
   - No auto-detection (simpler, more explicit)
   - Can be reused from notebook approach

4. **c/a Optimization Scope**: ✅ **Any structure with c≠a**
   - Not limited to tetragonal structures
   - Works for any lattice type where c/a ≠ 1

5. **Optimization Modes**: ✅ **Flags to run c/a, SWS, or both**
   - `optimize_ca=True/False` - Run c/a optimization
   - `optimize_sws=True/False` - Run SWS optimization
   - Can run independently or in sequence

6. **Parameter Auto-generation**: ✅ **Smart range generation**
   - Single value → create range (±3*step, 7 points, linspace)
   - Steps: 0.02 for c/a, 0.05 for SWS
   - None → calculate from structure, then create range
   - List → use as-is

7. **Parallel Execution**: ✅ **Optional with sequential phases**
   - Can parallelize within phases (future enhancement)
   - Phases must run in order: Phase 1 → Phase 2 → Phase 3

8. **Plotting**: ✅ **Matplotlib only**
   - Keep it simple with matplotlib
   - No need for interactive plots for now

9. **Results Storage**: ✅ **JSON + CSV**
   - JSON for workflow metadata and structured data
   - CSV for tabular data export
   - Human-readable and easy to inspect

10. **Notebook Integration**: ✅ **Python scripts only (initially)**
    - Focus on Python scripts first
    - Jupyter notebooks can be added later if needed
    - Keeps implementation simpler

11. **Job Monitoring**: ✅ **Poll with timeout + progress reporting**
    - Check job status periodically
    - Display progress to user
    - Timeout after reasonable duration

12. **Error Handling**: ✅ **Stop with informative error message**
    - Stop entire workflow on critical errors
    - Provide clear error messages
    - Allow user to fix issues and retry manually
    - Preserve intermediate results for debugging

---

## Next Steps

1. **Review this plan** - Discuss and refine the proposed structure
2. **Answer discussion questions** - Make decisions on open questions
3. **Prioritize features** - What should be implemented first?
4. **Define API** - Finalize function signatures and interfaces
5. **Create detailed technical spec** - More detailed design for each module
6. **Begin implementation** - Start with core workflow module

---

## Notes

- This workflow builds on the existing `create_emto_inputs()` and related functions
- The notebook workflow uses EMTO's Fortran EOS executable - we should support this but also provide fallback options
- The notebook handles percentage-based composition studies, but the workflow should be general enough for any parametric study
- DOS analysis is already implemented in `modules/dos.py` - we just need to integrate it
- Results parsing is already implemented in `modules/extract_results.py` - integration needed
- Consider backward compatibility with existing workflows

