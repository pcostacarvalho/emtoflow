#!/usr/bin/env python3
"""
Manual test of Morse estimation using first 7 points from PRN files.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from modules.extract_results import parse_kfcd
from modules.optimization.analysis import estimate_morse_minimum
import numpy as np
from scipy.optimize import curve_fit

# Path to PRN files
phase_path = project_root / "Cu0_Mg100" / "phase2_sws_optimization" / "fcd"

# First 7 SWS values from the config
sws_values = [2.52, 2.54, 2.56, 2.59, 2.61, 2.63, 2.65]

print("="*70)
print("MANUAL MORSE ESTIMATION TEST")
print("="*70)
print(f"\nUsing first 7 SWS values: {sws_values}")
print(f"Reading PRN files from: {phase_path}\n")

# Parse energies from PRN files
sws_parsed = []
energy_values = []

for sws in sws_values:
    file_id = f"CuMg_1.00_{sws:.2f}"
    prn_file = phase_path / f"{file_id}.prn"
    
    if not prn_file.exists():
        print(f"  ⚠ File not found: {prn_file}")
        continue
    
    try:
        results = parse_kfcd(str(prn_file), functional='GGA')
        if results.total_energy is None:
            print(f"  ⚠ No energy found in {prn_file.name}")
            continue
        
        energy = results.energies_by_functional.get('system', {}).get('GGA')
        if energy is None:
            energy = results.total_energy
        
        sws_parsed.append(sws)
        energy_values.append(energy)
        print(f"  SWS = {sws:.4f}: E = {energy:.6f} Ry")
    except Exception as e:
        print(f"  ⚠ Error parsing {prn_file.name}: {e}")

if len(sws_parsed) < 4:
    print(f"\n✗ Need at least 4 points, got {len(sws_parsed)}")
    sys.exit(1)

print(f"\n{'='*70}")
print("TESTING MORSE ESTIMATION")
print(f"{'='*70}\n")

# Test the estimate_morse_minimum function
morse_min, morse_energy, morse_info = estimate_morse_minimum(
    sws_parsed, energy_values
)

print(f"\nResults from estimate_morse_minimum():")
print(f"  Estimated minimum SWS: {morse_min:.6f}")
print(f"  Estimated minimum energy: {morse_energy:.6f} Ry")
print(f"  R²: {morse_info['r_squared']:.6f}")
print(f"  RMS: {morse_info['rms']:.6f}")
print(f"  Is valid: {morse_info['is_valid']}")

if morse_info.get('morse_params'):
    params = morse_info['morse_params']
    print(f"\nMorse parameters:")
    print(f"  a = {params['a']:.6f}")
    print(f"  b = {params['b']:.6f}")
    print(f"  c = {params['c']:.6f}")
    print(f"  lambda = {params['lambda']:.6f}")
    
    # Manual calculation check
    b = params['b']
    c = params['c']
    lam = params['lambda']
    
    if abs(c) > 1e-10:
        x0_eq = -b / (2.0 * c)
        print(f"\nManual calculation check:")
        print(f"  x0_eq = -b/(2c) = {x0_eq:.6f}")
        if x0_eq > 0:
            alx0_eq = np.log(x0_eq)
            r_eq_manual = -alx0_eq / lam
            print(f"  R_eq = -log(x0_eq)/lambda = {r_eq_manual:.6f}")
            print(f"  (Should match estimated minimum: {morse_min:.6f})")
        else:
            print(f"  ⚠ x0_eq is non-positive!")
else:
    print(f"\n⚠ No Morse parameters (fit failed)")
    if morse_info.get('error'):
        print(f"  Error: {morse_info['error']}")

print(f"\n{'='*70}")
print("MANUAL FIT TEST (using scipy directly)")
print(f"{'='*70}\n")

# Manual fit test with improved initial guesses
param_values = np.array(sws_parsed)
energy_array = np.array(energy_values)

# Sort by parameter
sort_idx = np.argsort(param_values)
param_values = param_values[sort_idx]
energy_array = energy_array[sort_idx]

def morse_func(r, a, b, c, lam):
    """Modified Morse: E(R) = a + b·exp(-λ·R) + c·exp(-2λ·R)"""
    x = np.exp(-lam * r)
    return a + b * x + c * x * x

# Improved initial guesses (matching the code)
energy_min = np.min(energy_array)
energy_max = np.max(energy_array)
energy_range = energy_max - energy_min
param_range = np.max(param_values) - np.min(param_values)
param_mean = np.mean(param_values)
param_min = float(np.min(param_values))
param_max = float(np.max(param_values))

# Estimate lambda
lam_init = 0.5 / param_mean

# Determine energy trend
if energy_array[-1] < energy_array[0]:
    r_guess = param_max * 1.15  # 15% beyond max
elif energy_array[0] < energy_array[-1]:
    r_guess = param_min * 0.85  # 15% before min
else:
    r_guess = param_mean

x0_init = np.exp(-lam_init * r_guess)
c_init = max(energy_range * 0.05, 1e-6)
b_init = -2.0 * c_init * x0_init
a_init = energy_min - b_init * x0_init - c_init * x0_init * x0_init

print(f"Initial guesses:")
print(f"  a = {a_init:.6f}")
print(f"  b = {b_init:.6f}")
print(f"  c = {c_init:.6f}")
print(f"  lambda = {lam_init:.6f}")
print(f"  r_guess = {r_guess:.6f}")
print(f"  x0_init = {x0_init:.6f}")

# Check what the initial guess predicts
print(f"\nInitial guess predictions:")
energy_pred_init = morse_func(param_values, a_init, b_init, c_init, lam_init)
for i, (r, e_act, e_pred) in enumerate(zip(param_values, energy_array, energy_pred_init)):
    print(f"  SWS={r:.2f}: actual={e_act:.6f}, predicted={e_pred:.6f}, diff={e_act-e_pred:.6f}")

# Try multiple fitting strategies
strategies = []

# Strategy 1: Current approach
strategies.append({
    'name': 'Current (improved guesses)',
    'p0': [a_init, b_init, c_init, lam_init],
    'bounds': ([-np.inf, -np.inf, 1e-10, 1e-10], [np.inf, np.inf, np.inf, np.inf])
})

# Strategy 2: More conservative lambda (smaller)
lam_init2 = 0.1 / param_mean  # Much smaller lambda
r_guess2 = param_max * 1.25  # 25% beyond max (closer to expected 3.3-3.4)
x0_init2 = np.exp(-lam_init2 * r_guess2)
c_init2 = max(energy_range * 0.05, 1e-6)
b_init2 = -2.0 * c_init2 * x0_init2
a_init2 = energy_min - b_init2 * x0_init2 - c_init2 * x0_init2 * x0_init2
strategies.append({
    'name': 'Smaller lambda, r_guess=1.25*max',
    'p0': [a_init2, b_init2, c_init2, lam_init2],
    'bounds': ([-np.inf, -np.inf, 1e-10, 1e-10], [np.inf, np.inf, np.inf, np.inf])
})

# Strategy 3: Even smaller lambda, r_guess at expected minimum (3.35)
lam_init3 = 0.05 / param_mean  # Very small lambda
r_guess3 = 3.35  # Expected minimum location
x0_init3 = np.exp(-lam_init3 * r_guess3)
c_init3 = max(energy_range * 0.05, 1e-6)
b_init3 = -2.0 * c_init3 * x0_init3
a_init3 = energy_min - b_init3 * x0_init3 - c_init3 * x0_init3 * x0_init3
strategies.append({
    'name': 'Very small lambda, r_guess=3.35',
    'p0': [a_init3, b_init3, c_init3, lam_init3],
    'bounds': ([-np.inf, -np.inf, 1e-10, 1e-10], [np.inf, np.inf, np.inf, np.inf])
})

# Strategy 4: Simple linear extrapolation approach
# Fit a quadratic to estimate minimum, then use that for Morse guess
coeffs = np.polyfit(param_values, energy_array, 2)
# Quadratic: E = ax² + bx + c, minimum at x = -b/(2a)
if coeffs[0] > 0:  # Parabola opens upward
    quad_min = -coeffs[1] / (2 * coeffs[0])
else:
    quad_min = param_max * 1.25  # Fallback

lam_init4 = 0.1 / param_mean
r_guess4 = max(quad_min, param_max * 1.2)  # Use quadratic estimate or 20% beyond max
x0_init4 = np.exp(-lam_init4 * r_guess4)
c_init4 = max(energy_range * 0.05, 1e-6)
b_init4 = -2.0 * c_init4 * x0_init4
a_init4 = energy_min - b_init4 * x0_init4 - c_init4 * x0_init4 * x0_init4
strategies.append({
    'name': 'Quadratic-guided guess',
    'p0': [a_init4, b_init4, c_init4, lam_init4],
    'bounds': ([-np.inf, -np.inf, 1e-10, 1e-10], [np.inf, np.inf, np.inf, np.inf])
})

print(f"\n{'='*70}")
print("TRYING MULTIPLE FITTING STRATEGIES")
print(f"{'='*70}\n")

best_fit = None
best_r_squared = -np.inf

for strategy in strategies:
    print(f"\n--- Strategy: {strategy['name']} ---")
    print(f"  Initial params: a={strategy['p0'][0]:.6f}, b={strategy['p0'][1]:.6f}, "
          f"c={strategy['p0'][2]:.6f}, lambda={strategy['p0'][3]:.6f}")
    
    try:
        # Try Levenberg-Marquardt first (no bounds, faster)
        popt, pcov = curve_fit(
            morse_func,
            param_values,
            energy_array,
            p0=strategy['p0'],
            maxfev=10000,
            method='lm'  # LM doesn't use bounds
        )
        
        a, b, c, lam = popt
        print(f"  ✓ Fit succeeded!")
        
        # Calculate equilibrium
        if abs(c) < 1e-10:
            print(f"  ✗ c parameter too small")
            continue
            
        x0_eq = -b / (2.0 * c)
        if x0_eq <= 0:
            print(f"  ✗ x0_eq is non-positive: {x0_eq}")
            continue
            
        alx0_eq = np.log(x0_eq)
        r_eq = -alx0_eq / lam
        
        # Calculate R²
        energy_predicted = morse_func(param_values, a, b, c, lam)
        ss_res = np.sum((energy_array - energy_predicted)**2)
        ss_tot = np.sum((energy_array - np.mean(energy_array))**2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        
        print(f"    R_eq = {r_eq:.6f}")
        print(f"    R² = {r_squared:.6f}")
        print(f"    Params: a={a:.6f}, b={b:.6f}, c={c:.6f}, lambda={lam:.6f}")
        
        if r_squared > best_r_squared:
            best_r_squared = r_squared
            best_fit = {
                'strategy': strategy['name'],
                'params': popt,
                'r_eq': r_eq,
                'r_squared': r_squared
            }
            
    except Exception as e:
        print(f"  ✗ Fit failed: {e}")

if best_fit:
    print(f"\n{'='*70}")
    print("BEST FIT RESULT")
    print(f"{'='*70}\n")
    print(f"Strategy: {best_fit['strategy']}")
    print(f"Estimated minimum SWS: {best_fit['r_eq']:.6f}")
    print(f"R²: {best_fit['r_squared']:.6f}")
    a, b, c, lam = best_fit['params']
    print(f"Final parameters:")
    print(f"  a = {a:.6f}")
    print(f"  b = {b:.6f}")
    print(f"  c = {c:.6f}")
    print(f"  lambda = {lam:.6f}")
else:
    print(f"\n{'='*70}")
    print("ALL STRATEGIES FAILED")
    print(f"{'='*70}\n")
    print("Trying original approach with increased maxfev...")
    
    try:
        popt, pcov = curve_fit(
            morse_func,
            param_values,
            energy_array,
            p0=[a_init, b_init, c_init, lam_init],
            maxfev=20000,  # Much higher
            bounds=(
                [-np.inf, -np.inf, 1e-10, 1e-10],
            [np.inf, np.inf, np.inf, np.inf]
            ),
            method='trf'  # Trust Region Reflective (uses bounds)
        )
        
        a, b, c, lam = popt
        print(f"\n✓ Fit succeeded with increased maxfev!")
        print(f"  a = {a:.6f}")
        print(f"  b = {b:.6f}")
        print(f"  c = {c:.6f}")
        print(f"  lambda = {lam:.6f}")
        
        # Calculate equilibrium
        if abs(c) < 1e-10:
            print(f"\n✗ c parameter too small, cannot calculate equilibrium")
        else:
            x0_eq = -b / (2.0 * c)
            print(f"\n  x0_eq = -b/(2c) = {x0_eq:.6f}")
            
            if x0_eq <= 0:
                print(f"  ⚠ x0_eq is non-positive!")
            else:
                alx0_eq = np.log(x0_eq)
                r_eq = -alx0_eq / lam
                print(f"  R_eq = -log(x0_eq)/lambda = {r_eq:.6f}")
                
                # Calculate R²
                energy_predicted = morse_func(param_values, a, b, c, lam)
                ss_res = np.sum((energy_array - energy_predicted)**2)
                ss_tot = np.sum((energy_array - np.mean(energy_array))**2)
                r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
                
                print(f"\n  R² = {r_squared:.6f}")
                print(f"  Estimated minimum SWS = {r_eq:.6f}")
                
                # Check if reasonable
                if r_eq < min(param_values) or r_eq > max(param_values):
                    print(f"  ⚠ Estimated minimum ({r_eq:.6f}) is outside data range [{min(param_values):.4f}, {max(param_values):.4f}]")
                else:
                    print(f"  ✓ Estimated minimum is within data range")

    except Exception as e:
        print(f"\n✗ Even with increased maxfev, fit failed: {e}")
        import traceback
        traceback.print_exc()

print(f"\n{'='*70}")
print("DATA SUMMARY")
print(f"{'='*70}\n")
print("SWS values:", sws_parsed)
print("Energy values:", [f"{e:.6f}" for e in energy_values])
print(f"\nEnergy is {'decreasing' if energy_values[-1] < energy_values[0] else 'increasing'} at boundaries")
print(f"Minimum energy in data: {min(energy_values):.6f} Ry at SWS = {sws_parsed[np.argmin(energy_values)]:.4f}")
