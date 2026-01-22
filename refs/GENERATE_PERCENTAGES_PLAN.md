# Generate Percentages Module - Implementation Plan

## Overview

Create a standalone `generate_percentages` module that generates multiple YAML configuration files from a master YAML, each representing a different alloy composition. This separates file generation from workflow execution, giving users control over when to submit calculations.

## User Workflow

### Step 1: Generate YAML Files
```bash
python bin/generate_percentages.py master_config.yaml
```

**Output:** Multiple YAML files with composition in filename:
- `Fe0_Pt100.yaml`
- `Fe25_Pt75.yaml`
- `Fe50_Pt50.yaml`
- `Fe75_Pt25.yaml`
- `Fe100_Pt0.yaml`

### Step 2: Run Calculations (user controlled)
```bash
# User manually submits each composition
python bin/run_optimization.py Fe50_Pt50.yaml
python bin/run_optimization.py Fe60_Pt40.yaml

# Or submit to SLURM
sbatch wrapper_Fe50_Pt50.sh
sbatch wrapper_Fe60_Pt40.sh
```

## Key Requirements

### 1. Composition Generation Modes (Keep Existing Logic)

Preserve all three modes from `alloy_loop.py`:

**Mode 1: Explicit List**
```yaml
loop_perc:
  percentages:
    - [0, 100]      # Pure element A
    - [25, 75]
    - [50, 50]
    - [75, 25]
    - [100, 0]      # Pure element B
```

**Mode 2: Phase Diagram**
```yaml
loop_perc:
  step: 10
  phase_diagram: true
```
- Binary: 11 compositions (0%, 10%, ..., 100%)
- Ternary: 66 compositions (triangular grid)
- Quaternary: 286 compositions

**Mode 3: Single Element Sweep**
```yaml
loop_perc:
  step: 20
  start: 0
  end: 100
  element_index: 0  # Vary first element
```

### 2. Input Methods Support

**Method A: CIF + Substitutions**
```yaml
cif_file: "FePt.cif"
substitutions:
  Fe:
    elements: ['Fe', 'Pt']
    concentrations: [0.5, 0.5]  # Will be varied by loop_perc
  Pt:
    elements: ['Pt']
    concentrations: [1.0]
```

**Method B: Lattice Parameters + Sites**
```yaml
lat: 2  # FCC
a: 3.7
sites:
  - position: [0, 0, 0]
    elements: ['Fe', 'Pt']
    concentrations: [0.5, 0.5]  # Will be varied by loop_perc
```

### 3. Structure-Agnostic Implementation

**Critical Insight**: Use `structure_builder.create_emto_structure()` as unified entry point:

```python
# Works for BOTH CIF and parameters
structure_pmg, structure_dict = create_emto_structure(
    cif_file=config.get('cif_file'),
    substitutions=config.get('substitutions'),
    lat=config.get('lat'),
    a=config.get('a'),
    sites=config.get('sites'),
    # ... other params
)
```

The `structure_pmg` contains:
- All sites with fractional coordinates
- Element composition per site (pure or partial occupancy)
- This is the "ground truth" for what elements/concentrations exist

**Extract Alloy Information from Structure:**
```python
# Iterate through sites to find alloy sites
for site_idx, site in enumerate(structure_pmg.sites):
    if hasattr(site.specie, 'symbol'):
        # Pure element site
        elements = [site.specie.symbol]
        concentrations = [1.0]
    else:
        # Alloy site (partial occupancy)
        elements = [el.symbol for el in site.species.elements]
        concentrations = list(site.species.get_atomic_fraction().values())
```

### 4. Zero Concentration Handling

**Requirement:** Treat 0% as alloy (keep element with 0.0 concentration)

```yaml
# Generated file for Fe0_Pt100.yaml
sites:
  - position: [0, 0, 0]
    elements: ['Fe', 'Pt']
    concentrations: [0.0, 1.0]  # Fe still present with 0.0
```

**Reason:** EMTO's CPA (Coherent Potential Approximation) requires all alloy components to be listed, even with zero concentration, for proper electronic structure calculations.

### 5. Oxidation State Removal

**Already implemented** in `structure_builder.py` (lines 619, 623):
```python
structure_pmg.remove_oxidation_states()
```

**Ensure this is called** when loading CIF in `generate_percentages`:
```python
if cif_file:
    structure_pmg = Structure.from_file(cif_file)
    structure_pmg.remove_oxidation_states()  # Critical for CIF files with oxidation states
```

### 6. Generated YAML Format

Each generated YAML should:
- **Copy entire original YAML** (all settings preserved)
- **Update concentrations** (in `substitutions` for CIF or `sites` for parameters)
- **Disable loop_perc** (set `enabled: false`)
- **Keep CIF path** (copy string reference, not file)
- **Update output_path** with composition subdirectory
- **Composition in filename**: `Element1XX_Element2YY.yaml`

**Example Generated File (`Fe50_Pt50.yaml`):**
```yaml
# All original settings copied
output_path: "FePt_study/Fe50_Pt50"
job_name: "FePt"

# CIF path preserved
cif_file: "/path/to/FePt.cif"

# Updated substitutions
substitutions:
  Fe:
    elements: ['Fe', 'Pt']
    concentrations: [0.5, 0.5]  # Updated from master
  Pt:
    elements: ['Pt']
    concentrations: [1.0]

# Loop disabled
loop_perc:
  enabled: false

# ... rest of original config (dmax, magnetic, optimize_ca, etc.)
```

## Implementation Details

### Module Structure

**File:** `modules/generate_percentages.py`

```python
#!/usr/bin/env python3
"""
Generate YAML files for different alloy compositions.

This module creates multiple YAML configuration files from a master YAML,
each representing a different composition percentage. Users can then
submit these files individually to run_optimization.py.
"""

def generate_percentage_configs(master_config_path: str, output_dir: str = None):
    """
    Generate YAML files for all compositions.

    Parameters
    ----------
    master_config_path : str
        Path to master YAML with loop_perc configuration
    output_dir : str, optional
        Directory for generated YAMLs (default: same as master YAML)

    Returns
    -------
    list
        List of generated YAML file paths
    """
    pass

def determine_loop_site(config: dict, structure_pmg) -> tuple:
    """
    Determine which site to vary based on config and structure.

    For CIF + substitutions: Find site with substitution elements
    For parameters: Use site_index from loop_perc

    Returns
    -------
    tuple
        (site_index, elements, base_concentrations)
    """
    pass

def generate_compositions(loop_config: dict, n_elements: int) -> list:
    """
    Generate composition list based on loop_perc mode.

    Reuse logic from alloy_loop.py:
    - Mode 1: Explicit percentages list
    - Mode 2: Phase diagram (all combinations)
    - Mode 3: Single element sweep
    """
    pass

def create_yaml_for_composition(base_config: dict, composition: list,
                                composition_name: str, structure_pmg,
                                site_idx: int, cif_method: bool) -> dict:
    """
    Create modified config for a specific composition.

    Steps:
    1. Deep copy base config
    2. Update concentrations:
       - CIF method: Update substitutions
       - Parameters method: Update sites[site_idx]['concentrations']
    3. Update output_path with composition subdirectory
    4. Disable loop_perc
    5. Preserve all other settings
    """
    pass

def write_yaml_file(config: dict, output_path: str):
    """Write config dictionary to YAML file with proper formatting."""
    pass
```

### Command Line Interface

**File:** `bin/generate_percentages.py`

```python
#!/usr/bin/env python3
"""
Generate YAML files for alloy percentage loop.

Usage:
    python bin/generate_percentages.py master_config.yaml [output_dir]

Examples:
    # Generate YAMLs in same directory as master
    python bin/generate_percentages.py FePt_master.yaml

    # Generate YAMLs in specific directory
    python bin/generate_percentages.py FePt_master.yaml ./configs/
"""

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    master_config = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None

    # Load config
    config = load_and_validate_config(master_config)

    # Validate loop_perc is enabled
    if not config['loop_perc'] or not config['loop_perc'].get('enabled'):
        print("Error: loop_perc must be enabled in master config")
        sys.exit(1)

    # Generate files
    generated_files = generate_percentage_configs(master_config, output_dir)

    # Print summary
    print(f"\nGenerated {len(generated_files)} YAML files:")
    for f in generated_files:
        print(f"  - {f}")

    print(f"\nNext steps:")
    print(f"  python bin/run_optimization.py <composition>.yaml")
```

### Integration with run_optimization.py

**Modification:** `run_optimization.py` should **ignore** `loop_perc` flag completely.

```python
def main():
    config = load_and_validate_config(config_file)

    # Remove loop_perc check - always run single workflow
    workflow = OptimizationWorkflow(config=config)
    results = workflow.run()

    # ... rest of single workflow logic
```

**Rationale:**
- `loop_perc` is **only relevant** for `generate_percentages.py`
- Once individual YAMLs are generated, they represent single compositions
- `run_optimization.py` just runs the alloy composition as specified

## Algorithm: Structure-Agnostic Concentration Update

### Problem
Need to update concentrations regardless of input method (CIF or parameters).

### Solution
Use the pymatgen structure as the "source of truth":

```python
def update_concentrations_in_config(config: dict, structure_pmg,
                                   site_idx: int, new_concentrations: list) -> dict:
    """
    Update concentrations in config based on structure type.

    Algorithm:
    1. Determine if CIF or parameter method
    2. Extract element list from structure_pmg.sites[site_idx]
    3. Update appropriate section in config
    """

    # Get elements from structure (always works)
    site = structure_pmg.sites[site_idx]
    if hasattr(site.specie, 'symbol'):
        elements = [site.specie.symbol]
    else:
        elements = [el.symbol for el in site.species.elements]

    # Deep copy config
    new_config = copy.deepcopy(config)

    # Determine input method and update accordingly
    if config.get('cif_file') and config.get('substitutions'):
        # CIF + substitutions method
        # Find which element in substitutions corresponds to this site
        for elem_key, subst_dict in new_config['substitutions'].items():
            if set(subst_dict['elements']) == set(elements):
                # Update this substitution
                new_config['substitutions'][elem_key]['concentrations'] = new_concentrations
                break

    elif config.get('sites'):
        # Parameter method
        new_config['sites'][site_idx]['concentrations'] = new_concentrations

    return new_config
```

## Composition Naming Convention

**Format:** `Element1XX_Element2YY_Element3ZZ.yaml`

```python
def format_composition_filename(elements: list, percentages: list) -> str:
    """
    Format: Fe50_Pt50.yaml

    - Percentages rounded to integers
    - Elements in order they appear in structure
    - Underscore separated
    """
    parts = []
    for elem, perc in zip(elements, percentages):
        parts.append(f"{elem}{int(round(perc))}")
    return "_".join(parts) + ".yaml"
```

**Examples:**
- Binary: `Fe50_Pt50.yaml`, `Cu75_Mg25.yaml`
- Ternary: `Fe50_Pt30_Co20.yaml`
- Pure (treated as alloy): `Fe0_Pt100.yaml`, `Fe100_Pt0.yaml`

## CIF + Substitutions: Detailed Workflow

### Master YAML
```yaml
cif_file: "FePt.cif"
substitutions:
  Fe:
    elements: ['Fe', 'Co']
    concentrations: [0.5, 0.5]  # Starting point (will be varied)
  Pt:
    elements: ['Pt']
    concentrations: [1.0]

loop_perc:
  enabled: true
  step: 25
  site_index: 0  # Refers to Fe sites in structure
  phase_diagram: false
  element_index: 0  # Vary Fe (first element in substitution)
```

### Generated Files

**Fe0_Co100.yaml:**
```yaml
cif_file: "FePt.cif"
substitutions:
  Fe:
    elements: ['Fe', 'Co']
    concentrations: [0.0, 1.0]  # Fe=0%, Co=100%
  Pt:
    elements: ['Pt']
    concentrations: [1.0]

loop_perc:
  enabled: false  # Disabled

output_path: "FePt_study/Fe0_Co100"
```

**Fe25_Co75.yaml:**
```yaml
cif_file: "FePt.cif"
substitutions:
  Fe:
    elements: ['Fe', 'Co']
    concentrations: [0.25, 0.75]  # Fe=25%, Co=75%
  Pt:
    elements: ['Pt']
    concentrations: [1.0]

loop_perc:
  enabled: false

output_path: "FePt_study/Fe25_Co75"
```

## Parameters + Sites: Detailed Workflow

### Master YAML
```yaml
lat: 2  # FCC
a: 3.7
sites:
  - position: [0, 0, 0]
    elements: ['Cu', 'Mg']
    concentrations: [0.5, 0.5]  # Will be varied

loop_perc:
  enabled: true
  step: 25
  site_index: 0
  element_index: 0  # Vary Cu
```

### Generated Files

**Cu0_Mg100.yaml:**
```yaml
lat: 2
a: 3.7
sites:
  - position: [0, 0, 0]
    elements: ['Cu', 'Mg']
    concentrations: [0.0, 1.0]  # Cu=0%, Mg=100%

loop_perc:
  enabled: false

output_path: "CuMg_study/Cu0_Mg100"
```

**Cu50_Mg50.yaml:**
```yaml
lat: 2
a: 3.7
sites:
  - position: [0, 0, 0]
    elements: ['Cu', 'Mg']
    concentrations: [0.5, 0.5]

loop_perc:
  enabled: false

output_path: "CuMg_study/Cu50_Mg50"
```

## Validation Requirements

### Master YAML Validation

**Required fields:**
- `loop_perc.enabled = true`
- Valid loop_perc mode configuration
- Either `cif_file` OR (`lat` + `a` + `sites`)
- For CIF: Must have `substitutions` if varying composition
- For parameters: Must have `sites` with multiple elements

**Validation checks:**
```python
def validate_master_config(config: dict):
    """
    Validate master config for percentage generation.

    Checks:
    1. loop_perc is enabled
    2. Structure input is valid (CIF or parameters)
    3. Site to vary has multiple elements (is an alloy)
    4. All loop_perc parameters are valid
    """

    # Check loop_perc enabled
    if not config.get('loop_perc') or not config['loop_perc'].get('enabled'):
        raise ValueError("loop_perc must be enabled in master config")

    # Check structure input
    has_cif = config.get('cif_file') is not None
    has_params = all([config.get('lat'), config.get('a'), config.get('sites')])

    if not (has_cif or has_params):
        raise ValueError("Must provide either cif_file or (lat, a, sites)")

    # Load structure to get elements
    structure_pmg, _ = create_emto_structure(
        cif_file=config.get('cif_file'),
        substitutions=config.get('substitutions'),
        lat=config.get('lat'),
        a=config.get('a'),
        sites=config.get('sites'),
        # ... other params
    )

    # Check that site has multiple elements
    site_idx = config['loop_perc']['site_index']
    site = structure_pmg.sites[site_idx]

    if hasattr(site.specie, 'symbol'):
        # Pure element site
        raise ValueError(f"Site {site_idx} is pure element, cannot vary composition")

    n_elements = len(site.species.elements)
    if n_elements < 2:
        raise ValueError(f"Site {site_idx} must have at least 2 elements for composition loop")

    return True
```

## Error Handling

### Common Errors

**1. loop_perc not enabled:**
```
Error: loop_perc.enabled must be true in master config
Solution: Set loop_perc.enabled: true
```

**2. Pure element site:**
```
Error: Site 0 is pure element (Fe), cannot vary composition
Solution: Use substitutions or define alloy in sites
```

**3. CIF without substitutions:**
```
Error: CIF input requires substitutions when using loop_perc
Solution: Add substitutions section to specify alloy composition
```

**4. Invalid site_index:**
```
Error: site_index 2 out of range (structure has 2 sites)
Solution: Check number of inequivalent sites in structure
```

## Testing Strategy

### Unit Tests

**Test 1: Composition Generation**
- Verify Mode 1 (explicit), Mode 2 (phase diagram), Mode 3 (sweep)
- Check correct number of compositions
- Validate percentages sum to 100%

**Test 2: CIF + Substitutions**
- Load CIF with substitutions
- Generate configs for different compositions
- Verify substitutions updated correctly
- Check oxidation states removed

**Test 3: Parameters + Sites**
- Create structure from parameters
- Generate configs for different compositions
- Verify sites updated correctly

**Test 4: Zero Concentration**
- Generate composition with 0% for one element
- Verify element still present with 0.0 concentration
- Check YAML format correct

**Test 5: Filename Generation**
- Binary alloys: `Fe50_Pt50.yaml`
- Ternary alloys: `Fe50_Pt30_Co20.yaml`
- Pure compositions: `Fe0_Pt100.yaml`, `Fe100_Pt0.yaml`

### Integration Tests

**Test 1: Full Generation Workflow**
```python
# Create master YAML
# Run generate_percentages
# Verify all files created
# Check each file is valid YAML
# Verify concentrations correct
```

**Test 2: Generated YAML → run_optimization**
```python
# Generate YAMLs
# Pick one generated YAML
# Run run_optimization.py with it
# Verify workflow executes correctly
```

## Migration from Current System

### Current System (alloy_loop.py)

**Behavior:** Automatically runs all compositions

```bash
python bin/run_optimization.py master_with_loop.yaml
# → Runs 11 compositions automatically
```

### New System (generate_percentages)

**Behavior:** Separate generation and execution

```bash
# Step 1: Generate files
python bin/generate_percentages.py master_with_loop.yaml
# → Creates 11 YAML files

# Step 2: Run individually (user control)
python bin/run_optimization.py Fe50_Pt50.yaml
python bin/run_optimization.py Fe60_Pt40.yaml
```

### Backward Compatibility

**Option 1:** Keep both systems
- `alloy_loop.py` remains for automatic execution
- `generate_percentages.py` added for manual control
- User chooses which to use

**Option 2:** Replace completely (recommended)
- Remove automatic loop from `run_optimization.py`
- Users must explicitly generate files first
- More transparent and controllable

**Recommendation:** Option 2 - forces users to see what compositions will be generated before running expensive calculations.

## File Organization

```
modules/
  ├── generate_percentages.py      # New module (main logic)
  └── alloy_loop.py                # Keep composition generation functions

bin/
  ├── generate_percentages.py      # New CLI script
  └── run_optimization.py          # Modified to ignore loop_perc

refs/
  └── GENERATE_PERCENTAGES_PLAN.md # This file

code-tests/
  └── test_generate_percentages.py # Unit tests
```

## Implementation Steps

1. **Create `modules/generate_percentages.py`**
   - Import composition generation functions from `alloy_loop.py`
   - Implement structure-agnostic concentration update
   - Implement YAML file generation

2. **Create `bin/generate_percentages.py`**
   - Command-line interface
   - Input validation
   - User feedback and summary

3. **Modify `bin/run_optimization.py`**
   - Remove loop_perc checking logic
   - Always run single workflow
   - Simplify code

4. **Update documentation**
   - Update `ALLOY_LOOP_USAGE.md` to reference new workflow
   - Add examples to README
   - Update config templates

5. **Create tests**
   - Unit tests for each function
   - Integration tests for full workflow
   - Test both CIF and parameter methods

6. **Update existing configs**
   - Add example master configs
   - Show before/after for migration

## Benefits of New Approach

### User Benefits
- **Control:** Submit calculations when ready
- **Review:** Inspect generated configs before running
- **Flexibility:** Run subset of compositions
- **Debugging:** Easier to test single composition
- **Resource Management:** Better SLURM job control

### Technical Benefits
- **Separation of Concerns:** Generation vs execution
- **Testability:** Each step testable independently
- **Transparency:** User sees all generated configs
- **Reproducibility:** Generated YAMLs are permanent records
- **Simplicity:** `run_optimization.py` becomes simpler

## Summary

This implementation plan creates a new `generate_percentages` module that:

1. ✅ Generates separate YAML files for each composition
2. ✅ Works with both CIF + substitutions and lattice parameters
3. ✅ Preserves all loop_perc modes (explicit, phase diagram, sweep)
4. ✅ Treats 0% as alloy (keeps element with 0.0 concentration)
5. ✅ Removes oxidation states from CIF files
6. ✅ Uses structure_builder.py as unified entry point
7. ✅ Disables loop_perc in generated files
8. ✅ Keeps CIF path reference (not copy)
9. ✅ Formats filenames with composition
10. ✅ Separates file generation from execution

The user workflow becomes: **Generate files → Review → Submit individually**
