# Alloy Percentage Loop - Usage Guide

This document explains how to use the alloy percentage loop feature to automatically generate and run calculations for multiple alloy compositions.

## Overview

The alloy loop feature allows you to:
- **Systematically explore alloy compositions** without manually creating multiple YAML files
- **Generate phase diagrams** for binary, ternary, and higher-order systems
- **Validate input files** with `prepare_only` mode before running expensive calculations
- **Maintain consistency** across all compositions (same parameters, only concentrations vary)

## Three Operating Modes

### Mode 1: Explicit Composition List

Specify exact compositions you want to test. Best for:
- Specific compositions of interest
- Non-uniform sampling
- Quick targeted studies

```yaml
loop_perc:
  enabled: true
  step: null
  start: null
  end: null
  site_index: 0
  element_index: null
  phase_diagram: false
  percentages:
    - [0, 100]      # Pure Mg
    - [25, 75]      # Cu25Mg75
    - [50, 50]      # Cu50Mg50
    - [75, 25]      # Cu75Mg25
    - [100, 0]      # Pure Cu
```

**Result**: 5 compositions exactly as specified

### Mode 2: Phase Diagram (All Combinations)

Generate all valid compositions with uniform step. Best for:
- Complete phase diagram exploration
- Systematic composition mapping
- Publication-quality data

```yaml
loop_perc:
  enabled: true
  step: 10                        # Step size in percentage
  start: null
  end: null
  site_index: 0
  element_index: null
  phase_diagram: true             # Enable phase diagram mode
  percentages: null
```

**Number of compositions**:
- **Binary** (2 elements, step=10): 11 points (0%, 10%, 20%, ..., 100%)
- **Binary** (2 elements, step=5): 21 points
- **Ternary** (3 elements, step=10): 66 points (triangular grid)
- **Ternary** (3 elements, step=5): 231 points
- **Quaternary** (4 elements, step=10): 286 points

**⚠️ Warning**: Ternary systems with small steps generate many calculations! Start with step=10 for testing.

### Mode 3: Single Element Sweep

Vary one element while others adjust automatically. Best for:
- Binary alloy studies
- Understanding effect of single element
- Quick composition scans

```yaml
loop_perc:
  enabled: true
  step: 20                        # Step size in percentage
  start: 0                        # Start at 0%
  end: 100                        # End at 100%
  site_index: 0                   # Which site to vary
  element_index: 0                # Vary Cu (0=Cu, 1=Mg)
  phase_diagram: false
  percentages: null
```

**Result**: Cu varies 0→100% in 20% steps, Mg automatically adjusts as complement

## Input File Preparation Mode

Use `prepare_only` to create input files without running calculations:

```yaml
prepare_only: true                # Create files only, don't run
```

**Use this to**:
- Validate your configuration
- Check generated input files
- Verify directory structure
- Debug before expensive calculations

**After validation**, set `prepare_only: false` to run the full workflow.

## Complete Example

```yaml
# CuMg_fcc_loop.yaml
output_path: "CuMg_study"
job_name: "CuMg"

# Structure definition
cif_file: null
lat: 2                              # FCC
a: 3.61
b: null
c: null
alpha: null
beta: null
gamma: null
sites:
  - position: [0, 0, 0]
    elements: ['Cu', 'Mg']
    concentrations: [0.5, 0.5]     # Will be overwritten by loop

# Enable loop with explicit compositions
loop_perc:
  enabled: true
  step: null
  start: null
  end: null
  site_index: 0
  element_index: null
  phase_diagram: false
  percentages:
    - [0, 100]
    - [25, 75]
    - [50, 50]
    - [75, 25]
    - [100, 0]

# Create files only (for validation)
prepare_only: true

# Optimization settings (will apply to all compositions)
optimize_ca: false
optimize_sws: true
initial_sws: [2.67]

# ... rest of standard configuration ...
```

## Running the Loop

```bash
python bin/run_optimization.py CuMg_fcc_loop.yaml
```

## Output Structure

```
CuMg_study_alloy_loop/
├── Cu0_Mg100/
│   ├── phase1_ca_optimization/    (if optimize_ca=true)
│   ├── phase2_sws_optimization/   (if optimize_sws=true)
│   └── phase3_optimized/
├── Cu25_Mg75/
│   ├── phase1_ca_optimization/
│   ├── phase2_sws_optimization/
│   └── phase3_optimized/
├── Cu50_Mg50/
│   └── ...
├── Cu75_Mg25/
│   └── ...
└── Cu100_Mg0/
    └── ...
```

Each composition gets:
- Own subdirectory named by composition (e.g., `Cu30_Mg70`)
- Complete workflow execution (c/a opt, SWS opt, final calc)
- All input files, output files, and plots
- Results organized exactly like single runs

## Parameter Reference

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | bool | `false` | Enable loop mode |
| `step` | float | `10` | Step size in percentage (for modes 2 & 3) |
| `start` | float | `0` | Start percentage (mode 3 only) |
| `end` | float | `100` | End percentage (mode 3 only) |
| `site_index` | int | `0` | Which site to vary (0-indexed) |
| `element_index` | int | `0` | Which element to vary (mode 3 only, 0-indexed) |
| `phase_diagram` | bool | `false` | Enable phase diagram mode |
| `percentages` | list | `null` | Explicit composition list (mode 1) |

## Advanced: Ternary Phase Diagram Example

```yaml
sites:
  - position: [0, 0, 0]
    elements: ['Fe', 'Pt', 'Co']
    concentrations: [0.33, 0.33, 0.34]

loop_perc:
  enabled: true
  step: 10                        # 66 compositions
  site_index: 0
  phase_diagram: true
  # Rest null
```

**Output**: 66 compositions forming triangular grid
- Pure phases: Fe100, Pt100, Co100
- Binary edges: Fe50Pt50, Fe50Co50, Pt50Co50
- Ternary interior: Fe40Pt30Co30, etc.

## Tips and Best Practices

1. **Start with `prepare_only: true`**
   - Always validate before running expensive calculations
   - Check a few generated input files manually

2. **Use coarse step for testing**
   - Phase diagram with `step: 20` for quick test
   - Refine to `step: 10` or `step: 5` for publication

3. **Single element sweep for binaries**
   - Mode 3 is equivalent to Mode 2 for binary systems
   - Mode 3 is more explicit about which element varies

4. **Explicit list for non-uniform sampling**
   - Use Mode 1 when you need specific compositions
   - Good for validating against experimental data points

5. **Check computational cost**
   - Each composition runs full workflow (c/a + SWS optimization)
   - Binary step=10: 11 calcs
   - Ternary step=10: 66 calcs
   - Ternary step=5: 231 calcs (careful!)

6. **Directory names**
   - Automatically formatted as `Element1XX_Element2YY`
   - Percentages rounded to integers

## Disabling Loop (Normal Mode)

To run a single composition (no loop):

```yaml
loop_perc: null                   # Disable loop
```

or

```yaml
loop_perc:
  enabled: false
  # All other parameters ignored
```

## Troubleshooting

**Error: "loop_perc is not supported with CIF files"**
- Loop only works with parameter-based structures (`lat`, `a`, `sites`)
- Convert your CIF to parameters first

**Error: "percentages must sum to 100%"**
- Check your explicit composition list
- Each composition must sum to exactly 100%

**Error: "site_index X is out of range"**
- Check how many sites you have in `sites` list
- `site_index` is 0-indexed

**Error: "element_index X is out of range"**
- Check how many elements at the site
- `element_index` is 0-indexed (0=first element)

**Too many compositions warning**
- Phase diagram generates many points for small steps
- Start with larger step (e.g., 20) for testing
- Use Mode 1 (explicit list) for sparse sampling

## Integration with Existing Workflow

The loop feature is a **thin wrapper** around the existing optimization workflow:
- Each composition runs the complete workflow
- All optimization settings apply to all compositions
- `prepare_only` flag works for both loop and single mode
- Results structure identical to single runs

No changes needed to existing analysis scripts!

## See Also

- `DEVELOPMENT_GUIDELINES.md` - Design principles
- `CuMg_fcc_loop_example.yaml` - Working example with all modes
- `modules/alloy_loop.py` - Implementation details
