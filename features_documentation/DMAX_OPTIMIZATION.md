# DMAX Optimization

## Overview

The `emtoflow.modules.dmax_optimizer` module automatically finds optimal cutoff
distances (DMAX) for each c/a ratio so that all calculations see **comparable
neighbor shells**. It is integrated into
the normal EMTOFlow workflow and is enabled purely via YAML configuration.

You typically turn DMAX optimization on when you:

- Sweep **c/a ratios** and/or **SWS values**, and
- Want a single, consistent neighbor-shell environment across all points.

---

## High-level workflow

When `optimize_dmax: true` is set in your config, EMTOFlow:

1. **Sorts c/a ratios** in descending order (largest first).
2. **Creates KSTR inputs** for all ratios using a single `dmax_initial` guess.
3. **Runs KSTR sequentially** for each ratio, monitoring `.prn` and log files.
4. **Extracts neighbor shell data** from the `.prn` files.
5. **Chooses a reference shell** from the largest c/a ratio (the most demanding case).
6. **Searches DMAX values** for each ratio that reproduce the same reference shell.
7. **Writes a log file** summarizing the optimized DMAX per ratio.
8. **Feeds optimized DMAX values** into the subsequent input generation steps
   (so all later EMTO runs use the optimized DMAXs).

KSTR runs are **early-terminated** as soon as sufficient neighbor data is
written, so you avoid waiting for full KSTR convergence at each trial DMAX.

---

## Minimal YAML configuration

DMAX optimization is controlled entirely in your YAML config. Example:

```yaml
# Basic settings
output_path: "./FePt_dmax_opt"
job_name: "fept_dmax"

# Structure (CIF or parameters)
cif_file: "path/to/FePt.cif"

# Parameter sweeps
ca_ratios: [0.92, 0.96, 1.00, 1.04]
sws_values: [2.60, 2.65, 2.70]

# Magnetic and functional
magnetic: "F"
functional: "GGA"

# Enable DMAX optimization
optimize_dmax: true
dmax_initial: 2.5          # Must be large enough for the LARGEST c/a
dmax_target_vectors: 100   # Target number of neighbor vectors
dmax_vector_tolerance: 15  # Acceptable ± deviation in neighbor count

# EMTO / KSTR executable
kstr_executable: "/path/to/kstr.exe"
```

Once this is set, you run either:

```bash
emtoflow-opt fept_dmax_config.yaml
```

or, from Python:

```python
from emtoflow import OptimizationWorkflow, load_and_validate_config

config = load_and_validate_config("fept_dmax_config.yaml")
workflow = OptimizationWorkflow(config="fept_dmax_config.yaml")
results = workflow.run()
```

No extra Python calls are needed; `run_dmax_optimization()` is invoked
internally by EMTOFlow when `optimize_dmax: true`.

---

## Key parameters

- **`optimize_dmax` (bool)**  
  - Turn DMAX optimization on or off.
  - When `false`, EMTOFlow uses the `dmax` value from your config directly.

- **`dmax_initial` (float)**  
  - Single initial DMAX guess used for all c/a ratios in the first pass.
  - Should be **large enough** for the most distorted / largest c/a ratio.
  - If too small, the optimizer may detect “DMAX too small” and adjust.

- **`dmax_target_vectors` (int)**  
  - Desired number of neighbor vectors (shell count).
  - Typically on the order of 80–150; depends on system and desired accuracy.

- **`dmax_vector_tolerance` (int)**  
  - Acceptable ± deviation from `dmax_target_vectors`.
  - Example: target=100, tolerance=15 ⇒ acceptable range is [85, 115].

- **`kstr_executable` (str)**  
  - Full path to your `kstr.exe` (or equivalent) binary.
  - Required whenever `optimize_dmax: true`.

---

## Outputs

When DMAX optimization is enabled, EMTOFlow writes:

- In `output_path/smx/`:
  - KSTR input and output files for the trial DMAX values.

- In `output_path/smx/logs/`:
  - `{job_name}_{ratio:.2f}.prn` – neighbor shell data extracted from KSTR.
  - `{job_name}_{ratio:.2f}.log` – KSTR log files for each c/a ratio.
  - `{job_name}_dmax_optimization.log` – summary of the DMAX optimization:
    - Target vectors and tolerance
    - Chosen reference shell
    - Final DMAX per c/a ratio

Downstream EMTO input generation (KGRN, KFCD, etc.) then uses these optimized
DMAX values instead of your original `dmax_initial`.

---

## Notes and best practices

- **Sequential, not parallel**  
  - KSTR runs are currently executed **sequentially** over c/a ratios.
  - The speedup comes primarily from **early termination**, not parallelism.

- **Choose a safe `dmax_initial`**  
  - Start with a value that you know is converged (or slightly over-converged)
    for the most extreme c/a ratio.
  - The optimizer will then try to lower it while keeping the neighbor shell
    count within your tolerance.

- **Inspect the log file**  
  - Always skim `{job_name}_dmax_optimization.log` to verify:
    - That a reasonable shell was selected as reference.
    - That all ratios converged to DMAX values within tolerance.

- **When not to use it**  
  - For quick tests or very small systems, a fixed, known-good DMAX may be
    simpler.
  - For production runs and systematic studies, DMAX optimization helps keep
    neighbor shells (and thus k-space sampling) consistent across many
    configurations.

