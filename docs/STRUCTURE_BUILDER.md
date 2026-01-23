# Structure Builder Module

## Overview

The `modules/structure_builder.py` module provides a unified interface for creating EMTO-compatible structure dictionaries from either CIF files or user-specified lattice parameters. This enables support for both experimental structures and custom alloys/ordered compounds.

## Key Features

- **Unified workflow**: Both CIF and parameter-based inputs use the same `create_emto_structure()` function
- **All 14 EMTO lattice types**: Supports cubic, tetragonal, hexagonal, orthorhombic, monoclinic, rhombohedral, and triclinic systems
- **CPA alloy support**: Handles random alloys with partial occupancies using pymatgen's `Species` objects
- **Ordered structures**: Supports multi-sublattice ordered intermetallics (L10, L12, B2, Heusler, etc.)
- **Element substitutions**: Replace elements in CIF files with alloy compositions
- **Automatic symmetry analysis**: Determines inequivalent sites (IT) and atom types (ITA) automatically
- **SWS calculation**: Converts lattice parameters to Wigner-Seitz radius for any lattice type

## Main Functions

### `create_emto_structure()`
Unified entry point that accepts either:
- CIF file path with optional substitutions
- Lattice parameters (`lat`, `a`, `b`, `c`, `alpha`, `beta`, `gamma`) with site specifications

Returns both pymatgen `Structure` object and EMTO structure dictionary.

### `lattice_param_to_sws()`
Converts lattice parameters to SWS (Wigner-Seitz radius) using pymatgen to automatically determine atoms per unit cell. Works for all 14 EMTO lattice types.

### `create_structure_from_params()`
Creates pymatgen Structure from lattice parameters and site specifications. Handles partial occupancies for CPA alloys.

## Usage Example

```python
from modules.structure_builder import create_emto_structure

# From CIF
structure_pmg, structure_dict = create_emto_structure(
    cif_file="FePt.cif",
    substitutions={
        'Fe': {'elements': ['Fe', 'Co'], 'concentrations': [0.7, 0.3]}
    }
)

# From parameters (FCC Fe-Pt alloy)
structure_pmg, structure_dict = create_emto_structure(
    lat=2,  # FCC
    a=3.7,
    sites=[{
        'position': [0, 0, 0],
        'elements': ['Fe', 'Pt'],
        'concentrations': [0.5, 0.5]
    }]
)
```

## Implementation Details

- Uses pymatgen for structure manipulation and symmetry analysis
- Automatically converts to primitive cell for CIF inputs (unless user specifies LAT)
- Handles oxidation states removal from CIF files
- Calculates EMTO primitive vectors (BSX, BSY, BSZ) for all lattice types
- Extracts atom information (IQ, IT, ITA) from symmetry analysis

## Related Modules

- `modules/lat_detector.py`: Lattice type detection and primitive vector generation
- `modules/element_database.py`: Default magnetic moments and element properties
- `modules/create_input.py`: Uses structure dictionaries to generate EMTO input files
