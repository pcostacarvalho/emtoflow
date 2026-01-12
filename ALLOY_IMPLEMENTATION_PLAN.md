# Alloy Implementation Plan - CPA Random Alloys

## Objective
Implement support for disordered alloys using CPA (Coherent Potential Approximation) with built-in lattice templates. User provides: lattice type, elements, concentrations, and initial geometry parameters.

## Scope
- **Lattice types**: FCC, BCC, Simple Cubic (single inequivalent site only)
- **Alloy type**: Random single-site disorder (all elements on same sublattice)
- **IQ/IT/ITA rules**:
  - IQ = 1 (single atom in primitive cell)
  - IT = ITA = 1, 2, 3, ..., N (one per element)
  - All elements share same IQ but different IT/ITA

## Key Design Decisions

### 1. Built-in KSTR Templates
**Approach**: Store pre-generated KSTR files in repository

**Location**: `/templates/kstr/` or `/modules/inputs/kstr_templates/`

**Files needed**:
- `fcc_template.kstr`
- `bcc_template.kstr`
- `sc_template.kstr` (simple cubic)

**Questions**:
- Q1: Should these templates use unit lattice constants (a=1.0, c=1.0) that get scaled by user input?
- Q2: What BSM value should be in templates? (currently using lat_mapping)

### 2. User Input Interface
**Required inputs**:
- Lattice type: 'fcc', 'bcc', or 'sc'
- Elements: list of chemical symbols (e.g., ['Fe', 'Pt', 'Co'])
- Concentrations: list of floats (e.g., [0.5, 0.3, 0.2])
- Initial c/a ratio
- Initial SWS value

**Questions**:
- Q3: How should user provide input? Options:
  - Command line arguments: `--alloy --lattice fcc --elements Fe Pt --conc 0.5 0.5 --ca 1.0 --sws 2.65`
  - Config file (JSON/YAML): separate from CIF workflow
  - Interactive prompts
  - Prefer which approach?

- Q4: Should there be a job name/ID prefix like the current CIF workflow uses structure name?

### 3. Element Database
**Required data per element**:
- Symbol
- a_scr (screening parameter)
- b_scr (screening parameter)
- default_moment (initial magnetic moment)

**Current implementation**: In `cif_extraction.py`, hardcoded values:
```python
a_scr_map = {...}
b_scr_map = {...}
default_moments = {...}
```

**Questions**:
- Q5: Should we centralize this in a separate database file/module (e.g., `element_database.py`)?
- Q6: What elements should be supported initially? (periodic table subset)

### 4. KGRN Generation Modifications

**File to modify**: `modules/inputs/kgrn.py`

**Current atom entry format**:
```
Symb  IQ  IT ITA NRM  CONC      a_scr b_scr |Teta    Phi    FXM  m(split)
Fe     1   1   1   1  1.000000  0.900 1.000  0.0000  0.0000  N   2.2000
```

**New format for 3-element alloy (Fe₀.₅Pt₀.₃Co₀.₂)**:
```
Fe     1   1   1   1  0.500000  0.900 1.000  0.0000  0.0000  N   2.2000
Pt     1   2   2   1  0.300000  0.900 1.000  0.0000  0.0000  N   0.5000
Co     1   3   3   1  0.200000  0.900 1.000  0.0000  0.0000  N   1.6000
```

**Implementation approach**:
- Modify `create_kgrn_input()` to handle alloy mode
- Loop through elements with their concentrations
- Assign IT=ITA incrementally (1, 2, 3, ...)
- All entries have IQ=1 for single-site alloys

**Questions**:
- Q7: Should this be a separate function `create_kgrn_input_alloy()` or integrated into existing function with mode flag?

### 5. Structure Dict Format for Alloys

**Current structure dict** (from CIF parsing):
```python
{
    'lat': 1,
    'atom_info': [
        {'symbol': 'Fe', 'IQ': 1, 'IT': 1, 'ITA': 1, 'conc': 1.0, ...},
        {'symbol': 'Pt', 'IQ': 2, 'IT': 2, 'ITA': 1, 'conc': 1.0, ...}
    ]
}
```

**Proposed alloy structure dict**:
```python
{
    'lat': 1,  # or from BSM mapping
    'lattice_type': 'fcc',
    'is_alloy': True,
    'atom_info': [
        {'symbol': 'Fe', 'IQ': 1, 'IT': 1, 'ITA': 1, 'conc': 0.5, 'a_scr': 0.9, 'b_scr': 1.0, 'default_moment': 2.2},
        {'symbol': 'Pt', 'IQ': 1, 'IT': 2, 'ITA': 2, 'conc': 0.3, 'a_scr': 0.9, 'b_scr': 1.0, 'default_moment': 0.5},
        {'symbol': 'Co', 'IQ': 1, 'IT': 3, 'ITA': 3, 'conc': 0.2, 'a_scr': 0.9, 'b_scr': 1.0, 'default_moment': 1.6}
    ]
}
```

**Questions**:
- Q8: Should we create a new function `create_alloy_structure()` to build this dict?
- Q9: Where should initial c/a and SWS values be stored?

### 6. Workflow Integration

**Current workflow** (from main script):
1. Parse CIF → get structure
2. Create KSTR from structure
3. Create KGRN from structure
4. Run DMAX optimization (vary c/a, vary SWS, fit EOS)

**Proposed alloy workflow**:
1. Parse user input → get alloy specification
2. Load built-in KSTR template (no modification needed)
3. Create KGRN from alloy specification
4. Run DMAX optimization (same as current)

**Questions**:
- Q10: Should there be a separate main entry point (e.g., `main_alloy.py`) or integrate into existing main with mode flag?
- Q11: Job naming convention for alloys? Suggestion: `{lattice}_{elements}_{concentration}` → `fcc_fept_0.5_0.5`

### 7. Input Validation

**Required checks**:
1. Concentrations sum to 1.0 (with tolerance, e.g., |sum - 1.0| < 1e-6)
2. Number of elements matches number of concentrations
3. Valid lattice type ('fcc', 'bcc', 'sc')
4. Valid element symbols (check against database)
5. All concentrations > 0 and < 1
6. c/a and SWS are positive numbers

**Implementation**:
```python
def validate_alloy_input(lattice_type, elements, concentrations, ca_ratio, sws):
    """Validate alloy input parameters, raise ValueError if invalid"""
    # Check 1: concentration sum
    if abs(sum(concentrations) - 1.0) > 1e-6:
        raise ValueError(f"Concentrations must sum to 1.0, got {sum(concentrations)}")

    # Check 2: length match
    if len(elements) != len(concentrations):
        raise ValueError(f"Number of elements ({len(elements)}) must match concentrations ({len(concentrations)})")

    # ... additional checks
```

### 8. KSTR Template Structure

**Template considerations**:
- Templates should be lattice-agnostic (no specific element symbols)
- Use generic placeholders or just structural information
- KSTR files typically don't contain chemical info, just positions

**Questions**:
- Q12: Since KSTR only contains structural info (NQ, positions), do templates need any modification at runtime or can they be used as-is?
- Q13: Should templates include comments indicating lattice type?

### 9. Directory Structure

**Current structure** (CIF-based):
```
job_id/
  ├── kfcd/
  ├── smx/
  ├── pot/
  ├── chd/
  ├── shp/
  ├── tmp/
  └── *.dat files
```

**Questions**:
- Q14: Should alloy jobs use same directory structure?
- Q15: Should alloy and CIF jobs be in separate parent directories?

### 10. File Modifications Summary

**New files needed**:
- `/templates/kstr/fcc_template.kstr`
- `/templates/kstr/bcc_template.kstr`
- `/templates/kstr/sc_template.kstr`
- `/modules/alloy_input.py` (or similar - to handle alloy-specific logic)
- `/modules/element_database.py` (optional - centralize element data)

**Files to modify**:
- `modules/inputs/kgrn.py` - add alloy support to KGRN generation
- Main script - add alloy workflow mode

**Files unchanged**:
- `modules/inputs/kstr.py` - not used for alloys (built-in templates instead)
- `modules/inputs/dos.py` - DOS calculation unchanged
- `modules/cif_extraction.py` - CIF workflow remains separate

---

## Implementation Phases

### Phase 1: Foundation
1. Create element database with a_scr, b_scr, default_moment for common elements
2. Create built-in KSTR templates for FCC, BCC, SC
3. Implement input validation function

### Phase 2: Core Logic
4. Create alloy structure dict builder
5. Modify KGRN generation to handle alloy mode
6. Add lattice type to BSM mapping

### Phase 3: Integration
7. Create user input interface (after clarifying Q3)
8. Integrate into workflow (after clarifying Q10)
9. Test with example cases

### Phase 4: Testing
10. Test Fe-Pt FCC alloy at various concentrations
11. Test 3+ element alloys
12. Verify concentration validation
13. Confirm DMAX optimization workflow works

---

## Design Decisions - ANSWERS

**A1**: For cubic structures (a=b=c), axes are always normalized. No c/a optimization needed, only SWS optimization. User provides only initial SWS value.

**A2**: Templates will have both the `lat` parameter and corresponding BSX/BSY/BSZ vectors already set correctly for each lattice type.

**A3**: Pass information as dictionary (can be JSON) to main function. This should work for BOTH alloy AND CIF structures (unified interface).

**A4**: Job ID format: `concA_elementA_concB_elementB` (e.g., `0.5_Fe_0.5_Pt`). EMTO has max 12 characters limit - if exceeded, just use elements without concentrations.

**A5**: Yes, centralize `default_moments` in separate module. Keep `a_scr` and `b_scr` hardcoded (not in database).

**A6**: Support periodic table subset.

**A7**: Use flag in existing `create_kgrn_input()` function (not separate function).

**A8**: Use same dictionary structure for both CIF and alloy cases. Hardcode extra entries for CIF case where needed.

**A9**: Store initial SWS value in the structure dictionary.

**A10**: Integrate into existing main script with mode flag (not separate entry point).

**A11**: For concentration loops: each concentration gets its own folder. Inside that folder, do geometry optimization with naming: `id_name + c/s + sws` (same as current).

**A12**: Templates can be used as-is for simple lattices. Add warning for user to check DMAX. Hardcode correct DMAX value in each template.

**A13**: No need for comments in templates. Just put lattice type in the filename (e.g., `fcc_template.kstr`).

**A14**: Yes, use same directory structure for alloy jobs.

**A15**: No separate parent directories. It's a flag: either alloy OR CIF mode, not both simultaneously.

---

## Implementation Strategy (Based on Answers)

### Unified Input System
Both CIF and alloy workflows will use a **dictionary-based input system**:

**CIF mode dictionary**:
```python
{
    'mode': 'cif',
    'cif_file': 'path/to/structure.cif',
    'initial_sws': 2.65,
    'initial_ca': 1.0,  # if applicable
    # ... other params
}
```

**Alloy mode dictionary**:
```python
{
    'mode': 'alloy',
    'lattice_type': 'fcc',  # or 'bcc', 'sc'
    'elements': ['Fe', 'Pt'],
    'concentrations': [0.5, 0.5],
    'initial_sws': 2.65,
    # No initial_ca for cubic structures
}
```

### KSTR Template Files
Create three template files with hardcoded DMAX and correct BSX/BSY/BSZ:

1. **`templates/kstr/fcc.kstr`**: lat=2, BSX=[0.5,0.5,0.0], BSY=[0.0,0.5,0.5], BSZ=[0.5,0.0,0.5]
2. **`templates/kstr/bcc.kstr`**: lat=3, BSX=[0.5,0.5,-0.5], BSY=[-0.5,0.5,0.5], BSZ=[0.5,-0.5,0.5]
3. **`templates/kstr/sc.kstr`**: lat=1, BSX=[1.0,0.0,0.0], BSY=[0.0,1.0,0.0], BSZ=[0.0,0.0,1.0]

Each template is used **as-is**, no runtime modification needed.

### Element Database Module
Create `modules/element_database.py`:
```python
# Only default_moments (a_scr, b_scr stay hardcoded elsewhere)
DEFAULT_MOMENTS = {
    'Fe': 2.2,
    'Pt': 0.5,
    'Co': 1.6,
    'Ni': 0.6,
    # ... periodic table subset
}
```

### Structure Dictionary Unification
**Unified structure dict** (works for both CIF and alloy):
```python
{
    'lat': 2,  # Bravais lattice type (1-14)
    'is_alloy': True,  # or False for CIF
    'lattice_type': 'fcc',  # only for alloys
    'initial_sws': 2.65,
    'atom_info': [
        {
            'symbol': 'Fe',
            'IQ': 1,
            'IT': 1,
            'ITA': 1,
            'conc': 0.5,
            'a_scr': 0.9,
            'b_scr': 1.0,
            'default_moment': 2.2
        },
        {
            'symbol': 'Pt',
            'IQ': 1,  # Same IQ for single-site alloy
            'IT': 2,
            'ITA': 2,
            'conc': 0.5,
            'a_scr': 0.9,
            'b_scr': 1.0,
            'default_moment': 0.5
        }
    ],
    # For CIF mode, additional fields:
    'BSX': [...],
    'BSY': [...],
    'BSZ': [...],
    'fractional_coords': [...],
    # etc.
}
```

### Job Naming for Alloys
- Format: `concA_elementA_concB_elementB` (e.g., `0.5_Fe_0.5_Pt`)
- If > 12 characters (EMTO limit): use just elements (e.g., `FePt`, `FePtCo`)
- During optimization: add `c` or `s` suffix + value (e.g., `0.5_Fe_0.5_Pt_s_2.65`)

### Geometry Optimization for Cubic Alloys
- **No c/a optimization** (since a=b=c always)
- **Only SWS optimization**: vary SWS, fit equation of state
- User provides only `initial_sws` in input dictionary

### Concentration Loops
For multiple concentrations:
```
alloy_study/
  ├── conc_050_Fe_050_Pt/
  │   ├── kfcd/
  │   ├── smx/
  │   ├── 0.5_Fe_0.5_Pt_s_2.60.dat
  │   ├── 0.5_Fe_0.5_Pt_s_2.65.dat
  │   └── ...
  ├── conc_070_Fe_030_Pt/
  │   └── ...
```

Each concentration folder runs full DMAX optimization workflow.

### Modified KGRN Function
Modify `modules/inputs/kgrn.py`:
```python
def create_kgrn_input(structure, path, id_namev, id_namer, SWS):
    """
    Create KGRN input. Works for both CIF and alloy modes.

    If structure['is_alloy'] == True:
      - Loop through atom_info
      - All entries have same IQ
      - IT and ITA increment: 1, 2, 3, ...
      - Use provided concentrations

    If structure['is_alloy'] == False:
      - Use existing CIF-based logic
    """
    lat = structure['lat']
    is_alloy = structure.get('is_alloy', False)

    # Build atom section
    atom_lines = []
    if is_alloy:
        # Single-site alloy: all atoms have IQ=1, IT=ITA=1,2,3...
        for i, atom in enumerate(structure['atom_info'], start=1):
            line = (f"{atom['symbol']:<5} {atom['IQ']:>2} {i:>3} {i:>3} "
                    f"{1:>3}  {atom['conc']:.6f}  {atom['a_scr']:.3f} {atom['b_scr']:.3f}  "
                    f"0.0000  0.0000  N  {atom['default_moment']:>7.4f}")
            atom_lines.append(line)
    else:
        # Existing CIF logic
        for atom in structure['atom_info']:
            line = (f"{atom['symbol']:<5} {atom['IQ']:>2} {atom['IT']:>3} {atom['ITA']:>3} "
                    f"{1:>3}  {atom['conc']:.6f}  {atom['a_scr']:.3f} {atom['b_scr']:.3f}  "
                    f"0.0000  0.0000  N  {atom['default_moment']:>7.4f}")
            atom_lines.append(line)

    atoms_section = "\n".join(atom_lines)
    # ... rest of template generation
```

### Main Workflow Integration
Modify main script to accept dictionary input:

```python
def main(input_dict):
    """
    Unified main function for both CIF and alloy workflows.

    Parameters
    ----------
    input_dict : dict
        Input parameters. Must contain 'mode' key ('cif' or 'alloy').
    """

    if input_dict['mode'] == 'cif':
        # Parse CIF, generate structure dict
        structure = parse_emto_structure(input_dict['cif_file'])
        structure['is_alloy'] = False
        structure['initial_sws'] = input_dict['initial_sws']
        # ... existing CIF workflow

    elif input_dict['mode'] == 'alloy':
        # Validate alloy input
        validate_alloy_input(
            input_dict['lattice_type'],
            input_dict['elements'],
            input_dict['concentrations'],
            input_dict['initial_sws']
        )

        # Build structure dict for alloy
        structure = create_alloy_structure(
            lattice_type=input_dict['lattice_type'],
            elements=input_dict['elements'],
            concentrations=input_dict['concentrations'],
            initial_sws=input_dict['initial_sws']
        )

        # Copy built-in KSTR template (no modification)
        copy_kstr_template(input_dict['lattice_type'], output_path)

    # Common workflow for both modes
    create_kgrn_input(structure, ...)
    run_dmax_optimization(...)
```

### Input Validation Function
Create `modules/alloy_input.py`:
```python
def validate_alloy_input(lattice_type, elements, concentrations, sws):
    """Validate alloy input parameters."""

    # Check 1: Valid lattice type
    if lattice_type not in ['fcc', 'bcc', 'sc']:
        raise ValueError(f"Invalid lattice type: {lattice_type}")

    # Check 2: Length match
    if len(elements) != len(concentrations):
        raise ValueError(
            f"Number of elements ({len(elements)}) must match "
            f"number of concentrations ({len(concentrations)})"
        )

    # Check 3: Concentration sum
    if abs(sum(concentrations) - 1.0) > 1e-6:
        raise ValueError(
            f"Concentrations must sum to 1.0, got {sum(concentrations)}"
        )

    # Check 4: Concentration range
    for conc in concentrations:
        if conc <= 0 or conc >= 1:
            raise ValueError(
                f"All concentrations must be in range (0, 1), got {conc}"
            )

    # Check 5: Valid elements
    from modules.element_database import DEFAULT_MOMENTS
    for elem in elements:
        if elem not in DEFAULT_MOMENTS:
            raise ValueError(f"Unsupported element: {elem}")

    # Check 6: Positive SWS
    if sws <= 0:
        raise ValueError(f"SWS must be positive, got {sws}")

def create_alloy_structure(lattice_type, elements, concentrations, initial_sws):
    """Create unified structure dict for alloy."""
    from modules.element_database import DEFAULT_MOMENTS
    from modules.cif_extraction import a_scr_map, b_scr_map

    # Map lattice type to lat number
    lat_map = {'sc': 1, 'fcc': 2, 'bcc': 3}
    lat = lat_map[lattice_type]

    # Build atom_info
    atom_info = []
    for i, (elem, conc) in enumerate(zip(elements, concentrations), start=1):
        atom_info.append({
            'symbol': elem,
            'IQ': 1,  # Single site for all atoms
            'IT': i,
            'ITA': i,
            'conc': conc,
            'a_scr': a_scr_map.get(elem, 0.9),
            'b_scr': b_scr_map.get(elem, 1.0),
            'default_moment': DEFAULT_MOMENTS[elem]
        })

    return {
        'lat': lat,
        'is_alloy': True,
        'lattice_type': lattice_type,
        'initial_sws': initial_sws,
        'atom_info': atom_info
    }
```

---

## File Changes Summary

### New Files
1. `templates/kstr/fcc.kstr` - FCC KSTR template
2. `templates/kstr/bcc.kstr` - BCC KSTR template
3. `templates/kstr/sc.kstr` - Simple cubic KSTR template
4. `modules/element_database.py` - Default magnetic moments
5. `modules/alloy_input.py` - Validation and structure builder

### Modified Files
1. `modules/inputs/kgrn.py` - Add `is_alloy` flag handling
2. Main script - Add dictionary-based input, mode flag

### Unchanged Files
- `modules/inputs/dos.py` - DOS parsing unchanged
- `modules/lat_detector.py` - Lattice detection for CIF unchanged
- `modules/cif_extraction.py` - CIF parsing unchanged (but may import from element_database)
