# Alloy Composition Loops

## Overview

Two modules provide functionality for systematic composition variation in alloy calculations:

1. **`modules/alloy_loop.py`**: Automatic execution loop (legacy, still available)
2. **`modules/generate_percentages/`**: File generation approach (recommended)

## Recommended Approach: Generate Percentages

The `generate_percentages` module separates file generation from execution, giving users control over when to submit calculations.

### Usage

**Step 1: Generate YAML files**
```bash
python bin/generate_percentages.py master_config.yaml
```

**Step 2: Run individually**
```bash
python bin/run_optimization.py Fe50_Pt50.yaml
python bin/run_optimization.py Fe60_Pt40.yaml
```

### Configuration

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

**For CIF method with substitutions:**
- **Recommended**: Use `substitution_elements` to specify elements directly:
  ```yaml
  loop_perc:
    enabled: true
    substitution_elements: ['Cu', 'Mg']  # Specify elements directly
    step: 10
    phase_diagram: true
  ```
- **Legacy**: Use `site_index` to identify elements via structure sites:
  ```yaml
  loop_perc:
    enabled: true
    site_index: [0, 1]  # Sites corresponding to Cu and Mg
    step: 10
    phase_diagram: true
  ```
- All substitutions must have the same elements (e.g., both Cu and Mg substitutions have ['Cu', 'Mg'])
- The same percentages will be applied to ALL matching substitutions
- Substitutions replace ALL sites of each specified element, so `substitution_elements` is clearer than `site_index`

### Three Modes

1. **Explicit list**: Specify exact compositions
2. **Phase diagram**: Generate all valid combinations with uniform step
3. **Single element sweep**: Vary first element while others adjust automatically
   - Always varies the first element (index 0)
   - Concentrations always match the element order in the site definition
   - Example: For `elements: ['Cu', 'Mg']`, concentrations are `[Cu%, Mg%]`

## Legacy Approach: Automatic Loop

The `alloy_loop.py` module automatically runs all compositions in sequence:

**Single site:**
```yaml
loop_perc:
  enabled: true
  step: 10
  site_index: 0
  phase_diagram: true
```

**Multiple sites:**
```yaml
loop_perc:
  enabled: true
  step: 10
  site_index: [0, 1]  # List of sites - same percentages for both sites
  phase_diagram: true
```

```bash
python bin/run_optimization.py master_config.yaml
# Automatically runs all compositions
```

## Module Structure

### `modules/generate_percentages/`
- `generator.py`: Main generation logic
- `composition.py`: Composition grid generation
- `yaml_writer.py`: YAML file writing

### `modules/alloy_loop.py`
- `run_with_percentage_loop()`: Main loop wrapper
- Composition generation functions

## Output Structure

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
