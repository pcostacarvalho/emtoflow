# Alloy Implementation Plan - CPA Random Alloys (REVISED)

## Objective
Implement support for disordered alloys using CPA (Coherent Potential Approximation) by creating pymatgen structures programmatically. User provides: lattice type, elements, their lattice sites, and concentrations.

## MAJOR DESIGN CHANGE (2026-01-12)

### Old vs. New Approach Comparison

| Aspect | Old Approach (Template-based) | New Approach (Pymatgen-based) |
|--------|------------------------------|-------------------------------|
| **Structure source** | Pre-generated KSTR template files | Pymatgen `Structure` objects |
| **Lattice types** | FCC, BCC, SC only | Any structure pymatgen supports |
| **IT determination** | Manual assignment (IT=ITA increment) | Automatic via symmetry analysis |
| **Code paths** | Separate for CIF vs alloy | Unified through `parse_emto_structure()` |
| **Template files** | Required (`fcc.kstr`, `bcc.kstr`, etc.) | Not needed |
| **Disorder handling** | Simple single-site only | Multi-sublattice, partial occupancy |
| **Extensibility** | Hard (need new templates) | Easy (use pymatgen builders) |

### Why This Change?

**OLD APPROACH limitations:**
- Template files need manual creation/maintenance
- IT/ITA logic was hardcoded and oversimplified
- Single-site disorder only (IQ=1 for all atoms)
- Couldn't handle multi-sublattice alloys (L10, L12, etc.)
- Separate code path from CIF workflow (duplication)

**NEW APPROACH advantages:**
1. **Unified workflow**: Both CIF and alloy use same `parse_emto_structure()` pipeline
2. **Proper IT handling**: Symmetry analysis determines inequivalent sites automatically
3. **No template files**: More maintainable and flexible
4. **Extensibility**: Easy to add any structure type pymatgen supports
5. **Multi-sublattice support**: Can handle complex alloys (L10, L12, Heusler, etc.)
6. **Native disorder**: Pymatgen's `Species` handles partial occupancies correctly

## Scope
- **Lattice types**: All 14 EMTO/Bravais lattice types supported
  - Cubic: SC (1), FCC (2), BCC (3)
  - Hexagonal: HCP (4)
  - Tetragonal: P (5), I (6)
  - Orthorhombic: P (7), I (8), C (9), F (10)
  - Monoclinic: P (11), C (12)
  - Triclinic (13), Rhombohedral (14)
- **Alloy types**:
  - Single-site disorder (CPA on one sublattice)
  - Multi-sublattice disorder (CPA on multiple sublattices independently)
  - Ordered intermetallics (L10, L12, B2, etc.)
- **IQ/IT/ITA rules**:
  - IQ determined from atom position in unit cell
  - IT determined from symmetry analysis (inequivalent sites)
  - ITA determined from element type on each site

## Key Design Decisions

### 1. Pymatgen Structure Generation (REVISED)
**Approach**: Create pymatgen `Structure` objects programmatically, then pass to existing `parse_emto_structure()`

**Benefits**:
- Leverage pymatgen's crystal structure database and builders
- Automatic handling of symmetry and space groups
- No need for template files
- Easy to extend to any structure type

**Implementation**:
```python
from pymatgen.core import Structure, Lattice, Species
import numpy as np

def lattice_param_to_sws(structure_pmg):
    """
    Convert lattice parameter to Wigner-Seitz radius (Bohr) using pymatgen structure.

    Parameters
    ----------
    structure_pmg : pymatgen.core.Structure
        Pymatgen Structure object with lattice and sites defined

    Returns
    -------
    float
        SWS radius in atomic units (Bohr)

    Notes
    -----
    This function uses pymatgen to calculate the number of atoms per unit cell,
    making it general for any lattice type (not just FCC/BCC/SC).

    The calculation follows:
    1. Get unit cell volume from pymatgen lattice
    2. Get number of atoms from len(structure.sites)
    3. Calculate volume per atom = V_cell / n_atoms
    4. Calculate SWS = (3 * V_atom / (4*π))^(1/3)
    """
    import numpy as np

    BOHR_TO_ANGSTROM = 0.529177

    # Get lattice volume in Angstrom³
    V_cell_angstrom = structure_pmg.lattice.volume

    # Convert to Bohr³
    V_cell_bohr = V_cell_angstrom / (BOHR_TO_ANGSTROM ** 3)

    # Get number of atoms in unit cell from pymatgen
    n_atoms = len(structure_pmg.sites)

    # Volume per atom in Bohr³
    V_atom = V_cell_bohr / n_atoms

    # Wigner-Seitz radius in Bohr
    sws = (3 * V_atom / (4 * np.pi)) ** (1/3)

    return sws

def create_alloy_structure_pymatgen(lat, a, sites, b=None, c=None, alpha=90, beta=90, gamma=90):
    """
    Create pymatgen Structure for alloy calculation supporting all 14 EMTO lattice types.

    Parameters
    ----------
    lat : int
        EMTO Bravais lattice number (1-14):
        1=SC, 2=FCC, 3=BCC, 4=HCP, 5=Tetragonal-P, 6=Tetragonal-I,
        7=Orthorhombic-P, 8=Orthorhombic-I, 9=Orthorhombic-C,
        10=Orthorhombic-F, 11=Monoclinic-P, 12=Monoclinic-C,
        13=Triclinic, 14=Rhombohedral
    a : float
        Lattice parameter a in Angstroms
    sites : list of dict
        Site specifications, e.g.:
        [
            {'position': [0, 0, 0], 'elements': ['Fe', 'Pt'], 'concentrations': [0.5, 0.5]},
            {'position': [0.5, 0.5, 0.5], 'elements': ['Co'], 'concentrations': [1.0]}
        ]
    b : float, optional
        Lattice parameter b in Angstroms (defaults to a for cubic)
    c : float, optional
        Lattice parameter c in Angstroms (defaults to a for cubic, 1.633*a for HCP)
    alpha : float, optional
        Lattice angle α in degrees (default: 90)
    beta : float, optional
        Lattice angle β in degrees (default: 90)
    gamma : float, optional
        Lattice angle γ in degrees (default: 90 for most, 120 for HCP)

    Returns
    -------
    Structure
        Pymatgen Structure object with partial occupancies

    Notes
    -----
    - Defaults to cubic lattice (a=b=c, all angles 90°) if b, c not specified
    - HCP defaults: c = 1.633*a (ideal ratio), gamma = 120°
    - User has freedom to specify all parameters for any lattice type
    """
    # Set default values for cubic lattices
    if b is None:
        b = a
    if c is None:
        # Special case for HCP
        if lat == 4:
            c = 1.633 * a  # Ideal c/a ratio for HCP
        else:
            c = a

    # Special case for HCP: gamma = 120°
    if lat == 4 and gamma == 90:
        gamma = 120

    # Create Lattice object from parameters
    lattice = Lattice.from_parameters(a, b, c, alpha, beta, gamma)

    # Add PeriodicSite with Species containing partial occupancies
    species_list = []
    coords_list = []

    for site_spec in sites:
        position = site_spec['position']
        elements = site_spec['elements']
        concentrations = site_spec['concentrations']

        # Create Species with partial occupancies
        if len(elements) == 1 and concentrations[0] == 1.0:
            # Pure occupancy
            species_list.append(elements[0])
        else:
            # Mixed occupancy (CPA)
            species_dict = {elem: conc for elem, conc in zip(elements, concentrations)}
            species_list.append(Species(species_dict))

        coords_list.append(position)

    # Create Structure
    structure = Structure(lattice, species_list, coords_list)

    # Calculate and store SWS
    sws = lattice_param_to_sws(structure)
    structure.properties = {'sws': sws}

    # Return Structure object
    return structure
```

### 2. User Input Interface (REVISED)
**Required inputs**:
- `lat`: EMTO Bravais lattice number (1-14) - supports all EMTO lattice types
  - 1=SC, 2=FCC, 3=BCC, 4=HCP, 5=Tetragonal-P, 6=Tetragonal-I,
  - 7=Orthorhombic-P, 8=Orthorhombic-I, 9=Orthorhombic-C, 10=Orthorhombic-F,
  - 11=Monoclinic-P, 12=Monoclinic-C, 13=Triclinic, 14=Rhombohedral
- Lattice parameter: `a` **in Angstroms (Å)** - will be converted to SWS internally
- Optional lattice parameters (default to cubic if not specified):
  - `b`: defaults to `a`
  - `c`: defaults to `a` (or `1.633*a` for HCP)
  - `alpha`, `beta`, `gamma`: defaults to 90° (or 120° for HCP gamma)
- Sites: list of dictionaries specifying:
  - `position`: fractional coordinates [x, y, z]
  - `elements`: list of element symbols on this site
  - `concentrations`: list of concentrations (must sum to 1.0 per site)
- SWS values: for optimization sweeps (optional, can be auto-calculated from lattice params)

**Lattice Parameter → SWS Conversion**:
The user provides the experimental lattice parameters in Angstroms, and the code automatically converts to the Wigner-Seitz radius (SWS) in atomic units (Bohr radii).

**Key improvement**: Uses pymatgen to calculate the number of atoms per unit cell, making it general for all 14 EMTO lattice types (not just FCC/BCC/SC).

Algorithm:
1. Create pymatgen Structure from lattice parameters (a, b, c, alpha, beta, gamma)
2. Get unit cell volume: `V_cell = structure.lattice.volume` (in Ų)
3. Convert to Bohr³: `V_cell_bohr = V_cell / (0.529177)³`
4. Get number of atoms: `n_atoms = len(structure.sites)` (automatically from pymatgen!)
5. Calculate volume per atom: `V_atom = V_cell_bohr / n_atoms`
6. Calculate SWS: `SWS = (3 * V_atom / (4*π))^(1/3)` (in Bohr radii)

**Example**: For FCC with a = 3.7 Å:
- Pymatgen determines n_atoms = 4 automatically
- V_cell = 3.7³ = 50.653 ų
- V_cell_bohr = 50.653 / 0.148185 = 341.89 Bohr³
- V_atom = 341.89 / 4 = 85.47 Bohr³
- SWS = (3 * 85.47 / (4*π))^(1/3) ≈ 2.69 Bohr

**Example inputs**:
```python
# Binary FCC random alloy (single-site disorder)
# User provides lattice parameter in Angstroms, SWS auto-calculated
create_emto_inputs(
    output_path="./fept_alloy",
    job_name="fept",
    is_alloy=True,
    lat=2,  # FCC
    a=3.7,  # Angstroms - will be converted to SWS≈2.69 Bohr internally
    sites=[
        {'position': [0, 0, 0], 'elements': ['Fe', 'Pt'], 'concentrations': [0.5, 0.5]}
    ],
    sws_values=[2.60, 2.65, 2.70]  # Optional: for SWS optimization sweep
)

# L10 FePt (ordered, two sublattices) - tetragonal
create_emto_inputs(
    output_path="./fept_l10",
    job_name="fept_l10",
    is_alloy=True,
    lat=5,  # Tetragonal-P
    a=3.7,  # Angstroms (a-axis)
    c=3.7 * 0.96,  # c-axis (c/a = 0.96)
    sites=[
        {'position': [0, 0, 0], 'elements': ['Fe'], 'concentrations': [1.0]},
        {'position': [0.5, 0.5, 0.5], 'elements': ['Pt'], 'concentrations': [1.0]}
    ],
    sws_values=[2.65]  # Optional: single SWS or sweep
)

# HCP Co-Cr alloy (uses default c/a = 1.633 and gamma = 120°)
create_emto_inputs(
    output_path="./cocr_hcp",
    job_name="cocr",
    is_alloy=True,
    lat=4,  # HCP
    a=2.51,  # Angstroms
    # c defaults to 1.633*a, gamma defaults to 120°
    sites=[
        {'position': [0, 0, 0], 'elements': ['Co', 'Cr'], 'concentrations': [0.7, 0.3]}
    ]
)
```

### 3. Phase Diagram Sweep Helper (Advanced Feature)

**Motivation**: Phase diagram calculations require sweeping over multiple compositions, where each composition is a fundamentally different material (not a geometric variation of the same material like c/a or SWS). A helper function automates this common workflow.

**Key Design Decision**: Keep concentration loops **explicit in user code** for simple cases, but provide **helper function** for phase diagram calculations where:
- User wants full compositional sweep (many compositions)
- Dimensionality matters (binary=1D, ternary=2D, quaternary=3D)
- Automatic directory organization is valuable

**Implementation**:
```python
def create_phase_diagram_sweep(
    base_output_path,
    base_job_name,
    elements,
    concentration_step=0.1,
    min_concentration=0.0,
    **alloy_params
):
    """
    Generate EMTO inputs for phase diagram calculation.

    Parameters
    ----------
    base_output_path : str
        Base directory (e.g., "./fept_phase_diagram")
    base_job_name : str
        Base job name (e.g., "fept")
    elements : list of str
        Element symbols (e.g., ['Fe', 'Pt'] or ['Fe', 'Pt', 'Co'])
    concentration_step : float
        Concentration grid spacing (default: 0.1)
    min_concentration : float
        Minimum concentration per element (default: 0.0)
        Set to 0.1 to exclude pure elements
    **alloy_params
        Parameters passed to create_emto_inputs:
        lattice_type, a, c_over_a, nl, dmax, sws_values, magnetic, etc.

    Returns
    -------
    list of dict
        Job summaries with concentrations and paths

    Examples
    --------
    # Binary FCC phase diagram (11 compositions)
    jobs = create_phase_diagram_sweep(
        base_output_path="./fept_diagram",
        base_job_name="fept",
        elements=['Fe', 'Pt'],
        concentration_step=0.1,
        lat=2,  # FCC
        a=3.7,
        sws_values=[2.60, 2.65, 2.70]
    )
    # Creates: Fe00_Pt100/, Fe10_Pt90/, ..., Fe100_Pt00/
    # File names inside simplified (no concentration in filename)

    # Ternary with finer grid, excluding edges (~210 compositions)
    jobs = create_phase_diagram_sweep(
        base_output_path="./feptco_diagram",
        base_job_name="feptco",
        elements=['Fe', 'Pt', 'Co'],
        concentration_step=0.05,
        min_concentration=0.05,
        lat=2,  # FCC
        a=3.7,
        sws_values=[2.65]
    )
    """
    import numpy as np

    # Generate concentration grid
    concentrations_list = _generate_concentration_grid(
        n_elements=len(elements),
        step=concentration_step,
        min_conc=min_concentration
    )

    print(f"\nPhase Diagram Sweep: {'-'.join(elements)}")
    print(f"Compositions: {len(concentrations_list)}")

    jobs_created = []
    for concs in concentrations_list:
        # Directory name: Fe50_Pt30_Co20 (keeps concentration info)
        conc_str = '_'.join([f"{elem}{int(c*100):02d}"
                             for elem, c in zip(elements, concs)])

        # Create single-site CPA structure
        sites = [{'position': [0, 0, 0],
                  'elements': elements,
                  'concentrations': list(concs)}]

        # Generate inputs
        # File names inside will be simplified (job_name without concentration)
        create_emto_inputs(
            output_path=os.path.join(base_output_path, conc_str),
            job_name=base_job_name,  # Simplified: no concentration in job_name
            cif_file=None,
            is_alloy=True,
            sites=sites,
            **alloy_params
        )

        jobs_created.append({
            'elements': elements,
            'concentrations': concs,
            'composition_string': conc_str,
            'output_path': os.path.join(base_output_path, conc_str)
        })

    return jobs_created

def _generate_concentration_grid(n_elements, step=0.1, min_conc=0.0):
    """
    Generate concentration combinations on compositional simplex.

    Binary (n=2): [x, 1-x] with x ∈ [min_conc, 1-min_conc]
    Ternary (n=3): [x, y, 1-x-y] with x,y ≥ min_conc and x+y ≤ 1-min_conc
    Higher: generalize using itertools.product
    """
    import numpy as np
    from itertools import product

    grid_1d = np.arange(0, 1 + step/2, step)
    grid_1d = np.round(grid_1d, decimals=10)  # Avoid float errors

    if n_elements == 2:
        # Binary: 1D sweep
        return [(x, 1-x) for x in grid_1d
                if x >= min_conc and (1-x) >= min_conc]

    elif n_elements == 3:
        # Ternary: 2D triangular grid
        valid = []
        for x in grid_1d:
            for y in grid_1d:
                z = 1 - x - y
                if (x >= min_conc and y >= min_conc and z >= min_conc
                    and abs(x + y + z - 1.0) < 1e-6):
                    valid.append((x, y, z))
        return valid

    else:
        # Higher dimensions: generalize
        valid = []
        for combo in product(grid_1d, repeat=n_elements-1):
            last = 1.0 - sum(combo)
            if (all(c >= min_conc for c in combo)
                and last >= min_conc
                and abs(sum(combo) + last - 1.0) < 1e-6):
                valid.append(tuple(combo) + (last,))
        return valid
```

**Complexity scaling**:
- Binary (step=0.1): 11 compositions
- Binary (step=0.05): 21 compositions
- Ternary (step=0.1): 66 compositions
- Ternary (step=0.1, min=0.1): 36 compositions (excluding edges)
- Ternary (step=0.05): 231 compositions
- Quaternary (step=0.1): 286 compositions

**Directory structure example**:
```
fept_phase_diagram/
├── Fe00_Pt100/
│   ├── smx/, shp/, pot/, chd/, fcd/, tmp/
│   └── fept_1.00_2.67.dat  # Simplified: no concentration in filename
├── Fe10_Pt90/
│   ├── smx/, shp/, pot/, chd/, fcd/, tmp/
│   └── fept_1.00_2.67.dat
├── Fe20_Pt80/
│   └── ...
...
└── Fe100_Pt00/
    └── ...
```

**Note**: Directory names contain composition info (Fe50_Pt30_Co20), but **file names inside are simplified** to avoid redundancy. The concentration is already clear from the directory name, so files use only the base job name: `fept_1.00_2.67.dat` instead of `fept_Fe50_Pt50_1.00_2.67.dat`.

### 4. Element Database
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

### 4. KGRN Generation (NO CHANGES NEEDED)

**File**: `modules/inputs/kgrn.py`

**Current implementation already handles alloys correctly!**

Since we're using `parse_emto_structure()` for both CIF and alloys:
- IQ, IT, ITA are determined by symmetry analysis
- The `create_kgrn_input()` function just reads from `structure['atom_info']`
- Works for both ordered and disordered structures

**Example for single-site random alloy (Fe₀.₅Pt₀.₅)**:
```
Symb  IQ  IT ITA NRM  CONC      a_scr b_scr |Teta    Phi    FXM  m(split)
Fe     1   1   1   1  0.500000  0.900 1.000  0.0000  0.0000  N   2.2000
Pt     1   1   2   1  0.500000  0.900 1.000  0.0000  0.0000  N   0.5000
```
- Both have IQ=1 (same site)
- Both have IT=1 (same inequivalent site)
- Different ITA (1 for Fe, 2 for Pt)

**Example for L10 ordered FePt (two sublattices)**:
```
Fe     1   1   1   1  1.000000  0.900 1.000  0.0000  0.0000  N   2.2000
Pt     2   2   1   1  1.000000  0.900 1.000  0.0000  0.0000  N   0.5000
```
- Different IQ (1 for Fe at [0,0,0], 2 for Pt at [0.5,0.5,0.5])
- Different IT (1 and 2) because symmetry analysis finds two inequivalent sites
- Both have ITA=1 (pure occupancy on each site)

### 5. Structure Dict Format (UNIFIED)

**With pymatgen approach, the structure dict format is IDENTICAL for CIF and alloys!**

Both workflows produce the same dict from `parse_emto_structure()`:
```python
{
    'lat': 2,  # From symmetry analysis
    'lattice_name': 'Face-centered cubic',
    'NL': 2,  # From element electronic structure
    'NQ3': 2,  # Number of atoms
    'BSX': [...], 'BSY': [...], 'BSZ': [...],  # EMTO primitive vectors
    'fractional_coords': [[0, 0, 0], [0.5, 0.5, 0.5]],
    'a': 3.7, 'b': 3.7, 'c': 3.7,
    'coa': 1.0, 'boa': 1.0,
    'atom_info': [
        {
            'symbol': 'Fe',
            'IQ': 1,
            'IT': 1,
            'ITA': 1,
            'conc': 0.5,
            'a_scr': 0.750,
            'b_scr': 1.100,
            'default_moment': 2.0
        },
        {
            'symbol': 'Pt',
            'IQ': 1,
            'IT': 1,
            'ITA': 2,
            'conc': 0.5,
            'a_scr': 0.750,
            'b_scr': 1.100,
            'default_moment': 0.4
        }
    ]
}
```

**Key point**: No need for `is_alloy` flag or special handling. The symmetry analysis in `parse_emto_structure()` automatically determines IQ/IT/ITA correctly for any structure type.

### 6. Workflow Integration (SIMPLIFIED)

**Unified workflow for both CIF and alloys**:
1. Get pymatgen Structure (either from CIF file OR create programmatically)
2. Parse structure with `parse_emto_structure(structure)` → get structure dict
3. Create KSTR from structure dict
4. Create SHAPE from structure dict
5. Create KGRN from structure dict
6. Create KFCD from structure dict
7. Run DMAX optimization (vary c/a, vary SWS, fit EOS)

**Implementation**:
```python
def create_emto_inputs(..., cif_file=None, is_alloy=False, lattice_type=None, a=None, sites=None):
    if cif_file is not None:
        # Existing CIF workflow
        structure_pmg = Structure.from_file(cif_file)
    elif is_alloy:
        # New alloy workflow
        structure_pmg = create_alloy_structure_pymatgen(lattice_type, a, sites, c_over_a)

    # UNIFIED: Parse structure (works for both!)
    structure = parse_emto_structure(structure_pmg)

    # UNIFIED: Generate all inputs (same code for both!)
    create_kstr_input(structure, ...)
    create_shape_input(structure, ...)
    create_kgrn_input(structure, ...)
    create_kfcd_input(structure, ...)
```

**Key insight**: By creating pymatgen Structures for alloys, we get the same data flow as CIF files!

### 7. Input Validation

**Required checks**:
1. Concentrations sum to 1.0 (with tolerance, e.g., |sum - 1.0| < 1e-6)
2. Number of elements matches number of concentrations
3. Valid EMTO lattice number (1-14)
4. Valid element symbols (check against database)
5. All concentrations > 0 and ≤ 1
6. Lattice parameters (a, b, c) are positive numbers
7. Angles (alpha, beta, gamma) are in valid range (0, 180) degrees

**Implementation**:
```python
def validate_alloy_input(lat, elements, concentrations, a, b=None, c=None,
                         alpha=90, beta=90, gamma=90):
    """Validate alloy input parameters, raise ValueError if invalid"""
    # Check 1: Valid lattice number
    if lat not in range(1, 15):
        raise ValueError(f"Lattice number must be 1-14, got {lat}")

    # Check 2: concentration sum
    if abs(sum(concentrations) - 1.0) > 1e-6:
        raise ValueError(f"Concentrations must sum to 1.0, got {sum(concentrations)}")

    # Check 3: length match
    if len(elements) != len(concentrations):
        raise ValueError(f"Number of elements ({len(elements)}) must match concentrations ({len(concentrations)})")

    # Check 4: Positive lattice parameters
    if a <= 0:
        raise ValueError(f"Lattice parameter a must be positive, got {a}")
    if b is not None and b <= 0:
        raise ValueError(f"Lattice parameter b must be positive, got {b}")
    if c is not None and c <= 0:
        raise ValueError(f"Lattice parameter c must be positive, got {c}")

    # Check 5: Valid angles
    for angle_name, angle_val in [('alpha', alpha), ('beta', beta), ('gamma', gamma)]:
        if not (0 < angle_val < 180):
            raise ValueError(f"Angle {angle_name} must be in range (0, 180), got {angle_val}")

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

## Implementation Phases (REVISED FOR PYMATGEN APPROACH)

### Phase 1: Foundation (COMPLETED ✅)
1. ✅ Create element database with default_moment for common elements
2. ~~Create built-in KSTR templates~~ **OBSOLETE - not needed with pymatgen**
3. ✅ Implement input validation function in `modules/alloy_input.py`

### Phase 2: Pymatgen Structure Builder (NEW)
4. Modify `parse_emto_structure()` to accept pymatgen `Structure` objects (not just CIF paths)
5. Create `create_alloy_structure_pymatgen()` in `modules/alloy_input.py`:
   - Accept `lat` (1-14) instead of `lattice_type` string
   - Accept `a, b, c, alpha, beta, gamma` lattice parameters (with smart defaults)
   - Build pymatgen `Lattice` using `Lattice.from_parameters(a, b, c, alpha, beta, gamma)`
   - **Implement generalized lattice parameter → SWS conversion**:
     - Use pymatgen to get cell volume: `structure.lattice.volume`
     - Use pymatgen to get number of atoms: `len(structure.sites)`
     - Convert volume from Ų to Bohr³: `V_bohr = V_angstrom / (0.529177)³`
     - Calculate V_atom = V_bohr / n_atoms (automatic for any lattice!)
     - Calculate SWS: `(3 * V_atom / (4*π))^(1/3)`
   - Add sites with `Species` containing partial occupancies
   - Return pymatgen `Structure` object with calculated SWS stored
6. Support all 14 EMTO lattice types with appropriate defaults:
   - Cubic (1-3): defaults to a=b=c, 90° angles
   - HCP (4): defaults to c=1.633*a, gamma=120°
   - Others: user specifies parameters explicitly
7. Test that pymatgen structures parse correctly through existing pipeline
8. Test SWS auto-calculation: verify FCC a=3.7Å → SWS≈2.69 Bohr

### Phase 3: Integration (SIMPLIFICATION)
8. Modify `workflows.py`:
   - Add `is_alloy`, `lat`, `a`, `b`, `c`, `alpha`, `beta`, `gamma`, `sites` parameters
   - If `is_alloy`: create pymatgen structure, then call `parse_emto_structure()`
   - If `cif_file`: use existing CIF workflow
   - Remove template copying code (obsolete)
9. Delete obsolete files:
   - `modules/kstr_template.py`
   - `modules/inputs/templates/kstr/` directory
10. Update validation to check lat parameter (1-14) instead of lattice_type string

### Phase 4: Documentation
11. **Update README.md** with pymatgen-based alloy examples
12. **Add "Alloy Mode" section** with examples for:
    - Single-site random alloys (FCC Fe-Pt)
    - Multi-site ordered structures (L10 FePt)
    - Ternary alloys
13. **Document site specification format**
14. Update implementation status #3 to "✅ Completed"

### Phase 5: Testing
15. Test Fe-Pt FCC random alloy (single-site disorder)
16. Test L10 FePt (ordered, two sublattices)
17. Test ternary alloy (Fe-Pt-Co)
18. Verify IT/ITA assignment matches expectations
19. Confirm SWS optimization workflow works for alloys
20. Verify CIF mode unchanged by modifications

### Phase 6: Phase Diagram Helper (Advanced Features)
21. Add `create_phase_diagram_sweep()` helper function in `modules/workflows.py`:
    - Generate concentration grids on simplex (binary, ternary, quaternary+)
    - Directory naming: `Fe50_Pt30_Co20` (keeps composition info in directory name)
    - **Simplified file naming**: use base `job_name` without concentration suffix
    - Support `min_concentration` to exclude pure elements
    - Call `create_emto_inputs()` for each composition
22. Add `_generate_concentration_grid()` internal helper:
    - Binary: 1D sweep with n+1 points
    - Ternary: 2D triangular grid with ~n²/2 points
    - Higher dimensions: generalize using itertools
23. **Add comprehensive docstring** with examples
24. **Update README.md** with phase diagram section:
    - Binary example (Fe-Pt with 11 points)
    - Ternary example (Fe-Pt-Co with ~66 points)
    - Explain file naming: directories have composition, files don't
    - Show directory structure with concentration-based names
    - Explain dimensionality scaling
25. Test phase diagram sweep:
    - Binary Fe-Pt: verify 11 directories: Fe00_Pt100 to Fe100_Pt00
    - Ternary Fe-Pt-Co: verify ~66 directories with Fe##_Pt##_Co## format
    - Verify files inside use simplified names (base job_name only)
    - Check no redundant concentration info in file names

**Rationale for Phase 6:**
- Phase diagram calculations are common in alloy research
- Concentration sweeps are fundamentally different from c/a or SWS sweeps:
  - Each concentration = different material (not same material at different geometry)
  - Requires separate directories and job names
  - User needs explicit control over which compositions to study
- Helper automates tedious nested loops while maintaining clarity
- Scales naturally from binary (1D) to ternary (2D) to higher dimensions

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

## File Changes Summary (REVISED)

### New Files
1. ✅ `modules/element_database.py` - Default magnetic moments
2. ✅ `modules/alloy_input.py` - Validation and pymatgen structure builder

### Modified Files
1. ✅ `modules/lat_detector.py` - Modify `parse_emto_structure()` to accept both CIF paths and pymatgen `Structure` objects
2. ✅ `modules/workflows.py` - Add alloy workflow using pymatgen structure creation
3. ⚠️ `modules/alloy_input.py` - Replace `create_alloy_structure()` with `create_alloy_structure_pymatgen()`
4. **`README.md`** - Add alloy examples with site specification format

### Files to DELETE
1. ~~`modules/kstr_template.py`~~ - Template copying no longer needed
2. ~~`modules/inputs/templates/kstr/fcc.kstr`~~ - Not needed with pymatgen
3. ~~`modules/inputs/templates/kstr/bcc.kstr`~~ - Not needed with pymatgen
4. ~~`modules/inputs/templates/kstr/sc.kstr`~~ - Not needed with pymatgen

### Unchanged Files
- `modules/inputs/kstr.py` - Works as-is with pymatgen structures
- `modules/inputs/shape.py` - Works as-is
- `modules/inputs/kgrn.py` - Already handles disorder correctly
- `modules/inputs/kfcd.py` - Works as-is
- `modules/inputs/dos.py` - DOS parsing unchanged

---

## README Documentation Updates

The README must be updated to reflect the new dictionary-based input system. The current usage:

```python
# Current (parameter-based)
create_emto_inputs(
    output_path="./fept_calc",
    job_name="fept",
    cif_file="testing/FePt.cif",
    dmax=1.3,
    ca_ratios=[0.92, 0.96, 1.00, 1.04],
    sws_values=[2.60, 2.65, 2.70]
)
```

Will become:

```python
# New (dictionary-based) - CIF mode
input_dict = {
    'mode': 'cif',
    'cif_file': 'testing/FePt.cif',
    'output_path': './fept_calc',
    'job_name': 'fept',
    'dmax': 1.3,
    'ca_ratios': [0.92, 0.96, 1.00, 1.04],
    'sws_values': [2.60, 2.65, 2.70]
}
create_emto_inputs(input_dict)

# New (dictionary-based) - Alloy mode
input_dict = {
    'mode': 'alloy',
    'lattice_type': 'fcc',
    'elements': ['Fe', 'Pt'],
    'concentrations': [0.5, 0.5],
    'output_path': './fept_alloy',
    'job_name': 'FePt_alloy',
    'initial_sws': 2.65,
    'sws_values': [2.60, 2.65, 2.70]  # For optimization
}
create_emto_inputs(input_dict)
```

**Required README sections to add/update:**

1. **Quick Start section**: Update all examples to use dictionary input
2. **New section: "Alloy Mode"**: Document CPA alloy workflow with examples
3. **New section: "Input Dictionary Reference"**: Document all possible keys for both modes
4. **Examples section**: Add alloy examples alongside existing CIF examples
5. **Implementation Status**: Update #3 to mark as "Completed" when done

**Example new section for README:**

```markdown
## Alloy Mode (CPA Random Alloys)

For disordered alloys using the Coherent Potential Approximation (CPA), you can use built-in lattice templates:

### Supported Lattices
- FCC (face-centered cubic)
- BCC (body-centered cubic)
- SC (simple cubic)

### Basic Alloy Example

```python
from modules.workflows import create_emto_inputs

# Fe₀.₅Pt₀.₅ random FCC alloy
alloy_input = {
    'mode': 'alloy',
    'lattice_type': 'fcc',
    'elements': ['Fe', 'Pt'],
    'concentrations': [0.5, 0.5],
    'initial_sws': 2.65,
    'output_path': './fept_alloy',
    'job_name': 'FePt50'
}
create_emto_inputs(alloy_input)
```

### Multi-element Alloy

```python
# Fe₀.₅Pt₀.₃Co₀.₂ random FCC alloy
alloy_input = {
    'mode': 'alloy',
    'lattice_type': 'fcc',
    'elements': ['Fe', 'Pt', 'Co'],
    'concentrations': [0.5, 0.3, 0.2],
    'initial_sws': 2.65,
    'output_path': './feptco_alloy',
    'job_name': 'FePtCo'
}
create_emto_inputs(alloy_input)
```

### SWS Optimization for Alloys

```python
# Optimize SWS for Fe₀.₅Pt₀.₅ alloy
alloy_input = {
    'mode': 'alloy',
    'lattice_type': 'fcc',
    'elements': ['Fe', 'Pt'],
    'concentrations': [0.5, 0.5],
    'initial_sws': 2.65,
    'sws_values': [2.55, 2.60, 2.65, 2.70, 2.75],  # SWS sweep
    'output_path': './fept_optimization',
    'job_name': 'FePt50'
}
create_emto_inputs(alloy_input)
```

**Note**: For cubic structures (FCC, BCC, SC), only SWS optimization is performed (no c/a optimization).

### Input Requirements
- **concentrations must sum to 1.0** (raises error otherwise)
- Job names are auto-truncated to 12 characters (EMTO limit)
- All elements must be in the supported element database
```


---

## QUICK REFERENCE: Implementation Checklist (Pymatgen Approach)

### Step 1: Modify `lat_detector.py`
- [ ] Update `parse_emto_structure()` to accept both `str` (CIF path) and pymatgen `Structure` objects
- [ ] Add type check: `if isinstance(cif_file_or_structure, str)` → read CIF, else use Structure directly
- [ ] Test: Create simple pymatgen Structure, pass to `parse_emto_structure()`, verify dict output

### Step 2: Create pymatgen structure builder in `alloy_input.py`
- [ ] Implement `create_alloy_structure_pymatgen(lat, a, sites, b=None, c=None, alpha=90, beta=90, gamma=90)`
  - [ ] Accept `lat` (1-14) instead of string lattice_type
  - [ ] Handle all lattice parameters with smart defaults
- [ ] **Add generalized lattice parameter → SWS conversion function**:
  - [ ] `lattice_param_to_sws(structure_pmg)` - accepts pymatgen Structure
  - [ ] Get volume: `V_angstrom = structure.lattice.volume`
  - [ ] Get atoms: `n_atoms = len(structure.sites)` (automatic!)
  - [ ] Convert to Bohr³: `V_bohr = V_angstrom / (0.529177)³`
  - [ ] `V_atom = V_bohr / n_atoms`
  - [ ] `SWS = (3 * V_atom / (4*π))^(1/3)`
  - [ ] Test: FCC a=3.7Å should give SWS≈2.69 Bohr
  - [ ] Test: HCP with different c/a ratios
- [ ] Build pymatgen `Lattice` using `Lattice.from_parameters(a, b, c, alpha, beta, gamma)`
- [ ] Add sites with partial occupancies using pymatgen `Species({'Fe': 0.5, 'Pt': 0.5})`
- [ ] Return pymatgen `Structure` object with SWS stored in properties
- [ ] Test: FCC with single site containing Fe/Pt 50-50
- [ ] Test: HCP structure with default c/a and gamma

### Step 3: Update `workflows.py`
- [ ] Add parameters: `is_alloy`, `lat`, `a`, `b`, `c`, `alpha`, `beta`, `gamma`, `sites`
- [ ] In alloy branch: call `create_alloy_structure_pymatgen()` → get pymatgen Structure
- [ ] Pass pymatgen Structure to `parse_emto_structure()` → get structure dict
- [ ] Remove `copy_kstr_template()` call (use existing KSTR generation)
- [ ] Update validation to check `lat` (1-14) instead of string lattice_type
- [ ] Test: Run full workflow for FCC Fe-Pt alloy (lat=2)
- [ ] Test: Run workflow for HCP alloy (lat=4) with defaults

### Step 4: Cleanup obsolete code
- [ ] Delete `modules/kstr_template.py`
- [ ] Delete `modules/inputs/templates/kstr/` directory
- [ ] Remove imports of `copy_kstr_template` from `workflows.py`
- [ ] Update `alloy_input.py` to remove old `create_alloy_structure()` (or repurpose as wrapper)

### Step 5: Documentation
- [ ] Update README.md with pymatgen-based examples
- [ ] Document `sites` format specification
- [ ] Add examples for single-site disorder, multi-sublattice, ordered structures
- [ ] Update implementation status #3 to "✅ Completed"

### Step 6: Testing
- [ ] Test FCC Fe-Pt random alloy (verify IT=1 for both, ITA=1,2)
- [ ] Test L10 FePt ordered (verify IT=1,2 for two sublattices)
- [ ] Test ternary Fe-Pt-Co
- [ ] Verify CIF workflow still works unchanged
- [ ] Compare generated KGRN files with expected format

### Step 7: Phase Diagram Helper (Advanced Features)
- [ ] Implement `create_phase_diagram_sweep()` in `workflows.py`:
  - [ ] Accept `elements`, `concentration_step`, `min_concentration`
  - [ ] Generate concentration grid using `_generate_concentration_grid()`
  - [ ] Directory naming: `Fe50_Pt30_Co20` (composition in directory name)
  - [ ] **Simplified file naming**: pass base `job_name` without concentration
  - [ ] Loop over compositions, call `create_emto_inputs()` for each
  - [ ] Return list of job summaries with composition info
- [ ] Implement `_generate_concentration_grid()` helper:
  - [ ] Binary case: 1D list comprehension
  - [ ] Ternary case: 2D nested loops
  - [ ] Higher dimensions: itertools.product
  - [ ] Apply `min_concentration` filter
  - [ ] Handle floating point precision (round to 10 decimals)
- [ ] Add comprehensive docstring with examples
- [ ] Update README.md with "Phase Diagram Calculations" section:
  - [ ] Binary example (Fe-Pt, 11 compositions)
  - [ ] Ternary example (Fe-Pt-Co, 66 compositions)
  - [ ] Explain file naming: directories have composition, files don't (avoids redundancy)
  - [ ] Show directory structure with concentration-based directory names
  - [ ] Explain complexity scaling (binary=n+1, ternary~n²/2)
- [ ] Test phase diagram sweep:
  - [ ] Binary Fe-Pt: step=0.1 → verify 11 directories: Fe00_Pt100 to Fe100_Pt00
  - [ ] Ternary Fe-Pt-Co: step=0.1 → verify ~66 directories: Fe##_Pt##_Co##
  - [ ] Ternary with min=0.1 → verify 36 directories (edges excluded)
  - [ ] Verify files inside directories use simplified names (no concentration)
  - [ ] Example: `Fe50_Pt50/fept_1.00_2.67.dat` NOT `Fe50_Pt50/fept_Fe50_Pt50_1.00_2.67.dat`

---

**Plan Last Updated:** January 13, 2026
**Major Revisions:**
- **Jan 12, 2026**: Switched from template-based to pymatgen-based approach
- **Jan 13, 2026**: Enhanced generality and simplicity
  - SWS conversion now uses pymatgen to calculate atoms per cell (works for any lattice)
  - Support all 14 EMTO lattice types (not just FCC/BCC/SC)
  - Simplified phase diagram **file naming**: directories keep composition (Fe50_Pt30_Co20), but files inside are simplified (no concentration in filename to avoid redundancy)
