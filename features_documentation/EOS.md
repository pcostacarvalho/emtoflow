# EOS Module

## Overview

The `emtoflow.modules.inputs.eos_emto` module provides functionality for creating
equation of state (EOS) input files for EMTO's EOS executable, running fits, and
parsing the resulting output. It supports multiple EOS fitting methods and is
integrated into the optimization workflow for finding optimal c/a ratios and
SWS (or volume) values, including optional **automatic range expansion** when
the equilibrium lies outside the initial scan.

## Key Features

- **EOS input file generation**: Creates formatted input files for EMTO's EOS executable
- **Multiple fitting methods**: Supports Modified Morse, Murnaghan, Polynomial, Cubic Spline, and Birch-Murnaghan EOS
- **Output parsing**: Extracts fitted parameters from EOS output files
- **Data structures**: Provides dataclasses for EOS parameters and data points
- **Integration**: Used by optimization workflow for c/a and SWS optimization

## Main functions

### `create_eos_input()`

Creates an EOS input file for EMTO's EOS executable.

```python
from emtoflow.modules.inputs.eos_emto import create_eos_input

create_eos_input(
    filename="eos.dat",
    job_name="fept",
    comment="c/a optimization",
    R_or_V_data=[0.96, 1.00, 1.04],  # c/a ratios or SWS values
    Energy_data=[-1234.5, -1235.0, -1234.8],  # Corresponding energies
    fit_type="MO88"  # MO88, MU37, POLN, SPLN, or ALL
)
```

**Parameters:**
- `filename`: Output file path
- `job_name`: Job identifier
- `comment`: Description comment
- `R_or_V_data`: List of R (SWS) or V (volume) values
- `Energy_data`: List of corresponding energy values
- `fit_type`: EOS fit type (MO88, MU37, POLN, SPLN, ALL)

### `parse_eos_output()`

Parses EOS output file and extracts fitted parameters for all available methods.

```python
from emtoflow.modules.inputs.eos_emto import parse_eos_output

results = parse_eos_output("fept.out")

# Access results by method
morse_params = results['morse']
polynomial_params = results['polynomial']
birch_murnaghan_params = results['birch_murnaghan']
spline_params = results['spline']
murnaghan_params = results['murnaghan']
```

**Returns:** Dictionary mapping method names to `EOSParameters` objects.

## EOS fitting methods

### Modified Morse EOS (MO88) - default
- **Type code**: `MO88`
- **Parameters**: a, b, c, lambda (Morse parameters)
- **Quality indicator**: IFAIL flag (0 = good)

### Polynomial Fit (POLN)
- **Type code**: `POLN`
- **Parameters**: Polynomial coefficients
- **Quality indicator**: Sum of squared residuals

### Cubic Spline Interpolation (SPLN)
- **Type code**: `SPLN`
- **Parameters**: Spline parameters
- **Quality indicator**: Sum of squared residuals

### Birch-Murnaghan EOS (BM52)
- **Type code**: `BM52` (when using ALL)
- **Parameters**: Standard Birch-Murnaghan parameters
- **Quality indicator**: IFAIL flag

### Murnaghan EOS (MU37)
- **Type code**: `MU37`
- **Parameters**: Standard Murnaghan parameters
- **Quality indicator**: IFAIL flag

## Data structures

### `EOSParameters`

Container for equation of state parameters:

```python
@dataclass
class EOSParameters:
    eos_type: str                    # Name of EOS method
    rwseq: float                     # Equilibrium Wigner-Seitz radius (au)
    v_eq: float                      # Equilibrium volume (au^3)
    eeq: float                       # Equilibrium energy (Ry)
    bmod: float                      # Bulk modulus (kBar)
    b_prime: float                   # Pressure derivative of bulk modulus
    gamma: float                     # Gruneisen constant
    fsumsq: float                    # Sum of squared residuals
    fit_quality: str                 # Assessment of fit quality
    data_points: List[EOSDataPoint]  # Data points for plotting
    additional_params: Dict[str, float]  # EOS-specific parameters
```

### `EOSDataPoint`

Single data point from EOS fit:

```python
@dataclass
class EOSDataPoint:
    r: float      # Wigner-Seitz radius
    etot: float   # Total energy (from calculation)
    efit: float   # Fitted energy
    prs: float    # Pressure
```

## Usage in optimization workflow

The EOS module is integrated into the optimization workflow through
`run_eos_fit`, which wraps input generation, EOS execution, and output parsing:

```python
from emtoflow.modules.optimization.analysis import run_eos_fit

# Run EOS fit for c/a optimization
optimal_ca, eos_results, metadata = run_eos_fit(
    output_path=phase_path,
    job_name="fept",
    comment="c/a optimization",
    r_or_v_data=ca_ratios,
    energy_data=energies,
    eos_executable="/path/to/eos.exe",
    eos_type="MO88",
    use_symmetric_selection=True,  # Enable symmetric point selection
    n_points_final=7                # Number of points for final fit
)
```

The `run_eos_fit()` function:

1. Creates an EOS input file via `create_eos_input()`.
2. Runs the EMTO EOS executable.
3. Parses the output with `parse_eos_output()`.
4. Extracts the optimal parameter (e.g. equilibrium SWS or c/a).
5. Returns the optimal value, all fit results, and a metadata dictionary.

---

## Symmetric point selection (optional)

When `use_symmetric_selection=True` and more than `n_points_final` points are
provided, `run_eos_fit()` can perform a two-stage fitting:

1. **Initial fit**: Use all provided points to locate the equilibrium.
2. **Symmetric selection**: Choose `n_points_final` points (default: 7) centered
   around the equilibrium.
3. **Final fit**: Re-fit EOS using only these symmetric points.

Benefits:

- Produces an energy curve that is more symmetric about the minimum.
- More reliable optimization when the equilibrium lies between sampled points.
- Helps avoid bias if many points are far from the minimum.

The metadata returned by `run_eos_fit()` indicates whether symmetric selection
was used and which points were chosen.

---

## Automatic range expansion (optional)

Sometimes the equilibrium lies **outside** the initial scan range or the fit
fails (e.g. returns NaNs). EMTOFlow can automatically expand the parameter
range using a **Modified Morse EOS** estimate of the minimum.

Expansion is triggered when:

1. The EOS fit returns NaN for key quantities (rwseq, eeq, bmod), or
2. The equilibrium value is outside the current parameter range, or
3. The energy is still strictly decreasing at the upper bound (or increasing
   at the lower bound).

High‑level workflow:

1. Save current parameter–energy data to JSON (always on).
2. Fit EOS with current data.
3. If expansion is needed:
   - Fit a Modified Morse EOS to estimate the global minimum.
   - Generate a new parameter vector centered around this estimate
     (same number of points as initial).
   - Run additional calculations for new points (skipping any that already
     exist).
   - Re-fit EOS, optionally with symmetric selection.
4. If the fit is still not acceptable:
   - Use all available data to estimate an updated initial guess (e.g.
     `initial_sws` or single `ca_ratios` value).
   - Report this suggestion and raise a clear error.

Configuration in YAML:

```yaml
# Enable automatic expansion of the parameter range
eos_auto_expand_range: false    # Default: false (opt-in)

# Control which data set is used for EOS fitting
eos_use_saved_data: false       # false: only current workflow points
                                # true: all accumulated points from JSON file
```

Notes:

- Parameter–energy data is **always** saved to JSON files
  (`sws_energy_data.json` or `ca_energy_data.json`), so you can reuse or
  inspect it across runs.
- Currently, the **Modified Morse EOS** is used internally to estimate the
  minimum for expansion; other EOS types are used for fitting but not yet for
  minimum estimation.

## EOS input file format

The generated input file format:

```
DIR_NAME.=
JOB_NAME.=fept
COMMENT..: c/a optimization
FIT_TYPE.=MO88       ! Use MO88, MU37, POLN, SPLN, ALL
N_of_Rws..=  7  Natm_in_uc..=   1 Polinoms_order..=  3 N_spline..=  5
R_or_V....=  R  R_or_V_in...= au. Energy_units....= Ry
  0.960000     -1234.500000  1
  0.980000     -1234.800000  1
  ...
PLOT.....=N
X_axis...=P X_min..=  -100.000 X_max..=  2000.000 N_Xpts.=  40
Y_axes...=V H
```

## EOS output file format

The EOS executable writes results to `<job_name>.out` with sections for each fit type:

```
Equation_of_state fitted by the modified Morse EOS
FITMO88: fsumsq= 1.234567E-06 IFAIL= 0

Ground state parameters:
  Rwseq (Wigner-Seitz radius) =    2.6500000000 au
  V_eq  (Equilibrium volume)  =   93.1234567890 au^3
  Eeq   (Equilibrium energy)  =  -1235.12345678 Ry
  Bmod  (Bulk modulus)        =  1234.56789012 kBar
  B'    (Pressure derivative) =    4.56789012
  Gamma (Gruneisen constant)  =    2.34567890

R           Etot             Efit            Prs
  2.60000  -1234.50000000  -1234.50123456   1234.56789       1
  2.65000  -1235.00000000  -1235.00000000      0.00000       1
  ...
```

## Plotting EOS Fits

The optimization workflow includes EOS plotting functionality:

```python
from emtoflow.modules.optimization.analysis import plot_eos_fit

plot_eos_fit(
    eos_output_file="fept.out",
    output_path="./plots",
    variable_name="c/a",
    variable_units="",
    eos_type="morse"  # morse, polynomial, birch_murnaghan, spline, murnaghan
)
```

## Integration Points

- **`modules/optimization/analysis.py`**: Uses EOS module for fitting
- **`modules/optimization/phase_execution.py`**: Calls EOS fitting in optimization phases
- **Optimization workflow**: Automatically runs EOS fits for c/a and SWS optimization

## Recommendations

1. **Default fit type**: Use `MO88` (Modified Morse) for most materials
2. **Compare fits**: Use `ALL` to compare all methods and select best fit
3. **Check quality**: Review `fit_quality` and `fsumsq` values
4. **Visualization**: Always plot EOS fits to verify quality
5. **Data points**: 
   - For symmetric fitting: Provide many points (e.g., 14) and let the code select 7 symmetric points
   - For standard fitting: Ensure sufficient data points (typically 5-7) for reliable fits
6. **Symmetric fitting**: Enable symmetric point selection when providing many points to ensure symmetric energy curves
7. **Automatic expansion**: Enable `eos_auto_expand_range` for automated workflows where equilibrium might fall outside initial range
   - The workflow uses Modified Morse EOS to estimate the minimum and automatically expands the range
   - Currently only Modified Morse EOS is supported for estimation (other EOS types need implementation)
8. **Data persistence**: Data is always saved automatically. Use `eos_use_saved_data: true` to use ALL accumulated points from saved file (includes data from previous runs), or `false` to use ONLY the current workflow's array

## Error Handling

- Validates input data lengths match
- Checks for EOS executable completion
- Verifies output file existence
- Handles parsing errors gracefully
- Provides informative error messages

## Related Modules

- `modules/optimization/analysis.py`: EOS fitting integration
- `modules/optimization/phase_execution.py`: Uses EOS in optimization phases
- `modules/extract_results.py`: Extracts energies from EMTO output files
