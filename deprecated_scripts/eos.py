from pymatgen.analysis.eos import EOS
import numpy as np
from utils.file_io import read_file

def compute_equation_of_state(volumes, energies, eos_type='polynomial', order=2):
    """
    Compute equation of state and find equilibrium.
    
    Parameters:
    -----------
    volumes : array-like
        Volume or lattice parameter values
    energies : array-like
        Corresponding energies
    eos_type : str
        Type of EOS: 'polynomial', 'birch_murnaghan', 'murnaghan', or 'all'
    order : int
        Polynomial order (2 or 3), only used if eos_type='polynomial'
    
    Returns:
    --------
    v_eq : float or dict
        Equilibrium volume/parameter (dict if eos_type='all')
    E_eq : float or dict
        Equilibrium energy (dict if eos_type='all')
    eos_fit : coefficients/EOS or dict
        Fitted EOS object or polynomial coefficients (dict if eos_type='all')
    fit_func : callable or dict
        Function that takes volume(s) and returns energy(ies) (dict if eos_type='all')
    """
    
    if eos_type == 'all':
        results = {}
        
        # Polynomial order 2
        print("\n" + "="*50)
        results['poly2'] = compute_equation_of_state(volumes, energies, 'polynomial', order=2)
        
        # Polynomial order 3
        print("\n" + "="*50)
        results['poly3'] = compute_equation_of_state(volumes, energies, 'polynomial', order=3)
        
        # Birch-Murnaghan
        print("\n" + "="*50)
        results['birch_murnaghan'] = compute_equation_of_state(volumes, energies, 'birch_murnaghan')
        
        # Murnaghan
        print("\n" + "="*50)
        results['murnaghan'] = compute_equation_of_state(volumes, energies, 'murnaghan')
        
        print("\n" + "="*50)
        
        return results
    
    if eos_type == 'polynomial':
        coeffs = np.polyfit(volumes, energies, order)
        
        if order == 2:
            a, b, c = coeffs
            v_eq = -b / (2 * a)
        elif order == 3:
            a, b, c, d = coeffs
            discriminant = 4*b**2 - 12*a*c
            
            if discriminant < 0:
                v_eq = volumes[np.argmin(energies)]
            else:
                x1 = (-2*b + np.sqrt(discriminant)) / (6*a)
                x2 = (-2*b - np.sqrt(discriminant)) / (6*a)
                E1 = np.polyval(coeffs, x1)
                E2 = np.polyval(coeffs, x2)
                v_eq = x1 if E1 < E2 else x2
        
        E_eq = np.polyval(coeffs, v_eq)
        fit_func = lambda v: np.polyval(coeffs, v)
        
        print(f"EOS Type: Polynomial (order {order})")
        print(f"Coefficients: {coeffs}")
        print(f"Equilibrium volume/parameter: {v_eq:.6f}")
        print(f"Equilibrium energy: {E_eq:.6f}")
        
        return v_eq, E_eq, coeffs, fit_func
    
    else:
        # Use pymatgen EOS
        eos = EOS(eos_type)
        eos_fit = eos.fit(volumes, energies)
        v_eq = eos_fit.v0
        E_eq = eos_fit.e0
        fit_func = lambda v: eos_fit.func(v)
        
        print(f"EOS Type: {eos_type}")
        print(f"Equilibrium volume/parameter: {v_eq:.6f}")
        print(f"Equilibrium energy: {E_eq:.6f}")
        print(f"Bulk modulus: {eos_fit.b0:.4f}")
        print(f"Bulk modulus derivative: {eos_fit.b1:.4f}")
        
        return v_eq, E_eq, eos_fit, fit_func
    
def parse_energies(ratios, sws, path, id_name):
    energies_lda = {v: [] for v in sws}
    energies_gga = {v: [] for v in sws}
    
    for r in ratios:
        for v in sws:
            try:
                out = read_file(f"{path}/fcd/{id_name}_{r:.2f}_{v:.2f}.prn")
                
                lda_found = False
                gga_found = False
                
                for line in out:
                    if "TOT-LDA" in line and not lda_found:
                        energies_lda[v].append(float(line.split()[1]))
                        lda_found = True
                    
                    if "TOT-GGA" in line and not gga_found:
                        energies_gga[v].append(float(line.split()[1]))
                        gga_found = True
                    
                    # Exit early if both found
                    if lda_found and gga_found:
                        break
                
                # Warn if data missing
                if not lda_found or not gga_found:
                    print(f"Warning: Missing energy data for r={r:.2f}, v={v:.2f}")
                    
            except FileNotFoundError:
                print(f"Warning: File not found for r={r:.2f}, v={v:.2f}")
            except (IndexError, ValueError) as e:
                print(f"Warning: Failed to parse energy for r={r:.2f}, v={v:.2f}: {e}")
    
    # If only one sws value, return flat lists for backward compatibility
    if len(sws) == 1:
        return energies_lda[sws[0]], energies_gga[sws[0]]
    
    # Otherwise return dictionaries keyed by sws value
    return energies_lda, energies_gga