# DMAX Optimization

## Overview

The `modules/dmax_optimizer.py` module automatically finds optimal cutoff distances (DMAX) for each c/a ratio to maintain consistent neighbor shell counts across parameter sweeps. This ensures comparable k-point density in electronic structure calculations.

## How It Works

1. Creates KSTR input files with initial DMAX guess for all c/a ratios
2. Runs KSTR calculations in parallel, extracting neighbor shell data from `.prn` files
3. Identifies reference shell number from the largest c/a ratio
4. Finds DMAX values that give the same shell number for all ratios
5. Generates final input files with optimized DMAX values

## Key Feature: Early Termination

The optimization uses early subprocess termination: KSTR processes are stopped as soon as the required neighbor data is written (~0.1s), rather than waiting for full completion (~30-60s). This provides a **300-600x speedup**.

## Usage

```python
from modules.create_input import create_emto_inputs

create_emto_inputs(
    output_path="./output",
    job_name="fept",
    cif_file="./FePt.cif",
    ca_ratios=[0.92, 0.96, 1.00, 1.04],
    sws_values=[2.60, 2.65, 2.70],
    magnetic='F',
    optimize_dmax=True,
    dmax_initial=2.5,
    dmax_target_vectors=100,
    dmax_vector_tolerance=15,
    kstr_executable="/path/to/kstr.exe"
)
```

## Parameters

- `optimize_dmax` (bool): Enable DMAX optimization
- `dmax_initial` (float): Initial DMAX guess (should be large enough for largest c/a ratio)
- `dmax_target_vectors` (int): Target number of k-vectors
- `dmax_vector_tolerance` (int): Acceptable deviation from target
- `kstr_executable` (str): Path to KSTR executable (required when optimizing)

## Output

Creates files in `output_path/smx/logs/`:
- `{job_name}_{ratio:.2f}.prn` - Neighbor shell data
- `{job_name}_{ratio:.2f}.log` - KSTR log files
- `{job_name}_dmax_optimization.log` - Optimization summary

## Algorithm

1. Sort ratios in descending order
2. Run KSTR for largest ratio with `dmax_initial`
3. Find shell closest to `target_vectors`
4. Use this shell number for all other ratios
5. Find DMAX values giving consistent shell numbers

## Performance

Typical performance on modern hardware:

| System | Ratios | Old Time | New Time | Speedup |
|--------|--------|----------|----------|---------|
| Cu (FCC) | 3 | ~45s | ~0.4s | 112x |
| Fe-Pt (L10) | 4 | ~120s | ~0.5s | 240x |
| Complex | 6 | ~300s | ~0.8s | 375x |

## Implementation

- `parse_prn_file()`: Extracts neighbor shell data from `.prn` files
- `optimize_dmax()`: Main optimization function
- Early termination via subprocess monitoring
- Parallel execution for multiple ratios
