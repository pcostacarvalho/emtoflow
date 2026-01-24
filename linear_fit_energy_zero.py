#!/usr/bin/env python3
"""
Morse potential fitting of energy data and estimation of minimum
"""

import numpy as np

def parse_data_file(filepath):
    """Parse the data file and extract R and Etot columns"""
    R_values = []
    Etot_values = []
    
    with open(filepath, 'r') as f:
        for line in f:
            # Skip header lines and empty lines
            if 'R' in line and 'Etot' in line:
                continue
            if not line.strip() or line.startswith('FITMO') or line.startswith('Equation') or line.startswith('SWS'):
                continue
            
            # Try to parse data lines
            parts = line.split()
            if len(parts) >= 2:
                try:
                    r_val = float(parts[0])
                    etot_val = float(parts[1])
                    R_values.append(r_val)
                    Etot_values.append(etot_val)
                except ValueError:
                    continue
    
    return np.array(R_values), np.array(Etot_values)

def morse_potential(r, D_e, a, r_e, E_shift):
    """
    Morse potential: E(r) = D_e * [exp(-2*a*(r - r_e)) - 2*exp(-a*(r - r_e))] + E_shift
    
    Parameters:
    - D_e: well depth (positive)
    - a: width parameter
    - r_e: equilibrium distance (where minimum occurs)
    - E_shift: energy shift (to account for reference energy)
    
    Minimum occurs at r = r_e with energy = -D_e + E_shift
    """
    return D_e * (np.exp(-2*a*(r - r_e)) - 2*np.exp(-a*(r - r_e))) + E_shift

def residuals(params, R, Etot):
    """Calculate residuals for Morse potential fit"""
    D_e, a, r_e, E_shift = params
    return Etot - morse_potential(R, D_e, a, r_e, E_shift)

def fit_morse_and_find_minimum(R, Etot):
    """Fit Morse potential using Levenberg-Marquardt algorithm"""
    # Initial parameter guesses
    # D_e: approximate well depth (difference between max and min energy)
    D_e_guess = abs(Etot.max() - Etot.min())
    # a: width parameter (guess based on data range)
    a_guess = 1.0 / (R.max() - R.min())
    # r_e: equilibrium distance (guess at middle of data range, or where energy is minimum)
    r_e_guess = R[np.argmin(Etot)]
    # E_shift: shift to match the energy scale
    E_shift_guess = Etot.min() + D_e_guess
    
    params = np.array([D_e_guess, a_guess, r_e_guess, E_shift_guess])
    
    # Simple Levenberg-Marquardt implementation
    lambda_lm = 0.001
    max_iter = 1000
    tolerance = 1e-8
    
    for iteration in range(max_iter):
        # Calculate current residuals and Jacobian
        res = residuals(params, R, Etot)
        chi_sq = np.sum(res**2)
        
        # Numerical Jacobian
        jacobian = np.zeros((len(R), 4))
        eps = 1e-6
        for i in range(4):
            params_plus = params.copy()
            params_plus[i] += eps
            res_plus = residuals(params_plus, R, Etot)
            jacobian[:, i] = (res_plus - res) / eps
        
        # Normal equations: (J^T J + lambda*I) * delta = J^T * res
        JtJ = jacobian.T @ jacobian
        JtR = jacobian.T @ res
        
        # Add damping
        JtJ_damped = JtJ + lambda_lm * np.diag(np.diag(JtJ))
        
        try:
            delta = np.linalg.solve(JtJ_damped, JtR)
        except np.linalg.LinAlgError:
            break
        
        # Update parameters
        params_new = params - delta
        
        # Check if improvement
        res_new = residuals(params_new, R, Etot)
        chi_sq_new = np.sum(res_new**2)
        
        if chi_sq_new < chi_sq:
            params = params_new
            lambda_lm *= 0.1
            if np.linalg.norm(delta) < tolerance:
                break
        else:
            lambda_lm *= 10.0
            if lambda_lm > 1e10:
                break
    
    D_e, a, r_e, E_shift = params
    
    # Calculate minimum energy
    E_min = morse_potential(r_e, D_e, a, r_e, E_shift)
    
    # Calculate R²
    fitted_values = morse_potential(R, D_e, a, r_e, E_shift)
    ss_res = np.sum((Etot - fitted_values)**2)
    ss_tot = np.sum((Etot - np.mean(Etot))**2)
    r_squared = 1 - (ss_res / ss_tot)
    
    # Estimate parameter uncertainties from covariance matrix
    try:
        JtJ_final = jacobian.T @ jacobian
        cov = np.linalg.inv(JtJ_final) * (ss_res / (len(R) - 4))
        errors = np.sqrt(np.diag(cov))
    except:
        errors = None
    
    return r_e, E_min, D_e, a, E_shift, r_squared, params, errors

def main():
    filepath = '/Users/pamco116/Documents/GitHub/EMTO_input_automation/Cu0_Mg100/phase2_sws_optimization/CuMg_sws.out'
    
    print("Parsing data file...")
    R, Etot = parse_data_file(filepath)
    
    print(f"\nFound {len(R)} data points")
    print(f"R range: {R.min():.5f} to {R.max():.5f}")
    print(f"Etot range: {Etot.min():.5f} to {Etot.max():.5f}")
    
    print("\nData points:")
    for i in range(len(R)):
        print(f"  R = {R[i]:8.5f}, Etot = {Etot[i]:12.5f}")
    
    print("\nPerforming Morse potential fit...")
    r_e, E_min, D_e, a, E_shift, r_squared, popt, errors = fit_morse_and_find_minimum(R, Etot)
    
    if r_e is not None:
        print(f"\nMorse potential fit results:")
        print(f"  Well depth (D_e) = {D_e:.6f}")
        print(f"  Width parameter (a) = {a:.6f}")
        print(f"  Equilibrium distance (r_e) = {r_e:.6f}")
        print(f"  Energy shift (E_shift) = {E_shift:.6f}")
        print(f"  R² = {r_squared:.6f}")
        
        print(f"\nMinimum energy:")
        print(f"  R_min = {r_e:.6f}")
        print(f"  E_min = {E_min:.6f} Ry")
        
        # Calculate uncertainties if available
        if errors is not None:
            print(f"\nParameter uncertainties:")
            print(f"  D_e = {D_e:.6f} ± {errors[0]:.6f}")
            print(f"  a = {a:.6f} ± {errors[1]:.6f}")
            print(f"  r_e = {r_e:.6f} ± {errors[2]:.6f}")
            print(f"  E_shift = {E_shift:.6f} ± {errors[3]:.6f}")
        
        # Show fitted values at data points
        print("\nFitted values:")
        for i in range(len(R)):
            fitted = morse_potential(R[i], D_e, a, r_e, E_shift)
            print(f"  R = {R[i]:8.5f}, Etot_actual = {Etot[i]:12.5f}, Etot_fitted = {fitted:12.5f}, diff = {Etot[i]-fitted:12.5f}")
    else:
        print("\nError: Could not fit Morse potential to the data")

if __name__ == '__main__':
    main()
