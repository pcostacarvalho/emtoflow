# Optimization Workflow Module

## Overview

The `modules/optimization_workflow.py` module provides a complete automated system for EMTO calculations that performs c/a ratio and SWS (volume) optimization with equation of state fitting.

## Main Class

### `OptimizationWorkflow`

Manages complete optimization workflow:

1. **c/a ratio optimization** (optional) - Find equilibrium c/a ratio
2. **SWS optimization** (optional) - Find equilibrium Wigner-Seitz radius
3. **Optimized structure calculation** - Run final calculation with optimized parameters
4. **Results parsing** - Extract energies, magnetic moments
5. **DOS analysis** (optional) - Parse and plot DOS data
6. **Visualization and reporting** - Generate plots and summary reports

## Usage

```python
from modules.optimization_workflow import OptimizationWorkflow
from utils.config_parser import load_and_validate_config

config = load_and_validate_config("config.yaml")
workflow = OptimizationWorkflow(config=config)
results = workflow.run()
```

## Configuration

See `refs/optimization_config_template.yaml` for complete template.

Key settings:
```yaml
optimize_ca: true          # Enable c/a optimization
optimize_sws: true        # Enable SWS optimization
prepare_only: false        # Create inputs only, don't run

ca_ratios: 0.95           # Single value (auto-generates range) or list
sws_values: 2.86         # Single value (auto-generates range) or list
initial_sws: [2.82]      # For c/a optimization

eos_executable: "/path/to/eos.exe"
eos_type: "MO88"          # MO88, POLN, SPLN, MU37, ALL
```

## Workflow Phases

### Phase 1: c/a Optimization
- Sweep c/a ratios at fixed SWS
- Fit equation of state
- Find optimal c/a ratio

### Phase 2: SWS Optimization
- Sweep SWS values at optimal c/a
- Fit equation of state
- Find optimal SWS (volume)
- Calculate derived parameters (a, c, volume)

### Phase 3: Final Calculation
- Run calculation with optimized parameters
- Parse results (energies, magnetic moments)

### Phase 4-6: Analysis
- DOS analysis (optional) - Supports both paramagnetic and spin-polarized DOS files
- Summary report generation
- Export results to JSON/CSV

## Smart Parameter Generation

The workflow automatically generates parameter ranges:

- **Single value** → Creates range around it (±3×step, 7 points)
- **List** → Uses as-is
- **None** → Calculates from structure, then generates range

Steps: 0.02 for c/a, 0.05 for SWS (user-configurable)

## Symmetric EOS Fitting

When you provide many points (e.g., 14) for c/a or SWS optimization, the workflow automatically performs symmetric point selection:

1. **Initial fit**: Fits EOS with all provided points to find equilibrium
2. **Symmetric selection**: Selects 7 points centered around the equilibrium
3. **Final fit**: Performs final fit with selected points (used for optimization)

This ensures the energy curve is symmetric around the equilibrium value, improving fit quality and optimization accuracy.

**Configuration:**
```yaml
symmetric_fit: true          # Enable symmetric fitting (default: true)
n_points_final: 7             # Number of points for final symmetric fit (default: 7)
```

**When to use:**
- Provide many points (e.g., 14) for better initial exploration
- The code automatically selects the best 7 symmetric points for final fit
- Warnings are issued if symmetry is not possible or equilibrium is outside range

## Automatic Range Expansion

When the equilibrium value falls outside the input parameter range, the workflow can automatically expand the range using Modified Morse EOS estimation:

**How it works:**
1. After initial EOS fit, checks if expansion is needed (equilibrium out of range, NaN values, energy monotonic)
2. If needed, fits Modified Morse EOS to current data points to estimate minimum
3. Generates new parameter vector (e.g., 14 points) centered around estimated minimum
4. Runs calculations for new points (only if not already calculated)
5. Re-fits EOS with expanded dataset using symmetric selection
6. If still not converged, suggests `initial_sws` or `ca_ratios` value for manual re-run

**Configuration:**
```yaml
eos_auto_expand_range: false         # Enable automatic expansion (default: false)
# Note: Range width is automatically calculated from number of points and step_size
#   range_width = (n_points - 1) × step_size, centered around estimated minimum
eos_use_saved_data: false            # Use all saved data vs only current workflow (default: false)
```

**Workflow:**
1. Follow user instructions (use initial points)
2. **Always save** current workflow data to file (automatic)
3. Choose data source for EOS fitting:
   - If `eos_use_saved_data: true`: Use ALL points from saved file
   - If `eos_use_saved_data: false`: Use ONLY current workflow's array
4. Verify EOS fit
5. If not adequate:
   - Estimate equilibrium using Morse EOS
   - Generate same number of points as initial around estimate
   - **Always save** expanded workflow points to file
   - Choose data source again (all saved vs workflow only)
   - Verify EOS fit again
   - Only apply symmetric selection if `symmetric_fit: true` is set
6. If fit still not ok:
   - Use all available data to estimate new equilibrium value
   - Print estimated value to user
   - Raise error with suggestion

**Example:**
If initial SWS range is [2.52, 2.82] with 7 points and energy is still decreasing at 2.82:
- Workflow detects expansion needed
- Fits Morse EOS to estimate minimum (e.g., at 2.95)
- Generates new range [2.80, 3.10] centered around 2.95 with 7 points (same as initial)
- **Always saves** expanded workflow points (initial 7 + newly calculated) to file
- Chooses data source for EOS fit:
  - If `eos_use_saved_data: true`: Uses ALL points from saved file (may include previous runs)
  - If `eos_use_saved_data: false`: Uses ONLY workflow points (initial 7 + newly calculated)
- Re-fits EOS with selected data
- If `symmetric_fit: true`, applies symmetric selection; otherwise uses all selected points

**Note**: Currently only Modified Morse EOS is implemented for minimum estimation. Other EOS types need to be implemented for full support.

**Data Persistence:**
Parameter-energy data is **always** saved to JSON files automatically (no option to disable):
- `{phase_path}/sws_energy_data.json` for SWS optimization
- `{phase_path}/ca_energy_data.json` for c/a optimization
- The `eos_use_saved_data` flag controls which data to use for fitting, not whether to save

**Output files:**
- Initial fit: `<job_name>_ca.out` or `<job_name>_sws.out`
- Final fit: `<job_name>_ca_final.out` or `<job_name>_sws_final.out`
- Plots use the final fit results when symmetric selection is enabled

## Output Structure

```
base_path/
├── phase1_ca_optimization/    # Phase 1 outputs
│   ├── eos_ca.png
│   └── eos_ca_results.json
├── phase2_sws_optimization/   # Phase 2 outputs
│   ├── eos_sws.png
│   ├── eos_sws_results.json
│   └── derived_params.json
├── phase3_optimized/           # Phase 3 outputs
│   ├── summary.txt
│   └── convergence.png
└── workflow_results.json       # Complete workflow results
```

## Module Structure

The workflow is split into focused modules:

- `modules/optimization/execution.py`: Calculation execution and validation
- `modules/optimization/phase_execution.py`: Phase 1-3 execution
- `modules/optimization/analysis.py`: EOS fitting, DOS analysis, reporting
- `modules/optimization/prepare_only.py`: Input generation without execution

## Integration

- Uses `structure_builder.py` for structure creation
- Uses `create_input.py` for input file generation
- Uses `modules/inputs/eos_emto.py` for EOS fitting
- Uses `modules/extract_results.py` for results parsing
- Uses `modules/dos.py` for DOS analysis
- Uses `utils/running_bash.py` for job execution

## Features

- **Flexible optimization**: Run c/a only, SWS only, or both
- **Smart defaults**: Auto-generates parameter ranges from single values
- **YAML configuration**: Reproducible workflows
- **SLURM integration**: Automatic job submission
- **Error handling**: Graceful failure handling with intermediate results
- **Progress tracking**: Visual progress reporting
