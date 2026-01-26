#!/usr/bin/env python3
"""
Parser for equation of state (EOS) fitting output file.
Extracts fitted parameters from different EOS models including:
- Polynomial fit
- Modified Morse EOS
- Birch-Murnaghan EOS
- Cubic spline interpolation
- Murnaghan EOS
"""

import re
from dataclasses import dataclass
from typing import Optional, List, Dict
import sys
import numpy as np


def morse_energy(r, a, b, c, lambda_param):
    """
    Modified Morse equation: E(r) = a + b·exp(-λ·r) + c·exp(-2λ·r)
    Returns RELATIVE energy (needs offset to get absolute energy)
    """

    x = np.exp(-lambda_param * r)
    return a + b * x + c * x * x

def create_eos_input(
    filename,
    job_name,
    comment,
    R_or_V_data,
    Energy_data,
    fit_type="ALL",
):
    """
    Create an FCD input file for EMTO.

    Parameters
    ----------
    filename : str
        Name of the output file (e.g., 'cr50.dat').
    job_name : str
        The job name (e.g., 'cr50').
    comment : str
        Comment line describing the calculation.
    R_or_V_data : list of float
        List of R or V values (first column).
    Energy_data : list of float
        List of energy values (second column).
    fit_type : str
        Type of fit to perform (MO88, MU37, POLN, SPLN, ALL).
    """

    # Validate input lengths match
    if len(R_or_V_data) != len(Energy_data):
        raise ValueError("R_or_V_data and Energy_data must have the same length")

    N_of_Rws = len(R_or_V_data)

    template = f"""DIR_NAME.=
JOB_NAME.={job_name}
COMMENT..: {comment}
FIT_TYPE.={fit_type:<4}       ! Use MO88, MU37, POLN, SPLN, ALL
N_of_Rws..= {N_of_Rws:2d}  Natm_in_uc..=   1 Polinoms_order..=  3 N_spline..=  5
R_or_V....=  R  R_or_V_in...= au. Energy_units....= Ry
"""

    # Add data lines
    for r_or_v, energy in zip(R_or_V_data, Energy_data):
        template += f"  {r_or_v:.6f}     {energy:.6f}  1\n"

    template += """PLOT.....=N
X_axis...=P X_min..=  -100.000 X_max..=  2000.000 N_Xpts.=  40
Y_axes...=V H
"""

    with open(filename, "w") as f:
        f.write(template)

    print(f"EOS input file '{filename}' created successfully.")



@dataclass
class EOSDataPoint:
    """Single data point from EOS fit"""
    r: float  # Wigner-Seitz radius
    etot: float  # Total energy (from calculation)
    efit: float  # Fitted energy
    prs: float  # Pressure


@dataclass
class EOSParameters:
    """Container for equation of state parameters"""
    eos_type: str
    rwseq: float  # Wigner-Seitz radius (au)
    v_eq: float  # Equilibrium volume (au^3)
    eeq: float  # Equilibrium energy (Ry)
    bmod: float  # Bulk modulus (kBar)
    b_prime: float  # Pressure derivative of bulk modulus
    gamma: float  # Gruneisen constant
    fsumsq: float  # Sum of squared residuals
    fit_quality: str  # Assessment of fit quality
    data_points: List[EOSDataPoint] = None  # Data points for plotting
    additional_params: Dict[str, float] = None  # For EOS-specific parameters

    def __str__(self):
        result = f"\n{self.eos_type}\n{'='*60}\n"
        result += f"Fit quality: {self.fit_quality}\n"
        result += f"Sum of squared residuals: {self.fsumsq:.6e}\n\n"
        result += f"Ground state parameters:\n"
        result += f"  Rwseq (Wigner-Seitz radius) = {self.rwseq:16.10f} au\n"
        result += f"  V_eq  (Equilibrium volume)  = {self.v_eq:16.10f} au^3\n"
        result += f"  Eeq   (Equilibrium energy)  = {self.eeq:16.10f} Ry\n"
        result += f"  Bmod  (Bulk modulus)        = {self.bmod:16.10f} kBar\n"
        result += f"  B'    (Pressure derivative) = {self.b_prime:16.10f}\n"
        result += f"  Gamma (Gruneisen constant)  = {self.gamma:16.10f}\n"

        if self.additional_params:
            result += f"\nAdditional parameters:\n"
            for key, value in self.additional_params.items():
                result += f"  {key:10s} = {value:16.10f}\n"

        if self.data_points:
            result += f"\nData points: {len(self.data_points)} points\n"

        return result


def parse_data_points(lines: List[str], start_idx: int) -> List[EOSDataPoint]:
    """Parse data points table (R, Etot, Efit, Prs)"""
    data_points = []

    # Look for data starting after the header line
    i = start_idx
    while i < len(lines):
        line = lines[i].strip()

        # Stop at blank line or new section
        if not line or 'FIT' in line or 'Ground state' in line:
            break

        # Parse data lines: R  Etot  Efit  Prs  Set
        # Example: 2.66000  -78878.79486800  -78878.79579819   2789.98089       1
        parts = line.split()
        if len(parts) >= 4:
            try:
                r = float(parts[0])
                etot = float(parts[1])
                efit = float(parts[2])
                prs = float(parts[3])
                data_points.append(EOSDataPoint(r=r, etot=etot, efit=efit, prs=prs))
            except ValueError:
                pass  # Skip lines that don't parse as numbers

        i += 1

    return data_points


def parse_polynomial_fit(lines: List[str], start_idx: int) -> Optional[EOSParameters]:
    """Parse polynomial fit section"""
    params = {}
    coefficients = {}
    fsumsq = None
    data_points = []

    i = start_idx

    # First, find and parse the data table
    for j in range(start_idx, min(start_idx + 20, len(lines))):
        if 'R           Etot             Efit            Prs' in lines[j]:
            data_points = parse_data_points(lines, j + 1)
            break

    while i < len(lines):
        line = lines[i]

        # Check for end of section
        if 'Equation_of_state fitted by' in line and i > start_idx:
            break

        # Extract fsumsq
        if 'FITPOLN:' in line and 'fsumsq' in line:
            match = re.search(r'fsumsq=\s*([\d.E+-]+)', line)
            if match:
                fsumsq = float(match.group(1))
                match_order = re.search(r'Order\s*=\s*(\d+)', line)
                if match_order:
                    params['order'] = int(match_order.group(1))

        # Extract ground state parameters
        if 'Rwseq' in line and '=' in line:
            match = re.search(r'=\s*([\d.+-]+)', line)
            if match:
                params['rwseq'] = float(match.group(1))
        elif 'V_eq' in line and '=' in line:
            match = re.search(r'=\s*([\d.+-]+)', line)
            if match:
                params['v_eq'] = float(match.group(1))
        elif 'Eeq' in line and '=' in line:
            match = re.search(r'=\s*([\d.E+-]+)', line)
            if match:
                params['eeq'] = float(match.group(1))
        elif 'Bmod' in line and '=' in line:
            match = re.search(r'=\s*([\d.+-]+)', line)
            if match:
                params['bmod'] = float(match.group(1))
        elif "B'" in line and '=' in line:
            match = re.search(r'=\s*([\d.+-]+)', line)
            if match:
                params['b_prime'] = float(match.group(1))
        elif 'Gamma' in line and '=' in line:
            match = re.search(r'=\s*([\d.+-]+)', line)
            if match:
                params['gamma'] = float(match.group(1))

        # Extract polynomial coefficients
        if 'C(' in line:
            match = re.search(r'C\(\s*(\d+)\)\s*=\s*([\d.E+-]+)', line)
            if match:
                coefficients[f'C({match.group(1)})'] = float(match.group(2))
        elif 'E(' in line:
            match = re.search(r'E\(\s*(\d+)\)\s*=\s*([\d.E+-]+)', line)
            if match:
                coefficients[f'E({match.group(1)})'] = float(match.group(2))
        elif 'V(' in line:
            match = re.search(r'V\(\s*(\d+)\)\s*=\s*([\d.E+-]+)', line)
            if match:
                coefficients[f'V({match.group(1)})'] = float(match.group(2))

        i += 1

    if all(k in params for k in ['rwseq', 'v_eq', 'eeq', 'bmod', 'b_prime', 'gamma']):
        coefficients.update({'order': params.get('order', 'N/A')})
        return EOSParameters(
            eos_type='Polynomial Fit',
            rwseq=params['rwseq'],
            v_eq=params['v_eq'],
            eeq=params['eeq'],
            bmod=params['bmod'],
            b_prime=params['b_prime'],
            gamma=params['gamma'],
            fsumsq=fsumsq if fsumsq else 0.0,
            fit_quality='Warning: Bulk modulus may be unreliable',
            data_points=data_points if data_points else None,
            additional_params=coefficients
        )
    return None


def parse_morse_fit(lines: List[str], start_idx: int) -> Optional[EOSParameters]:
    """Parse modified Morse EOS section"""
    params = {}
    morse_params = {}
    fsumsq = None
    ifail = None
    data_points = []

    i = start_idx

    # First, find and parse the data table
    for j in range(start_idx, min(start_idx + 20, len(lines))):
        if 'R           Etot             Efit            Prs' in lines[j]:
            data_points = parse_data_points(lines, j + 1)
            break

    while i < len(lines):
        line = lines[i]

        # Check for end of section
        if 'Equation_of_state fitted by' in line and i > start_idx:
            break

        # Extract fsumsq and ifail
        if 'FITMO88:' in line and 'fsumsq' in line:
            match = re.search(r'fsumsq=\s*([\d.E+-]+)', line)
            if match:
                fsumsq = float(match.group(1))
            match_ifail = re.search(r'IFAIL\s*=\s*(\d+)', line)
            if match_ifail:
                ifail = int(match_ifail.group(1))

        # Extract ground state parameters (handle NaN values)
        if 'Rwseq' in line and '=' in line:
            match = re.search(r'=\s*([\d.Na+-]+)', line, re.IGNORECASE)
            if match:
                val_str = match.group(1).strip()
                params['rwseq'] = float('nan') if val_str.upper() == 'NAN' else float(val_str)
        elif 'V_eq' in line and '=' in line:
            match = re.search(r'=\s*([\d.Na+-]+)', line, re.IGNORECASE)
            if match:
                val_str = match.group(1).strip()
                params['v_eq'] = float('nan') if val_str.upper() == 'NAN' else float(val_str)
        elif 'Eeq' in line and '=' in line:
            match = re.search(r'=\s*([\d.ENa+-]+)', line, re.IGNORECASE)
            if match:
                val_str = match.group(1).strip()
                params['eeq'] = float('nan') if val_str.upper() == 'NAN' else float(val_str)
        elif 'Bmod' in line and '=' in line:
            match = re.search(r'=\s*([\d.Na+-]+)', line, re.IGNORECASE)
            if match:
                val_str = match.group(1).strip()
                params['bmod'] = float('nan') if val_str.upper() == 'NAN' else float(val_str)
        elif "B'" in line and '=' in line:
            match = re.search(r'=\s*([\d.Na+-]+)', line, re.IGNORECASE)
            if match:
                val_str = match.group(1).strip()
                params['b_prime'] = float('nan') if val_str.upper() == 'NAN' else float(val_str)
        elif 'Gamma' in line and '=' in line:
            match = re.search(r'=\s*([\d.Na+-]+)', line, re.IGNORECASE)
            if match:
                val_str = match.group(1).strip()
                params['gamma'] = float('nan') if val_str.upper() == 'NAN' else float(val_str)

        # Extract Morse-specific parameters
        if 'a        =' in line:
            match = re.search(r'=\s*([\d.E+-]+)', line)
            if match:
                morse_params['a'] = float(match.group(1))
        elif 'b        =' in line:
            match = re.search(r'=\s*([\d.E+-]+)', line)
            if match:
                morse_params['b'] = float(match.group(1))
        elif 'c        =' in line:
            match = re.search(r'=\s*([\d.E+-]+)', line)
            if match:
                morse_params['c'] = float(match.group(1))
        elif 'lambda   =' in line:
            match = re.search(r'=\s*([\d.E+-]+)', line)
            if match:
                morse_params['lambda'] = float(match.group(1))

        i += 1

    if all(k in params for k in ['rwseq', 'v_eq', 'eeq', 'bmod', 'b_prime', 'gamma']):
        quality = 'Good' if ifail == 0 else f'Warning: IFAIL={ifail}'
        return EOSParameters(
            eos_type='Modified Morse EOS',
            rwseq=params['rwseq'],
            v_eq=params['v_eq'],
            eeq=params['eeq'],
            bmod=params['bmod'],
            b_prime=params['b_prime'],
            gamma=params['gamma'],
            fsumsq=fsumsq if fsumsq else 0.0,
            fit_quality=quality,
            data_points=data_points if data_points else None,
            additional_params=morse_params
        )
    return None


def parse_birch_murnaghan_fit(lines: List[str], start_idx: int) -> Optional[EOSParameters]:
    """Parse Birch-Murnaghan EOS section"""
    params = {}
    fsumsq = None
    ifail = None
    data_points = []

    i = start_idx

    # First, find and parse the data table
    for j in range(start_idx, min(start_idx + 20, len(lines))):
        if 'R           Etot             Efit            Prs' in lines[j]:
            data_points = parse_data_points(lines, j + 1)
            break

    while i < len(lines):
        line = lines[i]

        # Check for end of section
        if 'Equation_of_state fitted by' in line and i > start_idx:
            break

        # Extract fsumsq and ifail
        if 'FITBM52:' in line and 'fsumsq' in line:
            match = re.search(r'fsumsq=\s*([\d.E+-]+)', line)
            if match:
                fsumsq = float(match.group(1))
            match_ifail = re.search(r'IFAIL\s*=\s*(\d+)', line)
            if match_ifail:
                ifail = int(match_ifail.group(1))

        # Extract ground state parameters
        if 'Rwseq' in line and '=' in line:
            match = re.search(r'=\s*([\d.+-]+)', line)
            if match:
                params['rwseq'] = float(match.group(1))
        elif 'V_eq' in line and '=' in line:
            match = re.search(r'=\s*([\d.+-]+)', line)
            if match:
                params['v_eq'] = float(match.group(1))
        elif 'Eeq' in line and '=' in line:
            match = re.search(r'=\s*([\d.E+-]+)', line)
            if match:
                params['eeq'] = float(match.group(1))
        elif 'Bmod' in line and '=' in line:
            match = re.search(r'=\s*([\d.+-]+)', line)
            if match:
                params['bmod'] = float(match.group(1))
        elif "B'" in line and '=' in line:
            match = re.search(r'=\s*([\d.+-]+)', line)
            if match:
                params['b_prime'] = float(match.group(1))
        elif 'Gamma' in line and '=' in line:
            match = re.search(r'=\s*([\d.+-]+)', line)
            if match:
                params['gamma'] = float(match.group(1))

        i += 1

    if all(k in params for k in ['rwseq', 'v_eq', 'eeq', 'bmod', 'b_prime', 'gamma']):
        quality = 'Poor - parameters differ significantly from polynomial fit' if ifail != 0 else 'Good'
        return EOSParameters(
            eos_type='Birch-Murnaghan EOS',
            rwseq=params['rwseq'],
            v_eq=params['v_eq'],
            eeq=params['eeq'],
            bmod=params['bmod'],
            b_prime=params['b_prime'],
            gamma=params['gamma'],
            fsumsq=fsumsq if fsumsq else 0.0,
            fit_quality=quality,
            data_points=data_points if data_points else None,
            additional_params={'IFAIL': ifail} if ifail is not None else None
        )
    return None


def parse_spline_fit(lines: List[str], start_idx: int) -> Optional[EOSParameters]:
    """Parse cubic spline interpolation section"""
    params = {}
    fsumsq = None
    ncap = None
    data_points = []

    i = start_idx

    # First, find and parse the data table
    for j in range(start_idx, min(start_idx + 20, len(lines))):
        if 'R           Etot             Efit            Prs' in lines[j]:
            data_points = parse_data_points(lines, j + 1)
            break

    while i < len(lines):
        line = lines[i]

        # Check for end of section
        if 'Equation_of_state fitted by' in line and i > start_idx:
            break

        # Extract fsumsq and ncap
        if 'FITSPLN:' in line and 'fsumsq' in line:
            match = re.search(r'fsumsq=\s*([\d.E+-]+)', line)
            if match:
                fsumsq = float(match.group(1))
            match_ncap = re.search(r'NCAP\+3\s*=\s*(\d+)', line)
            if match_ncap:
                ncap = int(match_ncap.group(1))

        # Extract ground state parameters
        if 'Rwseq' in line and '=' in line:
            match = re.search(r'=\s*([\d.+-]+)', line)
            if match:
                params['rwseq'] = float(match.group(1))
        elif 'V_eq' in line and '=' in line:
            match = re.search(r'=\s*([\d.+-]+)', line)
            if match:
                params['v_eq'] = float(match.group(1))
        elif 'Eeq' in line and '=' in line:
            match = re.search(r'=\s*([\d.E+-]+)', line)
            if match:
                params['eeq'] = float(match.group(1))
        elif 'Bmod' in line and '=' in line:
            match = re.search(r'=\s*([\d.+-]+)', line)
            if match:
                params['bmod'] = float(match.group(1))
        elif "B'" in line and '=' in line:
            match = re.search(r'=\s*([\d.+-]+)', line)
            if match:
                params['b_prime'] = float(match.group(1))
        elif 'Gamma' in line and '=' in line:
            match = re.search(r'=\s*([\d.+-]+)', line)
            if match:
                params['gamma'] = float(match.group(1))

        i += 1

    if all(k in params for k in ['rwseq', 'v_eq', 'eeq', 'bmod', 'b_prime', 'gamma']):
        return EOSParameters(
            eos_type='Cubic Spline Interpolation',
            rwseq=params['rwseq'],
            v_eq=params['v_eq'],
            eeq=params['eeq'],
            bmod=params['bmod'],
            b_prime=params['b_prime'],
            gamma=params['gamma'],
            fsumsq=fsumsq if fsumsq else 0.0,
            fit_quality='Good',
            data_points=data_points if data_points else None,
            additional_params={'NCAP+3': ncap} if ncap is not None else None
        )
    return None


def parse_murnaghan_fit(lines: List[str], start_idx: int) -> Optional[EOSParameters]:
    """Parse Murnaghan EOS section"""
    params = {}
    fsumsq = None
    ifail = None
    data_points = []

    i = start_idx

    # First, find and parse the data table
    for j in range(start_idx, min(start_idx + 20, len(lines))):
        if 'R           Etot             Efit            Prs' in lines[j]:
            data_points = parse_data_points(lines, j + 1)
            break

    while i < len(lines):
        line = lines[i]

        # Check for end of section (end of file for Murnaghan)
        if i > start_idx + 50:  # Reasonable limit
            break

        # Extract fsumsq and ifail
        if 'FITMU37:' in line and 'fsumsq' in line:
            match = re.search(r'fsumsq=\s*([\d.E+-]+)', line)
            if match:
                fsumsq = float(match.group(1))
            match_ifail = re.search(r'IFAIL\s*=\s*(\d+)', line)
            if match_ifail:
                ifail = int(match_ifail.group(1))

        # Extract ground state parameters
        if 'Rwseq' in line and '=' in line:
            match = re.search(r'=\s*([\d.+-]+)', line)
            if match:
                params['rwseq'] = float(match.group(1))
        elif 'V_eq' in line and '=' in line:
            match = re.search(r'=\s*([\d.+-]+)', line)
            if match:
                params['v_eq'] = float(match.group(1))
        elif 'Eeq' in line and '=' in line:
            match = re.search(r'=\s*([\d.E+-]+)', line)
            if match:
                params['eeq'] = float(match.group(1))
        elif 'Bmod' in line and '=' in line:
            match = re.search(r'=\s*([\d.+-]+)', line)
            if match:
                params['bmod'] = float(match.group(1))
        elif "B'" in line and '=' in line:
            match = re.search(r'=\s*([\d.+-]+)', line)
            if match:
                params['b_prime'] = float(match.group(1))
        elif 'Gamma' in line and '=' in line:
            match = re.search(r'=\s*([\d.+-]+)', line)
            if match:
                params['gamma'] = float(match.group(1))

        i += 1

    if all(k in params for k in ['rwseq', 'v_eq', 'eeq', 'bmod', 'b_prime', 'gamma']):
        quality = 'Poor - parameters differ significantly from polynomial fit' if ifail != 0 else 'Good'
        return EOSParameters(
            eos_type='Murnaghan EOS',
            rwseq=params['rwseq'],
            v_eq=params['v_eq'],
            eeq=params['eeq'],
            bmod=params['bmod'],
            b_prime=params['b_prime'],
            gamma=params['gamma'],
            fsumsq=fsumsq if fsumsq else 0.0,
            fit_quality=quality,
            data_points=data_points if data_points else None,
            additional_params={'IFAIL': ifail} if ifail is not None else None
        )
    return None


def parse_eos_output(filename: str) -> Dict[str, EOSParameters]:
    """Parse the entire EOS output file"""
    with open(filename, 'r') as f:
        lines = f.readlines()

    results = {}

    for i, line in enumerate(lines):
        if 'Equation_of_state fitted by the polinomial fit' in line:
            params = parse_polynomial_fit(lines, i)
            if params:
                results['polynomial'] = params

        elif 'Equation_of_state fitted by the modified Morse EOS' in line:
            params = parse_morse_fit(lines, i)
            if params:
                results['morse'] = params

        elif 'Equation_of_state fitted by the Birch-Murnaghan EOS' in line:
            params = parse_birch_murnaghan_fit(lines, i)
            if params:
                results['birch_murnaghan'] = params

        elif 'Equation_of_state fitted by the cubic spline interpolation' in line:
            params = parse_spline_fit(lines, i)
            if params:
                results['spline'] = params

        elif 'Equation_of_state fitted by the Murnaghan EOS' in line:
            params = parse_murnaghan_fit(lines, i)
            if params:
                results['murnaghan'] = params

    return results


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python parse_eos_output.py <output_file>")
        print("Example: python parse_eos_output.py fept.out")
        sys.exit(1)

    filename = sys.argv[1]

    try:
        results = parse_eos_output(filename)

        if not results:
            print("No EOS parameters found in the output file.")
            sys.exit(1)

        print("\n" + "="*60)
        print("EQUATION OF STATE FITTING RESULTS")
        print("="*60)

        # Print all results
        for key, params in results.items():
            print(params)

        # Summary and recommendations
        print("\n" + "="*60)
        print("SUMMARY AND RECOMMENDATIONS")
        print("="*60)

        # Identify best fit (lowest fsumsq)
        best_fit = min(results.items(), key=lambda x: x[1].fsumsq)
        print(f"\nBest fit (lowest residual): {best_fit[1].eos_type}")
        print(f"  fsumsq = {best_fit[1].fsumsq:.6e}")

        # Show recommended values
        if 'morse' in results:
            print("\nRecommended parameters (Modified Morse EOS):")
            morse = results['morse']
            print(f"  Equilibrium volume: {morse.v_eq:.6f} au^3")
            print(f"  Equilibrium energy: {morse.eeq:.6f} Ry")
            print(f"  Bulk modulus:       {morse.bmod:.2f} kBar")
            print(f"  Wigner-Seitz R:     {morse.rwseq:.6f} au")

    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error parsing file: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
