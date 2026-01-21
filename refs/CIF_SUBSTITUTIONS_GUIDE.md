# CIF Element Substitutions Guide
 
## Overview
 
The CIF substitutions feature allows you to create alloy structures from pure element CIF files by replacing elements with partial occupancies (CPA - Coherent Potential Approximation).
 
## Use Cases
 
**When to use CIF + substitutions:**
- You have a CIF file for an ordered structure (e.g., FePt L10)
- You want to replace one or more elements with an alloy composition
- All sites of the same element should receive the same substitution
 
**When to use parameter-based workflow instead:**
- You need site-specific control (different substitutions on inequivalent sites)
- You're creating a structure from scratch
- You want ordered structures with specific site occupancies
 
## YAML Configuration
 
### Basic Example: Fe-Co/Pt Alloy from FePt CIF
 
```yaml
# Required parameters
output_path: "FeCoPt_alloy"
job_name: "fecoYaml"
 
# CIF file input
cif_file: "FePt.cif"
 
# Element substitutions
substitutions:
  Fe:
    elements: ['Fe', 'Co']
    concentrations: [0.7, 0.3]  # Fe70Co30
  Pt:
    elements: ['Pt']
    concentrations: [1.0]        # Pure Pt
 
# Rest of configuration
dmax: 1.3
magnetic: 'F'
sws_values: [2.60, 2.65, 2.70]
```
 
**Result:** All Fe sites in the CIF become Fe0.7Co0.3, all Pt sites remain pure Pt.
 
### Example: No Substitutions (Regular CIF)
 
```yaml
cif_file: "FePt.cif"
substitutions: null  # or omit this key entirely
```
 
**Result:** Standard CIF workflow with no element substitutions.
 
## Configuration Rules
 
### Required Fields
 
- `cif_file`: Must be provided (substitutions only work with CIF files)
- `elements`: List of element symbols (must be provided)
- `concentrations`: List of concentrations (must be provided, no defaults)
 
### Validation Rules
 
1. **CIF file required**: Substitutions only work with CIF files
   ```yaml
   # ✗ WRONG - cannot use substitutions with parameter input
   lat: 2
   a: 3.7
   substitutions: {...}  # ERROR!
   ```
 
2. **All elements must exist in CIF**: Error if substitution references non-existent element
   ```yaml
   cif_file: "FePt.cif"  # Contains Fe and Pt only
   substitutions:
     Co: {...}  # ERROR: Co not in structure
   ```
 
3. **Concentrations must sum to 1.0**: Each substitution must have valid concentrations
   ```yaml
   # ✗ WRONG - concentrations sum to 1.1
   substitutions:
     Fe:
       elements: ['Fe', 'Co']
       concentrations: [0.7, 0.4]  # ERROR: 0.7 + 0.4 = 1.1
   ```
 
4. **Lists must match length**: Elements and concentrations lists must have same length
   ```yaml
   # ✗ WRONG - length mismatch
   substitutions:
     Fe:
       elements: ['Fe', 'Co', 'Ni']
       concentrations: [0.5, 0.5]  # ERROR: 3 elements, 2 concentrations
   ```
 
5. **No defaults**: Must provide concentrations even for single-element lists
   ```yaml
   # ✗ WRONG - missing concentrations
   substitutions:
     Pt:
       elements: ['Pt']
       # concentrations missing - ERROR!
 
   # ✓ CORRECT
   substitutions:
     Pt:
       elements: ['Pt']
       concentrations: [1.0]
   ```
 
## Workflow Details
 
### Internal Processing
 
When you provide substitutions, the workflow:
 
1. **Load CIF** → pymatgen Structure
2. **Apply substitutions** → Modified Structure with partial occupancies
3. **Parse to EMTO format** → Structure dictionary
4. **Generate inputs** → KSTR, SHAPE, KGRN, KFCD files
 
### Console Output
 
```
Parsing CIF file: FePt.cif
  Applying element substitutions:
    Fe → [Fe, Co] with concentrations [0.700, 0.300]
    Pt → [Pt] with concentrations [1.000]
 
  Detected lattice: LAT=5 (Body-centered tetragonal)
  Number of atoms: NQ3=2
  ...
```
 
### Generated Structure
 
The KGRN input will reflect the partial occupancies:
 
```
Atom data:
Symb  IQ  IT ITA SWS  CONC      a_scr b_scr  moment
Fe     1   1   1   1  0.700000  0.000 0.000  2.0000
Co     1   1   2   1  0.300000  0.000 0.000  1.7000
Pt     2   2   1   1  1.000000  0.000 0.000  0.4000
```
 
## Advanced Examples
 
### Binary Alloy on All Sites
 
Replace both elements in a binary structure:
 
```yaml
cif_file: "NiAl.cif"
substitutions:
  Ni:
    elements: ['Ni', 'Co']
    concentrations: [0.5, 0.5]
  Al:
    elements: ['Al', 'Ga']
    concentrations: [0.8, 0.2]
```
 
**Result:** All Ni → Ni50Co50, all Al → Al80Ga20
 
### Ternary Alloy Substitution
 
Replace one element with a three-component alloy:
 
```yaml
cif_file: "FePt.cif"
substitutions:
  Fe:
    elements: ['Fe', 'Co', 'Ni']
    concentrations: [0.5, 0.3, 0.2]
  Pt:
    elements: ['Pt']
    concentrations: [1.0]
```
 
**Result:** All Fe → Fe50Co30Ni20, all Pt remains pure
 
### Selective Substitution
 
Only replace some elements, leave others unchanged:
 
```yaml
cif_file: "FeNiCo.cif"
substitutions:
  Fe:
    elements: ['Fe', 'Cr']
    concentrations: [0.9, 0.1]
  # Ni and Co not in substitutions → remain unchanged
```
 
**Result:** Fe → Fe90Cr10, Ni and Co unchanged
 
## Error Messages
 
Common validation errors and solutions:
 
### Error: "substitutions is only supported with CIF files"
 
```
ConfigValidationError: substitutions is only supported with CIF files.
If using parameter-based structure (lat, a, sites), define the alloy directly in 'sites'.
```
 
**Solution:** Use parameter workflow instead:
```yaml
lat: 2
a: 3.7
sites:
  - position: [0, 0, 0]
    elements: ['Fe', 'Co']
    concentrations: [0.7, 0.3]
```
 
### Error: "Element 'X' in substitutions not found in CIF structure"
 
```
ValueError: Element 'Co' in substitutions not found in CIF structure.
Available elements: Fe, Pt
```
 
**Solution:** Check the CIF file - make sure the element exists
 
### Error: "concentrations must sum to 1.0"
 
```
ConfigValidationError: Substitution for 'Fe': concentrations must sum to 1.0, got: 0.95
```
 
**Solution:** Fix concentrations to sum exactly to 1.0:
```yaml
concentrations: [0.7, 0.3]  # 0.7 + 0.3 = 1.0 ✓
```
 
## Integration with Optimization Workflow
 
Substitutions work seamlessly with the full optimization workflow:
 
```yaml
output_path: "FeCoPt_optimization"
job_name: "fecooptim"
 
# Structure input
cif_file: "FePt.cif"
substitutions:
  Fe:
    elements: ['Fe', 'Co']
    concentrations: [0.7, 0.3]
  Pt:
    elements: ['Pt']
    concentrations: [1.0]
 
# Optimization phases
optimize_ca: true
optimize_sws: true
initial_sws: [2.65]
 
# EMTO parameters
dmax: 1.3
magnetic: 'F'
 
# ... rest of config
```
 
The optimization workflow will:
1. Apply substitutions to create alloy structure
2. Run c/a optimization (Phase 1)
3. Run SWS optimization (Phase 2)
4. Perform final calculation (Phase 3)
5. Generate results and plots
 
## Comparison: CIF + Substitutions vs. Parameter Workflow
 
| Feature | CIF + Substitutions | Parameter Workflow |
|---------|--------------------|--------------------|
| **Input** | Existing CIF file | Lattice parameters |
| **Site control** | All sites of same element | Individual site control |
| **Use case** | Quick alloy variants | Custom structures |
| **Lattice detection** | Automatic | Manual (specify LAT) |
| **Best for** | Experimental structures | Hypothetical alloys |
 
## Implementation Details
 
### Files Modified
 
1. **`utils/config_parser.py`**
   - Added `validate_substitutions_config()` function
   - Added `substitutions: None` default
 
2. **`modules/structure_builder.py`**
   - Added `apply_substitutions_to_structure()` function
   - Modified `create_emto_structure()` to accept `structure_pmg` parameter
 
3. **`modules/create_input.py`**
   - Import `apply_substitutions_to_structure`
   - Extract `substitutions` from config
   - Apply substitutions before EMTO conversion
 
4. **`refs/optimization_config_template.yaml`**
   - Added substitutions section with examples
 
### Design Principles
 
Following `DEVELOPMENT_GUIDELINES.md`:
 
- ✓ **Centralized validation** in `config_parser.py`
- ✓ **Centralized defaults** in `apply_config_defaults()`
- ✓ **Explicit configuration** with `null` for unused features
- ✓ **Modular implementation** with clear separation of concerns
 
## See Also
 
- `ALLOY_WORKFLOW_GUIDE.md` - Parameter-based alloy creation
- `DEVELOPMENT_GUIDELINES.md` - Code design principles
- `optimization_config_template.yaml` - Complete configuration template