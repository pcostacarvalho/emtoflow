# Plan: Single Expansion Based on Morse EOS Estimation (SIMPLIFIED)

## Problem Statement

When the equilibrium value falls outside the input parameter range, the EOS fit may:
1. Return NaN or invalid values (IFAIL != 0)
2. Show energy still decreasing/increasing at boundaries
3. Make symmetric selection impossible

**Solution**: Estimate minimum using Modified Morse EOS fitting from current points, generate new parameter vector around estimate, re-run calculations once, then fit with symmetric selection.

## Core Strategy

1. **After initial EOS fit**: Check if expansion needed (equilibrium out of range OR NaN values)
2. **If needed**: Estimate minimum using Modified Morse EOS fitting from current points
3. **Generate new parameter vector**: Create ~14 points centered around estimated minimum
4. **Re-run calculations** for new points (skip if already calculated)
5. **Re-fit EOS** with symmetric selection (7 points around equilibrium)
6. **If still not converged**: Estimate Morse EOS again and suggest `initial_sws` value to user

## Key Simplifications

1. **Always save data** - No option needed, just always save to JSON file
2. **One config flag** - `eos_use_saved_data` (true = use all saved data, false = use only current)
3. **Remove PRN scanning** - Not needed if we always save to JSON
4. **Simplified detection** - Only 3 key criteria instead of 6
5. **Consolidated data handling** - One helper function handles loading/merging

## Implementation Plan

### 1. Detection Function (Simplified)

#### `detect_expansion_needed()`

```python
def detect_expansion_needed(
    eos_results: Dict[str, Any],
    param_values: List[float],
    energy_values: List[float],
    equilibrium_value: float
) -> Tuple[bool, str]:
    """
    Determine if parameter range expansion is needed.
    
    Returns (needs_expansion: bool, reason: str)
    """
```

**Expansion criteria** (any triggers expansion):
1. **NaN values**: EOS fit returned NaN for rwseq, eeq, or bmod
2. **Equilibrium outside range**: equilibrium_value < min(param) OR > max(param)
3. **Energy monotonic**: Energy still decreasing at max OR increasing at min

**Simplified from 6 criteria to 3 most important ones**

### 2. Morse EOS Estimation Function

#### `estimate_morse_minimum()`

```python
def estimate_morse_minimum(
    param_values: List[float],
    energy_values: List[float]
) -> Tuple[float, float, Dict[str, Any]]:
    """
    Estimate minimum using Modified Morse EOS fitting.
    
    Fits Modified Morse equation: E(R) = a + b·exp(-λ·R) + c·exp(-2λ·R)
    Equilibrium found from: x0 = -b/(2c), R_eq = -log(x0)/λ
    
    Based on fitmo88.for (V.L.Moruzzi et al. Phys.Rev.B, 37, 790-799 (1988))
    
    Returns (estimated_min_param, estimated_min_energy, fit_info)
    fit_info includes: morse_params (a, b, c, lambda), r_squared, rms, is_valid
    """
```

**Algorithm**:
1. Fit Modified Morse equation: `E(R) = a + b·exp(-λ·R) + c·exp(-2λ·R)` using `scipy.optimize.curve_fit`
2. Calculate equilibrium: `x0 = -b/(2c)`, `R_eq = -log(x0)/λ`
3. Calculate R² and RMS: Assess fit quality
4. Validate: `is_valid = (r_squared > 0.7) and (c > 0)`

**Note**: Currently only implements Modified Morse EOS. Other EOS types (Birch-Murnaghan, Murnaghan, Polynomial) need to be implemented for full support.

### 3. Generate New Parameter Vector

#### `generate_parameter_vector_around_estimate()`

```python
def generate_parameter_vector_around_estimate(
    estimated_minimum: float,
    step_size: float,
    n_points: int = 14,
) -> List[float]:
    """
    Generate parameter vector centered around estimated minimum.
    
    Range width is automatically calculated: range_width = (n_points - 1) × step_size
    Range: [estimate - half_width, estimate + half_width]
    Returns sorted list of n_points evenly spaced values.
    """
```

### 4. Data Persistence (Simplified)

**Always save** parameter-energy data to JSON file after parsing energies (no option, always happens).

#### `save_parameter_energy_data()`

```python
def save_parameter_energy_data(
    phase_path: Path,
    parameter_name: str,  # 'sws' or 'ca'
    parameter_values: List[float],
    energy_values: List[float]
) -> Path:
    """
    Save parameter values and energies to JSON file.
    Merges with existing data if file exists (avoids duplicates).
    
    File: {phase_path}/{parameter_name}_energy_data.json
    Format: {"data_points": [{"parameter": float, "energy": float}, ...]}
    
    This is ALWAYS called - no user option to disable saving.
    """
```

#### `load_parameter_energy_data()`

```python
def load_parameter_energy_data(
    phase_path: Path,
    parameter_name: str
) -> Tuple[List[float], List[float]]:
    """
    Load parameter values and energies from saved file.
    Returns (parameter_values, energy_values) or (None, None) if not found.
    """
```

#### `prepare_data_for_eos_fit()` (NEW - Consolidated Helper)

```python
def prepare_data_for_eos_fit(
    current_param_values: List[float],
    current_energy_values: List[float],
    phase_path: Path,
    parameter_name: str,
    use_saved_data: bool
) -> Tuple[List[float], List[float]]:
    """
    Prepare data for EOS fitting based on user preference.
    
    If use_saved_data=True: Use ALL points from saved file (accumulated over time)
    If use_saved_data=False: Use ONLY current workflow's array (just generated)
    
    Always saves current data to file (no option to disable).
    
    Returns (final_param_values, final_energy_values) sorted by parameter.
    """
```

**Key Points:**
- **Saving is automatic** - Always saves to file, no user option
- **User chooses data source** - Flag controls whether to use all saved data or only current workflow
- **After expansion** - Same logic applies: use all saved data or only workflow points

### 5. Integration Workflow (Simplified)

```python
def optimize_sws_with_expansion(...):
    # Step 1: Initial calculations with provided sws_values
    # ... run calculations ...
    
            # Step 2: Parse energies and prepare data for EOS fitting
            sws_parsed, energy_values = parse_energies_from_prn_files(...)
            
            # Always save current workflow data to file (automatic, no option)
            save_parameter_energy_data(phase_path, 'sws', sws_parsed, energy_values)
            
            # Choose data source for EOS fitting based on user flag
            use_saved_data = config.get('eos_use_saved_data', False)
            if use_saved_data:
                # Use ALL points from saved file
                sws_values, energy_values = load_parameter_energy_data(phase_path, 'sws')
                if sws_values is None:
                    # Fallback to current workflow if no saved file
                    sws_values, energy_values = sws_parsed, energy_values
            else:
                # Use ONLY current workflow's array
                sws_values, energy_values = sws_parsed, energy_values
    
    # Step 3: Initial EOS fit
    optimal_sws, eos_results, metadata = run_eos_fit(
        r_or_v_data=sws_values,
        energy_data=energy_values,
        ...
    )
    
    # Step 4: Check if expansion needed
    if config.get('eos_auto_expand_range', False):
        needs_expansion, reason = detect_expansion_needed(
            eos_results, sws_values, energy_values, optimal_sws
        )
        
        if needs_expansion:
            print(f"\n⚠ Expansion needed: {reason}")
            
            # Step 5: Estimate Morse EOS minimum
            morse_min, morse_energy, morse_info = estimate_morse_minimum(
                sws_values, energy_values
            )
            
            if not morse_info['is_valid']:
                raise RuntimeError(
                    f"Cannot estimate Morse EOS minimum (R² = {morse_info['r_squared']:.3f}). "
                    f"Please manually expand parameter range."
                )
            
            print(f"  Morse EOS estimate: minimum at {morse_min:.6f}")
            
            # Step 6: Generate new parameter vector (use same number of points as initial)
            initial_n_points = len(sws_values)
            new_sws_values = generate_parameter_vector_around_estimate(
                estimated_minimum=morse_min,
                step_size=config.get('sws_step', 0.05),
                n_points=initial_n_points,
            )
            
            # Step 7: Identify which points need calculation
            existing_set = set(sws_values)
            new_points_to_calculate = [v for v in new_sws_values if v not in existing_set]
            
            if new_points_to_calculate:
                print(f"  Calculating {len(new_points_to_calculate)} new points...")
                # Run calculations for new points
                new_sws_calculated, new_energy_values = run_calculations_for_parameter_values(
                    parameter_values=new_points_to_calculate,
                    other_params={'optimal_ca': optimal_ca},
                    phase_path=phase_path,
                    config=config,
                    run_calculations_func=run_calculations_func,
                    validate_calculations_func=validate_calculations_func
                )
                
                # Merge with existing
                all_sws_values = sws_values + new_sws_calculated
                all_energy_values = energy_values + new_energy_values
            else:
                print(f"  All points already calculated")
                all_sws_values = sws_values
                all_energy_values = energy_values
            
            # ALWAYS save updated workflow data to file (automatic, no option)
            save_parameter_energy_data(phase_path, 'sws', all_sws_values, all_energy_values)
            
            # Choose data source for EOS fitting based on user flag
            if use_saved_data:
                # Use ALL points from saved file (accumulated over time)
                saved_sws, saved_energy = load_parameter_energy_data(phase_path, 'sws')
                if saved_sws:
                    print(f"  Using all {len(saved_sws)} points from saved file for EOS fit")
                    all_sws_values = saved_sws
                    all_energy_values = saved_energy
                else:
                    print(f"  No saved file found, using workflow points only")
            else:
                # Use ONLY current workflow's array (just generated)
                print(f"  Using workflow points only ({len(all_sws_values)} points)")
            
            # Step 8: Re-fit EOS with selected data (symmetric selection only if user enabled it)
            optimal_sws, eos_results, metadata = run_eos_fit(
                r_or_v_data=all_sws_values,
                energy_data=all_energy_values,
                ...
                use_symmetric_selection=config.get('symmetric_fit', False),  # Use all points by default
                n_points_final=config.get('n_points_final', 7)
            )
            
            # Step 9: Check if converged
            needs_expansion_again, reason_again = detect_expansion_needed(
                eos_results, all_sws_values, all_energy_values, optimal_sws
            )
            
            if needs_expansion_again:
                # Estimate Morse EOS again and suggest value
                morse_min2, _, morse_info2 = estimate_morse_minimum(
                    all_sws_values, all_energy_values
                )
                
                suggested_initial = morse_min2 if morse_info2['is_valid'] else optimal_sws
                
                raise RuntimeError(
                    f"Failed to find equilibrium after expansion.\n"
                    f"SUGGESTION: Re-run with initial_sws: {suggested_initial:.6f}"
                )
            
            # Update for results
            sws_values = all_sws_values
            energy_values = all_energy_values
    
    # Continue with normal workflow...
    return optimal_sws, phase_results
```

### 6. Calculation Re-running Function

#### `run_calculations_for_parameter_values()`

```python
def run_calculations_for_parameter_values(
    parameter_values: List[float],
    other_params: Dict[str, Any],
    phase_path: Path,
    config: Dict[str, Any],
    run_calculations_func: Callable,
    validate_calculations_func: Callable,
    parameter_name: str = 'sws'
) -> Tuple[List[float], List[float]]:
    """
    Run calculations for given parameter values.
    Returns (calculated_params, energy_values) for successful calculations only.
    """
```

### 7. Configuration (Simplified)

```yaml
# Automatic range expansion
eos_auto_expand_range: false  # Enable automatic expansion (default: false)
# Note: Range width is automatically calculated from number of points and step_size
#   range_width = (n_points - 1) × step_size, centered around estimated minimum
# Note: Expanded vector uses same number of points as initial user input

# Data usage for EOS fitting
eos_use_saved_data: false  # Choose data source for EOS fitting (default: false)
# When true: Use ALL points from saved file (accumulated over multiple runs)
# When false: Use ONLY current workflow's array (just generated)
# When false: Uses only current workflow data (default)
# Data is always saved to file regardless of this flag
```

**Removed**:
- `eos_save_parameter_data` (always save, no option needed)
- `eos_parameter_data_file` (always use default filename)
- `eos_use_all_available_files` (PRN scanning removed)

### 8. Metadata

```python
{
    'expansion_used': bool,
    'morse_estimate': float,
    'expanded_range': Tuple[float, float],
    'points_added': int,
    'converged_after_expansion': bool
}
```

## Key Simplifications Summary

1. **Always save data** - No config option, just always do it
2. **One data flag** - `eos_use_saved_data` controls whether to use saved data
3. **Removed PRN scanning** - Not needed, always use JSON file
4. **Consolidated data handling** - One helper function `prepare_data_for_eos_fit()`
5. **Simplified detection** - 3 criteria instead of 6
6. **Cleaner workflow** - Fewer steps, less duplication

## Implementation Steps

### Phase 1: Core Functions
1. Implement `detect_expansion_needed()` (simplified)
2. Implement `estimate_morse_minimum()` - Uses Modified Morse EOS fitting
3. Implement `generate_parameter_vector_around_estimate()`
4. Add unit tests

**Note**: Currently only Modified Morse EOS is implemented. Other EOS types (Birch-Murnaghan, Murnaghan, Polynomial) need to be implemented for full support.

### Phase 2: Data Persistence
1. Implement `save_parameter_energy_data()` - Always save (automatic, no option)
2. Implement `load_parameter_energy_data()` - Load from JSON
3. Update workflow to:
   - Always save current workflow data to file
   - Use flag `eos_use_saved_data` to choose data source for EOS fitting:
     - `true`: Use ALL points from saved file
     - `false`: Use ONLY current workflow's array
4. Test data persistence and loading

### Phase 3: Calculation Re-running
1. Implement `run_calculations_for_parameter_values()`
2. Test with existing infrastructure
3. Handle partial failures gracefully

### Phase 4: Integration
1. Modify `optimize_ca_ratio()` to support expansion
2. Modify `optimize_sws()` to support expansion
3. Integrate with existing workflow
4. Add convergence check after expansion

### Phase 5: Configuration and Testing
1. Add simplified configuration options
2. Enhance metadata tracking
3. Test with Cu0_Mg100 case
4. Update documentation

## Backward Compatibility

- Feature is **opt-in** via `eos_auto_expand_range: false` (default)
- Data is always saved (no breaking change, just adds files)
- `eos_use_saved_data: false` (default) ensures existing behavior
- No breaking changes to function signatures
