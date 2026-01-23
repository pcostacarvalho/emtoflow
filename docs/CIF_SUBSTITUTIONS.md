# CIF Element Substitutions

## Overview

The `modules/structure_builder.py` module supports replacing elements in CIF files with alloy compositions using partial occupancies (CPA - Coherent Potential Approximation).

## Use Cases

**When to use CIF + substitutions:**
- You have a CIF file for an ordered structure (e.g., FePt L10)
- You want to replace one or more elements with an alloy composition
- All sites of the same element should receive the same substitution

**When to use parameter-based workflow instead:**
- You need site-specific control (different substitutions on inequivalent sites)
- You're creating a structure from scratch
- You want ordered structures with specific site occupancies

## Configuration

```yaml
# Required parameters
cif_file: "FePt.cif"

# Element substitutions
substitutions:
  Fe:
    elements: ['Fe', 'Co']
    concentrations: [0.7, 0.3]  # Fe70Co30
  Pt:
    elements: ['Pt']
    concentrations: [1.0]        # Pure Pt
```

## Validation Rules

1. **CIF file required**: Substitutions only work with CIF files
2. **All elements must exist**: Error if substitution references non-existent element
3. **Concentrations must sum to 1.0**: Each substitution must have valid concentrations
4. **Lists must match length**: Elements and concentrations lists must have same length
5. **No defaults**: Must provide concentrations even for single-element lists

## Workflow

1. Load CIF → pymatgen Structure
2. Apply substitutions → Modified Structure with partial occupancies
3. Parse to EMTO format → Structure dictionary
4. Generate inputs → KSTR, SHAPE, KGRN, KFCD files

## Example Output

The KGRN input will reflect the partial occupancies:

```
Atom data:
Symb  IQ  IT ITA SWS  CONC      a_scr b_scr  moment
Fe     1   1   1   1  0.700000  0.000 0.000  2.0000
Co     1   1   2   1  0.300000  0.000 0.000  1.7000
Pt     2   2   1   1  1.000000  0.000 0.000  0.4000
```

## Implementation

The substitution logic is in `modules/structure_builder.py`:
- `apply_substitutions_to_structure()`: Applies substitutions to pymatgen Structure
- Integrated into `create_emto_structure()` workflow
- Validation handled in `utils/config_parser.py`

## Comparison: CIF + Substitutions vs. Parameter Workflow

| Feature | CIF + Substitutions | Parameter Workflow |
|---------|--------------------|--------------------|
| **Input** | Existing CIF file | Lattice parameters |
| **Site control** | All sites of same element | Individual site control |
| **Use case** | Quick alloy variants | Custom structures |
| **Lattice detection** | Automatic | Manual (specify LAT) |
