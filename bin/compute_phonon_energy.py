#!/usr/bin/env python3
"""
Compute Debye phonon energy for binary compositions (AX_BY format) using optimal
SWS and bulk modulus from phase2 EOS output files (*_sws_final.out). 
Automatically detects compositions in the base directory and uses pymatgen
for atomic mass lookup. Writes element% vs phonon energy and optionally plots.
"""

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
from scipy.integrate import quad
from pymatgen.core import Element

# Add project root for imports
_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from modules.inputs.eos_emto import parse_eos_output

# Physical constants (SI units)
kB = 1.380649e-23        # J/K
hbar = 1.054571817e-34   # J·s
pi = np.pi

convert_u_to_kg = 1.66053906660e-27
convert_au_to_m = 5.29177210903e-11   # Bohr to m
J_to_meV = 1 / 1.602176634e-22


def F_nu(v=1/3):
    """F(v) as defined in Eq. (B.14)."""
    term1 = (2/3) * (2 / (1 - 2*v))**(3/2)
    term2 = (1/3) * (1 / (1 - v))**(3/2)
    prefactor = (3 / (1 + v))**(1/2)
    return prefactor * (term1 + term2)**(-1/3)


def debye_function(x):
    """Debye function D(x)."""
    if x == 0:
        return 0.0
    integrand = lambda y: y**3 / (np.exp(y) - 1)
    integral, _ = quad(integrand, 0, x)
    return 3.0 * integral / x**3


def debye_temperature(r, B, M, v=1/3):
    """
    Debye temperature theta(r).
    r : characteristic radius (m)
    B : bulk modulus (Pa)
    M : atomic mass (kg)
    """
    Fv = F_nu(v)
    prefactor = (4*pi/3)**(-1/6)
    return (hbar / kB) * prefactor * Fv * np.sqrt(r * B / M)


def phonon_energy(r, B, M, T, v=1/3):
    """
    Phonon energy E_ph(r, T) in J.
    T : temperature (K)
    """
    theta = debye_temperature(r, B, M, v)
    x = theta / T
    return 3*kB*T*debye_function(x) + (9/8)*kB*theta


def detect_compositions(base_dir):
    """
    Detect composition folders matching pattern AX_BY in base_dir.
    Returns sorted list of composition strings (e.g., ['Cu100_Mg0', 'Cu90_Mg10', ...]).
    """
    base_dir = Path(base_dir)
    if not base_dir.exists() or not base_dir.is_dir():
        return []
    
    # Pattern: ElementSymbol(s) + number + underscore + ElementSymbol(s) + number
    # E.g., Cu100_Mg0, Fe50_Ni50, Al75_Cu25
    pattern = re.compile(r'^[A-Z][a-z]?\d+_[A-Z][a-z]?\d+$')
    
    compositions = []
    for item in base_dir.iterdir():
        if item.is_dir() and pattern.match(item.name):
            compositions.append(item.name)
    
    # Sort by second element percentage (ascending) for consistent ordering
    def sort_key(comp):
        m = re.match(r'^[A-Z][a-z]?\d+_([A-Z][a-z]?)(\d+)$', comp)
        if m:
            return int(m.group(2))
        return 0
    
    return sorted(compositions, key=sort_key)


def parse_composition(comp_str):
    """
    Parse composition string AX_BY and return (elem1, p1, elem2, p2).
    Returns: (element1_symbol, fraction1, element2_symbol, fraction2)
    Fractions are 0..1.
    """
    m = re.match(r'^([A-Z][a-z]?)(\d+)_([A-Z][a-z]?)(\d+)$', comp_str)
    if not m:
        raise ValueError(f"Cannot parse composition: {comp_str}")
    elem1, pct1, elem2, pct2 = m.groups()
    pct1, pct2 = int(pct1), int(pct2)
    if pct1 + pct2 != 100:
        raise ValueError(f"Percentages must sum to 100: {comp_str} ({pct1}+{pct2}={pct1+pct2})")
    return elem1, pct1 / 100.0, elem2, pct2 / 100.0


def get_atomic_mass(element_symbol):
    """
    Get atomic mass (amu) for element symbol using pymatgen.
    
    Parameters
    ----------
    element_symbol : str
        Element symbol (e.g., 'Cu', 'Mg', 'Fe')
    
    Returns
    -------
    float
        Atomic mass in amu
    
    Raises
    ------
    ValueError
        If element symbol is invalid
    """
    try:
        element = Element(element_symbol)
        return element.atomic_mass
    except Exception as e:
        raise ValueError(f"Invalid element symbol: {element_symbol}. Error: {e}")


def get_eos_params_from_file(out_path):
    """
    Parse EOS results file and return (r_bohr, B_GPa).
    Supports both JSON (sws_optimization_results.json) and .out files.
    Prefer 'morse' fit; otherwise use first available EOS.
    """
    out_path = Path(out_path)
    
    # Handle JSON files
    if out_path.suffix == '.json':
        with open(out_path, 'r') as f:
            data = json.load(f)
        
        # Check for eos_fits in JSON
        if 'eos_fits' not in data:
            raise RuntimeError(f"No 'eos_fits' found in {out_path}")
        
        eos_fits = data['eos_fits']
        if not eos_fits:
            raise RuntimeError(f"No EOS fits found in {out_path}")
        
        # Prefer morse, otherwise use first available
        if 'morse' in eos_fits:
            morse_data = eos_fits['morse']
            r_bohr = morse_data['rwseq']
            # bulk_modulus in JSON is already in GPa
            B_GPa = morse_data['bulk_modulus']
        else:
            # Use first available EOS fit
            first_eos = next(iter(eos_fits.values()))
            r_bohr = first_eos['rwseq']
            B_GPa = first_eos['bulk_modulus']
        
        return r_bohr, B_GPa
    
    # Handle .out files (original behavior)
    else:
        results = parse_eos_output(str(out_path))
        if not results:
            raise RuntimeError(f"No EOS fits found in {out_path}")
        eos = results.get("morse") or next(iter(results.values()))
        r_bohr = eos.rwseq
        # bmod is in kBar; 1 GPa = 10 kBar
        B_GPa = eos.bmod * 0.1
        return r_bohr, B_GPa


def run(base_dir, id="CuMg", temperatures=None, output_file=None, plot=True):
    """
    For each composition, read phase2 {id}_sws_final.out, compute phonon energy
    at each temperature, write element% vs phonon energy, and optionally plot.

    base_dir : path to directory containing composition folders (e.g. Cu90_Mg10/)
    id : job/system id used for the EOS output filename (e.g. CuMg -> CuMg_sws_final.out)
    temperatures : list of temperatures in K (e.g. [100, 200, 300, 400])
    Each folder must contain phase2_sws_optimization/{id}_sws_final.out
    """
    if temperatures is None:
        temperatures = [300.0]
    temperatures = sorted(set(float(T) for T in temperatures))

    base_dir = Path(base_dir)
    
    # Auto-detect compositions
    compositions = detect_compositions(base_dir)
    if not compositions:
        print(f"No composition folders found in {base_dir}")
        print("Expected format: AX_BY (e.g., Cu100_Mg0, Fe50_Ni50)")
        return
    
    print(f"Found {len(compositions)} composition(s): {', '.join(compositions)}")
    
    # Determine element pair from first composition
    elem1, p1, elem2, p2 = parse_composition(compositions[0])
    elem2_name = elem2  # Second element name for percentage axis
    
    rows = []
    sws_final_name = f"sws_optimization_results.json"

    for comp in compositions:
        phase2_dir = base_dir / comp / "phase2_sws_optimization"
        out_file = phase2_dir / sws_final_name

        if not out_file.exists():
            print(f"  Skip {comp}: not found {out_file}")
            continue

        try:
            r_bohr, B_GPa = get_eos_params_from_file(out_file)
        except Exception as e:
            print(f"  Skip {comp}: {e}")
            continue

        try:
            elem1_name, p1, elem2_name, p2 = parse_composition(comp)
            elem2_pct = p2 * 100.0
            
            # Get atomic masses
            mass1 = get_atomic_mass(elem1_name)
            mass2 = get_atomic_mass(elem2_name)
            
            M_kg = (p1 * mass1 + p2 * mass2) * convert_u_to_kg
        except (ValueError, KeyError) as e:
            print(f"  Skip {comp}: {e}")
            continue
        
        r_m = r_bohr * convert_au_to_m
        B_Pa = B_GPa * 1e9

        E_ph_meV_by_T = {}
        for T in temperatures:
            E_ph_J = phonon_energy(r_m, B_Pa, M_kg, T)
            E_ph_meV_by_T[T] = E_ph_J * J_to_meV

        rows.append({
            "composition": comp,
            "elem2_percent": elem2_pct,
            "elem2_name": elem2_name,
            "r_bohr": r_bohr,
            "B_GPa": B_GPa,
            "phonon_energy_meV_by_T": E_ph_meV_by_T,
        })
        E_str = "  ".join(f"T={T:.0f}K:{E_ph_meV_by_T[T]:.2f}" for T in temperatures)
        print(f"  {comp}: {elem2_name}={elem2_pct:.0f}%, r={r_bohr:.6f} Bohr, B={B_GPa:.3f} GPa  E_ph(meV): {E_str}")

    if not rows:
        print("No compositions processed. Check base_dir and phase2 *_sws_final.out files.")
        return

    # Default output file
    if output_file is None:
        output_file = base_dir / f"phonon_energy_vs_{elem2_name}_percent.dat"
    else:
        output_file = Path(output_file)

    # Write table: elem2%, composition, r_bohr, B_GPa, then one column per T
    with open(output_file, "w") as f:
        T_cols = "  ".join(f"E_ph_meV_T{T:.0f}K" for T in temperatures)
        f.write(f"# {elem2_name}_percent  composition  r_bohr  B_GPa  {T_cols}\n")
        for r in rows:
            E_cols = "  ".join(f"{r['phonon_energy_meV_by_T'][T]:12.6f}" for T in temperatures)
            f.write(f"{r['elem2_percent']:6.1f}  {r['composition']:12s}  {r['r_bohr']:.6f}  {r['B_GPa']:.4f}  {E_cols}\n")

    print(f"\nWrote: {output_file}")

    if plot:
        import matplotlib.pyplot as plt
        elem2_pct = [r["elem2_percent"] for r in rows]
        fig, ax = plt.subplots(1, 1, figsize=(8, 5))
        for T in temperatures:
            E_ph = [r["phonon_energy_meV_by_T"][T] for r in rows]
            ax.plot(elem2_pct, E_ph, "o-", markersize=6, label=f"T = {T:.0f} K")
        ax.set_xlabel(f"{elem2_name} percentage (%)")
        ax.set_ylabel("Phonon energy (meV)")
        # Get first element name for title
        elem1_name = rows[0]["composition"].split("_")[0].rstrip("0123456789")
        ax.set_title(f"Phonon energy vs {elem2_name} percentage ({elem1_name}-{elem2_name})")
        ax.legend(loc="best", fontsize=9)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plot_path = output_file.with_suffix(".png")
        plt.savefig(plot_path, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"Plot saved: {plot_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Compute phonon energy for binary compositions (AX_BY format) from phase2 EOS output."
    )
    parser.add_argument(
        "base_dir",
        type=str,
        nargs="?",
        default=".",
        help="Base directory containing composition folders",
    )
    parser.add_argument(
        "-i", "--id",
        type=str,
        default="CuMg",
        metavar="ID",
        help="Job/system ID for EOS file: phase2_sws_optimization/ID_sws_final.out (default: CuMg)",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output file for element%% vs phonon energy (default: base_dir/phonon_energy_vs_{element}_percent.dat)",
    )
    parser.add_argument(
        "-T", "--temperature",
        type=float,
        nargs="+",
        default=[300.0],
        metavar="K",
        help="Temperature(s) in K; can be repeated (default: 300). E.g. -T 100 200 300 400",
    )
    parser.add_argument(
        "--no-plot",
        action="store_true",
        help="Do not generate the plot",
    )
    args = parser.parse_args()

    run(
        base_dir=args.base_dir,
        id=args.id,
        temperatures=args.temperature,
        output_file=args.output,
        plot=not args.no_plot,
    )


if __name__ == "__main__":
    main()
