# EMTO Optimization Workflow Implementation Plan

## Overview

This document outlines the plan to implement an automated workflow for EMTO calculations that performs:
1. **c/a ratio optimization** - Find equilibrium tetragonal distortion
2. **SWS (volume) optimization** - Find equilibrium Wigner-Seitz radius
3. **Optimized structure calculation** - Run final calculation with optimized parameters
4. **Results parsing and analysis** - Extract energies, magnetic moments, DOS
5. **Visualization and reporting** - Generate plots and summary reports

This workflow is based on the notebook `files/codes_for_opt/pm_parse_percentages.ipynb` and will integrate with the existing repo structure.

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

    Workflow:
    1. c/a ratio optimization
    2. SWS optimization
    3. Optimized structure calculation
    4. Results parsing
    5. DOS analysis
    6. Visualization and reporting
    """

    def __init__(self, base_path, job_name, emto_config, eos_executable):
        """
        Parameters:
        -----------
        base_path : str
            Base directory for all calculations
        job_name : str
            Job identifier
        emto_config : dict
            Configuration for EMTO (lat, sites, dmax, magnetic, etc.)
        eos_executable : str
            Path to EMTO EOS executable
        """
        pass

    def run_ca_optimization(self, ca_ratios, initial_sws, eos_type='MO88'):
        """
        Phase 1: Optimize c/a ratio.

        Steps:
        1. Create EMTO inputs for c/a sweep
        2. Run calculations (or use existing results)
        3. Parse energies
        4. Fit EOS and find optimal c/a
        5. Save results and plots

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
        2. Run calculations
        3. Parse energies
        4. Fit EOS and find optimal SWS
        5. Calculate derived parameters (a, c, volume)
        6. Save results and plots

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

## Questions for Discussion

1. **Calculation Management**: Should the workflow actually submit/run EMTO calculations, or assume they're already done?
   - Option A: Full automation (submit jobs, wait for completion)
   - Option B: Semi-automated (user runs calculations, workflow does analysis)
   - Option C: Hybrid (detect if calculations exist, run if missing)

2. **Configuration Format**: How should users specify workflow parameters?
   - Option A: Python dictionaries (as shown above)
   - Option B: YAML configuration files
   - Option C: Both (YAML for complex workflows, dict for quick scripts)

3. **EOS Executable**: How to handle EMTO EOS executable path?
   - Option A: Always require user to specify path
   - Option B: Auto-detect from environment variables
   - Option C: Optional - use Python EOS fitting if executable not available

4. **Plotting Backend**: What plotting approach to use?
   - Option A: Matplotlib only (current approach)
   - Option B: Add Plotly for interactive plots
   - Option C: Both (Matplotlib default, Plotly optional)

5. **Parallel Execution**: How to handle parallel calculations?
   - Option A: Built-in using multiprocessing
   - Option B: Integrate with SLURM/job schedulers
   - Option C: Leave to user (provide utilities but don't enforce)

6. **Results Storage**: What format for storing intermediate results?
   - Option A: JSON only (human-readable)
   - Option B: Pickle (Python objects, but not portable)
   - Option C: HDF5 (efficient for large data)
   - Option D: Multiple formats with user choice

7. **Notebook Integration**: Should we provide Jupyter notebook templates?
   - Option A: Yes, provide interactive notebook examples
   - Option B: No, focus on Python scripts
   - Option C: Both

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

