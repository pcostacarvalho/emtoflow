# EMTO Input Automation - Alloy Support Complete! 🎉

## Workflow Architecture

### Unified Structure Creation Flow

```
USER INPUT
    │
    ├──► CIF File Path ─────┐
    │                       │
    └──► Parameters         │
         • lat (1-14)       │
         • a, b, c          │
         • sites            │
         • alpha,beta,gamma │
                            │
                            ▼
                ┌───────────────────────────┐
                │ create_emto_structure()   │
                │ (modules/structure        │
                │  _builder.py)             │
                └───────────┬───────────────┘
                            │
                            ▼
                ┌───────────────────────────┐
                │ Structure Dictionary      │
                │ • lat, lattice_name       │
                │ • NQ3, NL                 │
                │ • atom_info (IQ,IT,ITA)   │
                │ • BSX, BSY, BSZ           │
                │ • a, b, c, boa, coa       │
                └───────────┬───────────────┘
                            │
      ┌─────────────────────┼─────────────────────┐
      │                     │                     │
      ▼                     ▼                     ▼
┌──────────┐        ┌──────────┐         ┌──────────┐
│  KSTR    │        │  SHAPE   │         │  KGRN    │
│  Input   │        │  Input   │         │  Input   │
│ Generator│        │ Generator│         │ Generator│
└──────────┘        └──────────┘         └──────────┘
      │                     │                     │
      ▼                     ▼                     ▼
  smx/*.dat            shp/*.dat            *.dat
```

### Function Call Chain

```python
# User calls:
create_emto_inputs(
    cif_file="Cu.cif"          # OR
    lat=2, a=3.7, sites=[...]  # Parameter workflow
)
    ↓
# Internally calls:
structure = create_emto_structure(
    cif_file=... OR lat=, a=, sites=...
)
    ↓
# Which calls (for parameter workflow):
structure_pmg = create_structure_from_params(lat, a, sites, ...)
    ↓
# Then converts to EMTO dict:
structure_dict = _structure_to_emto_dict(structure_pmg)
    ↓
# Finally generates all input files:
create_kstr_input(structure_dict, ...)
create_shape_input(structure_dict, ...)
create_kgrn_input(structure_dict, ...)
create_kfcd_input(structure_dict, ...)
```

## Complete Examples

### Example 1: CIF Workflow (Ordered Structures)

```python
from modules.workflows import create_emto_inputs

# Pure FCC Cu from CIF
create_emto_inputs(
    output_path="./cu_calc",
    job_name="cu",
    cif_file="Cu.cif",
    dmax=1.3,
    ca_ratios=[1.00],
    sws_values=[2.60, 2.65, 2.70],
    magnetic='P'
)
```

### Example 2: FCC Random Alloy (CPA)

```python
# Fe-Pt 50-50 random alloy
sites = [{'position': [0, 0, 0],
          'elements': ['Fe', 'Pt'],
          'concentrations': [0.5, 0.5]}]

create_emto_inputs(
    output_path="./fept_alloy",
    job_name="fept",
    lat=2,  # FCC
    a=3.7,  # Lattice parameter (Angstroms)
    sites=sites,
    dmax=1.3,
    ca_ratios=[1.00],
    sws_values=[2.60, 2.65, 2.70],
    magnetic='F'
)
```

### Example 3: L10 Ordered Structure

```python
# L10 FePt (ordered, two sublattices)
sites = [
    {'position': [0, 0, 0], 'elements': ['Fe'], 'concentrations': [1.0]},
    {'position': [0.5, 0.5, 0.5], 'elements': ['Pt'], 'concentrations': [1.0]}
]

create_emto_inputs(
    output_path="./fept_l10",
    job_name="fept_l10",
    lat=5,  # Body-centered tetragonal
    a=3.7,
    c=3.7 * 0.96,  # Tetragonal distortion
    sites=sites,
    dmax=1.3,
    ca_ratios=[0.96],
    sws_values=[2.60, 2.65],
    magnetic='F'
)
```

### Example 4: Ternary Random Alloy

```python
# Fe-Co-Ni Cantor alloy component
sites = [{'position': [0, 0, 0],
          'elements': ['Fe', 'Co', 'Ni'],
          'concentrations': [0.33, 0.33, 0.34]}]

create_emto_inputs(
    output_path="./feconi",
    job_name="feconi",
    lat=2,  # FCC
    a=3.6,
    sites=sites,
    dmax=1.3,
    sws_values=[2.55, 2.60, 2.65],
    magnetic='F'
)
```

### Example 5: HCP with Defaults

```python
# HCP Co (automatic c/a = 1.633, gamma = 120°)
sites = [{'position': [0, 0, 0],
          'elements': ['Co'],
          'concentrations': [1.0]}]

create_emto_inputs(
    output_path="./co_hcp",
    job_name="co",
    lat=4,  # HCP
    a=2.51,  # c and gamma auto-determined
    sites=sites,
    dmax=1.3,
    sws_values=[2.55, 2.60],
    magnetic='F'
)
```

## Supported Lattice Types (LAT 1-14)

| LAT | Name | Notes |
|-----|------|-------|
| 1 | Simple cubic (SC) | a=b=c, α=β=γ=90° |
| 2 | Face-centered cubic (FCC) | Most alloys |
| 3 | Body-centered cubic (BCC) | Fe, Cr, W, etc. |
| 4 | Hexagonal (HCP) | Auto: c=1.633a, γ=120° |
| 5 | Simple tetragonal (ST) | L10, L12 structures |
| 6 | Body-centered tetragonal (BCT) | — |
| 7-14 | Orthorhombic, Monoclinic, Triclinic, Rhombohedral | Full support |

## Sites Specification Format

```python
sites = [
    {
        'position': [x, y, z],           # Fractional coordinates (0-1)
        'elements': ['El1', 'El2', ...], # Element symbols
        'concentrations': [c1, c2, ...]  # Must sum to 1.0
    },
    # ... more sites for ordered structures
]
```

**Examples:**
- **Pure element:** `{'position': [0,0,0], 'elements': ['Cu'], 'concentrations': [1.0]}`
- **Binary CPA:** `{'position': [0,0,0], 'elements': ['Fe','Pt'], 'concentrations': [0.5,0.5]}`
- **Ternary CPA:** `{'position': [0,0,0], 'elements': ['Fe','Co','Ni'], 'concentrations': [0.33,0.33,0.34]}`

## Key Features of New Implementation

✅ **Unified Workflow**
- Both CIF and parameter inputs use same code path
- Single entry point: `create_emto_structure()`

✅ **All 14 Lattice Types**
- Not limited to FCC/BCC/SC
- Full support for HCP, tetragonal, orthorhombic, etc.

✅ **Smart Defaults**
- Cubic: b=a, c=a automatically
- HCP: c=1.633*a, γ=120° automatically

✅ **Proper CPA Support**
- Correct ITA and concentration extraction
- Multi-component alloys (binary, ternary, etc.)

✅ **Ordered Structures**
- L10, L12, B2, Heusler, etc.
- Multiple inequivalent sites

✅ **Generalized SWS Conversion**
- Uses pymatgen to calculate atoms per cell
- Works for any lattice type

✅ **Custom Magnetic Moments**
```python
create_emto_inputs(
    ...,
    user_magnetic_moments={'Fe': 2.5, 'Pt': 0.4}
)
```

## What Changed?

**Before (Old Alloy Implementation):**
- Template files needed (fcc.kstr, bcc.kstr)
- Only FCC, BCC, SC supported
- Separate code path from CIF workflow
- Hard-coded IT/ITA assignments

**After (New Implementation):**
- No template files needed
- All 14 lattice types supported
- Unified with CIF workflow
- Automatic IT/ITA from symmetry analysis
- 453 lines of code removed

## Module Organization

```
modules/
├── structure_builder.py    # NEW! Unified structure creation
│   ├── lattice_param_to_sws()
│   ├── create_structure_from_params()
│   ├── create_emto_structure()      # Main entry point
│   └── _structure_to_emto_dict()
├── workflows.py            # UPDATED! Simplified
├── lat_detector.py         # Backward compatibility
└── inputs/
    ├── kstr.py             # Unchanged
    ├── shape.py            # Unchanged
    ├── kgrn.py             # SIMPLIFIED! Single code path
    └── kfcd.py             # Unchanged
```

## Testing

All test files verify functionality:
- `test_cpa_fix.py` - ITA/concentration extraction for CPA alloys
- `test_step2_structure_builder.py` - Structure builder module
- `test_step3_workflow.py` - Full workflow integration

Run tests locally (requires pymatgen):
```bash
python test_step2_structure_builder.py
python test_step3_workflow.py
```

---

**Last Updated:** January 13, 2026
**Status:** Alloy implementation complete (Steps 1-6)
