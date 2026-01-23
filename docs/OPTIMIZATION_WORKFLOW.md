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
- DOS analysis (optional)
- Summary report generation
- Export results to JSON/CSV

## Smart Parameter Generation

The workflow automatically generates parameter ranges:

- **Single value** → Creates range around it (±3×step, 7 points)
- **List** → Uses as-is
- **None** → Calculates from structure, then generates range

Steps: 0.02 for c/a, 0.05 for SWS (user-configurable)

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
