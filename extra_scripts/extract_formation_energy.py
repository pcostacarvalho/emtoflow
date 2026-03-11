#!/usr/bin/env python3
"""
Extract phase 3 energies from EMTO calculations and compute formation energies.
Uses energy per site from fcd calculation outputs.

Supports generic binary alloys A-B:
- Discovery mode: finds all folders named AX_BY (e.g. Cu50_Mg50) and parses composition from the name.
- Single-folder mode: use one folder by name (e.g. TiAg). If the folder name is not AX_BY,
  composition must be provided in the formation energy config YAML.

Config file (e.g. formation_energy_config.yaml):
  element_a: Cu
  element_b: Mg
  reference_energy_a: -3310.060512
  reference_energy_b: -400.662871
  # Optional: single folder to process (otherwise discover all AX_BY in cwd)
  folder: null
  # Required when folder is set and folder name is not AX_BY (e.g. folder: TiAg)
  composition: null   # fractions summing to 1, e.g. [2/3, 1/3], or percentages summing to 100, e.g. [50, 50]
"""

import argparse
import re
import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys

try:
    import yaml
except ImportError:
    yaml = None

from emtoflow.modules.extract_results import parse_kfcd
sys.path.insert(0, str(Path(__file__).parent.parent))
# Default config (Cu-Mg) when no config file is used
DEFAULT_ELEMENT_A = "Cu"
DEFAULT_ELEMENT_B = "Mg"
DEFAULT_E_REF_A = -3310.060512
DEFAULT_E_REF_B = -400.662871
DEFAULT_CONFIG_FILENAME = "formation_energy_config.yaml"


def find_fcd_prn_file(folder_path):
    """
    Find the fcd/prn file in the folder structure.
    Looks in: phase3_optimized_calculation/fcd/*.prn or fcd/*.prn
    """
    folder = Path(folder_path)
    
    # Try phase3_optimized_calculation/fcd/*.prn first
    phase3_fcd = folder / "phase3_optimized_calculation" / "fcd"
    if phase3_fcd.exists():
        prn_files = list(phase3_fcd.glob("*.prn"))
        if prn_files:
            return prn_files[0]  # Return first .prn file found
    
    # Try fcd/*.prn
    fcd_dir = folder / "fcd"
    if fcd_dir.exists():
        prn_files = list(fcd_dir.glob("*.prn"))
        if prn_files:
            return prn_files[0]  # Return first .prn file found
    
    return None


def extract_phase3_energy(folder_path, functional='GGA'):
    """
    Extract total energy and energy per site from fcd/prn file.
    Falls back to workflow_results.json if prn file not found.
    Returns: (total_energy, energy_per_site) or (None, None) if not found
    """
    folder = Path(folder_path)
    
    # First try to get from fcd/prn file
    prn_file = find_fcd_prn_file(folder_path)
    
    if prn_file is not None:
        try:
            results = parse_kfcd(str(prn_file), functional=functional)
            
            total_energy = results.total_energy
            energy_per_site = results.energy_per_site
            
            return total_energy, energy_per_site
            
        except Exception as e:
            print(f"  Error parsing {prn_file}: {e}")
    
    # Fallback: try workflow_results.json
    json_file = folder / "workflow_results.json"
    if json_file.exists():
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            total_energy = data.get('final_energy')
            energy_per_site = data.get('final_energy_per_site')
            
            if energy_per_site is not None:
                return total_energy, energy_per_site
            elif total_energy is not None:
                # If only total energy is available, return it but warn
                print(f"  Warning: Only total energy found in {json_file}, energy per site not available")
                return total_energy, None
                
        except json.JSONDecodeError:
            print(f"  Error: Could not parse JSON in {json_file}")
        except Exception as e:
            print(f"  Error reading {json_file}: {e}")
    
    return None, None


def _ax_by_regex(element_a, element_b):
    """
    Build regex pattern for folder names AX_BY (e.g. Cu50_Mg50, Ag45.2_Mg54.8).
    Supports integer and decimal percentages in the name.
    """
    # Match numbers with optional decimal part: digits or digits.digits
    num_pattern = r"(\d+(?:\.\d+)?)"
    return re.compile(
        r"^" + re.escape(element_a) + num_pattern + r"_" + re.escape(element_b) + num_pattern + r"$"
    )


def folder_matches_ax_by(folder_name, element_a, element_b):
    """Return True if folder name matches AX_BY for the given elements."""
    return _ax_by_regex(element_a, element_b).match(folder_name) is not None


def parse_composition_from_folder(folder_name, element_a, element_b):
    """
    Parse composition from folder name like 'Cu30_Mg70' or 'Ti50_Ag50'.
    Returns: (pct_a, pct_b) or (None, None) if folder name does not match AX_BY.
    """
    m = _ax_by_regex(element_a, element_b).match(folder_name)
    if m:
        pct_a = float(m.group(1))
        pct_b = float(m.group(2))
        # Allow for small rounding differences when decimals are used in names
        if abs(pct_a + pct_b - 100.0) < 1e-6:
            return pct_a, pct_b
    return None, None


def _normalize_composition(composition):
    """
    Accept composition as either fractions (sum ≈ 1, e.g. [2/3, 1/3]) or percentages (sum ≈ 100).
    Returns (pct_a, pct_b) as floats summing to 100.
    """
    if not isinstance(composition, (list, tuple)) or len(composition) != 2:
        raise ValueError("Config 'composition' must be a list of two numbers [x_a, x_b].")
    x_a, x_b = float(composition[0]), float(composition[1])
    total = x_a + x_b
    if abs(total - 1.0) < 0.01:
        # Fractions (e.g. 2/3, 1/3)
        return x_a * 100.0, x_b * 100.0
    if 99.0 <= total <= 101.0:
        # Percentages
        return x_a, x_b
    raise ValueError(
        f"Config 'composition' must sum to 1 (fractions, e.g. [2/3, 1/3]) or to 100 (percentages). Got sum = {total}."
    )


def load_formation_energy_config(config_path):
    """
    Load and validate formation energy config from YAML.
    Returns dict with: element_a, element_b, reference_energy_a, reference_energy_b,
    folder (optional), composition (optional).
    If folder is set and folder name is not AX_BY, composition is required.
    """
    if yaml is None:
        raise RuntimeError("PyYAML is required for config file support. Install with: pip install pyyaml")
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r") as f:
        cfg = yaml.safe_load(f)
    if not cfg or not isinstance(cfg, dict):
        raise ValueError("Config must be a non-empty YAML object.")

    element_a = cfg.get("element_a", DEFAULT_ELEMENT_A)
    element_b = cfg.get("element_b", DEFAULT_ELEMENT_B)
    reference_energy_a = cfg.get("reference_energy_a", DEFAULT_E_REF_A)
    reference_energy_b = cfg.get("reference_energy_b", DEFAULT_E_REF_B)
    folder = cfg.get("folder")
    composition = cfg.get("composition")

    for key, val in [("element_a", element_a), ("element_b", element_b)]:
        if not isinstance(val, str) or not val.strip():
            raise ValueError(f"Config '{key}' must be a non-empty string.")
    for key, val in [("reference_energy_a", reference_energy_a), ("reference_energy_b", reference_energy_b)]:
        if not isinstance(val, (int, float)):
            raise ValueError(f"Config '{key}' must be a number (Ry/site).")

    comp_out = composition
    if folder is not None:
        folder = str(folder).strip()
        folder_basename = Path(folder).name
        if not folder_matches_ax_by(folder_basename, element_a, element_b):
            if composition is None:
                raise ValueError(
                    f"Folder '{folder}' does not match pattern {element_a}X_{element_b}Y (e.g. {element_a}50_{element_b}50). "
                    "You must set 'composition' in the formation energy config YAML (e.g. composition: [50, 50] or [2/3, 1/3])."
                )
            pct_a, pct_b = _normalize_composition(composition)
            comp_out = [pct_a, pct_b]

    return {
        "element_a": element_a.strip(),
        "element_b": element_b.strip(),
        "reference_energy_a": float(reference_energy_a),
        "reference_energy_b": float(reference_energy_b),
        "folder": folder,
        "composition": comp_out,
    }


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Extract phase 3 energies and compute formation energies for binary A-B alloys."
    )
    parser.add_argument(
        "--config", "-c",
        type=str,
        default=None,
        help=f"Path to formation energy config YAML (default: {DEFAULT_CONFIG_FILENAME} in cwd)",
    )
    parser.add_argument("--element-a", type=str, default=None, help="Element A (e.g. Cu)")
    parser.add_argument("--element-b", type=str, default=None, help="Element B (e.g. Mg)")
    parser.add_argument("--E-a", type=float, default=None, help="Reference energy A (Ry/site)")
    parser.add_argument("--E-b", type=float, default=None, help="Reference energy B (Ry/site)")
    parser.add_argument("--folder", type=str, default=None, help="Single folder to process (e.g. TiAg). If not AX_BY, set composition in config.")
    parser.add_argument("--composition", type=str, default=None, help="Composition as pct_a,pct_b (e.g. 50,50). Required if folder is not AX_BY.")
    return parser.parse_args()


def main():
    args = _parse_args()
    current_dir = Path.cwd()

    # Load config: file first, then CLI overrides
    config_path = args.config or current_dir / DEFAULT_CONFIG_FILENAME
    if Path(config_path).exists() and yaml is not None:
        try:
            cfg = load_formation_energy_config(config_path)
        except Exception as e:
            print(f"Error loading config {config_path}: {e}")
            sys.exit(1)
    else:
        cfg = {
            "element_a": DEFAULT_ELEMENT_A,
            "element_b": DEFAULT_ELEMENT_B,
            "reference_energy_a": DEFAULT_E_REF_A,
            "reference_energy_b": DEFAULT_E_REF_B,
            "folder": None,
            "composition": None,
        }

    if args.element_a is not None:
        cfg["element_a"] = args.element_a
    if args.element_b is not None:
        cfg["element_b"] = args.element_b
    if args.E_a is not None:
        cfg["reference_energy_a"] = args.E_a
    if args.E_b is not None:
        cfg["reference_energy_b"] = args.E_b
    if args.folder is not None:
        cfg["folder"] = args.folder
    if args.composition is not None:
        parts = [x.strip() for x in args.composition.split(",")]
        if len(parts) != 2:
            print("Error: --composition must be two numbers separated by comma (e.g. 50,50)")
            sys.exit(1)
        try:
            cfg["composition"] = [float(parts[0]), float(parts[1])]
        except ValueError:
            print("Error: --composition must be two numbers (e.g. 50,50)")
            sys.exit(1)

    # Re-validate: if folder set and not AX_BY, composition required (fractions sum to 1 or percentages sum to 100)
    folder = cfg.get("folder")
    element_a = cfg["element_a"]
    element_b = cfg["element_b"]
    if folder:
        folder_basename = Path(folder).name
        if not folder_matches_ax_by(folder_basename, element_a, element_b):
            if not cfg.get("composition"):
                print(
                    f"Error: Folder '{folder}' does not match pattern {element_a}X_{element_b}Y. "
                    "Set 'composition' in the config YAML (e.g. composition: [50, 50] or [2/3, 1/3]) or use --composition."
                )
                sys.exit(1)
            try:
                pct_a, pct_b = _normalize_composition(cfg["composition"])
                cfg["composition"] = [pct_a, pct_b]
            except ValueError as e:
                print(f"Error: {e}")
                sys.exit(1)

    E_ref_a = cfg["reference_energy_a"]
    E_ref_b = cfg["reference_energy_b"]

    # Resolve folders and (pct_a, pct_b) per folder
    entries = []  # list of (folder_path, pct_a, pct_b)

    if folder is not None:
        folder_path = current_dir / folder if not Path(folder).is_absolute() else Path(folder)
        if not folder_path.is_dir():
            print(f"Error: Folder not found: {folder_path}")
            sys.exit(1)
        folder_basename = folder_path.name
        if folder_matches_ax_by(folder_basename, element_a, element_b):
            pct_a, pct_b = parse_composition_from_folder(folder_basename, element_a, element_b)
        else:
            pct_a, pct_b = cfg["composition"][0], cfg["composition"][1]
        entries.append((folder_path, pct_a, pct_b))
    else:
        pattern = _ax_by_regex(element_a, element_b)
        composition_folders = sorted(
            [d for d in current_dir.iterdir() if d.is_dir() and pattern.match(d.name)]
        )
        if not composition_folders:
            print(f"No composition folders found matching {element_a}X_{element_b}Y (e.g. {element_a}50_{element_b}50)")
            return
        for d in composition_folders:
            pct_a, pct_b = parse_composition_from_folder(d.name, element_a, element_b)
            if pct_a is not None:
                entries.append((d, pct_a, pct_b))

    print("Extracting phase 3 energies from fcd/prn files...")
    print("-" * 60)

    results_per_site = {}   # pct_a -> energy_per_site
    results_total = {}     # pct_a -> total_energy

    def _fmt_pct(p):
        return f"{int(p)}" if abs(p - round(p)) < 1e-9 else f"{p:.4g}"

    for folder_path, pct_a, pct_b in entries:
        total_energy, energy_per_site = extract_phase3_energy(folder_path)
        if energy_per_site is not None:
            results_per_site[pct_a] = energy_per_site
            if total_energy is not None:
                results_total[pct_a] = total_energy
            print(f"{folder_path.name:15s} {element_a}: {_fmt_pct(pct_a)}%  Total: {total_energy:12.6f} Ry  Per site: {energy_per_site:12.6f} Ry/site")
        else:
            print(f"{folder_path.name:15s} {element_a}: {_fmt_pct(pct_a)}%  Energy: NOT FOUND")

    if not results_per_site:
        print("\nNo energies were extracted. Please check the file structure.")
        return

    print("\n" + "=" * 60)
    print("Reference energies (per site):")
    print(f"  E({element_a} 100%) = {E_ref_a:.6f} Ry/site")
    print(f"  E({element_b} 100%) = {E_ref_b:.6f} Ry/site")
    print("=" * 60)

    formation_energies = {}
    print("\nFormation Energies:")
    print("-" * 60)

    for pct_a in sorted(results_per_site.keys()):
        pct_b = 100 - pct_a
        conc_a = pct_a / 100.0
        conc_b = pct_b / 100.0
        E_alloy = results_per_site[pct_a]
        E_form = E_alloy - E_ref_a * conc_a - E_ref_b * conc_b
        formation_energies[pct_a] = E_form
        print(f"{element_a}{_fmt_pct(pct_a)}_{element_b}{_fmt_pct(pct_b)}  E_form = {E_form:12.6f} Ry/site")

    # Output files use "A_percent" in header (generic); support float for exact fractions (e.g. 2/3)
    output_file = "formation_energies.dat"
    with open(output_file, "w") as f:
        f.write(f"# {element_a}_percent  FormationEnergy(Ry/site)\n")
        for pct_a in sorted(formation_energies.keys()):
            f.write(f"{pct_a:10.6f}  {formation_energies[pct_a]:15.8f}\n")
    print(f"\nFormation energies saved to: {output_file}")

    output_file_raw = "energies_raw.dat"
    with open(output_file_raw, "w") as f:
        f.write(f"# {element_a}_percent  EnergyPerSite(Ry/site)  TotalEnergy(Ry)\n")
        for pct_a in sorted(results_per_site.keys()):
            energy_per_site = results_per_site[pct_a]
            total_energy = results_total.get(pct_a)
            if total_energy is not None:
                f.write(f"{pct_a:10.6f}  {energy_per_site:15.8f}  {total_energy:15.8f}\n")
            else:
                f.write(f"{pct_a:10.6f}  {energy_per_site:15.8f}  {'N/A':>15s}\n")
    print(f"Raw energies saved to: {output_file_raw}")

    # Plot
    pct_a_list = np.array(sorted(formation_energies.keys()))
    e_form_values = np.array([formation_energies[p] for p in pct_a_list])

    plt.figure(figsize=(10, 6))
    plt.plot(pct_a_list, e_form_values, "o-", linewidth=2, markersize=8, color="royalblue", label="Formation Energy")
    plt.axhline(y=0, color="gray", linestyle="--", linewidth=1, alpha=0.5)
    plt.xlabel(f"{element_a} Percentage (%)", fontsize=12)
    plt.ylabel("Formation Energy (Ry/site)", fontsize=12)
    plt.title(f"Formation Energy of {element_a}-{element_b} Alloys (per site)", fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=10)
    plt.tight_layout()
    plt.savefig("formation_energy_vs_composition.png", dpi=300)
    print("Plot saved to: formation_energy_vs_composition.png")
    plt.show()


if __name__ == "__main__":
    main()
