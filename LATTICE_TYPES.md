# EMTO Lattice Types Reference

## Lattice Type (LAT) Parameter

The `lat` parameter in EMTO specifies the Bravais lattice type. Values range from 1 to 14.

| LAT | Name | Crystal System | Description |
|-----|------|----------------|-------------|
| 1 | SC | Cubic | Simple cubic |
| 2 | FCC | Cubic | Face-centered cubic |
| 3 | BCC | Cubic | Body-centered cubic |
| 4 | HCP | Hexagonal | Hexagonal close-packed |
| 5 | BCT | Tetragonal | Body-centered tetragonal |
| 6 | ST | Tetragonal | Simple tetragonal |
| 7 | ORC | Orthorhombic | C-centered orthorhombic |
| 8 | ORCF | Orthorhombic | Face-centered orthorhombic |
| 9 | ORCI | Orthorhombic | Body-centered orthorhombic |
| 10 | ORCC | Orthorhombic | Base-centered orthorhombic |
| 11 | HEX | Hexagonal | Simple hexagonal |
| 12 | RHL | Rhombohedral | Rhombohedral |
| 13 | MCL | Monoclinic | Base-centered monoclinic |
| 14 | MCLC | Monoclinic | C-centered monoclinic |

## Common Examples

### Cubic Systems
- **SC (1)**: Po (Polonium)
- **FCC (2)**: Cu, Al, Ag, Au, Ni, Pt, Pb
- **BCC (3)**: Fe, Cr, Mo, W, V

### Tetragonal Systems
- **BCT (5)**: In, Sn (white tin)
- **ST (6)**: TiO₂ (rutile)

### Hexagonal Systems
- **HCP (4)**: Mg, Ti, Co, Zn, Cd
- **HEX (11)**: Graphite structure

### Others
- **RHL (12)**: Bi, Sb, As
- **ORCF (8)**: α-U (uranium)

## Auto-Detection

When using CIF files, the toolkit automatically detects the lattice type:

```python
from modules.workflows import create_emto_inputs

# LAT is auto-detected from CIF
create_emto_inputs(
    output_path="./output",
    job_name="cu",
    cif_file="./Cu.cif",  # Will detect LAT=2 (FCC)
    dmax=1.3,
    magnetic='P'
)
```

## Manual Specification

For alloy calculations or custom structures, specify `lat` directly:

```python
# FCC Fe-Pt alloy
sites = [{'position': [0, 0, 0],
          'elements': ['Fe', 'Pt'],
          'concentrations': [0.5, 0.5]}]

create_emto_inputs(
    output_path="./fept_alloy",
    job_name="fept",
    lat=2,  # FCC
    a=3.7,
    sites=sites,
    dmax=1.3,
    sws_values=[2.60, 2.65, 2.70],
    magnetic='F'
)
```

## Lattice Parameters by System

| Crystal System | Required Parameters | Optional |
|----------------|---------------------|----------|
| Cubic (1-3) | `a` | - |
| Tetragonal (5-6) | `a`, `c` | - |
| Hexagonal (4, 11) | `a`, `c` | - |
| Orthorhombic (7-10) | `a`, `b`, `c` | - |
| Rhombohedral (12) | `a` | `alpha` |
| Monoclinic (13-14) | `a`, `b`, `c` | `beta` |

### Notes

- For cubic systems: `b=a`, `c=a` (automatically set)
- For HCP (LAT=4): `c/a` ratio typically ~1.633
- For tetragonal: `c/a` ratio defines distortion from cubic
- All angles default to 90° except:
  - HCP: gamma=120°
  - Rhombohedral: alpha≠90° (all angles equal)
  - Monoclinic: beta≠90°

## Quick Reference

### By Symmetry

**Highest symmetry (cubic):**
- LAT 1, 2, 3: One parameter (a)

**Medium symmetry:**
- LAT 4, 5, 6, 11: Two parameters (a, c)
- LAT 7-10: Three parameters (a, b, c)

**Lower symmetry:**
- LAT 12: One parameter + angle (a, alpha)
- LAT 13-14: Three parameters + angle (a, b, c, beta)

## Validation

The toolkit validates lattice parameters during input generation:

```python
# This will raise an error (missing 'c' for HCP)
create_emto_inputs(
    lat=4,  # HCP
    a=3.0,  # Missing c!
    # Error: HCP requires both 'a' and 'c' parameters
)

# Correct usage
create_emto_inputs(
    lat=4,  # HCP
    a=3.0,
    c=4.9,  # c/a = 1.633
    # ✓ Valid
)
```
