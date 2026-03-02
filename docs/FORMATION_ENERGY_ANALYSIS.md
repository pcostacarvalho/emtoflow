# Formation Energy Analysis

This document describes the scripts for extracting and analyzing formation energies from EMTO alloy calculations.

## Overview

The formation energy analysis tools work for **generic binary alloys A-B**. They extract phase 3 total energies and compute formation energies using:
«
```
E_form(A_x, B_{1-x}) = E(A_x, B_{1-x}) - x*E(A) - (1-x)*E(B)
```

where:
- `E(A_x, B_{1-x})` is the energy per site of the alloy
- `E(A)`, `E(B)` are the reference energies per site of pure A and B (Ry/site)
- `x` is the concentration of element A (between 0 and 1)

**Modes:**
- **Discovery mode:** Script finds all subfolders named **AX_BY** (e.g. `Cu50_Mg50`, `Fe30_Ni70`) and parses composition from the folder name.
- **Single-folder mode:** You set a specific folder (e.g. `TiAg` or `TiAg_fcc`). If the folder name is **not** in the form AX_BY, you **must** provide **composition** in the config YAML (e.g. `composition: [50, 50]`).

---

## How to use the script

### Option 1: Many compositions (folders named AX_BY)

1. Put your run directory where each composition has its own subfolder named like `Cu50_Mg50`, `Cu60_Mg40`, etc. (element symbols + percentages that sum to 100).

2. In that directory, create `formation_energy_config.yaml` with your elements and reference energies (Ry/site):
   ```yaml
   element_a: Cu
   element_b: Mg
   reference_energy_a: -3310.060512
   reference_energy_b: -400.662871
   # folder and composition left null → discovery mode
   folder: null
   composition: null
   ```

3. Run the script from that directory:
   ```bash
   cd /path/to/CuMg_fcc
   python /path/to/EMTO_input_automation/bin/extract_formation_energy.py
   ```
   If you don’t create a config file, the script uses Cu–Mg defaults and looks for `Cu*_Mg*` folders.

4. Outputs (in the same directory): `formation_energies.dat`, `energies_raw.dat`, and `formation_energy_vs_composition.png`.

---

### Option 2: One folder whose name is not AX_BY (e.g. TiAg)

1. Put the folder to process in the current directory (e.g. a folder named `TiAg` or `TiAg_fcc`).

2. Create `formation_energy_config.yaml` with elements, reference energies, **folder** name, and **composition** (required when the folder name is not AX_BY):
   ```yaml
   element_a: Ti
   element_b: Ag
   reference_energy_a: -1234.0    # your pure Ti energy/site (Ry)
   reference_energy_b: -567.0     # your pure Ag energy/site (Ry)
   folder: TiAg
   composition: [50, 50]          # 50% Ti, 50% Ag; must sum to 100
   ```

3. Run the script:
   ```bash
   cd /path/to/parent_of_TiAg
   python /path/to/EMTO_input_automation/bin/extract_formation_energy.py
   ```
   Or point to the config explicitly:
   ```bash
   python /path/to/EMTO_input_automation/bin/extract_formation_energy.py --config formation_energy_config.yaml
   ```

4. Outputs: one row in `formation_energies.dat` and `energies_raw.dat`, and a one-point plot in `formation_energy_vs_composition.png`.

---

### Command-line overrides

You can override config values without editing the YAML:

```bash
python bin/extract_formation_energy.py --config formation_energy_config.yaml
python bin/extract_formation_energy.py --element-a Ti --element-b Ag --E-a -1234.0 --E-b -567.0
python bin/extract_formation_energy.py --folder TiAg --composition 50,50
```

Use `--config` to point to a config file in another location.

---

## Formation energy config (YAML)

The Python script reads `formation_energy_config.yaml` from the current directory (or a path given with `--config`). If the file is missing, it defaults to Cu–Mg with built-in reference energies.

**Required (or defaults):** `element_a`, `element_b`, `reference_energy_a`, `reference_energy_b` (Ry/site).

**Optional:**
- **folder:** Name of a single folder to process (e.g. `TiAg`). If omitted, the script discovers all subfolders matching AX_BY.
- **composition:** List of two numbers. **Required when `folder` is set and the folder name is not in the form AX_BY** (e.g. folder `TiAg`). You can use either **fractions that sum to 1** (e.g. `[0.6666666667, 0.3333333333]` or `[2/3, 1/3]` in YAML if your parser supports it) or **percentages that sum to 100** (e.g. `[50, 50]`).

Example for a single folder not named AX_BY:
```yaml
element_a: Ti
element_b: Ag
reference_energy_a: -1234.0
reference_energy_b: -567.0
folder: TiAg
composition: [50, 50]   # required when folder is not Ti50_Ag50 etc.
```

See `docs/formation_energy_config_example.yaml` for full examples.

## Scripts

### 1. Python Script (Recommended)

**File:** `bin/extract_formation_energy.py`

This script extracts phase 3 energies, calculates formation energies, and generates plots. It supports generic A–B alloys via config and optional single-folder mode.

**Usage:**
```bash
cd /path/to/your_run   # Directory containing AX_BY subfolders, or place formation_energy_config.yaml here
python extract_formation_energy.py
# Or with explicit config:
python extract_formation_energy.py --config formation_energy_config.yaml
# Single folder (e.g. TiAg); composition must be in config if folder name is not AX_BY:
python extract_formation_energy.py --config formation_energy_config.yaml
```

**Output:**
- `energies_raw.dat` - Raw energies per site (and total) for each composition
- `formation_energies.dat` - Formation energies (Ry/site)
- `formation_energy_vs_composition.png` - Plot of formation energy vs element A percentage

**Requirements:**
- Python 3.6+
- numpy
- matplotlib

### 2. Bash Script

**File:** `bin/extract_formation_energy.sh`

A bash-only alternative that extracts energies and calculates formation energies without Python dependencies.

**Usage:**
```bash
cd /path/to/CuMg_fcc
bash extract_formation_energy.sh
```

**Output:**
- `energies_raw.dat` - Raw total energies
- `formation_energies.dat` - Formation energies

To plot after running the bash script:
```bash
python plot_formation_energy.py
```

### 3. Plotting Script

**File:** `bin/plot_formation_energy.py`

Standalone plotting script for data generated by either extraction method.

**Usage:**
```bash
# Plot formation energies
python plot_formation_energy.py

# Plot raw total energies
python plot_formation_energy.py --raw
```

## Directory Structure

The scripts expect a directory structure like:

```
CuMg_fcc/
├── Cu0_Mg100/
│   ├── workflow_results.json
│   └── ...
├── Cu10_Mg90/
│   ├── workflow_results.json
│   └── ...
├── Cu20_Mg80/
├── ...
├── Cu100_Mg0/
└── ...
```

## Energy Extraction

The scripts read the final energy from `workflow_results.json` files in each composition folder.

Expected JSON structure:
```json
{
  "job_name": "CuMg",
  "optimal_ca": 1.0,
  "optimal_sws": 2.7033254965,
  "phases_completed": ["phase2_sws_optimization", "phase3_optimized_calculation", "dos_analysis"],
  "final_energy": -3310.060502,
  "structure_info": {
    "lattice_type": 2,
    "lattice_name": "Face-centered cubic",
    "num_atoms": 1
  }
}
```

The scripts look for the `final_energy` field, which contains the optimized total energy in Rydberg units.

## Output Format

Column headers use the first element symbol (e.g. `Cu_percent` for Cu–Mg). For a generic A–B run they will show `A_percent`.

### energies_raw.dat
```
# Cu_percent  EnergyPerSite(Ry/site)  TotalEnergy(Ry)
    0  -123.45678901  -...
   10  -123.45678902  -...
  ...
```

### formation_energies.dat
```
# Cu_percent  FormationEnergy(Ry/site)
    0   0.00000000
   10  -0.00012345
  ...
```

## Troubleshooting

### "Folder 'X' does not match pattern AX_BY ... You must set 'composition'"
- When using **single-folder mode** with a folder name that is not in the form `AX_BY` (e.g. `TiAg` instead of `Ti50_Ag50`), you must set **composition** in `formation_energy_config.yaml`, e.g. `composition: [50, 50]` for 50% A, 50% B. The two numbers must sum to 100.

### "No composition folders found matching AX_BY"
- In discovery mode, subfolders must be named like `Cu50_Mg50` (element symbols + percentages that sum to 100). Check that `element_a` and `element_b` in the config match the folder naming.

### "No energies were extracted"
- Check that `workflow_results.json` or fcd/*.prn files exist in each composition folder
- Verify that the JSON/files contain phase 3 energy data

### "Missing pure element energies"
- In discovery mode, ensure both pure-endpoint folders exist (e.g. `Cu0_Mg100` and `Cu100_Mg0`) if you need formation energies at 0% and 100%. The script does not require them for the formula; reference energies come from the config.

### "Energy not found in workflow_results.json"
The Python script will print available keys if it can't find the energy. Check the JSON structure and modify the `extract_phase3_energy()` function if needed to match your specific JSON format.

### Bash Script Notes
- The bash script works best with `jq` installed for JSON parsing
- Without `jq`, it falls back to basic grep patterns which may be less robust
- Install jq: `sudo apt install jq` (Linux) or `brew install jq` (macOS)

## Example Workflow

```bash
# 1. Navigate to your alloy calculation directory
cd /path/to/CuMg_fcc

# 2. Run the extraction and plotting (Python)
python /path/to/EMTO_input_automation/bin/extract_formation_energy.py

# OR use bash script + separate plotting
bash /path/to/EMTO_input_automation/bin/extract_formation_energy.sh
python /path/to/EMTO_input_automation/bin/plot_formation_energy.py

# 3. View results
cat formation_energies.dat
open formation_energy_vs_composition.png  # macOS
# Or xdg-open formation_energy_vs_composition.png  # Linux
```

## Notes

- Formation energy values are typically negative for stable alloys
- Pure elements (0% and 100%) should have formation energy = 0 by definition
- Reference energies E(A) and E(B) are set in the config (or CLI); they do not have to come from folders in the run directory
