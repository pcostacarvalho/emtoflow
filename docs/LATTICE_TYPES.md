# EMTO Lattice Types Reference

## Lattice Type (LAT) Parameter

The `lat` parameter in EMTO specifies the Bravais lattice type. Values range from 1 to 14.

| LAT | Name | Crystal System | Description |
|-----|------|----------------|-------------|
| 1 | SC | Cubic | Simple cubic |
| 2 | FCC | Cubic | Face-centered cubic |
| 3 | BCC | Cubic | Body-centered cubic |
| 4 | HCP | Hexagonal | Hexagonal close-packed |
| 5 | ST | Tetragonal | Simple tetragonal |
| 6 | BCT | Tetragonal | Body-centered tetragonal |
| 7 | RHL | Trigonal | Trigonal/Rhombohedral |
| 8 | ORC | Orthorhombic | Simple orthorhombic |
| 9 | ORCC | Orthorhombic | Base-centered orthorhombic |
| 10 | ORCI | Orthorhombic | Body-centered orthorhombic |
| 11 | ORCF | Orthorhombic | Face-centered orthorhombic |
| 12 | MCL | Monoclinic | Simple monoclinic |
| 13 | MCLC | Monoclinic | Base-centered monoclinic |
| 14 | TRI | Triclinic | Simple triclinic |

## Primitive Vectors

Primitive vectors for each lattice type in units of lattice parameters (a, b, c):

### LAT 1: Simple Cubic (SC)
```
v1 = (1, 0, 0)
v2 = (0, 1, 0)
v3 = (0, 0, 1)
```

### LAT 2: Face-Centered Cubic (FCC)
```
v1 = (0.5, 0.5, 0)
v2 = (0, 0.5, 0.5)
v3 = (0.5, 0, 0.5)
```

### LAT 3: Body-Centered Cubic (BCC)
```
v1 = (0.5, 0.5, -0.5)
v2 = (-0.5, 0.5, 0.5)
v3 = (0.5, -0.5, 0.5)
```

### LAT 4: Hexagonal Close-Packed (HCP)
```
v1 = (1, 0, 0)
v2 = (-0.5, 0.866025, 0)      # sqrt(3)/2 ≈ 0.866025
v3 = (0, 0, c/a)               # typically c/a ≈ 1.633
Basis: 2 atoms
  atom1 = (0, 0, 0)
  atom2 = (0.333333, 0.666667, 0.5)
```

### LAT 5: Simple Tetragonal (ST)
```
v1 = (1, 0, 0)
v2 = (0, 1, 0)
v3 = (0, 0, c/a)
```

### LAT 6: Body-Centered Tetragonal (BCT)
```
v1 = (1, 0, 0)
v2 = (0, 1, 0)
v3 = (0.5, 0.5, c/a/2)
```

### LAT 7: Trigonal/Rhombohedral (RHL)
```
v1 = (0, 1, c/a)
v2 = (-sqrt(3)/2, -0.5, c/a)      # sqrt(3)/2 ≈ 0.866025
v3 = (sqrt(3)/2, -0.5, c/a)
Note: All three angles are equal (alpha = beta = gamma)
Special case: If bsz(1) < 1e-7, then boa = -1.0
```

### LAT 8: Simple Orthorhombic (ORC)
```
v1 = (1, 0, 0)
v2 = (0, b/a, 0)
v3 = (0, 0, c/a)
```

### LAT 9: Base-Centered Orthorhombic (ORCC)
```
v1 = (0.5, -b/a/2, 0)
v2 = (0.5, b/a/2, 0)
v3 = (0, 0, c/a)
```

### LAT 10: Body-Centered Orthorhombic (ORCI)
```
v1 = (0.5, -b/a/2, c/a/2)
v2 = (0.5, b/a/2, -c/a/2)
v3 = (-0.5, b/a/2, c/a/2)
```

### LAT 11: Face-Centered Orthorhombic (ORCF)
```
v1 = (0.5, 0, c/a/2)
v2 = (0.5, b/a/2, 0)
v3 = (0, b/a/2, c/a/2)
```

### LAT 12: Simple Monoclinic (MCL)
```
v1 = (1, 0, 0)
v2 = (b/a*cos(gamma), b/a*sin(gamma), 0)
v3 = (0, 0, c/a)
Note: gamma ≠ 90°, alpha = beta = 90°
```

### LAT 13: Base-Centered Monoclinic (MCLC)
```
v1 = (0, -b/a, 0)
v2 = (0.5*sin(gamma), -0.5*cos(gamma), -0.5*c/a)
v3 = (0.5*sin(gamma), -0.5*cos(gamma), 0.5*c/a)
Note: gamma ≠ 90°, alpha = beta = 90°
```

### LAT 14: Simple Triclinic (TRI)
```
v1 = (1, 0, 0)
v2 = (b/a*cos(gamma), b/a*sin(gamma), 0)
v3 = (c/a*cos(beta), c/a*(cos(alpha)-cos(beta)*cos(gamma))/sin(gamma), 
      c/a*sqrt(1-cos²(gamma)-cos²(alpha)-cos²(beta)+2*cos(alpha)*cos(beta)*cos(gamma))/sin(gamma))
Note: All angles may differ from 90°
```

### Notes on Vectors

- All vectors are normalized to lattice parameter `a`
- Ratios like `b/a`, `c/a` define the unit cell shape
- For cubic systems (LAT 1-3): `b/a = c/a = 1`
- Angles are in radians for calculations (converted from degrees)
- EMTO internally uses these primitive vectors to construct the crystal

## Common Examples

### Cubic Systems
- **SC (1)**: Po (Polonium)
- **FCC (2)**: Cu, Al, Ag, Au, Ni, Pt, Pb
- **BCC (3)**: Fe, Cr, Mo, W, V

### Tetragonal Systems
- **ST (5)**: TiO₂ (rutile)
- **BCT (6)**: In, Sn (white tin)

### Hexagonal Systems
- **HCP (4)**: Mg, Ti, Co, Zn, Cd

### Others
- **RHL (7)**: Bi, Sb, As
- **ORCF (11)**: α-U (uranium)
- **TRI (14)**: K₂Cr₂O₇

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
| Hexagonal (4) | `a`, `c` | - |
| Trigonal (7) | `a`, `c` | `alpha` (all angles equal) |
| Orthorhombic (8-11) | `a`, `b`, `c` | - |
| Monoclinic (12-13) | `a`, `b`, `c` | `gamma` (for LAT 12), `beta` (for LAT 13) |
| Triclinic (14) | `a`, `b`, `c` | `alpha`, `beta`, `gamma` |

### Notes

- For cubic systems: `b=a`, `c=a` (automatically set)
- For HCP (LAT=4): `c/a` ratio typically ~1.633, gamma=120°
- For tetragonal: `c/a` ratio defines distortion from cubic
- For trigonal (LAT=7): All three angles are equal (alpha = beta = gamma)
- All angles default to 90° except:
  - HCP (LAT=4): gamma=120°
  - Trigonal (LAT=7): alpha=beta=gamma≠90° (all angles equal)
  - Simple monoclinic (LAT=12): gamma≠90°
  - Base-centered monoclinic (LAT=13): beta≠90°
  - Triclinic (LAT=14): All angles may differ from 90°

## Quick Reference

### By Symmetry

**Highest symmetry (cubic):**
- LAT 1, 2, 3: One parameter (a)

**Medium symmetry:**
- LAT 4, 5, 6, 7: Two parameters (a, c)
- LAT 8-11: Three parameters (a, b, c)

**Lower symmetry:**
- LAT 12-13: Three parameters + angle (a, b, c, gamma/beta)
- LAT 14: Three parameters + three angles (a, b, c, alpha, beta, gamma)

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
