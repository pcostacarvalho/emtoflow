#!/usr/bin/env python3
"""
Compute Debye phonon energy for Cu-Mg compositions using optimal SWS and bulk
modulus from phase2 EOS output files (*_sws_final.out). Writes Mg% vs phonon
energy and optionally plots the result.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
from scipy.integrate import quad

# Add project root for imports
_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from modules.inputs.eos_emto import parse_eos_output

# Physical constants (SI units)
kB = 1.380649e-23        # J/K
hbar = 1.054571817e-34   # J·s
pi = np.pi

mass_mg = 24.305   # amu
mass_cu = 63.546   # amu

convert_u_to_kg = 1.66053906660e-27
convert_au_to_m = 5.29177210903e-11   # Bohr to m
J_to_meV = 1 / 1.602176634e-22

# Cu-Mg compositions: Cu100_Mg0, Cu90_Mg10, ..., Cu0_Mg100 (Mg 0, 10, ..., 100)
COMPOSITIONS = [
    "Cu100_Mg0", "Cu90_Mg10", "Cu80_Mg20", "Cu70_Mg30",  "Cu74_Mg26", "Cu72_Mg28", "Cu68_Mg32", "Cu66_Mg34",  "Cu64_Mg36", "Cu62_Mg38", "Cu60_Mg40", 
    "Cu50_Mg50", "Cu40_Mg60", "Cu30_Mg70", "Cu20_Mg80", "Cu10_Mg90", "Cu0_Mg100",
]


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


def parse_composition(comp_str):
    """Return (p_cu, p_mg) from e.g. 'Cu90_Mg10' (fractions 0..1)."""
    import re
    m = re.match(r"Cu(\d+)_Mg(\d+)", comp_str, re.IGNORECASE)
    if not m:
        raise ValueError(f"Cannot parse composition: {comp_str}")
    cu_pct = int(m.group(1))
    mg_pct = int(m.group(2))
    if cu_pct + mg_pct != 100:
        raise ValueError(f"Cu+Mg must sum to 100: {comp_str}")
    return cu_pct / 100.0, mg_pct / 100.0


def get_eos_params_from_file(out_path):
    """
    Parse *_sws_final.out and return (r_bohr, B_GPa).
    Prefer 'morse' fit; otherwise use first available EOS.
    """
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
    at each temperature, write Mg% vs phonon energy, and optionally plot.

    base_dir : path to directory containing composition folders (e.g. Cu90_Mg10/)
    id : job/system id used for the EOS output filename (e.g. CuMg -> CuMg_sws_final.out)
    temperatures : list of temperatures in K (e.g. [100, 200, 300, 400])
    Each folder must contain phase2_sws_optimization/{id}_sws_final.out
    """
    if temperatures is None:
        temperatures = [300.0]
    temperatures = sorted(set(float(T) for T in temperatures))

    base_dir = Path(base_dir)
    rows = []
    sws_final_name = f"sws_optimization_results.json"

    for comp in COMPOSITIONS:
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

        p_cu, p_mg = parse_composition(comp)
        mg_pct = p_mg * 100.0
        M_kg = (p_cu * mass_cu + p_mg * mass_mg) * convert_u_to_kg
        r_m = r_bohr * convert_au_to_m
        B_Pa = B_GPa * 1e9

        E_ph_meV_by_T = {}
        for T in temperatures:
            E_ph_J = phonon_energy(r_m, B_Pa, M_kg, T)
            E_ph_meV_by_T[T] = E_ph_J * J_to_meV

        rows.append({
            "composition": comp,
            "mg_percent": mg_pct,
            "r_bohr": r_bohr,
            "B_GPa": B_GPa,
            "phonon_energy_meV_by_T": E_ph_meV_by_T,
        })
        E_str = "  ".join(f"T={T:.0f}K:{E_ph_meV_by_T[T]:.2f}" for T in temperatures)
        print(f"  {comp}: Mg={mg_pct:.0f}%, r={r_bohr:.6f} Bohr, B={B_GPa:.3f} GPa  E_ph(meV): {E_str}")

    if not rows:
        print("No compositions processed. Check base_dir and phase2 *_sws_final.out files.")
        return

    # Default output file
    if output_file is None:
        output_file = base_dir / "phonon_energy_vs_Mg_percent.dat"
    else:
        output_file = Path(output_file)

    # Write table: Mg%, composition, r_bohr, B_GPa, then one column per T
    with open(output_file, "w") as f:
        T_cols = "  ".join(f"E_ph_meV_T{T:.0f}K" for T in temperatures)
        f.write(f"# Mg_percent  composition  r_bohr  B_GPa  {T_cols}\n")
        for r in rows:
            E_cols = "  ".join(f"{r['phonon_energy_meV_by_T'][T]:12.6f}" for T in temperatures)
            f.write(f"{r['mg_percent']:6.1f}  {r['composition']:12s}  {r['r_bohr']:.6f}  {r['B_GPa']:.4f}  {E_cols}\n")

    print(f"\nWrote: {output_file}")

    if plot:
        import matplotlib.pyplot as plt
        mg = [r["mg_percent"] for r in rows]
        fig, ax = plt.subplots(1, 1, figsize=(8, 5))
        for T in temperatures:
            E_ph = [r["phonon_energy_meV_by_T"][T] for r in rows]
            ax.plot(mg, E_ph, "o-", markersize=6, label=f"T = {T:.0f} K")
        ax.set_xlabel("Mg percentage (%)")
        ax.set_ylabel("Phonon energy (meV)")
        ax.set_title("Phonon energy vs Mg percentage (Cu-Mg)")
        ax.legend(loc="best", fontsize=9)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plot_path = output_file.with_suffix(".png")
        plt.savefig(plot_path, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"Plot saved: {plot_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Compute phonon energy for Cu-Mg compositions from phase2 EOS output."
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
        help="Output file for Mg%% vs phonon energy (default: base_dir/phonon_energy_vs_Mg_percent.dat)",
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
