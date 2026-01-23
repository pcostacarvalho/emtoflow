# Generate Percentages Module

## Overview

The `modules/generate_percentages/` module creates multiple YAML configuration files from a master YAML, each representing a different alloy composition. This separates file generation from workflow execution, giving users control over when to submit calculations.

## User Workflow

**Step 1: Generate YAML files**
```bash
python bin/generate_percentages.py master_config.yaml
```

This creates a folder (matching `output_path` from master config) containing all YAML files:
```
CuMg_fcc/
├── Cu0_Mg100.yaml
├── Cu10_Mg90.yaml
├── Cu50_Mg50.yaml
└── ...
```

**Step 2: Submit individually**
```bash
cd CuMg_fcc
python ../bin/run_optimization.py Cu50_Mg50.yaml
python ../bin/run_optimization.py Cu60_Mg40.yaml
```

Or from the parent directory:
```bash
python bin/run_optimization.py CuMg_fcc/Cu50_Mg50.yaml
python bin/run_optimization.py CuMg_fcc/Cu60_Mg40.yaml
```

## Key Features

- **Structure-agnostic**: Works with both CIF + substitutions and lattice parameters
- **Three composition modes**: Explicit list, phase diagram, single element sweep
- **Zero concentration handling**: Treats 0% as alloy (keeps element with 0.0 concentration)
- **Oxidation state removal**: Automatically removes oxidation states from CIF files
- **Composition naming**: Generates files with composition in filename (e.g., `Fe50_Pt50.yaml`)

## Module Structure

### `generator.py`
Main generation logic:
- `generate_percentage_configs()`: Main entry point
- `determine_loop_site()`: Identifies which site to vary
- `create_yaml_for_composition()`: Creates modified config for specific composition

### `composition.py`
Composition generation:
- `generate_compositions()`: Generates composition list based on mode
- Supports binary, ternary, and higher-order systems
- Handles phase diagram grids and single element sweeps

### `yaml_writer.py`
YAML file writing:
- `write_yaml_file()`: Writes config dictionary to YAML with proper formatting
- Preserves all original settings
- Updates concentrations and disables loop_perc

## Configuration Modes

### Mode 1: Explicit List
```yaml
loop_perc:
  percentages:
    - [0, 100]
    - [25, 75]
    - [50, 50]
```

### Mode 2: Phase Diagram
```yaml
loop_perc:
  step: 10
  phase_diagram: true
```
- Binary: 11 compositions (step=10)
- Ternary: 66 compositions (step=10)

### Mode 3: Single Element Sweep
```yaml
loop_perc:
  step: 20
  start: 0
  end: 100
  element_index: 0
```

## Output

### Folder Structure

YAML files are created inside a folder matching the master config's `output_path`:

**Master config:**
```yaml
output_path: CuMg_fcc
```

**Generated structure:**
```
Current directory/
└── CuMg_fcc/
    ├── Cu0_Mg100.yaml
    ├── Cu10_Mg90.yaml
    ├── Cu50_Mg50.yaml
    ├── Cu90_Mg10.yaml
    └── Cu100_Mg0.yaml
```

### Generated Files

Each YAML file:
- Copies entire original YAML
- Updates concentrations (in `substitutions` for CIF or `sites` for parameters)
- Disables `loop_perc` (set `enabled: false`)
- Sets `output_path` to just the composition name (e.g., `Cu100_Mg0`)
  - The base folder structure is created by `generate_percentages`
  - When running the workflow, calculations will be created in `{base_folder}/{composition_name}/`

**Example:**
- Master config: `output_path: CuMg_fcc`
- Generated file location: `CuMg_fcc/Cu100_Mg0.yaml`
- File contents: `output_path: Cu100_Mg0`
- When run: Creates `CuMg_fcc/Cu100_Mg0/` for calculations

## Implementation Details

- Uses `structure_builder.create_emto_structure()` as unified entry point
- Extracts alloy information from pymatgen Structure
- Handles both CIF and parameter workflows transparently
- Validation in `utils/config_parser.py`

## Related Modules

- `modules/alloy_loop.py`: Legacy automatic loop (still available)
- `modules/structure_builder.py`: Structure creation and parsing
- `utils/config_parser.py`: Configuration validation
