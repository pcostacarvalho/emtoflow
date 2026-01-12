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

## Questions Summary (Requires User Input)

**Q1**: Should KSTR templates use unit lattice constants (a=1.0) that get scaled?

**Q2**: What BSM value for templates?

**Q3**: Preferred user input method? (CLI args / config file / interactive)

**Q4**: Job naming convention for alloys?

**Q5**: Centralize element database in separate module?

**Q6**: Which elements to support initially?

**Q7**: Separate function for alloy KGRN or integrated with flag?

**Q8**: Create new `create_alloy_structure()` function?

**Q9**: Where to store initial c/a and SWS values?

**Q10**: Separate entry point or integrated with mode flag?

**Q11**: Job naming suggestion: `{lattice}_{elements}_{concentration}`?

**Q12**: Do KSTR templates need runtime modification?

**Q13**: Should templates include lattice type comments?

**Q14**: Same directory structure for alloy jobs?

**Q15**: Separate alloy/CIF parent directories?
