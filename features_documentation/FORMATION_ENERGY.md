# Formation Energy computation (Extra Script)

This document describes the **optional helper scripts** in `extra_scripts/` for
extracting and analyzing formation energies from EMTOFlow alloy calculations.

These tools are not part of the core EMTOFlow workflow; they sit on top of
`workflow_results.json` outputs and are meant for quick post‑processing of
binary alloys.

---

## Concept

For a binary alloy A–B, the formation energy per site is:

```text
E_form(A_x B_{1-x}) = E(A_x B_{1-x}) - x·E(A) - (1-x)·E(B)
```

where:

- `E(A_x B_{1-x})` – optimized alloy energy per site.
- `E(A)`, `E(B)` – reference energies per site of pure A and B (Ry/site).
- `x` – atomic fraction of A.

The scripts:

- Read final energies from EMTOFlow outputs (typically `workflow_results.json`).
- Combine them with **user-provided** pure-element reference energies.
- Produce:
  - `energies_raw.dat` – raw total and per‑site energies.
  - `formation_energies.dat` – formation energies.
  - `formation_energy_vs_composition.png` – formation‑energy vs composition plot.

Reference energies are **never** inferred from the alloy runs; you must supply
them in a small YAML config or via CLI flags.

---

## Python helper: `extra_scripts/extract_formation_energy.py`

### Discovery mode (many compositions)

Use when you have a directory with many composition subfolders named like
`AX_BY`, for example:

```text
CuMg_fcc/
├── Cu0_Mg100/
├── Cu10_Mg90/
├── Cu20_Mg80/
└── ...
```

Each composition folder should contain a `workflow_results.json` with a
`final_energy` field (Ry).

**Steps:**

1. `cd` into the parent directory (e.g. `CuMg_fcc`).
2. Optionally create `formation_energy_config.yaml`:

   ```yaml
   element_a: Cu
   element_b: Mg
   reference_energy_a: -3310.060512   # E(Cu) per site
   reference_energy_b: -400.662871    # E(Mg) per site
   folder: null        # null → scan all AX_BY folders
   composition: null
   ```

3. Run:

   ```bash
   python extra_scripts/extract_formation_energy.py
   # or with explicit config:
   python extra_scripts/extract_formation_energy.py --config formation_energy_config.yaml
   ```

The script will:

- Discover all subfolders matching `AX_BY` (e.g. `Cu50_Mg50`).
- Parse compositions from folder names.
- Read `final_energy` from each `workflow_results.json`.
- Write `energies_raw.dat`, `formation_energies.dat`,
  `formation_energy_vs_composition.png` in the current directory.

### Single‑folder mode (non‑AX_BY name)

Use when you have a single folder whose name does **not** encode composition
(e.g. `TiAg` instead of `Ti50_Ag50`).

1. `cd` into the parent directory containing the folder (e.g. `TiAg`).

2. Create `formation_energy_config.yaml`:

   ```yaml
   element_a: Ti
   element_b: Ag
   reference_energy_a: -1234.0        # E(Ti) per site
   reference_energy_b: -567.0         # E(Ag) per site
   folder: TiAg                       # folder to process
   composition: [50, 50]              # 50% Ti, 50% Ag (must sum to 100)
   ```

3. Run:

   ```bash
   python extra_scripts/extract_formation_energy.py --config formation_energy_config.yaml
   ```

This produces single‑point outputs in the current directory (same files as in
discovery mode, but with one row / one point).

### Config and CLI overrides

- The script reads `formation_energy_config.yaml` from the current directory,
  or from a path passed via `--config`.
- You can override YAML values on the command line, for example:

  ```bash
  python extra_scripts/extract_formation_energy.py \
    --element-a Ti --element-b Ag --E-a -1234.0 --E-b -567.0

  python extra_scripts/extract_formation_energy.py \
    --folder TiAg --composition 50,50
  ```

See the script help (`-h`) for the full list of options.

---

## Expected JSON structure

Each composition folder is expected to contain a `workflow_results.json` with a
`final_energy` key, e.g.:

```json
{
  "job_name": "CuMg",
  "optimal_ca": 1.0,
  "optimal_sws": 2.7033254965,
  "phases_completed": ["phase2_sws_optimization", "phase3_optimized_calculation"],
  "final_energy": -3310.060502
}
```

If the key name differs in your setup, you may need to adapt the helper
function in `extract_formation_energy.py`.

---

## Notes and caveats

- These scripts are **extras** on top of EMTOFlow; they are not required for
  the main optimization workflows.
- Reference energies for pure A and B must be supplied:
  - In `formation_energy_config.yaml`, or
  - Via CLI flags (`--E-a`, `--E-b`).
- Discovery mode assumes folder names like `Cu50_Mg50`; for other naming
  schemes, use single‑folder mode and set `composition` explicitly.