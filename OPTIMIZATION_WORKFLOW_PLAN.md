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
- **Steps**: 0.02 for c/a, 0.05 for SWS

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
- Multi-composition comparative analysis

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

**Steps**: 0.02 for c/a, 0.05 for SWS, total of 7 points

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

        Steps: 0.02 for c/a, 0.05 for SWS
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
        3. Wait for calculations to complete
        4. Parse energies from KFCD outputs using parse_energies()
        5. Run EOS fit using _run_eos_fit()
        6. Extract optimal c/a from EOS results
        7. Save results and create EOS plot

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
        3. Wait for calculations to complete
        4. Parse energies from KFCD outputs
        5. Run EOS fit
        6. Extract optimal SWS
        7. Calculate derived parameters (a, c, volume) using:
           volume = 4*π*((sws*bohr_to_angstrom)**3)*4/3
           a = (volume/ca)**(1/3)
           c = a*ca
        8. Save results and create EOS plot

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

### New Module: `modules/multi_composition_analysis.py`

For analyzing results across multiple compositions:

```python
class MultiCompositionAnalysis:
    """
    Analyze and compare results across multiple compositions/percentages.
    """

    def __init__(self, compositions, reference_composition=None):
        """
        Parameters:
        -----------
        compositions : list
            List of composition values (e.g., [0.0, 0.1, 0.2, ...])
        reference_composition : float, optional
            Reference composition for percentage calculations
        """
        pass

    def add_results(self, composition, workflow_results):
        """
        Add results from OptimizationWorkflow for a composition.
        """
        pass

    def calculate_percentage_changes(self):
        """
        Calculate percentage changes relative to reference composition.
        """
        pass

    def plot_lattice_parameters(self, output_file='lattice_params.png'):
        """
        Plot a, c, c/a vs composition with percentage changes.
        """
        pass

    def plot_magnetic_moments(self, output_file='magnetic_moments.png'):
        """
        Plot total and element-specific magnetic moments vs composition.
        """
        pass

    def plot_volumes(self, output_file='volumes.png'):
        """
        Plot SWS and volume vs composition with percentage changes.
        """
        pass

    def plot_dos_comparison(self, output_file='dos_comparison.png'):
        """
        Create multi-panel DOS plots for all compositions.
        """
        pass

    def export_csv(self, output_file='results.csv'):
        """
        Export all results to CSV file.
        """
        pass

    def generate_full_report(self, output_dir='analysis_report'):
        """
        Generate complete analysis report with all plots and data.
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
base_path/
├── composition_0.0/
│   ├── ca_optimization/
│   │   ├── smx/              # KSTR files
│   │   ├── shp/              # SHAPE files
│   │   ├── fcd/              # KFCD files
│   │   ├── *.dat             # KGRN files
│   │   ├── eos.dat           # EOS input
│   │   ├── eos.out           # EOS output
│   │   └── ca_eos_plot.png
│   ├── sws_optimization/
│   │   ├── smx/
│   │   ├── shp/
│   │   ├── fcd/
│   │   ├── *.dat
│   │   ├── eos.dat
│   │   ├── eos.out
│   │   └── sws_eos_plot.png
│   ├── optimized/
│   │   ├── smx/
│   │   ├── shp/
│   │   ├── fcd/
│   │   ├── *.dat
│   │   ├── *.dos
│   │   ├── convergence.png
│   │   └── summary.txt
│   └── results_composition_0.0.json
├── composition_0.1/
│   └── ...
├── analysis/
│   ├── lattice_parameters.png
│   ├── magnetic_moments.png
│   ├── volumes.png
│   ├── dos_comparison.png
│   └── all_results.csv
└── workflow_summary.md
```

---

## Workflow Execution Modes

### Mode 1: Full Automated Workflow

```python
from modules.optimization_workflow import OptimizationWorkflow
from modules.multi_composition_analysis import MultiCompositionAnalysis

# Setup
compositions = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]
ca_ratios = np.linspace(0.89, 1.01, 7)
sws_range = np.linspace(2.77, 2.95, 7)
initial_sws = [2.82]

# Configuration
emto_config = {
    'lat': 5,                    # Body-centered tetragonal
    'dmax': 1.52,
    'magnetic': 'P',             # Paramagnetic
    'NL': 3,
    'NQ3': 4,
    'fractional_coords': np.array([...]),
    'sites': [...]
}

# Multi-composition analysis
analysis = MultiCompositionAnalysis(compositions, reference_composition=0.0)

# Run workflow for each composition
for comp in compositions:
    workflow = OptimizationWorkflow(
        base_path=f'composition_{comp:.1f}',
        job_name=f'system_p{comp:.1f}',
        emto_config=emto_config,
        eos_executable='/path/to/eos.exe'
    )

    # Run complete workflow
    results = workflow.run_complete_workflow(ca_ratios, sws_range, initial_sws)

    # Add to analysis
    analysis.add_results(comp, results)

# Generate comparative analysis
analysis.calculate_percentage_changes()
analysis.generate_full_report(output_dir='analysis')
```

### Mode 2: Step-by-Step Workflow

```python
# Run each phase manually with full control
workflow = OptimizationWorkflow(...)

# Phase 1: c/a optimization
optimal_ca, ca_results = workflow.run_ca_optimization(ca_ratios, initial_sws)
print(f"Optimal c/a: {optimal_ca}")

# Phase 2: SWS optimization
optimal_sws, sws_results, derived = workflow.run_sws_optimization(optimal_ca, sws_range)
print(f"Optimal SWS: {optimal_sws}")
print(f"Derived: a={derived['a']:.4f}, c={derived['c']:.4f}, V={derived['vol']:.4f}")

# Phase 3: Optimized calculation
calc_path = workflow.run_optimized_calculation(optimal_ca, optimal_sws)

# Phase 4: Parse results
kgrn, kfcd, report = workflow.parse_results(calc_path)

# Phase 5: DOS analysis
dos_data = workflow.analyze_dos(calc_path, plot=True)

# Phase 6: Generate report
workflow.generate_report(output_file='final_summary.txt')
```

### Mode 3: Resume from Existing Calculations

```python
# Skip calculation steps if output already exists
workflow = OptimizationWorkflow(..., skip_existing=True)

# Will check for existing output and skip if found
results = workflow.run_complete_workflow(ca_ratios, sws_range, initial_sws)
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
- Run multiple compositions in parallel
- Parallel EMTO calculations where possible
- Efficient resource utilization

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

## Implementation Priorities

### Phase A: Core Workflow (High Priority)
1. ✅ `OptimizationWorkflow` class structure
2. ✅ c/a optimization function
3. ✅ SWS optimization function
4. ✅ Integration with EMTO EOS executable
5. ✅ Results parsing integration

### Phase B: Analysis Tools (Medium Priority)
1. `MultiCompositionAnalysis` class
2. Comparative plotting functions
3. CSV export functionality
4. Percentage change calculations

### Phase C: Advanced Features (Low Priority)
1. Parallel execution support
2. Interactive visualizations
3. Web-based dashboard
4. Automatic report generation (LaTeX/Markdown)

### Phase D: Testing and Documentation (Ongoing)
1. Unit tests for each module
2. Integration tests for full workflow
3. Example notebooks
4. User guide documentation

---

## Example Use Cases

### Use Case 1: FePt DLM Study (from notebook)
Study paramagnetic FePt with different percentages:

```python
# Setup for FePt DLM study
compositions = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]
ca_ratios = np.linspace(0.89, 1.01, 7)
sws_range = np.linspace(2.77, 2.95, 7)

emto_config = {
    'lat': 5,  # BCT
    'dmax': 1.52,
    'magnetic': 'P',
    'fractional_coords': np.array([
        [0.0, 0.5, 0.5],
        [0.5, 0.0, 0.5],
        [0.0, 0.0, 0.0],
        [0.5, 0.5, 0.0]
    ])
}

# Run workflow
analysis = run_multi_composition_workflow(
    compositions=compositions,
    ca_ratios=ca_ratios,
    sws_range=sws_range,
    emto_config=emto_config,
    base_path='fept_dlm_study',
    eos_executable='/path/to/eos.exe'
)

# Results automatically saved and plotted
```

### Use Case 2: Single Material Optimization
Quick optimization of a single structure:

```python
workflow = OptimizationWorkflow(
    base_path='my_material',
    job_name='opt',
    emto_config={...},
    eos_executable='/path/to/eos.exe'
)

# Run full workflow
results = workflow.run_complete_workflow(
    ca_ratios=np.linspace(0.90, 1.10, 11),
    sws_range=np.linspace(2.5, 3.0, 11),
    initial_sws=[2.7]
)

# Get optimal parameters
print(f"Optimal c/a: {results['optimal_ca']:.6f}")
print(f"Optimal SWS: {results['optimal_sws']:.6f}")
print(f"Optimal a: {results['a']:.6f} Å")
print(f"Optimal c: {results['c']:.6f} Å")
```

### Use Case 3: Compare EOS Methods
Test different EOS fitting approaches:

```python
# Test multiple EOS methods
for method in ['MO88', 'POLN', 'SPLN', 'ALL']:
    optimal_ca, results = workflow.run_ca_optimization(
        ca_ratios=ca_ratios,
        initial_sws=initial_sws,
        eos_type=method
    )
    print(f"{method}: optimal c/a = {optimal_ca:.6f}")
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

### ❓ To Discuss

1. **Results Storage**: What format for storing intermediate results?
   - Option A: JSON only (human-readable, easy to inspect)
   - Option B: Pickle (Python objects, but not portable)
   - Option C: HDF5 (efficient for large data)
   - Option D: Multiple formats with user choice
   - **Recommendation**: JSON for workflow metadata + CSV for tabular data

2. **Notebook Integration**: Should we provide Jupyter notebook templates?
   - Option A: Yes, provide interactive notebook examples
   - Option B: No, focus on Python scripts
   - Option C: Both
   - **Recommendation**: Start with Python scripts, add notebooks later if needed

3. **Job Monitoring**: How to handle waiting for calculation completion?
   - Option A: Block and wait (simple but ties up process)
   - Option B: Poll with timeout (check every N seconds)
   - Option C: Return immediately and provide status check function
   - **Recommendation**: Poll with timeout + progress reporting

4. **Error Handling**: What if EMTO calculations fail?
   - Option A: Stop entire workflow
   - Option B: Continue with available results
   - Option C: Retry with different parameters
   - **Recommendation**: Stop with informative error message, allow manual retry

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

