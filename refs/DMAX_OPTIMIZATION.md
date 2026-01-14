# DMAX Optimization

## Overview

DMAX optimization finds optimal cutoff distances for each c/a ratio to maintain consistent neighbor shell counts across the parameter sweep. This ensures comparable k-point density in electronic structure calculations.

## How It Works

1. Creates KSTR input files with an initial DMAX guess for all c/a ratios
2. Runs KSTR calculations in parallel, extracting neighbor shell data from `.prn` files
3. Identifies a reference shell number from the largest c/a ratio
4. Finds DMAX values that give the same shell number for all ratios
5. Generates final input files with optimized DMAX values

The optimization uses early subprocess termination: KSTR processes are stopped as soon as the required neighbor data is written (~0.1s), rather than waiting for full completion (~30-60s).

## Usage

### Basic Example

```python
from modules.workflows import create_emto_inputs

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

### Parameters

- `optimize_dmax` (bool): Enable DMAX optimization. Default: False
- `dmax_initial` (float): Initial DMAX guess. Should be large enough for the largest c/a ratio. Default: 2.0
- `dmax_target_vectors` (int): Target number of k-vectors. Default: 100
- `dmax_vector_tolerance` (int): Acceptable deviation from target. Default: 15
- `kstr_executable` (str): Path to KSTR executable. Required when `optimize_dmax=True`

### Job Name Constraints

Job names are limited to 10 characters (including ratio suffix) due to Fortran fixed-format requirements:

```python
# Valid
job_name="fe"      # "fe_1.00" = 7 chars ✓
job_name="fept"    # "fept_0.92" = 9 chars ✓

# Invalid
job_name="fept_alloy"  # "fept_alloy_1.00" = 15 chars ✗
```

If a name is too long, the code raises a `ValueError` with a clear message.

## Output

### Files Created

The optimization creates these files in `output_path/smx/logs/`:

- `{job_name}_{ratio:.2f}.prn` - Neighbor shell data
- `{job_name}_{ratio:.2f}.log` - KSTR log files
- `{job_name}_{ratio:.2f}_stdout.log` - Process output
- `{job_name}_{ratio:.2f}_dmax_initial_{value}.dat` - Initial input files
- `{job_name}_dmax_optimization.log` - Optimization summary

### Optimization Log

Example output from `{job_name}_dmax_optimization.log`:

```
======================================================================
DMAX OPTIMIZATION LOG
======================================================================
Job Name: fept
Target Vectors: 100
Number of Ratios: 4

======================================================================
OPTIMIZED DMAX VALUES
======================================================================
Ratio (c/a)     DMAX         Shells     Vectors
----------------------------------------------------------------------
0.92            1.650        18         95
0.96            1.680        18         98
1.00            1.710        18         102
1.04            1.740        18         97
======================================================================

STATISTICS
----------------------------------------------------------------------
DMAX Range: 1.650 - 1.740 (Δ=0.090)
Shell Range: 18 - 18 (Δ=0)
Vector Range: 95 - 102 (Δ=7)
Average Vectors: 98.0

✓ Perfect shell consistency across all ratios
```

## Algorithm Details

### Reference Shell Selection

The algorithm uses the largest c/a ratio as reference:

1. Sort ratios in descending order: `[1.04, 1.00, 0.96, 0.92]`
2. Run KSTR for largest ratio (1.04) with `dmax_initial`
3. Find shell closest to `target_vectors` (e.g., Shell 18 with 95 vectors)
4. Use this shell number for all other ratios

This ensures that if `dmax_initial` is sufficient for the most demanding case (largest c/a), it will work for all smaller ratios.

### Early Termination

The optimization monitors `.prn` files in real-time:

```
Traditional approach: 30-60s per ratio
Optimized approach:   ~0.1s per ratio

Speedup: ~300-600x faster
```

Process flow:
1. Start KSTR subprocess (non-blocking)
2. Poll `.prn` file every 0.1 seconds
3. Detect IQ=1 section completion
4. Terminate subprocess immediately
5. Parse neighbor shell data

## Troubleshooting

### Error: "DMAX too small"

The initial DMAX isn't capturing enough shells. Increase `dmax_initial`:

```python
dmax_initial=2.5  # Try larger value
```

### Error: "Could not find Shell X for all ratios"

The target shell isn't available in all ratios. Either:
- Increase `dmax_initial` to capture more shells
- Adjust `dmax_target_vectors` and `dmax_vector_tolerance`

### Error: "Job name too long"

Shorten the job name:

```python
# Instead of:
job_name="my_system"  # "my_system_1.00" = 13 chars ✗

# Use:
job_name="sys"  # "sys_1.00" = 7 chars ✓
```

## Performance

Typical performance on modern hardware:

| System | Ratios | Old Time | New Time | Speedup |
|--------|--------|----------|----------|---------|
| Cu (FCC) | 3 | ~45s | ~0.4s | 112x |
| Fe-Pt (L10) | 4 | ~120s | ~0.5s | 240x |
| Complex | 6 | ~300s | ~0.8s | 375x |

## Example Scripts

See `tests/test_fast_dmax_extraction.py` for a complete working example.
