# Plan: Single Expansion Based on Parabola Estimation

## Problem Statement

When the equilibrium value falls outside the input parameter range, the EOS fit may:
1. Return NaN or invalid values (IFAIL != 0)
2. Show energy still decreasing/increasing at boundaries
3. Make symmetric selection impossible

**Solution**: Estimate parabola minimum from current points, generate new parameter vector around estimate, re-run calculations once, then fit with symmetric selection.

## Proposed Solution: Single Smart Expansion

### Core Strategy

1. **After initial EOS fit**: Check fit quality and energy trends
2. **If problematic**: Estimate parabola minimum from current points
3. **Generate new parameter vector**: Create ~14 points centered around estimated minimum
4. **Re-run calculations** for new points
5. **Re-fit EOS** with symmetric selection (7 points around equilibrium)
6. **If still not converged**: Estimate parabola again and suggest `initial_sws` value to user

### Key Features

- **Single expansion**: Only one round of additional calculations (not iterative)
- **Smart targeting**: Uses parabola estimate to center new range
- **Symmetric fitting**: New range allows proper symmetric selection
- **User guidance**: If still fails, suggests initial_sws value for manual re-run
- **Configurable**: Can be enabled/disabled via flag

## Implementation Plan

### 1. Detection Function

#### `detect_expansion_needed()`

```python
def detect_expansion_needed(
    eos_results: Dict[str, Any],
    param_values: List[float],
    energy_values: List[float],
    equilibrium_value: float
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Determine if parameter range expansion is needed.
    
    Parameters
    ----------
    eos_results : dict
        EOS fit results
    param_values : List[float]
        Parameter values used in fit
    energy_values : List[float]
        Energy values used in fit
    equilibrium_value : float
        Equilibrium value from EOS fit (may be NaN)
    
    Returns
    -------
    tuple of (needs_expansion, reason, diagnostics)
        needs_expansion : bool
        reason : str (reason for expansion)
        diagnostics : dict with detailed info
    """
```

**Expansion criteria** (any of these triggers expansion):
1. **NaN values**: EOS fit returned NaN for rwseq, eeq, or bmod
2. **IFAIL > 0**: EOS fit quality flag indicates problems
3. **Equilibrium outside range**: equilibrium_value < min(param) OR > max(param)
4. **Energy still decreasing**: Energy decreasing at maximum parameter value
5. **Energy still increasing**: Energy increasing at minimum parameter value
6. **Minimum at boundary**: Minimum energy at first or last point

**Diagnostics returned**:
```python
{
    'has_nan': bool,
    'ifail': int,
    'equilibrium_outside_range': bool,
    'energy_decreasing_at_max': bool,
    'energy_increasing_at_min': bool,
    'min_at_boundary': str,  # 'left', 'right', None
}
```

### 2. Parabola Estimation Function

#### `estimate_parabola_minimum()`

```python
def estimate_parabola_minimum(
    param_values: List[float],
    energy_values: List[float]
) -> Tuple[float, float, Dict[str, Any]]:
    """
    Estimate minimum of energy parabola by fitting quadratic polynomial.
    
    Fits E(param) = a*param² + b*param + c
    Minimum occurs at param_min = -b/(2*a) if a > 0
    
    Parameters
    ----------
    param_values : List[float]
        Parameter values (must be sorted)
    energy_values : List[float]
        Corresponding energy values
    
    Returns
    -------
    tuple of (estimated_min_param, estimated_min_energy, fit_info)
        estimated_min_param : float
            Estimated parameter value at minimum
        estimated_min_energy : float
            Estimated energy at minimum
        fit_info : dict
            - coefficients: [a, b, c] (quadratic coefficients)
            - r_squared: float (fit quality, 0-1)
            - is_valid: bool (parabola opens upward, a > 0)
            - standard_error: float (uncertainty in estimate)
    """
```

**Algorithm**:
1. Fit quadratic: `E = a*x² + b*x + c` using `numpy.polyfit(degree=2)`
2. Calculate vertex: `x_min = -b/(2*a)` (if a > 0, parabola opens upward)
3. Calculate R²: Assess fit quality
4. Validate: Check if a > 0 (parabola has minimum, not maximum)
5. Calculate standard error: Estimate uncertainty
6. Return estimate and quality metrics

**Validation**:
- `is_valid = True` if:
  - a > 0 (parabola opens upward)
  - R² > 0.7 (reasonable fit)
  - Standard error is reasonable

### 3. Generate New Parameter Vector

#### `generate_parameter_vector_around_estimate()`

```python
def generate_parameter_vector_around_estimate(
    estimated_minimum: float,
    step_size: float,
    n_points: int = 14,
    expansion_factor: float = 3.0
) -> List[float]:
    """
    Generate parameter vector centered around estimated minimum.
    
    Parameters
    ----------
    estimated_minimum : float
        Parabola-estimated minimum parameter value
    step_size : float
        Step size for parameter spacing (from config: ca_step or sws_step)
    n_points : int
        Number of points to generate (default: 14, allows symmetric selection of 7)
    expansion_factor : float
        Factor for range width: range = ±expansion_factor * step_size (default: 3.0)
    
    Returns
    -------
    List[float]
        Sorted list of parameter values centered around estimate
    """
```

**Algorithm**:
- Calculate range: `min_val = estimate - expansion_factor * step_size`
- Calculate range: `max_val = estimate + expansion_factor * step_size`
- Generate `n_points` evenly spaced values: `np.linspace(min_val, max_val, n_points)`
- Return sorted list

**Example**:
- Estimate: 2.95
- step_size: 0.05
- expansion_factor: 3.0
- Range: [2.95 - 0.15, 2.95 + 0.15] = [2.80, 3.10]
- Generate 14 points: [2.80, 2.82, ..., 3.08, 3.10]

### 4. Integration Workflow

#### Modified `optimize_ca_ratio()` and `optimize_sws()`

**New workflow**:
```python
def optimize_sws_with_expansion(...):
    # Step 1: Initial calculations with provided sws_values
    # Step 2: Initial EOS fit
    optimal_sws, eos_results, metadata = run_eos_fit(...)
    
    # Step 3: Check if expansion needed
    if config.get('eos_auto_expand_range', False):
        needs_expansion, reason, diagnostics = detect_expansion_needed(
            eos_results, sws_values, energy_values, optimal_sws
        )
        
        if needs_expansion:
            print(f"\n⚠ Expansion needed: {reason}")
            
            # Step 4: Estimate parabola minimum
            parabola_min, parabola_energy, parabola_info = estimate_parabola_minimum(
                sws_values, energy_values
            )
            
            if parabola_info['is_valid']:
                print(f"  Parabola estimate: minimum at {parabola_min:.6f} "
                      f"(R² = {parabola_info['r_squared']:.3f})")
                
                # Step 5: Generate new parameter vector
                new_sws_values = generate_parameter_vector_around_estimate(
                    estimated_minimum=parabola_min,
                    step_size=config.get('sws_step', 0.05),
                    n_points=config.get('eos_expansion_n_points', 14),
                    expansion_factor=config.get('eos_expansion_factor', 3.0)
                )
                
                # Identify which points need calculation
                existing_set = set(sws_values)
                new_points = [v for v in new_sws_values if v not in existing_set]
                
                print(f"  Generating new vector with {len(new_sws_values)} points "
                      f"centered around {parabola_min:.6f}")
                print(f"  New points to calculate: {len(new_points)}")
                print(f"  New range: [{min(new_sws_values):.4f}, {max(new_sws_values):.4f}]")
                
                # Step 6: Run calculations for new points
                # (reuse existing calculation infrastructure)
                new_sws_calculated, new_energy_values = run_calculations_for_parameter_values(
                    parameter_values=new_points,
                    other_params={'optimal_ca': optimal_ca},
                    phase_path=phase_path,
                    config=config,
                    run_calculations_func=run_calculations_func,
                    validate_calculations_func=validate_calculations_func
                )
                
                # Merge with existing data
                all_sws_values = sws_values + new_sws_calculated
                all_energy_values = energy_values + new_energy_values
                
                # Sort by parameter value
                sorted_pairs = sorted(zip(all_sws_values, all_energy_values))
                all_sws_values = [s for s, e in sorted_pairs]
                all_energy_values = [e for s, e in sorted_pairs]
                
                # Step 7: Re-fit EOS with symmetric selection
                optimal_sws, eos_results, metadata = run_eos_fit(
                    r_or_v_data=all_sws_values,
                    energy_data=all_energy_values,
                    output_path=phase_path,
                    job_name=f"{config['job_name']}_sws",
                    comment=f"SWS optimization (after expansion)",
                    eos_executable=config['eos_executable'],
                    eos_type=config.get('eos_type', 'MO88'),
                    use_symmetric_selection=True,
                    n_points_final=7
                )
                
                # Step 8: Check if converged
                needs_expansion_again, reason_again, diagnostics_again = detect_expansion_needed(
                    eos_results, all_sws_values, all_energy_values, optimal_sws
                )
                
                if needs_expansion_again:
                    # Estimate parabola again from expanded dataset
                    parabola_min2, parabola_energy2, parabola_info2 = estimate_parabola_minimum(
                        all_sws_values, all_energy_values
                    )
                    
                    # Suggest initial_sws value
                    suggested_initial = parabola_min2 if parabola_info2['is_valid'] else optimal_sws
                    
                    raise RuntimeError(
                        f"Failed to find equilibrium within range after expansion.\n\n"
                        f"Initial range: [{min(sws_values):.6f}, {max(sws_values):.6f}]\n"
                        f"Expanded range: [{min(all_sws_values):.6f}, {max(all_sws_values):.6f}]\n"
                        f"Reason: {reason_again}\n\n"
                        f"Parabola estimate from expanded data:\n"
                        f"  Estimated minimum: {parabola_min2:.6f}\n"
                        f"  Fit quality (R²): {parabola_info2['r_squared']:.3f}\n"
                        f"  Estimated minimum energy: {parabola_energy2:.6f} Ry\n\n"
                        f"SUGGESTION: Re-run optimization with:\n"
                        f"  initial_sws: {suggested_initial:.6f}\n"
                        f"  (or sws_values centered around {suggested_initial:.6f})"
                    )
                
                # Update sws_values for results
                sws_values = all_sws_values
                energy_values = all_energy_values
                
            else:
                # Parabola fit not valid - can't estimate
                raise RuntimeError(
                    f"Cannot estimate parabola minimum (R² = {parabola_info['r_squared']:.3f}). "
                    f"Energy curve may not be parabolic. Please manually expand parameter range."
                )
    
    # Continue with normal workflow...
    return optimal_sws, phase_results
```

### 5. Calculation Re-running Function

#### `run_calculations_for_parameter_values()`

```python
def run_calculations_for_parameter_values(
    parameter_values: List[float],
    other_params: Dict[str, Any],  # c/a, structure, etc.
    phase_path: Path,
    config: Dict[str, Any],
    run_calculations_func: Callable,
    validate_calculations_func: Callable,
    parameter_name: str = 'sws'  # 'sws' or 'ca'
) -> Tuple[List[float], List[float]]:
    """
    Run calculations for given parameter values.
    
    Parameters
    ----------
    parameter_values : List[float]
        New parameter values to calculate
    other_params : dict
        Other parameters (e.g., optimal_ca for SWS optimization)
    phase_path : Path
        Phase output directory
    config : dict
        Configuration dictionary
    run_calculations_func : callable
        Function to run calculations
    validate_calculations_func : callable
        Function to validate calculations
    parameter_name : str
        'sws' or 'ca' (determines which parameter is varying)
    
    Returns
    -------
    tuple of (calculated_params, energy_values)
        calculated_params : List of parameter values that were successfully calculated
        energy_values : Corresponding energy values
    """
```

**Implementation**:
1. Create EMTO inputs for new parameter values
2. Run calculations (reuse existing infrastructure)
3. Validate calculations completed
4. Parse energies from PRN files
5. Return parameter values and energies (only successful calculations)

### 6. Configuration

```yaml
# Automatic range expansion for out-of-range equilibrium
eos_auto_expand_range: false  # Enable automatic expansion (default: false)
eos_expansion_n_points: 14  # Number of points in expanded vector (default: 14)
eos_expansion_factor: 3.0  # Range factor: ±factor*step_size around estimate (default: 3.0)
```

### 7. Metadata and Reporting

**Enhanced metadata**:
```python
{
    'expansion_used': bool,
    'parabola_estimate': {
        'estimated_min_param': float,
        'estimated_min_energy': float,
        'r_squared': float,
        'is_valid': bool
    },
    'expanded_range': Tuple[float, float],
    'initial_range': Tuple[float, float],
    'points_added': int,
    'converged_after_expansion': bool
}
```

### 8. Convergence Criteria

**Converged when ALL of these are true**:
1. Equilibrium value is within parameter range
2. EOS fit is valid (no NaN, IFAIL=0 or acceptable)
3. Energy has minimum in middle of range (not at boundary)
4. Symmetric selection is possible (if enabled)

## Example Workflow: Cu0_Mg100 Case

**Initial state**:
- SWS range: [2.52, 2.54, ..., 2.82] (15 points)
- Energy: Still decreasing at 2.82
- EOS fit: NaN (IFAIL=2)

**Expansion step**:
1. **Parabola estimation**: 
   - Fit quadratic to current points
   - Estimate minimum at SWS ≈ 2.95 (R² = 0.98)
   
2. **Generate new vector**:
   - Centered around 2.95
   - Range: [2.80, 3.10] (2.95 ± 3×0.05)
   - 14 points: [2.80, 2.82, ..., 3.08, 3.10]
   
3. **Run calculations**:
   - Calculate for new points (some may overlap with existing)
   - Parse energies
   
4. **Re-fit EOS**:
   - Use all points (original + new)
   - Symmetric selection: Choose 7 points around equilibrium
   - Final fit with symmetric points

**If still not converged**:
- Estimate parabola again from expanded dataset
- Suggest `initial_sws: 2.97` (or similar) for user to re-run manually

## Error Messages

**If expansion fails**:
```
RuntimeError: Failed to find equilibrium within range after expansion.

Initial range: [2.52, 2.82]
Expanded range: [2.80, 3.10]
Reason: Energy still decreasing at maximum SWS

Parabola estimate from expanded data:
  Estimated minimum: 2.97
  Fit quality (R²): 0.95
  Estimated minimum energy: -400.62 Ry

SUGGESTION: Re-run optimization with:
  initial_sws: 2.97
  (or sws_values centered around 2.97)
```

## Implementation Steps

### Phase 1: Core Functions
1. Implement `detect_expansion_needed()`
2. Implement `estimate_parabola_minimum()`
3. Implement `generate_parameter_vector_around_estimate()`
4. Add unit tests

### Phase 2: Calculation Re-running
1. Implement `run_calculations_for_parameter_values()`
2. Test with existing calculation infrastructure
3. Handle partial failures gracefully

### Phase 3: Integration
1. Modify `optimize_ca_ratio()` to support expansion
2. Modify `optimize_sws()` to support expansion
3. Integrate with existing calculation workflow
4. Add convergence check after expansion

### Phase 4: Configuration and Reporting
1. Add configuration options
2. Enhance metadata tracking
3. Update warnings and progress messages
4. Update summary reports

### Phase 5: Testing and Documentation
1. Test with Cu0_Mg100 case (energy decreasing)
2. Test with various scenarios
3. Update documentation
4. Add examples

## Backward Compatibility

- Feature is **opt-in** via `eos_auto_expand_range: false` (default)
- Existing workflows unchanged if flag not set
- No breaking changes to function signatures
- Can be enabled per-phase or globally

## Considerations

### Pros
- Single expansion (not iterative) - simpler and faster
- Smart targeting using parabola estimate
- Provides user guidance if still fails
- Limited computational cost (one round of extra calculations)

### Cons
- May not find equilibrium if estimate is poor
- Requires re-running calculations (computational cost)
- Need to handle calculation failures gracefully
- Parabola estimate may be inaccurate for non-parabolic curves

### Mitigations
- Validate parabola fit quality (R² threshold)
- Provide clear error message with suggestion if fails
- Graceful handling of calculation failures
- User can disable if not wanted

## Testing Scenarios

1. **Energy decreasing** (Cu0_Mg100): Estimate ~2.95, expand, should converge
2. **Energy increasing**: Estimate below range, expand left
3. **Equilibrium slightly outside**: One expansion should suffice
4. **Poor parabola fit**: Should handle gracefully, suggest manual expansion
5. **Normal case**: No expansion needed, should skip
6. **Calculation failures**: Handle gracefully, use available points
