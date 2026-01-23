# EOS Module

## Overview

The `modules/inputs/eos_emto.py` module provides functionality for creating equation of state (EOS) input files for EMTO's EOS executable and parsing the resulting output. It supports multiple EOS fitting methods and is integrated into the optimization workflow for finding optimal c/a ratios and SWS values.

## Key Features

- **EOS input file generation**: Creates formatted input files for EMTO's EOS executable
- **Multiple fitting methods**: Supports Modified Morse, Murnaghan, Polynomial, Cubic Spline, and Birch-Murnaghan EOS
- **Output parsing**: Extracts fitted parameters from EOS output files
- **Data structures**: Provides dataclasses for EOS parameters and data points
- **Integration**: Used by optimization workflow for c/a and SWS optimization

## Main Functions

### `create_eos_input()`

Creates an EOS input file for EMTO's EOS executable.

```python
from modules.inputs.eos_emto import create_eos_input

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
from modules.inputs.eos_emto import parse_eos_output

results = parse_eos_output("fept.out")

# Access results by method
morse_params = results['morse']
polynomial_params = results['polynomial']
birch_murnaghan_params = results['birch_murnaghan']
spline_params = results['spline']
murnaghan_params = results['murnaghan']
```

**Returns:** Dictionary mapping method names to `EOSParameters` objects.

## EOS Fitting Methods

### Modified Morse EOS (MO88)
- **Type code**: `MO88`
- **Best for**: Most materials, recommended default
- **Parameters**: a, b, c, lambda (Morse parameters)
- **Quality indicator**: IFAIL flag (0 = good)

### Polynomial Fit (POLN)
- **Type code**: `POLN`
- **Best for**: Quick fits, less reliable bulk modulus
- **Parameters**: Polynomial coefficients
- **Quality indicator**: Sum of squared residuals

### Cubic Spline Interpolation (SPLN)
- **Type code**: `SPLN`
- **Best for**: Smooth interpolation
- **Parameters**: Spline parameters
- **Quality indicator**: Sum of squared residuals

### Birch-Murnaghan EOS (BM52)
- **Type code**: `BM52` (when using ALL)
- **Best for**: High-pressure studies
- **Parameters**: Standard Birch-Murnaghan parameters
- **Quality indicator**: IFAIL flag

### Murnaghan EOS (MU37)
- **Type code**: `MU37`
- **Best for**: Simple EOS fits
- **Parameters**: Standard Murnaghan parameters
- **Quality indicator**: IFAIL flag

## Data Structures

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

## Usage in Optimization Workflow

The EOS module is integrated into the optimization workflow:

```python
from modules.optimization.analysis import run_eos_fit

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
1. Creates EOS input file using `create_eos_input()`
2. Runs EMTO EOS executable
3. Parses output using `parse_eos_output()`
4. Extracts optimal parameter (rwseq)
5. Returns optimal value, all fit results, and metadata

### Symmetric Point Selection

When `use_symmetric_selection=True` and more than `n_points_final` points are provided, the function performs a two-stage fitting process:

1. **Initial fit**: Fits EOS with all provided points to find equilibrium value
2. **Symmetric selection**: Selects `n_points_final` points (default: 7) centered around the equilibrium
3. **Final fit**: Performs final EOS fit with the selected symmetric points

This ensures the energy curve is symmetric around the equilibrium, which is important for accurate optimization results.

**Benefits:**
- Ensures symmetric energy curve around equilibrium
- More reliable optimization when equilibrium falls between data points
- Better fit quality when many points are provided

**Warnings:**
The function will issue warnings (but not fail) if:
- Equilibrium is outside the input range (extrapolation)
- Symmetric selection is not possible (equilibrium too close to boundary)
- Fewer than requested points are available

**Metadata:**
The function returns a metadata dictionary containing:
- `symmetric_selection_used`: Whether symmetric selection was performed
- `initial_points`: Number of points in initial fit
- `final_points`: Number of points in final fit
- `equilibrium_value`: Equilibrium value from fit
- `equilibrium_in_range`: Whether equilibrium is within input range
- `selected_indices`: Indices of selected points
- `warnings`: List of warning messages

## EOS Input File Format

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

## EOS Output File Format

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
from modules.optimization.analysis import plot_eos_fit

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
