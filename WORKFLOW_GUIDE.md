# EMTO Input Automation - Complete Workflow Guide

## Overview

This guide covers all supported workflows for EMTO input generation:
1. **CIF workflow** - Ordered structures from crystallographic files
2. **Parameter workflow** - Custom structures (alloys, ordered compounds)
3. **DMAX optimization** - Automated cutoff distance optimization

---

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

### With DMAX Optimization

```
                    optimize_dmax=True
                            │
                            ▼
                ┌───────────────────────────┐
                │ Create initial KSTR       │
                │ inputs with dmax_initial  │
                └───────────┬───────────────┘
                            │
                            ▼
                ┌───────────────────────────┐
                │ Run KSTR (non-blocking)   │
                │ Monitor .prn files        │
                │ Terminate early (~0.1s)   │
                └───────────┬───────────────┘
                            │
                            ▼
                ┌───────────────────────────┐
                │ Find optimal DMAX values  │
                │ Ensure shell consistency  │
                └───────────┬───────────────┘
                            │
                            ▼
                ┌───────────────────────────┐
                │ Generate final inputs     │
                │ with optimized DMAX       │
                └───────────────────────────┘
```

---

## Workflow 1: CIF-Based Structures

For ordered structures with crystallographic data.

### Example: Pure FCC Copper

```python
from modules.workflows import create_emto_inputs

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

### Example: L10 FePt from CIF

```python
create_emto_inputs(
    output_path="./fept_l10",
    job_name="fept",
    cif_file="FePt.cif",
    dmax=1.3,
    ca_ratios=[0.92, 0.96, 1.00, 1.04],
    sws_values=[2.60, 2.65, 2.70],
    magnetic='F'
)
```

**Features:**
- Auto-detects LAT parameter
- Extracts inequivalent atoms from symmetry
- Determines c/a ratio from structure
- Calculates SWS from volume if not provided

---

## Workflow 2: Parameter-Based Structures (Alloys)

For custom structures defined by lattice parameters and atomic sites.

### Example: FCC Random Alloy (CPA)

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

### Example: L10 Ordered Structure

```python
# L10 FePt (two sublattices)
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

### Example: Ternary Random Alloy

```python
# Fe-Co-Ni alloy
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

### Example: HCP Structure with Auto-Defaults

```python
# HCP Co (c and gamma auto-determined)
sites = [{'position': [0, 0, 0],
          'elements': ['Co'],
          'concentrations': [1.0]}]

create_emto_inputs(
    output_path="./co_hcp",
    job_name="co",
    lat=4,  # HCP
    a=2.51,  # c=1.633*a and gamma=120° set automatically
    sites=sites,
    dmax=1.3,
    sws_values=[2.55, 2.60],
    magnetic='F'
)
```

**Features:**
- All 14 EMTO lattice types supported
- CPA (random) and ordered structures
- Smart defaults for cubic and HCP systems
- Custom magnetic moments per element

---

## Workflow 3: DMAX Optimization

Automatically finds optimal cutoff distances for consistent neighbor shells across c/a ratios.

### Basic Example

```python
create_emto_inputs(
    output_path="./fept_optimized",
    job_name="fept",
    cif_file="FePt.cif",
    ca_ratios=[0.92, 0.96, 1.00, 1.04],
    sws_values=[2.60, 2.65, 2.70],
    magnetic='F',
    # DMAX optimization parameters
    optimize_dmax=True,
    dmax_initial=2.5,
    dmax_target_vectors=100,
    dmax_vector_tolerance=15,
    kstr_executable="/path/to/kstr.exe"
)
```

### With Parameter Workflow

```python
# DMAX optimization for Fe-Pt alloy
sites = [{'position': [0, 0, 0],
          'elements': ['Fe', 'Pt'],
          'concentrations': [0.5, 0.5]}]

create_emto_inputs(
    output_path="./fept_alloy_opt",
    job_name="fept",
    lat=2,
    a=3.7,
    sites=sites,
    ca_ratios=[0.96, 1.00, 1.04, 1.08],
    sws_values=[2.60, 2.65, 2.70],
    magnetic='F',
    optimize_dmax=True,
    dmax_initial=2.5,
    dmax_target_vectors=100,
    kstr_executable="/path/to/kstr.exe"
)
```

**How it works:**
1. Creates KSTR inputs with `dmax_initial` for all c/a ratios
2. Runs KSTR calculations with early termination (~0.1s per ratio)
3. Extracts neighbor shell data from `.prn` files
4. Finds DMAX values giving consistent shell numbers
5. Generates final inputs with optimized DMAX values

**Performance:**
- Traditional: 30-60s per ratio
- Optimized: ~0.1s per ratio
- Speedup: ~300-600x

**See:** [DMAX_OPTIMIZATION.md](DMAX_OPTIMIZATION.md) for full documentation.

---

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
- **Ordered (2 sites):** Two separate site dictionaries with different positions

---

## Supported Lattice Types (LAT 1-14)

| LAT | Name | Crystal System | Required Parameters |
|-----|------|----------------|---------------------|
| 1 | SC | Cubic | `a` |
| 2 | FCC | Cubic | `a` |
| 3 | BCC | Cubic | `a` |
| 4 | HCP | Hexagonal | `a`, `c` (auto: c=1.633a) |
| 5 | BCT | Tetragonal | `a`, `c` |
| 6 | ST | Tetragonal | `a`, `c` |
| 7 | ORC | Orthorhombic | `a`, `b`, `c` |
| 8 | ORCF | Orthorhombic | `a`, `b`, `c` |
| 9 | ORCI | Orthorhombic | `a`, `b`, `c` |
| 10 | ORCC | Orthorhombic | `a`, `b`, `c` |
| 11 | HEX | Hexagonal | `a`, `c` |
| 12 | RHL | Rhombohedral | `a`, `alpha` |
| 13 | MCL | Monoclinic | `a`, `b`, `c`, `beta` |
| 14 | MCLC | Monoclinic | `a`, `b`, `c`, `beta` |

**See:** [LATTICE_TYPES.md](LATTICE_TYPES.md) for complete reference with primitive vectors.

---

## Common Parameters

### Required
- `output_path`: Base directory for outputs
- `job_name`: Job identifier (max 10 chars including ratio suffix)
- `cif_file` OR `(lat, a, sites)`: Structure specification
- `magnetic`: 'P' (paramagnetic) or 'F' (ferromagnetic)

### Optional
- `dmax`: Maximum distance parameter (default: 1.8)
- `ca_ratios`: List of c/a ratios (default: from structure)
- `sws_values`: Wigner-Seitz radii (default: calculated from structure)
- `user_magnetic_moments`: Custom magnetic moments dict
- `create_job_script`: Generate SLURM script (default: True)
- `job_mode`: 'serial' or 'parallel' (default: 'serial')

### DMAX Optimization
- `optimize_dmax`: Enable optimization (default: False)
- `dmax_initial`: Initial DMAX guess (default: 2.0)
- `dmax_target_vectors`: Target k-vectors (default: 100)
- `dmax_vector_tolerance`: Tolerance (default: 15)
- `kstr_executable`: Path to KSTR executable (required if optimizing)

---

## Job Name Constraints

Job names are limited to 10 characters (including ratio suffix) due to Fortran format:

```python
# Valid
job_name="fe"      # "fe_1.00" = 7 chars ✓
job_name="fept"    # "fept_0.92" = 9 chars ✓

# Invalid
job_name="fept_alloy"  # "fept_alloy_1.00" = 15 chars ✗
```

The code validates and raises a clear error if the name is too long.

---

## Custom Magnetic Moments

Override default magnetic moments per element:

```python
create_emto_inputs(
    ...,
    user_magnetic_moments={'Fe': 2.5, 'Pt': 0.4}
)
```

---

## Output Structure

```
output_path/
├── smx/
│   ├── jobname_ratio.dat         # KSTR input files
│   └── logs/                     # KSTR outputs (if optimizing)
│       ├── *.prn                 # Neighbor shell data
│       ├── *.log                 # KSTR logs
│       └── *_dmax_optimization.log
├── shp/
│   └── jobname_ratio.dat         # SHAPE input files
├── pot/                          # Potential directory
├── chd/                          # Charge density directory
├── fcd/
│   └── jobname_ratio_sws.dat     # KFCD input files
├── tmp/                          # Temporary files
├── jobname_ratio_sws.dat         # KGRN input files
└── run_jobname.sh                # SLURM job script
```

---

## Key Features

✅ **Unified Workflow**
- Both CIF and parameter inputs use same code path
- Single entry point: `create_emto_structure()`

✅ **All 14 Lattice Types**
- Full support for cubic, tetragonal, hexagonal, orthorhombic, monoclinic, rhombohedral

✅ **Smart Defaults**
- Cubic: b=a, c=a automatically
- HCP: c=1.633*a, γ=120° automatically

✅ **CPA Support**
- Correct ITA and concentration extraction
- Multi-component alloys (binary, ternary, quaternary, etc.)

✅ **Ordered Structures**
- L10, L12, B2, Heusler, and custom ordered compounds
- Multiple inequivalent sites

✅ **DMAX Optimization**
- Automated cutoff distance optimization
- Early subprocess termination (~300-600x speedup)
- Consistent neighbor shells across c/a ratios

✅ **Job Management**
- SLURM script generation
- Serial and parallel modes
- Configurable time/resources

---

## Advanced Examples

### Multi-Component High-Entropy Alloy

```python
# CoCrFeMnNi (Cantor alloy)
sites = [{'position': [0, 0, 0],
          'elements': ['Co', 'Cr', 'Fe', 'Mn', 'Ni'],
          'concentrations': [0.2, 0.2, 0.2, 0.2, 0.2]}]

create_emto_inputs(
    output_path="./cantor_alloy",
    job_name="cantor",
    lat=2,  # FCC
    a=3.6,
    sites=sites,
    dmax=1.3,
    sws_values=[2.55, 2.60, 2.65],
    magnetic='F',
    user_magnetic_moments={
        'Co': 1.6, 'Cr': 0.0, 'Fe': 2.2, 'Mn': 2.3, 'Ni': 0.6
    }
)
```

### Full c/a and SWS Sweep with Optimization

```python
create_emto_inputs(
    output_path="./fept_full_sweep",
    job_name="fept",
    cif_file="FePt.cif",
    ca_ratios=[0.88, 0.92, 0.96, 1.00, 1.04, 1.08],
    sws_values=[2.55, 2.60, 2.65, 2.70, 2.75],
    magnetic='F',
    optimize_dmax=True,
    dmax_initial=2.8,
    dmax_target_vectors=100,
    kstr_executable="/path/to/kstr.exe",
    create_job_script=True,
    job_mode='parallel',
    prcs=4,
    time="24:00:00",
    account="your_account"
)
```

This creates:
- 6 KSTR files (one per c/a ratio, DMAX optimized)
- 6 SHAPE files
- 30 KGRN files (6 ratios × 5 SWS values)
- 30 KFCD files
- Parallel SLURM scripts for efficient execution

---

## Function Call Chain

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
# Optional DMAX optimization:
if optimize_dmax:
    dmax_per_ratio = _run_dmax_optimization(...)
    ↓
# Generate all input files:
create_kstr_input(structure, ...)
create_shape_input(structure, ...)
create_kgrn_input(structure, ...)
create_kfcd_input(structure, ...)
```

---

## Troubleshooting

### Job name too long
```
ValueError: Job name 'my_system' is too long (12 chars)
```
**Solution:** Use shorter names (max 10 chars including ratio)

### Missing c for HCP
```
ValueError: HCP requires both 'a' and 'c' parameters
```
**Solution:** Provide `c` parameter or let it default to `c=1.633*a`

### DMAX too small
```
ERROR: Could not find Shell X for all ratios
```
**Solution:** Increase `dmax_initial` parameter

---

## See Also

- [DMAX_OPTIMIZATION.md](DMAX_OPTIMIZATION.md) - Complete DMAX optimization guide
- [LATTICE_TYPES.md](LATTICE_TYPES.md) - Lattice type reference and primitive vectors
- [README.md](README.md) - Quick start and installation
