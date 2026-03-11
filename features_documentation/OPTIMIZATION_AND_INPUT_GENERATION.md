# Optimization Workflow and Input Generation

## Overview

EMTOFlow provides two core building blocks for workflows:

- **`OptimizationWorkflow`** (`from emtoflow import OptimizationWorkflow`)  
  High-level driver: reads a validated config, runs the c/a and SWS optimization
  phases (if enabled), performs the final optimized calculation, and triggers
  analysis (DOS, reports).

- **`create_emto_inputs`** (`from emtoflow import create_emto_inputs`)  
  Lower-level helper: generates EMTO input files (KSTR, SHAPE, KGRN, KFCD, and
  optional job scripts) for a given structure and parameter grid, without
  running the optimization phases.

For end users, the main entry points are:

- **CLI**: `emtoflow-opt config.yaml`
- **Python API**:
  - High-level optimization: `OptimizationWorkflow` + `load_and_validate_config`
  - Input-only generation: `create_emto_inputs`

---

## High-level workflow: `OptimizationWorkflow`

### Main class

```python
from emtoflow import OptimizationWorkflow, load_and_validate_config

config = load_and_validate_config("config.yaml")
workflow = OptimizationWorkflow(config="config.yaml")
results = workflow.run()
```

The workflow performs:

1. **c/a optimization** (optional) – sweep c/a ratios at fixed SWS, fit EOS, find equilibrium c/a.
2. **SWS optimization** (optional) – sweep SWS values at optimal c/a, fit EOS, find equilibrium SWS and derived lattice parameters.
3. **Optimized structure calculation** – run final EMTO calculation at optimized parameters and parse energies/magnetic moments.
4. **Analysis** (optional) – DOS analysis, plots, summary reports, JSON/CSV exports.

Configuration is documented in `docs/optimization_config_template.yaml`. Only
the optimization- and input-related behavior is summarized here.

## Workflow phases and smart parameter generation

`OptimizationWorkflow` automatically builds parameter ranges for `ca_ratios`
and `sws_values` from your config (single values, lists, or `null`) and runs
the phases:

- **Phase 1 – c/a optimization** (if `optimize_ca: true`):
  - Sweep c/a at fixed SWS, fit EOS, find optimal c/a.
- **Phase 2 – SWS optimization** (if `optimize_sws: true`):
  - Sweep SWS at optimal c/a, fit EOS, find optimal SWS and derived `a`, `c`,
    volume.
- **Phase 3 – final calculation**:
  - Run EMTO with optimized parameters, parse energies and magnetic moments.
- **Analysis**:
  - DOS analysis and reporting if enabled in the config.

See `EOS.md` for details of EOS fitting, symmetric selection, and automatic
range expansion.

## Input generation with `create_emto_inputs`

For manual sweeps or external drivers you can use the input generator directly
without running the full optimization workflow:

```python
from emtoflow import create_emto_inputs

create_emto_inputs(
    output_path="./output",
    job_name="fept",
    cif_file="FePt.cif",          # OR use lat, a, sites parameters
    dmax=1.3,
    ca_ratios=[0.96, 1.00, 1.04],
    sws_values=[2.60, 2.65, 2.70],
    magnetic="F"
)
```

This unified function:

- Builds the EMTO structure dictionary (via `emtoflow.modules.structure_builder`).
- Generates all EMTO input files (KSTR, SHAPE, KGRN, KFCD) for each (c/a, SWS)
  combination.
- Respects flags like `optimize_dmax` (DMAX optimization) and
  `create_job_script` (SLURM job scripts).

`create_emto_inputs` is exactly what `OptimizationWorkflow` calls internally in
each phase; use it when you only need the inputs and will control execution
yourself.

The input file types and on-disk layout are:

- **KSTR (structure)** – crystal structure and atomic positions  
  (`emtoflow.modules.inputs.kstr`).
- **SHAPE (shape functions)** – muffin-tin shape data  
  (`emtoflow.modules.inputs.shape`).
- **KGRN (Green's function)** – main EMTO calculation input  
  (`emtoflow.modules.inputs.kgrn`).
- **KFCD (charge density)** – charge-density input, referencing KGRN  
  (`emtoflow.modules.inputs.kfcd`).

Typical directory structure under `output_path`:

```text
output_path/
├── smx/                    # KSTR input files
│   └── jobname_ratio.dat
├── shp/                    # SHAPE input files
│   └── jobname_ratio.dat
├── pot/                    # Potential directory
├── chd/                    # Charge density directory
├── fcd/                    # KFCD input files
│   └── jobname_ratio_sws.dat
├── tmp/                    # Temporary files
├── jobname_ratio_sws.dat   # KGRN input files
└── run_jobname.sh          # SLURM job script (if created)
```
