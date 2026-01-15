"""
Equation of State Fitting - Fortran Algorithm Port to Python

This module implements the exact algorithms from the Fortran EOS program
in source/ folder, maintaining the same numerical methods and workflow.

Author: Ported from I.A. Abrikosov's Fortran code
Reference: Condensed Matter Theory Group, Uppsala University
"""

import numpy as np
from scipy.optimize import minimize, minimize_scalar
from scipy.interpolate import CubicSpline
import warnings

# ============================================================================
# Constants (from modules.for)
# ============================================================================

PKBAR = 147107.8  # Conversion factor to kbar
AU_TO_A = 0.529177  # Bohr to Angstrom
RY_TO_EV = 13.6  # Rydberg to eV
PI = np.pi
PI43 = 4.0 / 3.0 * PI
EV_A3_TO_GPA = 160.2176  # eV/A^3 to GPa conversion


# ============================================================================
# Least Squares Polynomial Fitting (from lsfit.for and fitpoln.for)
# ============================================================================

def lsfit_polynomial(volumes, energies, degree):
    """
    Least squares polynomial fit using orthogonal polynomials.

    This implements the LSFIT subroutine from lsfit.for using
    Forsythe orthogonal polynomials for numerical stability.

    Parameters:
    -----------
    volumes : array-like
        Volume data points
    energies : array-like
        Energy data points
    degree : int
        Polynomial degree

    Returns:
    --------
    coeffs : ndarray
        Polynomial coefficients [c0, c1, c2, ..., c_degree]
        where E(V) = c0 + c1*V + c2*V^2 + ... + c_degree*V^degree
    sigma2 : float
        Variance of the fit
    coeff_cov : ndarray
        Covariance matrix of coefficients
    """
    x = np.array(volumes, dtype=np.float64)
    y = np.array(energies, dtype=np.float64)
    n = len(x)
    m = degree + 1  # Number of coefficients

    # Use numpy polyfit with full covariance
    # This is equivalent to the orthogonal polynomial approach in Fortran
    coeffs_poly = np.polyfit(x, y, degree, full=False, cov=True)
    coeffs = coeffs_poly[0][::-1]  # Reverse to match [c0, c1, c2, ...]

    # Calculate residuals
    y_fit = np.polyval(coeffs[::-1], x)
    residuals = y - y_fit
    sigma2 = np.sum(residuals**2) / max(1, n - m)

    # Covariance matrix
    if isinstance(coeffs_poly[1], np.ndarray):
        coeff_cov = coeffs_poly[1][::-1, ::-1]
    else:
        coeff_cov = np.eye(m) * sigma2

    return coeffs, sigma2, coeff_cov


def fit_polynomial(volumes, energies, iuse, degree, v0_guess=None):
    """
    Polynomial fit following FITPOLN subroutine from fitpoln.for

    Parameters:
    -----------
    volumes : array-like
        Volume or Wigner-Seitz radius data
    energies : array-like
        Energy data
    iuse : array-like
        Flags (1=use, 0=skip) for each data point
    degree : int
        Polynomial degree (minimum 3)
    v0_guess : float, optional
        Initial guess for equilibrium volume

    Returns:
    --------
    results : dict
        Dictionary containing:
        - v0: equilibrium volume
        - e0: equilibrium energy
        - b0: bulk modulus (in GPa)
        - b0_prime: pressure derivative of bulk modulus
        - gamma: Gruneisen parameter
        - coeffs: polynomial coefficients
        - rms: RMS error of fit
    """
    # Select points to use
    mask = np.array(iuse, dtype=bool)
    v_use = np.array(volumes)[mask]
    e_use = np.array(energies)[mask]

    # Find approximate V0 from minimum energy
    if v0_guess is None:
        idx_min = np.argmin(e_use)
        v0_guess = v_use[idx_min]

    # Transform to displacement coordinates: v_disp = V - V0
    # This improves numerical stability (fitpoln.for:88)
    v_disp = v_use - v0_guess

    # Fit polynomial
    coeffs, sigma2, coeff_cov = lsfit_polynomial(v_disp, e_use, degree)

    # Find minimum using numerical optimization (fitpoln.for:110)
    # E(v) = sum(coeffs[i] * v^i)
    def poly_eval(v_disp_val):
        return np.polyval(coeffs[::-1], v_disp_val)

    def poly_deriv(v_disp_val):
        """First derivative"""
        if degree == 0:
            return 0.0
        deriv_coeffs = coeffs[1:] * np.arange(1, degree + 1)
        return np.polyval(deriv_coeffs[::-1], v_disp_val)

    def poly_deriv2(v_disp_val):
        """Second derivative"""
        if degree < 2:
            return 0.0
        deriv2_coeffs = coeffs[2:] * np.arange(2, degree + 1) * np.arange(1, degree)
        return np.polyval(deriv2_coeffs[::-1], v_disp_val)

    # Find minimum in displacement coordinates
    v_disp_left = v_disp[0]
    v_disp_right = v_disp[-1]

    result = minimize_scalar(poly_eval, bounds=(v_disp_left, v_disp_right),
                            method='bounded')
    v_disp_eq = result.x
    v_eq = v_disp_eq + v0_guess
    e_eq = result.fun

    # Calculate ground state parameters (fitpoln.for:148-150)
    # Bulk modulus: B = V * d²E/dV²
    d2E_dV2 = poly_deriv2(v_disp_eq)
    b0 = v_eq * d2E_dV2 * EV_A3_TO_GPA  # Convert eV/A^3 to GPa

    # Gruneisen parameter: gamma = -V/(2*B) * dB/dV
    # For polynomial, we calculate from derivatives
    # gamma = -(1/2) * (V/B) * d³E/dV³ / (d²E/dV²) - 1/2
    if degree >= 3:
        deriv3_coeffs = coeffs[3:] * np.arange(3, degree + 1) * np.arange(2, degree) * np.arange(1, degree - 1)
        d3E_dV3 = np.polyval(deriv3_coeffs[::-1], v_disp_eq) if len(deriv3_coeffs) > 0 else 0.0
        gamma = -(v_eq / (2 * d2E_dV2)) * d3E_dV3 / d2E_dV2 - 0.5 if d2E_dV2 != 0 else 0.0
    else:
        gamma = 0.0

    # B' = 2*(gamma + 1)
    b0_prime = 2.0 * (gamma + 1.0)

    # Calculate RMS error
    y_fit = np.polyval(coeffs[::-1], v_disp)
    rms = np.sqrt(np.mean((e_use - y_fit)**2))

    return {
        'v0': v_eq,
        'e0': e_eq,
        'b0': b0,
        'b0_prime': b0_prime,
        'gamma': gamma,
        'coeffs': coeffs,
        'v0_displacement': v0_guess,
        'rms': rms,
        'sigma2': sigma2
    }


# ============================================================================
# Murnaghan EOS (from fitmu37.for)
# ============================================================================

def murnaghan_energy(params, V):
    """
    Murnaghan equation of state energy.

    From fitmu37.for:227-229
    E(V) = E0 + (B0*V0/B') * [(V0/V)^(B'-1)/(B'-1) + V/V0 - B'/(B'-1)]

    Parameters:
    -----------
    params : tuple
        (E0, B0, V0, B_prime)
    V : float or array
        Volume(s)

    Returns:
    --------
    E : float or array
        Energy at volume V
    """
    E0, B0, V0, Bp = params

    term1 = (V0 / V)**(Bp - 1.0) / (Bp - 1.0)
    term2 = V / V0
    term3 = Bp / (Bp - 1.0)

    E = E0 + B0 * V0 / Bp * (term1 + term2 - term3)
    return E


def murnaghan_pressure(params, V):
    """
    Murnaghan pressure (fitmu37.for:235)
    P = (B0/B') * [(V0/V)^B' - 1]
    """
    E0, B0, V0, Bp = params
    P = (B0 / Bp) * ((V0 / V)**Bp - 1.0)
    return P


def murnaghan_bulk_modulus(params, V):
    """
    Murnaghan bulk modulus (fitmu37.for:236)
    B(V) = B0 * (V0/V)^B'
    """
    E0, B0, V0, Bp = params
    B = B0 * (V0 / V)**Bp
    return B


def fit_murnaghan(volumes, energies, iuse, init_guess):
    """
    Fit Murnaghan EOS following FITMU37 subroutine from fitmu37.for

    Only uses compressed data (V < 1.05*V0) as in fitmu37.for:98

    Parameters:
    -----------
    volumes : array-like
        Volume data
    energies : array-like
        Energy data
    iuse : array-like
        Use flags (1=use, 0=skip)
    init_guess : dict
        Initial guesses from polynomial fit:
        - 'v0': equilibrium volume
        - 'e0': equilibrium energy
        - 'b0': bulk modulus (GPa)
        - 'gamma': Gruneisen parameter

    Returns:
    --------
    results : dict
        Fitted parameters and properties
    """
    # Select points to use AND only compressed (fitmu37.for:86-98)
    mask = np.array(iuse, dtype=bool)
    v_all = np.array(volumes)[mask]
    e_all = np.array(energies)[mask]

    # Only use compressed data: V < 1.05*V0 (fitmu37.for:98)
    v0_init = init_guess['v0']
    compressed_mask = v_all <= 1.05 * v0_init

    if np.sum(compressed_mask) < 4:
        warnings.warn("Not enough compressed data points for Murnaghan fit")
        # Use all data as fallback
        v_use = v_all
        e_use = e_all
    else:
        v_use = v_all[compressed_mask]
        e_use = e_all[compressed_mask]

    # Initial parameters (fitmu37.for:76-80)
    # Convert B0 from GPa to eV/A^3
    B0_init = init_guess['b0'] / EV_A3_TO_GPA
    Bp_init = 2.0 * (init_guess['gamma'] + 1.0)
    params_init = [init_guess['e0'], B0_init, v0_init, Bp_init]

    # Fit using least squares (similar to NAG E04FDF)
    def residuals(params):
        E_fit = murnaghan_energy(params, v_use)
        return np.sum((e_use - E_fit)**2)

    # Bounds to ensure physical parameters
    bounds = [
        (init_guess['e0'] - 0.5, init_guess['e0'] + 0.5),  # E0
        (B0_init * 0.5, B0_init * 2.0),  # B0
        (v0_init * 0.9, v0_init * 1.1),  # V0
        (2.0, 8.0)  # B'
    ]

    # Optimize (fitmu37.for:108-111)
    result = minimize(residuals, params_init, method='L-BFGS-B',
                     bounds=bounds, options={'maxiter': 200})

    if not result.success:
        warnings.warn(f"Murnaghan fit did not converge: {result.message}")

    E0_fit, B0_fit, V0_fit, Bp_fit = result.x

    # Convert B0 back to GPa
    B0_fit_gpa = B0_fit * EV_A3_TO_GPA

    # Gruneisen parameter (fitmu37.for:144)
    gamma_fit = 0.5 * Bp_fit - 1.0

    # Calculate RMS error
    E_fit_all = murnaghan_energy(result.x, v_use)
    rms = np.sqrt(np.mean((e_use - E_fit_all)**2))

    # Calculate pressure and bulk modulus at equilibrium
    P0 = murnaghan_pressure(result.x, V0_fit)  # Should be ~0
    B_eq = murnaghan_bulk_modulus(result.x, V0_fit)

    return {
        'v0': V0_fit,
        'e0': E0_fit,
        'b0': B0_fit_gpa,
        'b0_prime': Bp_fit,
        'gamma': gamma_fit,
        'params': result.x,
        'rms': rms,
        'n_points_used': len(v_use),
        'success': result.success
    }


# ============================================================================
# Birch-Murnaghan EOS (from fitbm52.for)
# ============================================================================

def birch_murnaghan_energy(params, V):
    """
    Birch-Murnaghan equation of state (3rd order).

    From fitbm52.for:235-239
    η = V/V0
    ε = 0.5*(1 - η^(-2/3))
    E(V) = E0 + 4.5*B0*V0*ε²*[1 - (B'-4)*ε]

    Parameters:
    -----------
    params : tuple
        (E0, B0, V0, B_prime)
    V : float or array
        Volume(s)

    Returns:
    --------
    E : float or array
        Energy at volume V
    """
    E0, B0, V0, Bp = params

    eta = V / V0
    eta_m23 = eta**(-2.0/3.0)
    epsilon = 0.5 * (1.0 - eta_m23)

    E = E0 + 4.5 * B0 * V0 * epsilon**2 * (1.0 - (Bp - 4.0) * epsilon)
    return E


def birch_murnaghan_pressure(params, V):
    """
    Birch-Murnaghan pressure (fitbm52.for:247-248)
    P = -1.5*B0*(η^(-5/3) - η^(-7/3))*[1 - 1.5*(B'-4)*ε]
    """
    E0, B0, V0, Bp = params

    eta = V / V0
    eta_m23 = eta**(-2.0/3.0)
    eta_m53 = eta_m23 / eta
    eta_m73 = eta_m53 * eta_m23
    epsilon = 0.5 * (1.0 - eta_m23)

    P = -1.5 * B0 * (eta_m53 - eta_m73) * (1.0 - 1.5 * (Bp - 4.0) * epsilon)
    return P


def birch_murnaghan_bulk_modulus(params, V):
    """
    Birch-Murnaghan bulk modulus (fitbm52.for:249-250)
    B(V) = B0*η^(-5/3)*[1 + 0.5*(1-η^(-2/3))*(5 - 3*B' - 13.5*(4-B')*ε)]
    """
    E0, B0, V0, Bp = params

    eta = V / V0
    eta_m23 = eta**(-2.0/3.0)
    eta_m53 = eta_m23 / eta
    epsilon = 0.5 * (1.0 - eta_m23)

    term = 1.0 + 0.5 * (1.0 - eta_m23) * (5.0 - 3.0*Bp - 13.5*(4.0-Bp)*epsilon)
    B = B0 * eta_m53 * term
    return B


def fit_birch_murnaghan(volumes, energies, iuse, init_guess):
    """
    Fit Birch-Murnaghan EOS following FITBM52 subroutine from fitbm52.for

    Only uses compressed data (V < 1.05*V0) as in fitbm52.for:105

    Parameters:
    -----------
    volumes : array-like
        Volume data
    energies : array-like
        Energy data
    iuse : array-like
        Use flags (1=use, 0=skip)
    init_guess : dict
        Initial guesses from polynomial fit

    Returns:
    --------
    results : dict
        Fitted parameters and properties
    """
    # Select points to use AND only compressed (fitbm52.for:92-106)
    mask = np.array(iuse, dtype=bool)
    v_all = np.array(volumes)[mask]
    e_all = np.array(energies)[mask]

    # Only use compressed data: V < 1.05*V0 (fitbm52.for:105)
    v0_init = init_guess['v0']
    compressed_mask = v_all <= 1.05 * v0_init

    if np.sum(compressed_mask) < 4:
        warnings.warn("Not enough compressed data points for Birch-Murnaghan fit")
        v_use = v_all
        e_use = e_all
    else:
        v_use = v_all[compressed_mask]
        e_use = e_all[compressed_mask]

    # Initial parameters (fitbm52.for:81-85)
    B0_init = init_guess['b0'] / EV_A3_TO_GPA
    Bp_init = 2.0 * (init_guess['gamma'] + 1.0)
    params_init = [init_guess['e0'], B0_init, v0_init, Bp_init]

    # Fit using least squares
    def residuals(params):
        E_fit = birch_murnaghan_energy(params, v_use)
        return np.sum((e_use - E_fit)**2)

    # Bounds
    bounds = [
        (init_guess['e0'] - 0.5, init_guess['e0'] + 0.5),  # E0
        (B0_init * 0.5, B0_init * 2.0),  # B0
        (v0_init * 0.9, v0_init * 1.1),  # V0
        (2.0, 8.0)  # B'
    ]

    # Optimize (fitbm52.for:115-119)
    result = minimize(residuals, params_init, method='L-BFGS-B',
                     bounds=bounds, options={'maxiter': 200})

    if not result.success:
        warnings.warn(f"Birch-Murnaghan fit did not converge: {result.message}")

    E0_fit, B0_fit, V0_fit, Bp_fit = result.x
    B0_fit_gpa = B0_fit * EV_A3_TO_GPA
    gamma_fit = 0.5 * Bp_fit - 1.0

    # Calculate RMS error
    E_fit_all = birch_murnaghan_energy(result.x, v_use)
    rms = np.sqrt(np.mean((e_use - E_fit_all)**2))

    return {
        'v0': V0_fit,
        'e0': E0_fit,
        'b0': B0_fit_gpa,
        'b0_prime': Bp_fit,
        'gamma': gamma_fit,
        'params': result.x,
        'rms': rms,
        'n_points_used': len(v_use),
        'success': result.success
    }


# ============================================================================
# Modified Morse EOS (from fitmo88.for)
# ============================================================================

def morse_energy(params, R):
    """
    Modified Morse function energy.

    From fitmo88.for:237
    E(R) = a + b*exp(-λ*R) + c*exp(-2*λ*R)

    Parameters:
    -----------
    params : tuple
        (a, b, c, lambda)
    R : float or array
        Wigner-Seitz radius

    Returns:
    --------
    E : float or array
        Energy at radius R
    """
    a, b, c, lam = params
    x = np.exp(-lam * R)
    E = a + b * x + c * x**2
    return E


def morse_pressure(params, R):
    """
    Modified Morse pressure (fitmo88.for:239)
    P = λ³*exp(-λ*R)*(b + 2c*exp(-λ*R)) / (4π*(λ*R)²) * pkbar
    """
    a, b, c, lam = params
    alx = -lam * R
    x = np.exp(alx)
    twocx = 2.0 * c * x
    P = x * lam**3 * (b + twocx) / (4.0 * PI * alx**2) * PKBAR
    return P


def morse_bulk_modulus(params, R):
    """
    Modified Morse bulk modulus (fitmo88.for:240-241)
    """
    a, b, c, lam = params
    alx = -lam * R
    x = np.exp(alx)
    twocx = 2.0 * c * x

    term1 = (b + 2.0 * twocx) - 2.0 / alx * (b + twocx)
    B = -(x * lam**3) / (12.0 * PI * alx) * term1 * PKBAR
    return B


def fit_morse(volumes, energies, iuse, init_guess):
    """
    Fit Modified Morse EOS following FITMO88 subroutine from fitmo88.for

    Parameters:
    -----------
    volumes : array-like
        Volume data
    energies : array-like
        Energy data
    iuse : array-like
        Use flags
    init_guess : dict
        Initial guesses from polynomial fit

    Returns:
    --------
    results : dict
        Fitted parameters and properties
    """
    # Convert volumes to Wigner-Seitz radii
    mask = np.array(iuse, dtype=bool)
    v_use = np.array(volumes)[mask]
    e_use = np.array(energies)[mask]
    R_use = (v_use / PI43)**(1.0/3.0)

    # Initial guesses (fitmo88.for:72-77)
    R0 = (init_guess['v0'] / PI43)**(1.0/3.0)
    Grun = init_guess['gamma']
    Bmod = init_guess['b0'] / EV_A3_TO_GPA

    # Check for valid Gruneisen parameter
    if Grun <= 0.1:
        # If Gruneisen is too small or negative, use a reasonable default
        warnings.warn(f"Gruneisen parameter from polynomial ({Grun:.3f}) is too small. Using default value 1.5")
        Grun = 1.5

    # Check for valid bulk modulus
    if Bmod <= 0:
        warnings.warn(f"Bulk modulus from polynomial ({Bmod:.3f}) is invalid. Cannot fit Morse EOS.")
        # Return NaN results
        return {
            'v0': np.nan,
            'e0': np.nan,
            'b0': np.nan,
            'b0_prime': np.nan,
            'gamma': np.nan,
            'params': [np.nan, np.nan, np.nan, np.nan],
            'rms': np.nan,
            'success': False
        }

    lam = 2.0 * Grun / R0  # lambda parameter
    alr0 = -lam * R0

    # Check for numerical stability
    if abs(alr0) < 0.01:
        warnings.warn(f"Lambda*R0 is too small ({alr0:.6f}). Cannot fit Morse EOS reliably.")
        return {
            'v0': np.nan,
            'e0': np.nan,
            'b0': np.nan,
            'b0_prime': np.nan,
            'gamma': np.nan,
            'params': [np.nan, np.nan, np.nan, np.nan],
            'rms': np.nan,
            'success': False
        }

    x0 = np.exp(alr0)
    c_init = -Bmod / PKBAR * 6.0 * PI * alr0 / (x0**2 * lam**3)
    b_init = -2.0 * x0 * c_init
    a_init = -b_init * x0 - c_init * x0**2

    params_init = [a_init, b_init, c_init, lam]

    # Check if initial parameters are valid
    if not np.all(np.isfinite(params_init)):
        warnings.warn("Initial parameters for Morse fit contain NaN or Inf. Cannot proceed.")
        return {
            'v0': np.nan,
            'e0': np.nan,
            'b0': np.nan,
            'b0_prime': np.nan,
            'gamma': np.nan,
            'params': [np.nan, np.nan, np.nan, np.nan],
            'rms': np.nan,
            'success': False
        }

    # Fit using least squares
    def residuals(params):
        try:
            E_fit = morse_energy(params, R_use)
            if not np.all(np.isfinite(E_fit)):
                return 1e10  # Large penalty
            return np.sum((e_use - E_fit)**2)
        except:
            return 1e10

    # Optimize (fitmo88.for:100-104)
    try:
        result = minimize(residuals, params_init, method='L-BFGS-B',
                         options={'maxiter': 200})
    except Exception as e:
        warnings.warn(f"Morse optimization failed: {e}")
        return {
            'v0': np.nan,
            'e0': np.nan,
            'b0': np.nan,
            'b0_prime': np.nan,
            'gamma': np.nan,
            'params': [np.nan, np.nan, np.nan, np.nan],
            'rms': np.nan,
            'success': False
        }

    if not result.success:
        warnings.warn(f"Morse fit did not converge: {result.message}")

    a, b, c, lam = result.x

    # Check for valid fitted parameters
    if not np.all(np.isfinite([a, b, c, lam])) or abs(c) < 1e-15:
        warnings.warn("Morse fit produced invalid parameters")
        return {
            'v0': np.nan,
            'e0': np.nan,
            'b0': np.nan,
            'b0_prime': np.nan,
            'gamma': np.nan,
            'params': result.x,
            'rms': np.nan,
            'success': False
        }

    # Calculate equilibrium parameters (fitmo88.for:222-227)
    try:
        x0_eq = -b / (2.0 * c)
        if x0_eq <= 0:
            raise ValueError("x0_eq is non-positive")
        alx0_eq = np.log(x0_eq)
        R_eq = -alx0_eq / lam
        V_eq = PI43 * R_eq**3

        # Ground state energy
        E_eq = a + b * x0_eq + c * x0_eq**2

        # Bulk modulus at equilibrium
        B_eq = -c * x0_eq**2 * lam**3 / (6.0 * PI * alx0_eq) * PKBAR
        B_eq_gpa = B_eq / PKBAR * EV_A3_TO_GPA

        # Gruneisen parameter (fitmo88.for:226)
        gamma_eq = lam * R_eq / 2.0
        Bp_eq = 2.0 * (gamma_eq + 1.0)

        # Calculate RMS error
        E_fit_all = morse_energy(result.x, R_use)
        rms = np.sqrt(np.mean((e_use - E_fit_all)**2))

        return {
            'v0': V_eq,
            'e0': E_eq,
            'b0': B_eq_gpa,
            'b0_prime': Bp_eq,
            'gamma': gamma_eq,
            'params': result.x,
            'rms': rms,
            'success': result.success
        }
    except Exception as e:
        warnings.warn(f"Morse equilibrium calculation failed: {e}")
        return {
            'v0': np.nan,
            'e0': np.nan,
            'b0': np.nan,
            'b0_prime': np.nan,
            'gamma': np.nan,
            'params': result.x,
            'rms': np.nan,
            'success': False
        }


# ============================================================================
# Cubic Spline Interpolation (from fitspln.for)
# ============================================================================

def fit_cubic_spline(volumes, energies, iuse, n_spline=5):
    """
    Fit cubic spline following FITSPLN subroutine from fitspln.for

    Parameters:
    -----------
    volumes : array-like
        Volume data
    energies : array-like
        Energy data
    iuse : array-like
        Use flags
    n_spline : int
        Number of interior knots (default 5)

    Returns:
    --------
    results : dict
        Fitted parameters and properties
    """
    # Select points to use
    mask = np.array(iuse, dtype=bool)
    v_use = np.array(volumes)[mask]
    e_use = np.array(energies)[mask]

    # Create cubic spline (fitspln.for:90-98)
    spline = CubicSpline(v_use, e_use, bc_type='natural')

    # Find minimum (fitspln.for:110-111)
    v_left = v_use[0]
    v_right = v_use[-1]

    result = minimize_scalar(spline, bounds=(v_left, v_right), method='bounded')
    v_eq = result.x
    e_eq = result.fun

    # Calculate derivatives at equilibrium
    dE_dV = spline(v_eq, 1)  # First derivative
    d2E_dV2 = spline(v_eq, 2)  # Second derivative
    d3E_dV3 = spline(v_eq, 3)  # Third derivative

    # Bulk modulus
    b0 = v_eq * d2E_dV2 * EV_A3_TO_GPA

    # Gruneisen parameter
    gamma = -(v_eq / (2 * d2E_dV2)) * d3E_dV3 / d2E_dV2 - 0.5 if d2E_dV2 != 0 else 0.0
    b0_prime = 2.0 * (gamma + 1.0)

    # Calculate RMS error
    e_fit = spline(v_use)
    rms = np.sqrt(np.mean((e_use - e_fit)**2))

    return {
        'v0': v_eq,
        'e0': e_eq,
        'b0': b0,
        'b0_prime': b0_prime,
        'gamma': gamma,
        'spline': spline,
        'rms': rms,
        'success': True
    }


# ============================================================================
# Main EOS Fitting Function (from 0eos.for)
# ============================================================================

def compute_equation_of_state(volumes, energies, eos_type='all',
                              polynomial_order=3, iuse=None,
                              verbose=True):
    """
    Compute equation of state following the exact workflow from 0eos.for

    This is the main function that replicates the Fortran program's logic:
    1. Always run polynomial fit first (provides initial guesses)
    2. Use polynomial results as starting point for other methods
    3. Apply data selection rules (compressed data for Murnaghan/BM)
    4. Cross-validate results between methods

    Parameters:
    -----------
    volumes : array-like
        Volume or lattice parameter values (Å³)
    energies : array-like
        Corresponding energies (eV)
    eos_type : str
        Type of EOS: 'polynomial', 'murnaghan', 'birch_murnaghan',
        'morse', 'spline', or 'all'
    polynomial_order : int
        Polynomial order (minimum 3 for calculating all parameters)
    iuse : array-like, optional
        Flags indicating which points to use (1=use, 0=skip)
        If None, all points are used
    verbose : bool
        Print results

    Returns:
    --------
    results : dict or dict of dicts
        If eos_type='all', returns dict with keys for each method
        Otherwise returns dict with fitted parameters
    """
    volumes = np.array(volumes, dtype=np.float64)
    energies = np.array(energies, dtype=np.float64)

    # Default: use all points
    if iuse is None:
        iuse = np.ones(len(volumes), dtype=int)
    else:
        iuse = np.array(iuse, dtype=int)

    # Ensure minimum polynomial order
    polynomial_order = max(polynomial_order, 3)

    # ========================================================================
    # Step 1: ALWAYS run polynomial fit first (0eos.for:182-188)
    # This provides initial guesses for other methods
    # ========================================================================
    if verbose:
        print("="*70)
        print("POLYNOMIAL FIT (provides initial guesses)")
        print("="*70)

    poly_results = fit_polynomial(volumes, energies, iuse, polynomial_order)

    if verbose:
        print(f"Order: {polynomial_order}")
        print(f"V0 = {poly_results['v0']:.6f} Ų")
        print(f"E0 = {poly_results['e0']:.8f} eV")
        print(f"B0 = {poly_results['b0']:.4f} GPa")
        print(f"B' = {poly_results['b0_prime']:.4f}")
        print(f"γ  = {poly_results['gamma']:.4f}")
        print(f"RMS = {poly_results['rms']:.6e} eV")

    # Use polynomial results as initial guess for other methods
    init_guess = poly_results

    # ========================================================================
    # Step 2: Fit requested EOS type(s)
    # ========================================================================

    if eos_type == 'polynomial':
        return poly_results

    elif eos_type == 'all':
        results = {'polynomial': poly_results}

        # Murnaghan (0eos.for:218-223)
        if verbose:
            print("\n" + "="*70)
            print("MURNAGHAN EOS")
            print("="*70)
        murn_results = fit_murnaghan(volumes, energies, iuse, init_guess)
        results['murnaghan'] = murn_results

        if verbose:
            print(f"V0 = {murn_results['v0']:.6f} Ų")
            print(f"E0 = {murn_results['e0']:.8f} eV")
            print(f"B0 = {murn_results['b0']:.4f} GPa")
            print(f"B' = {murn_results['b0_prime']:.4f}")
            print(f"γ  = {murn_results['gamma']:.4f}")
            print(f"RMS = {murn_results['rms']:.6e} eV")
            print(f"Points used: {murn_results['n_points_used']} (compressed only)")

        # Birch-Murnaghan (0eos.for:200-205)
        if verbose:
            print("\n" + "="*70)
            print("BIRCH-MURNAGHAN EOS")
            print("="*70)
        bm_results = fit_birch_murnaghan(volumes, energies, iuse, init_guess)
        results['birch_murnaghan'] = bm_results

        if verbose:
            print(f"V0 = {bm_results['v0']:.6f} Ų")
            print(f"E0 = {bm_results['e0']:.8f} eV")
            print(f"B0 = {bm_results['b0']:.4f} GPa")
            print(f"B' = {bm_results['b0_prime']:.4f}")
            print(f"γ  = {bm_results['gamma']:.4f}")
            print(f"RMS = {bm_results['rms']:.6e} eV")
            print(f"Points used: {bm_results['n_points_used']} (compressed only)")

        # Modified Morse (0eos.for:191-196)
        if verbose:
            print("\n" + "="*70)
            print("MODIFIED MORSE EOS")
            print("="*70)
        morse_results = fit_morse(volumes, energies, iuse, init_guess)
        results['morse'] = morse_results

        if verbose:
            if morse_results['success'] and np.isfinite(morse_results['v0']):
                print(f"V0 = {morse_results['v0']:.6f} Ų")
                print(f"E0 = {morse_results['e0']:.8f} eV")
                print(f"B0 = {morse_results['b0']:.4f} GPa")
                print(f"B' = {morse_results['b0_prime']:.4f}")
                print(f"γ  = {morse_results['gamma']:.4f}")
                print(f"RMS = {morse_results['rms']:.6e} eV")
            else:
                print("Morse fit failed (see warnings above)")
                print("Note: Morse EOS requires good initial estimates of Gruneisen parameter.")

        # Cubic Spline (0eos.for:209-214)
        if verbose:
            print("\n" + "="*70)
            print("CUBIC SPLINE INTERPOLATION")
            print("="*70)
        spline_results = fit_cubic_spline(volumes, energies, iuse)
        results['spline'] = spline_results

        if verbose:
            print(f"V0 = {spline_results['v0']:.6f} Ų")
            print(f"E0 = {spline_results['e0']:.8f} eV")
            print(f"B0 = {spline_results['b0']:.4f} GPa")
            print(f"B' = {spline_results['b0_prime']:.4f}")
            print(f"γ  = {spline_results['gamma']:.4f}")
            print(f"RMS = {spline_results['rms']:.6e} eV")

        # Cross-validation (0eos.for validation checks)
        if verbose:
            print("\n" + "="*70)
            print("CROSS-VALIDATION")
            print("="*70)
            _cross_validate_results(results)

        return results

    elif eos_type == 'murnaghan':
        if verbose:
            print("\n" + "="*70)
            print("MURNAGHAN EOS")
            print("="*70)
        results = fit_murnaghan(volumes, energies, iuse, init_guess)
        if verbose:
            _print_single_result(results)
        return results

    elif eos_type == 'birch_murnaghan':
        if verbose:
            print("\n" + "="*70)
            print("BIRCH-MURNAGHAN EOS")
            print("="*70)
        results = fit_birch_murnaghan(volumes, energies, iuse, init_guess)
        if verbose:
            _print_single_result(results)
        return results

    elif eos_type == 'morse':
        if verbose:
            print("\n" + "="*70)
            print("MODIFIED MORSE EOS")
            print("="*70)
        results = fit_morse(volumes, energies, iuse, init_guess)
        if verbose:
            _print_single_result(results)
        return results

    elif eos_type == 'spline':
        if verbose:
            print("\n" + "="*70)
            print("CUBIC SPLINE INTERPOLATION")
            print("="*70)
        results = fit_cubic_spline(volumes, energies, iuse)
        if verbose:
            _print_single_result(results)
        return results

    else:
        raise ValueError(f"Unknown eos_type: {eos_type}")


def _print_single_result(results):
    """Helper to print single method results"""
    print(f"V0 = {results['v0']:.6f} Ų")
    print(f"E0 = {results['e0']:.8f} eV")
    print(f"B0 = {results['b0']:.4f} GPa")
    print(f"B' = {results['b0_prime']:.4f}")
    print(f"γ  = {results['gamma']:.4f}")
    print(f"RMS = {results['rms']:.6e} eV")


def _cross_validate_results(results):
    """
    Cross-validate results between methods (0eos.for:140-150 pattern)
    Warns if different methods give significantly different results
    """
    # Use polynomial as reference (it's always computed first)
    ref = results['polynomial']

    print(f"{'Method':<25} {'ΔV0 (%)':<12} {'ΔE0 (%)':<12} {'ΔB0 (%)':<12}")
    print("-"*70)

    for name, res in results.items():
        if name == 'polynomial':
            continue

        # Skip failed methods
        if not res.get('success', True) or not np.isfinite(res['v0']):
            print(f"{name:<25} {'FAILED':<12} {'FAILED':<12} {'FAILED':<12}")
            continue

        dv = abs(res['v0'] - ref['v0']) / ref['v0'] * 100
        de = abs(res['e0'] - ref['e0']) / abs(ref['e0']) * 100
        db = abs(res['b0'] - ref['b0']) / ref['b0'] * 100

        print(f"{name:<25} {dv:<12.2f} {de:<12.4f} {db:<12.2f}")

        # Warnings (following Fortran thresholds)
        if dv > 10:
            print(f"  WARNING: {name} V0 differs >10% from polynomial")
        if db > 20:
            print(f"  WARNING: {name} B0 differs >20% from polynomial")
