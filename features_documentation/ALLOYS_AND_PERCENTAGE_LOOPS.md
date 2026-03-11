# Alloy Composition Loops

## Overview

EMTOFlow supports systematic composition variation (alloy loops) via:

- **Alloy definitions**:
  - Either from **lattice parameters** (`lat` + `sites`) or from **CIF + substitutions**.
- **Composition looping**:
  - Recommended: generate one YAML per composition using
    `emtoflow.modules.generate_percentages` and the `emtoflow-generate-percentages`
    CLI, then run each with `emtoflow-opt`.
  - Legacy: use `emtoflow.modules.alloy_loop` to run all compositions inside a
    single workflow call.

This document explains **(1)** how to set up alloys in YAML and **(2)** how to
loop over percentages in both parameter-based and CIF-based workflows.

---

## Defining alloys

### A. Parameter-based alloys (`lat` + `sites`)

Random alloys and ordered structures can be defined directly in YAML using
`lat`, lattice parameters, and a `sites` list.

**Binary random alloy example (Cu–Mg, FCC):**

```yaml
lat: 2
a: 3.7

sites:
  - position: [0, 0, 0]
    elements: ['Cu', 'Mg']
    concentrations: [0.67, 0.33]   # 67% Cu, 33% Mg
```

**Ternary example (Fe–Co–Ni):**

```yaml
sites:
  - position: [0, 0, 0]
    elements: ['Fe', 'Co', 'Ni']
    concentrations: [0.5, 0.3, 0.2]
```

Rules:

- `elements` lists species at a given crystallographic site.
- `concentrations` are fractions (sum to 1.0) in the same order as `elements`.

### B. CIF-based alloys (`cif_file` + `substitutions`)

For structures defined by a CIF, you can introduce alloys via `substitutions`:

```yaml
cif_file: "path/to/your_structure.cif"

substitutions:
  Cu:
    elements: ['Cu', 'Mg']
    concentrations: [0.67, 0.33]
  Mg:
    elements: ['Cu', 'Mg']
    concentrations: [0.67, 0.33]
```

Rules:

- Each key under `substitutions` (e.g., `Cu`, `Mg`) refers to a **base element**
  present in the CIF.
- All substitutions that will be looped over must share the same `elements`
  list (e.g. `['Cu', 'Mg']`).
- Substitutions replace **all sites** of each specified element in the CIF with
  a random alloy according to `concentrations`.

---

## Looping over compositions

The recommended workflow is:

1. Add a `loop_perc` section to your **master YAML**.
2. Use `emtoflow-generate-percentages` to create one YAML per composition.
3. Run (or submit) each generated YAML as a standard EMTOFlow job.

### CLI workflow

- Prepare a master config, e.g. `master_config.yaml` with `loop_perc` set.
- From the repo root:

```bash
emtoflow-generate-percentages master_config.yaml
```

This creates a folder (matching `output_path` from the master config) containing
all composition YAML files:

```text
CuMg_fcc/
├── Cu0_Mg100.yaml
├── Cu10_Mg90.yaml
├── Cu50_Mg50.yaml
└── ...
```

- Run individual compositions:

```bash
emtoflow-opt CuMg_fcc/Cu50_Mg50.yaml
emtoflow-opt CuMg_fcc/Cu60_Mg40.yaml
```

### CLI workflow

**Step 1: Generate YAML files**

```bash
emtoflow-generate-percentages master_config.yaml
```

This creates a folder (matching `output_path` from the master config) containing
all composition YAML files:

```text
CuMg_fcc/
├── Cu0_Mg100.yaml
├── Cu10_Mg90.yaml
├── Cu50_Mg50.yaml
└── ...
```

**Step 2: Run individual compositions**

```bash
emtoflow-opt CuMg_fcc/Cu50_Mg50.yaml
emtoflow-opt CuMg_fcc/Cu60_Mg40.yaml
```

---

## Configuring `loop_perc` in the master YAML

### A. Parameter-based alloys (`lat` + `sites`)

**Single site variation:**
```yaml
# Master config with loop_perc enabled
loop_perc:
  enabled: true
  step: 10
  site_index: 0  # Single site (integer)
  phase_diagram: true  # Generate all combinations
  # OR
  percentages: [[0,100], [25,75], [50,50], [75,25], [100,0]]  # Explicit list
```

**Multiple sites with same percentages:**
```yaml
# Vary multiple sites simultaneously with the same percentages
loop_perc:
  enabled: true
  step: 10
  site_index: [0, 1]  # List of sites - apply same percentages to sites 0 and 1
  phase_diagram: true
```

**Note:** When using `site_index` as a list, all specified sites must have:
- The same number of elements
- The same element symbols (order should match)
- The same percentages will be applied to all sites in each iteration

### B. CIF + substitutions

When using a CIF plus `substitutions`, you can loop over compositions by
specifying **elements directly**:

```yaml
cif_file: "path/to/your_structure.cif"

substitutions:
  Cu:
    elements: ['Cu', 'Mg']
    concentrations: [0.67, 0.33]
  Mg:
    elements: ['Cu', 'Mg']
    concentrations: [0.67, 0.33]

loop_perc:
  enabled: true
  substitution_elements: ['Cu', 'Mg']  # Specify elements directly (recommended)
  step: 10
  phase_diagram: false
```

Notes:

- All substitutions listed in `substitution_elements` must have the **same**
  `elements` array (e.g., both Cu and Mg use `['Cu', 'Mg']`).
- The same percentages are applied to **all** matching substitutions at each
  step (e.g., Cu0–Mg100, Cu10–Mg90, …, Cu100–Mg0).
- Substitutions replace **all sites** of each element, so `substitution_elements`
  is clearer and safer than using `site_index` for CIF-based alloys.

### Three modes

1. **Explicit list**: Specify exact compositions
2. **Phase diagram**: Generate all valid combinations with uniform step
3. **Single element sweep**: Vary first element while others adjust automatically
   - Always varies the first element (index 0)
   - Concentrations always match the element order in the site definition
   - Example: For `elements: ['Cu', 'Mg']`, concentrations are `[Cu%, Mg%]`

---

## Module structure

### `emtoflow.modules.generate_percentages`
- `generator.py`: Main generation logic
- `composition.py`: Composition grid generation
- `yaml_writer.py`: YAML file writing

### `emtoflow.modules.alloy_loop`
- `run_with_percentage_loop()`: Main loop wrapper
- Composition generation functions

## Output structure (generate_percentages)

```
output_path/
├── Fe0_Pt100/
│   └── [optimization workflow outputs]
├── Fe25_Pt75/
│   └── [optimization workflow outputs]
├── Fe50_Pt50/
│   └── [optimization workflow outputs]
└── ...
```

Each composition gets its own subdirectory with complete workflow execution.

## Benefits of Generate Percentages Approach

- ✓ Review compositions before running
- ✓ Control when to submit calculations
- ✓ Test single compositions first
- ✓ Better resource management
- ✓ Easier debugging
