# DOS Parser Refactoring Plan

## Current Issues Identified

### 1. **CRITICAL: **** (Asterisk) Handling**
**Location**: `modules/dos.py:95-109` in `_read_data_block()`

**Problem**:
- Fortran overflow values represented as `****` or `*********` cause `float()` conversion to fail
- Current code catches `ValueError` and **breaks** parsing, losing all subsequent data
- Examples found in: `testing/examples/dos/fept_0.96_2.86_k21.dos`

**Impact**:
- Data loss after first overflow value
- Silent failure - no warning to user
- Invalid DOS calculations for systems with numerical overflow

**Fix Required**:
```python
# Instead of:
data.append([float(x) for x in vals])

# Should handle:
data.append([np.nan if '*' in x else float(x) for x in vals])
```

---

### 2. **CRITICAL: Understanding ITA (Interacting Type Atom) vs IT (Sublattice) Data**
**Location**: `modules/dos.py:208-257`

**Correct Data Structure**:
- **IT columns** (in Total DOS section): Pre-weighted sublattice total DOS (no orbital resolution)
  - Column structure: `[E, Total, NOS, IT1, IT2, IT3, ...]`
  - These are the **correct sublattice totals** already weighted by CPA

- **ITA sections** (individual "Atom" sections): Concentration components within each sublattice (with orbital resolution)
  - Each sublattice (IT) has multiple ITAs representing different concentration components
  - Example: `IT=1: ITA=1 (Pt), ITA=2 (Pt)` and `IT=2: ITA=1 (Fe), ITA=2 (Fe)`
  - These are NOT errors - they are **correct individual ITA contributions**

**Relationship**:
```python
# For sublattice N with concentrations [c1, c2, ...]:
IT_N_total = c1 * ITA_1_total + c2 * ITA_2_total + ...

# This should match:
IT_N_total == get_dos('sublattice', sublattice=N)
```

**Current Problem**:
- Old `get_sublattice_dos()` sums ITAs without proper concentration weighting
- No way to get orbital-resolved sublattice DOS (requires weighted ITA sum)
- Terminology confusion: "atom" sections are actually "ITA" components

**Impact**:
- Need to rename functions to use ITA terminology for clarity
- Need to add concentration-weighted summation for orbital-resolved sublattice DOS
- Need verification function to check weighted ITA sum matches IT column

---

### 3. **MAJOR: plot_partial() Hardcoded for 2 Sublattices**
**Location**: `modules/dos.py:331-373`

**Problem**:
- Hardcoded to plot only IT 1 (column 3) and IT 2 (column 4)
- Fails for systems with 1, 3, 4+ sublattices
- No dynamic detection of number of sublattices

**Current Code**:
```python
ax.plot(dos_up[:, 0], dos_up[:, 3], label='IT 1', ...)  # Hardcoded column 3
ax.plot(dos_up[:, 0], dos_up[:, 4], label='IT 2', ...)  # Hardcoded column 4
```

**Fix Required**:
- Detect number of sublattices from data shape
- Loop through all IT columns dynamically
- Use color cycle for plotting

---

### 4. **MEDIUM: Column Index Inconsistency**
**Location**: Throughout `modules/dos.py`

**Problem**:
- Total DOS data has columns: `[E, Total, NOS, IT1, IT2, ...]`
- Atom DOS data has columns: `[E, Total, s, p, d]`
- Different column meanings cause confusion
- NOS column (index 2) in total data is ignored in all functions

**Current Behavior**:
- `get_total_dos()` returns ALL columns including NOS
- No function to specifically extract NOS data
- Documentation mentions NOS but no API to access it

---

### 5. **MINOR: Missing Element-Level Functions**
**Location**: Guide mentions them, but missing from code

**Gap**:
- `dos_guide.md` lines 18, 49-57, 83 reference `element` parameter and `get_element_dos()`
- No such function exists in `modules/dos.py`
- Guide shows: `plot_dos('file.dos', plot_type='element', element='fe')`
- This would fail - 'element' is not a valid plot_type

**Impact**:
- Documentation-code mismatch
- Users following guide will get errors
- No way to sum DOS across all atoms of same element type

---

## Proposed Refactoring Plan

### Phase 1: Critical Fixes (High Priority)

#### Task 1.1: Fix **** Handling
**File**: `modules/dos.py:95-109`
**Changes**:
```python
def _read_data_block(self, lines: List[str], start_idx: int) -> np.ndarray:
    """Read a data block until empty line or TNOS."""
    data = []
    i = start_idx
    while i < len(lines):
        line = lines[i].strip()
        if not line or 'TNOS' in line or 'Sublattice' in line or 'Total DOS' in line:
            break
        try:
            vals = line.split()
            # Convert **** to NaN instead of breaking
            converted = []
            for x in vals:
                if '*' in x:  # Handle ****, *********, etc.
                    converted.append(np.nan)
                else:
                    converted.append(float(x))
            data.append(converted)
        except (ValueError, IndexError) as e:
            # Log warning but continue parsing
            import warnings
            warnings.warn(f"Error parsing line {i}: {line.strip()[:50]}... - {e}")
            break
        i += 1
    return np.array(data) if data else None
```

**Testing**: Verify with `testing/examples/dos/fept_0.96_2.86_k21.dos` that all data is parsed

---

#### Task 1.2: Create new get_dos() function (replaces get_total_dos and get_sublattice_dos)
**File**: `modules/dos.py` (new function)
**Design**: Unified interface for accessing all data from Total DOS sections

**New Implementation**:
```python
def get_dos(self, data_type: str = 'total', sublattice: Optional[int] = None,
            spin_polarized: bool = True) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """
    Get DOS data from the Total DOS sections.

    Reads directly from 'Total DOS and NOS and partial (IT)' sections.
    Column structure: [E, Total, NOS, IT1, IT2, IT3, ...]

    Parameters
    ----------
    data_type : str
        Type of data to extract:
        - 'total': Total DOS (column 1)
        - 'nos': Number of States (column 2)
        - 'sublattice': Sublattice/IT DOS (requires sublattice parameter)
    sublattice : int, optional
        Sublattice index (1, 2, 3, ...) - required when data_type='sublattice'
    spin_polarized : bool
        If True, return separate spin channels. If False, sum them.

    Returns
    -------
    dos_down : np.ndarray
        Spin down data, columns: [E, DOS_value]
    dos_up : np.ndarray or None
        Spin up data (None if spin_polarized=False)

    Examples
    --------
    >>> parser.get_dos('total')  # Get total DOS
    >>> parser.get_dos('nos')     # Get number of states
    >>> parser.get_dos('sublattice', sublattice=1)  # Get sublattice 1 DOS
    >>> parser.get_dos('sublattice', sublattice=2)  # Get sublattice 2 DOS
    """
    # Determine column index
    if data_type == 'total':
        col_idx = 1
    elif data_type == 'nos':
        col_idx = 2
    elif data_type == 'sublattice':
        if sublattice is None:
            raise ValueError("Must specify sublattice when data_type='sublattice'")
        # Validate sublattice exists
        num_sublattices = self.data['total_down'].shape[1] - 3  # Subtract E, Total, NOS
        if sublattice < 1 or sublattice > num_sublattices:
            raise KeyError(f"Sublattice {sublattice} not found. Available: 1-{num_sublattices}")
        # Column index: 2 (skip E, Total, NOS) + sublattice
        col_idx = 2 + sublattice
    else:
        raise ValueError(f"data_type must be 'total', 'nos', or 'sublattice', got '{data_type}'")

    # Extract energy and data columns
    dos_down = np.column_stack([
        self.data['total_down'][:, 0],      # Energy
        self.data['total_down'][:, col_idx]  # DOS value
    ])

    dos_up = None
    if self.data['total_up'] is not None:
        dos_up = np.column_stack([
            self.data['total_up'][:, 0],      # Energy
            self.data['total_up'][:, col_idx]  # DOS value
        ])

    if spin_polarized:
        return dos_down, dos_up
    else:
        total = dos_down.copy()
        if dos_up is not None:
            total[:, 1] += dos_up[:, 1]
        return total, None
```

**Breaking Changes**:
- **REMOVE** `get_total_dos()` - replaced by `get_dos('total')`
- **REMOVE** `get_sublattice_dos()` - replaced by `get_dos('sublattice', sublattice=N)`
- **REMOVE** `get_orbital_dos()` - functionality merged into `get_ITA_dos()`
- **RENAME** `get_atom_dos()` → `get_ITA_dos()` - new signature with ITA_index and concentration parameters

**Rationale**:
- Clear separation of concerns:
  - `get_dos()` → IT (sublattice) total DOS from Total DOS section (no orbital resolution)
  - `get_ITA_dos()` → Individual ITA sections (with orbital selection and concentration weighting)
- Correct terminology: "ITA" (Interacting Type Atom) instead of "atom"
- Enables orbital-resolved sublattice DOS via concentration-weighted ITA summation
- Forces users to understand ITA vs IT distinction

**Migration Guide - Data Functions**:
```python
# OLD → NEW
parser.get_total_dos()              →  parser.get_dos('total')
parser.get_sublattice_dos(1)        →  parser.get_dos('sublattice', sublattice=1)
parser.get_atom_dos(atom_number=1)  →  parser.get_ITA_dos(sublattice=1, ITA_index=1, orbital='total')
parser.get_atom_dos(atom_number=2)  →  parser.get_ITA_dos(sublattice=1, ITA_index=2, orbital='total')
parser.get_orbital_dos(1, 'd')      →  parser.get_ITA_dos(sublattice=1, ITA_index=1, orbital='d')

# NEW: Orbital-resolved sublattice DOS with concentration weighting
parser.get_ITA_dos(sublattice=1, orbital='d', sum_ITAs=True, concentrations=[0.5, 0.5])
```

**Migration Guide - Plotter Functions**:
```python
# OLD → NEW
plotter.plot_partial()                          →  plotter.plot_sublattice()  # Renamed, plots all sublattices
plotter.plot_sublattice(sublattice=1)           →  plotter.plot_sublattice(sublattice=1)  # New implementation using IT data
plotter.plot_atom(atom_number=1)                →  plotter.plot_ITA(sublattice=1, ITA_index=1)
plotter.plot_atom(atom_number=1, orbital_resolved=True)
                                                →  plotter.plot_ITA(sublattice=1, ITA_index=1, orbital_resolved=True)
plotter.plot_orbital(atom_number=1, orbital='d')→  plotter.plot_ITA(sublattice=1, ITA_index=1, orbital='d')
```

**Migration Guide - Helper Functions**:
```python
# OLD → NEW
parser.list_sublattices()           →  sorted(set(sub for _, _, sub in parser.list_ITAs()))
parser.list_atoms()                 →  parser.list_ITAs()  # Renamed for clarity
```

---

#### Task 1.3: Rename get_atom_dos() to get_ITA_dos() with concentration-weighted summation
**File**: `modules/dos.py:135-168` (existing function to be refactored)
**Design**: Unified interface for accessing ITA (Interacting Type Atom) orbital data with concentration weighting

**Current Implementation Issues**:
- Uses sequential `atom_number` (1, 2, 3, 4...) which is opaque
- Terminology confusion: "atom" should be "ITA" (concentration component)
- No concentration weighting for orbital-resolved sublattice DOS
- Separate `get_orbital_dos()` function is redundant
- File structure: Same sublattice (IT) can have multiple ITAs
- Example: `Sublattice 1 Atom Pt` can appear twice (2 Pt ITAs on sublattice 1 with different concentrations)
- Column structure: `[E, Total, s, p, d]`

**File Structure Example (ITA ordering)**:
```
# IT ordering: For each IT, all ITAs in numeric order
Sublattice 1 Atom Pt spin DOWN   # IT=1, ITA=1 (e.g., c=0.7)
Sublattice 1 Atom Pt spin DOWN   # IT=1, ITA=2 (e.g., c=0.3)
Sublattice 2 Atom Fe spin DOWN   # IT=2, ITA=1 (e.g., c=0.5)
Sublattice 2 Atom Fe spin DOWN   # IT=2, ITA=2 (e.g., c=0.5)

# Relationship:
# IT1_total = 0.7 * ITA1_total + 0.3 * ITA2_total (should match get_dos('sublattice', sublattice=1))
# IT1_d_orbital = 0.7 * ITA1_d + 0.3 * ITA2_d (only available via weighted ITA sum)
```

**New Implementation**:
```python
def get_ITA_dos(self, sublattice: int, ITA_index: int = 1, orbital: str = 'total',
                sum_ITAs: bool = False, concentrations: Optional[List[float]] = None,
                spin_polarized: bool = True) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """
    Get DOS for a specific ITA (Interacting Type Atom) with orbital selection.

    Reads from ITA-specific sections:
    'Sublattice X Atom ELEMENT spin DOWN/UP'
    Column structure: [E, Total, s, p, d]

    Note: Each sublattice (IT) can have multiple ITAs representing different concentration
    components within the CPA. Use ITA_index to specify which ITA (1, 2, ...), or use
    sum_ITAs=True to compute concentration-weighted orbital-resolved sublattice DOS.

    Parameters
    ----------
    sublattice : int
        Sublattice (IT) index (1, 2, 3, ...)
    ITA_index : int
        Which ITA on this sublattice (1 = first occurrence, 2 = second, etc.)
        Ignored if sum_ITAs=True. Default: 1
    orbital : str
        Orbital to extract:
        - 'total': Total DOS for this ITA (column 1)
        - 's': s-orbital DOS (column 2)
        - 'p': p-orbital DOS (column 3)
        - 'd': d-orbital DOS (column 4)
    sum_ITAs : bool
        If True, compute concentration-weighted sum over all ITAs on this sublattice.
        Requires concentrations parameter. Default: False
    concentrations : list of float, optional
        Concentration weights for each ITA when sum_ITAs=True.
        Must sum to 1.0 and have length equal to number of ITAs on this sublattice.
        Required when sum_ITAs=True.
        Example: [0.7, 0.3] for 2 ITAs on sublattice
    spin_polarized : bool
        If True, return separate spin channels. If False, sum them.

    Returns
    -------
    dos_down : np.ndarray
        Spin down data, columns: [E, DOS_value]
    dos_up : np.ndarray or None
        Spin up data (None if spin_polarized=False)

    Examples
    --------
    >>> parser.get_ITA_dos(sublattice=1, ITA_index=1, orbital='d')  # 1st Pt ITA, d-orbital
    >>> parser.get_ITA_dos(sublattice=1, ITA_index=2, orbital='d')  # 2nd Pt ITA, d-orbital
    >>> parser.get_ITA_dos(sublattice=2, ITA_index=1, orbital='s')  # 1st Fe ITA, s-orbital

    # Orbital-resolved sublattice DOS (weighted sum)
    >>> parser.get_ITA_dos(sublattice=1, orbital='d', sum_ITAs=True, concentrations=[0.7, 0.3])

    Notes
    -----
    When sum_ITAs=True and orbital='total', the weighted sum should match:
    get_dos('sublattice', sublattice=N) within numerical precision.
    """
    # Find all ITAs on this sublattice
    ITAs_on_sublattice = [(atom_num, elem) for atom_num, elem, sub in self.atom_info if sub == sublattice]

    if not ITAs_on_sublattice:
        available_sublattices = sorted(set(sub for _, _, sub in self.atom_info))
        raise KeyError(f"Sublattice {sublattice} not found. Available sublattices: {available_sublattices}")

    # Determine column index for orbital
    orbital_map = {
        'total': 1,
        's': 2,
        'p': 3,
        'd': 4
    }

    if orbital not in orbital_map:
        raise ValueError(f"orbital must be 'total', 's', 'p', or 'd', got '{orbital}'")

    col_idx = orbital_map[orbital]

    if sum_ITAs:
        # Concentration-weighted sum over all ITAs on this sublattice
        if concentrations is None:
            raise ValueError(
                f"concentrations parameter is required when sum_ITAs=True. "
                f"Sublattice {sublattice} has {len(ITAs_on_sublattice)} ITA(s)."
            )

        if len(concentrations) != len(ITAs_on_sublattice):
            raise ValueError(
                f"concentrations length ({len(concentrations)}) must match number of ITAs "
                f"on sublattice {sublattice} ({len(ITAs_on_sublattice)})"
            )

        if not np.isclose(sum(concentrations), 1.0):
            raise ValueError(
                f"concentrations must sum to 1.0, got {sum(concentrations)}"
            )

        dos_down_sum = None
        dos_up_sum = None

        for (atom_num, _), conc in zip(ITAs_on_sublattice, concentrations):
            down_key = f'atom_{atom_num}_down'
            up_key = f'atom_{atom_num}_up'

            if down_key not in self.data:
                continue

            if dos_down_sum is None:
                dos_down_sum = np.column_stack([
                    self.data[down_key][:, 0],
                    conc * self.data[down_key][:, col_idx]
                ])
                if up_key in self.data and self.data[up_key] is not None:
                    dos_up_sum = np.column_stack([
                        self.data[up_key][:, 0],
                        conc * self.data[up_key][:, col_idx]
                    ])
            else:
                dos_down_sum[:, 1] += conc * self.data[down_key][:, col_idx]
                if up_key in self.data and self.data[up_key] is not None and dos_up_sum is not None:
                    dos_up_sum[:, 1] += conc * self.data[up_key][:, col_idx]

        if spin_polarized:
            return dos_down_sum, dos_up_sum
        else:
            total = dos_down_sum.copy()
            if dos_up_sum is not None:
                total[:, 1] += dos_up_sum[:, 1]
            return total, None

    else:
        # Get single ITA
        if ITA_index < 1 or ITA_index > len(ITAs_on_sublattice):
            raise KeyError(
                f"ITA_index {ITA_index} out of range. "
                f"Sublattice {sublattice} has {len(ITAs_on_sublattice)} ITA(s)"
            )

        # Get the sequential atom_number for this sublattice and ITA_index
        atom_number = ITAs_on_sublattice[ITA_index - 1][0]  # -1 because ITA_index is 1-based

        # Get the ITA data
        down_key = f'atom_{atom_number}_down'
        up_key = f'atom_{atom_number}_up'

        if down_key not in self.data:
            raise KeyError(f"Data for sublattice {sublattice}, ITA {ITA_index} not found")

        # Extract energy and orbital columns
        dos_down = np.column_stack([
            self.data[down_key][:, 0],      # Energy
            self.data[down_key][:, col_idx]  # Orbital DOS
        ])

        dos_up = None
        if up_key in self.data and self.data[up_key] is not None:
            dos_up = np.column_stack([
                self.data[up_key][:, 0],      # Energy
                self.data[up_key][:, col_idx]  # Orbital DOS
            ])

        if spin_polarized:
            return dos_down, dos_up
        else:
            total = dos_down.copy()
            if dos_up is not None:
                total[:, 1] += dos_up[:, 1]
            return total, None
```

**Side Effects**:
- **RENAMES** `get_atom_dos()` → `get_ITA_dos()` for correct terminology
- **REMOVES** `get_orbital_dos()` - functionality merged into `get_ITA_dos()`
- Changes parameter from `atom_number` (opaque sequential) to `sublattice + ITA_index` (matches file structure)
- Adds `orbital` parameter with options: 'total', 's', 'p', 'd'
- Adds `sum_ITAs` parameter for concentration-weighted summation
- Adds `concentrations` parameter (required when `sum_ITAs=True`)
- **BREAKS COMPATIBILITY** with code using old `atom_number` parameter

**Note on sum_ITAs with concentrations**:
- When `sum_ITAs=True`, computes concentration-weighted sum of ITA DOS
- Enables **orbital-resolved sublattice DOS** (not available from IT columns)
- For `orbital='total'`, weighted sum should match `get_dos('sublattice')` within numerical precision
- For `orbital='s'/'p'/'d'`, provides orbital-resolved sublattice DOS
- User must provide correct concentrations from their CPA calculation
- Concentrations must sum to 1.0 and match number of ITAs on sublattice

**Verification**:
A separate verification function should be added to check that:
```python
weighted_ITA_sum == IT_column_data  # Within numerical tolerance
```

---

#### Task 1.4: Add verify_ITA_sum() function
**File**: `modules/dos.py` (new function after `get_ITA_dos()`)
**Purpose**: Verify that concentration-weighted ITA sum matches IT column data

**New Implementation**:
```python
def verify_ITA_sum(self, sublattice: int, concentrations: List[float],
                   tolerance: float = 1e-6) -> Dict[str, bool]:
    """
    Verify that concentration-weighted ITA sum matches IT column data.

    This function checks the relationship:
    sum(c_i * ITA_i_total) == IT_total (within tolerance)

    Parameters
    ----------
    sublattice : int
        Sublattice (IT) index to verify
    concentrations : list of float
        Concentration weights for each ITA (must sum to 1.0)
    tolerance : float
        Numerical tolerance for comparison. Default: 1e-6

    Returns
    -------
    dict
        Dictionary with verification results:
        {
            'spin_down_match': bool,
            'spin_up_match': bool,
            'max_diff_down': float,
            'max_diff_up': float
        }

    Examples
    --------
    >>> result = parser.verify_ITA_sum(sublattice=1, concentrations=[0.7, 0.3])
    >>> if result['spin_down_match']:
    ...     print("Verification passed!")
    """
    # Get IT column data
    it_dos_down, it_dos_up = self.get_dos('sublattice', sublattice=sublattice,
                                           spin_polarized=True)

    # Get weighted ITA sum
    ita_sum_down, ita_sum_up = self.get_ITA_dos(sublattice=sublattice, orbital='total',
                                                  sum_ITAs=True, concentrations=concentrations,
                                                  spin_polarized=True)

    # Compare
    max_diff_down = np.max(np.abs(it_dos_down[:, 1] - ita_sum_down[:, 1]))
    spin_down_match = max_diff_down < tolerance

    max_diff_up = 0.0
    spin_up_match = True
    if it_dos_up is not None and ita_sum_up is not None:
        max_diff_up = np.max(np.abs(it_dos_up[:, 1] - ita_sum_up[:, 1]))
        spin_up_match = max_diff_up < tolerance

    return {
        'spin_down_match': spin_down_match,
        'spin_up_match': spin_up_match,
        'max_diff_down': max_diff_down,
        'max_diff_up': max_diff_up
    }
```

**Purpose**:
- Validates that user-provided concentrations are correct
- Checks data consistency between IT and ITA sections
- Useful for debugging CPA calculations
- Provides quantitative difference metrics

---

### Phase 2: Major Improvements

#### Task 2.1: Rename plot_partial() to plot_sublattice() and remove old plot_sublattice()
**Files**:
- `modules/dos.py:331-373` (plot_partial - rename to plot_sublattice)
- `modules/dos.py:487-543` (plot_sublattice - REMOVE this one)

**Rationale**:
- Current `plot_partial()` correctly uses IT columns from Total DOS section
- Current `plot_sublattice()` incorrectly sums individual atom data
- The correct implementation should be called `plot_sublattice()` since it plots sublattice DOS
- "Partial DOS" and "Sublattice DOS" are the same thing (IT contributions)

**Changes**:
1. **REMOVE** old `plot_sublattice()` function (lines 487-543) - it uses wrong data source
2. **RENAME** `plot_partial()` to `plot_sublattice()` (keep implementation, just rename)
3. Update to use `get_dos()` and support dynamic sublattices

**New Implementation** (renamed from plot_partial):
```python
def plot_sublattice(self, sublattice: Optional[int] = None, spin_polarized: bool = True,
                    figsize: Tuple[float, float] = (8, 6), save: Optional[str] = None,
                    show: bool = True):
    """
    Plot sublattice DOS (IT contributions).

    Uses get_dos() to extract sublattice data from IT columns.
    If sublattice is None, plots all sublattices.

    Parameters
    ----------
    sublattice : int, optional
        Specific sublattice to plot. If None, plots all sublattices.
    spin_polarized : bool
        If True, plot spin-up and spin-down separately
    figsize : tuple
        Figure size (width, height)
    save : str, optional
        Filename to save plot
    show : bool
        Whether to display the plot
    """
    # Auto-detect number of sublattices
    num_sublattices = self.parser.data['total_down'].shape[1] - 3  # Subtract E, Total, NOS

    if num_sublattices < 1:
        raise ValueError("No sublattice data found in DOS file")

    # Determine which sublattices to plot
    if sublattice is not None:
        if sublattice < 1 or sublattice > num_sublattices:
            raise ValueError(f"Sublattice {sublattice} not found. Available: 1-{num_sublattices}")
        sublattices_to_plot = [sublattice]
        title = f'Sublattice {sublattice} DOS'
    else:
        sublattices_to_plot = list(range(1, num_sublattices + 1))
        title = f'Sublattice DOS ({num_sublattices} sublattices)'

    fig, ax = plt.subplots(figsize=figsize)

    # Plot each sublattice
    colors = plt.cm.tab10.colors  # Use color cycle
    for sublat in sublattices_to_plot:
        dos_down, dos_up = self.parser.get_dos('sublattice', sublattice=sublat,
                                                 spin_polarized=True)
        color = colors[(sublat - 1) % len(colors)]
        label = f'Sublattice {sublat}' if len(sublattices_to_plot) > 1 else 'DOS'

        if spin_polarized and dos_up is not None:
            ax.plot(dos_up[:, 0], dos_up[:, 1], label=label,
                   linestyle='-', color=color)
            ax.plot(dos_down[:, 0], -dos_down[:, 1],
                   linestyle='--', color=color)
        else:
            dos_total = dos_down[:, 1] + (dos_up[:, 1] if dos_up is not None else 0)
            ax.plot(dos_down[:, 0], dos_total, label=label, color=color)

    if spin_polarized:
        ax.axhline(0, color='black', linewidth=0.5)

    ax.axvline(0, color='gray', linestyle='--', alpha=0.5, label='E_F')
    ax.set_xlabel('Energy (Ry)')
    ax.set_ylabel('DOS (states/Ry)')
    ax.legend()
    ax.set_title(title)
    plt.tight_layout()

    if save:
        plt.savefig(save, dpi=300)
    if show:
        plt.show()

    return fig, ax
```

**Benefits**:
- Works with any number of sublattices (1, 2, 3, 4+)
- Uses centralized get_dos() for data access (correct IT columns)
- Can plot single sublattice or all sublattices
- Dynamic color cycling
- Dynamic title shows sublattice count
- Removes incorrect implementation that summed atom data

---

#### Task 2.2: Rename plot_atom() to plot_ITA() and merge with plot_orbital()
**Files**:
- `modules/dos.py:375-435` (plot_atom - rename to plot_ITA and update)
- `modules/dos.py:437-485` (plot_orbital - REMOVE)

**Rationale**:
- `plot_orbital()` is redundant - just calls `plot_atom()` with specific orbital
- Rename `plot_atom()` to `plot_ITA()` for correct terminology
- Merge functionality into single `plot_ITA()` function with `orbital` parameter
- Simpler API with one function instead of two

**New Signature**:
```python
def plot_ITA(self, sublattice: int, ITA_index: int = 1, orbital: str = 'total',
             orbital_resolved: bool = False, spin_polarized: bool = True,
             figsize: Tuple[float, float] = (8, 6), save: Optional[str] = None,
             show: bool = True):
    """
    Plot ITA (Interacting Type Atom) DOS with orbital selection.

    Parameters
    ----------
    sublattice : int
        Sublattice (IT) index (1, 2, 3, ...)
    ITA_index : int
        Which ITA on this sublattice (1 = first occurrence, 2 = second, etc.)
        Default: 1
    orbital : str
        Orbital to plot: 'total', 's', 'p', or 'd'
        - If orbital='total' and orbital_resolved=False: plot total DOS
        - If orbital='total' and orbital_resolved=True: plot s, p, d separately
        - If orbital='s'/'p'/'d': plot only that orbital
        Default: 'total'
    orbital_resolved : bool
        If True and orbital='total', plot s, p, d orbitals separately
        Ignored if orbital is 's', 'p', or 'd'
        Default: False
    spin_polarized : bool
        If True, plot spin-up and spin-down separately
    figsize : tuple
        Figure size (width, height)
    save : str, optional
        Filename to save plot
    show : bool
        Whether to display the plot

    Examples
    --------
    >>> plotter.plot_ITA(sublattice=1, ITA_index=1)  # Total DOS for 1st ITA on sublattice 1
    >>> plotter.plot_ITA(sublattice=1, ITA_index=1, orbital_resolved=True)  # s, p, d separately
    >>> plotter.plot_ITA(sublattice=1, ITA_index=2, orbital='d')  # Only d-orbital for 2nd ITA
    """
```

**Implementation Logic**:
```python
# Get ITA info for title
ITAs_on_sublattice = [(atom_num, elem) for atom_num, elem, sub in self.parser.atom_info if sub == sublattice]
if not ITAs_on_sublattice or ITA_index < 1 or ITA_index > len(ITAs_on_sublattice):
    raise ValueError(f"Invalid sublattice {sublattice} or ITA_index {ITA_index}")

atom_number, element = ITAs_on_sublattice[ITA_index - 1]

fig, ax = plt.subplots(figsize=figsize)

if orbital == 'total' and orbital_resolved:
    # Plot s, p, d separately
    orbitals = ['s', 'p', 'd']
    colors = ['C0', 'C1', 'C2']
    for orb, color in zip(orbitals, colors):
        dos_down, dos_up = self.parser.get_ITA_dos(sublattice, ITA_index, orbital=orb,
                                                     spin_polarized=True)
        if spin_polarized and dos_up is not None:
            ax.plot(dos_up[:, 0], dos_up[:, 1], label=orb, linestyle='-', color=color)
            ax.plot(dos_down[:, 0], -dos_down[:, 1], linestyle='--', color=color)
        else:
            dos_total = dos_down[:, 1] + (dos_up[:, 1] if dos_up is not None else 0)
            ax.plot(dos_down[:, 0], dos_total, label=orb, color=color)
    title = f'ITA {ITA_index} ({element.upper()}, sublattice {sublattice}) - Orbital resolved'
else:
    # Plot single orbital (total, s, p, or d)
    dos_down, dos_up = self.parser.get_ITA_dos(sublattice, ITA_index, orbital=orbital,
                                                 spin_polarized=True)
    label = orbital if orbital != 'total' else 'Total'
    if spin_polarized and dos_up is not None:
        ax.plot(dos_up[:, 0], dos_up[:, 1], label=label, color='blue', linestyle='-')
        ax.plot(dos_down[:, 0], -dos_down[:, 1], color='blue', linestyle='--')
    else:
        dos_total = dos_down[:, 1] + (dos_up[:, 1] if dos_up is not None else 0)
        ax.plot(dos_down[:, 0], dos_total, label=label, color='black')

    orbital_str = f'{orbital}-orbital' if orbital != 'total' else ''
    title = f'ITA {ITA_index} ({element.upper()}, sublattice {sublattice}) {orbital_str} DOS'

# Common plotting elements
if spin_polarized:
    ax.axhline(0, color='black', linewidth=0.5)
ax.axvline(0, color='gray', linestyle='--', alpha=0.5, label='E_F')
ax.set_xlabel('Energy (Ry)')
ax.set_ylabel('DOS (states/Ry)')
ax.legend()
ax.set_title(title)
plt.tight_layout()

if save:
    plt.savefig(save, dpi=300)
if show:
    plt.show()

return fig, ax
```

**Benefits**:
- Single function for all ITA plotting needs
- Correct terminology: "ITA" instead of "atom"
- Backwards compatible behavior with `orbital_resolved` parameter
- Can plot specific orbital or all orbitals
- Uses new `get_ITA_dos()` with sublattice/ITA_index parameters
- Cleaner API - removes redundant `plot_orbital()` function

**Breaking Changes**:
- **RENAMES** `plot_atom()` → `plot_ITA()`
- Old signature: `plot_atom(atom_number, orbital_resolved=False, ...)`
- New signature: `plot_ITA(sublattice, ITA_index=1, orbital='total', orbital_resolved=False, ...)`
- **REMOVES** `plot_orbital()` function entirely

---

#### Task 2.3: Rename list_atoms() to list_ITAs() and remove list_sublattices()
**Files**:
- `modules/dos.py:259-268` (list_atoms - rename to list_ITAs)
- `modules/dos.py:270-272` (list_sublattices - REMOVE)

**Rationale**:
- Correct terminology: "ITA" instead of "atom"
- `list_ITAs()` already returns sublattice information in each tuple
- Having a separate `list_sublattices()` is redundant
- Users can extract unique sublattices from `list_ITAs()` if needed

**Actions**:
- **RENAME** `list_atoms()` → `list_ITAs()`
- **REMOVE** `list_sublattices()` function entirely

**New Implementation**:
```python
def list_ITAs(self) -> List[Tuple[int, str, int]]:
    """
    Return list of ITAs (Interacting Type Atoms) with their info.

    Returns
    -------
    list of tuples
        Each tuple is (ITA_number, element, sublattice)
        ITA_number is the internal sequential numbering (1, 2, 3, ...)
        For access by sublattice, use sublattice and ITA_index parameters in get_ITA_dos()

    Examples
    --------
    >>> parser.list_ITAs()
    [(1, 'pt', 1), (2, 'pt', 1), (3, 'fe', 2), (4, 'fe', 2)]

    # Extract unique sublattices
    >>> ITAs = parser.list_ITAs()
    >>> sublattices = sorted(set(sub for _, _, sub in ITAs))
    """
    return self.atom_info
```

**Migration**:
```python
# OLD
atoms = parser.list_atoms()
sublattices = parser.list_sublattices()

# NEW
ITAs = parser.list_ITAs()  # Renamed from list_atoms()
sublattices = sorted(set(sub for _, _, sub in ITAs))  # Extract manually
```

**Note**: The internal parser still has `atom_info` which stores this data. The renaming just makes the terminology consistent.

---

### Phase 3: Documentation & Consistency

#### Task 3.1: Update dos_guide.md
- Remove references to non-existent 'element' functionality
- Document column structures clearly
- Add examples with NaN handling
- Clarify sublattice vs atom DOS difference

#### Task 3.2: Add Validation Tests
- Test with files containing ****
- Test with 1, 2, 3+ sublattice systems
- Test NaN propagation through calculations

---

## Other Weak Points in Repository

### 1. **No Input Validation on Column Indices**
**Files**: All plotting functions
**Issue**: No bounds checking before accessing columns like `[:, 3]` or `[:, 4]`
**Risk**: IndexError on systems with fewer columns

### 2. **Inconsistent Error Messages**
**Files**: Throughout `dos.py`
**Issue**: Some functions show available options, others don't
**Example**: `get_atom_dos()` shows available atoms, but `get_sublattice_dos()` doesn't show available sublattices in old implementation

### 3. **No Unit Tests**
**Files**: No test files found for dos.py
**Issue**: Changes risk breaking existing functionality
**Need**: `testing/test_dos.py` with edge cases

### 4. **Silent Failures**
**Files**: `_read_data_block()`
**Issue**: Parse errors silently break without logging
**Risk**: Users don't know data is incomplete

### 5. **Orbital Data for Sublattice is Misleading**
**Files**: `get_sublattice_dos()` docstring claims to return `[E, Total, s, p, d]`
**Issue**: Summing atoms gives orbital data, but IT columns don't have orbital resolution
**Conflict**: Two different data sources give different information

---

## Migration Path

### Breaking Changes Alert - No Backward Compatibility
This refactor **removes and renames functions** for correct ITA/IT terminology and is a **BREAKING CHANGE**:

**Removed Data Functions**:
1. `get_total_dos()` → **REMOVED** - use `get_dos('total')` instead
2. `get_sublattice_dos()` → **REMOVED** - use `get_dos('sublattice', sublattice=N)` instead
3. `get_orbital_dos()` → **REMOVED** - functionality merged into `get_ITA_dos()`

**Renamed Data Functions**:
1. `get_atom_dos()` → **RENAMED** to `get_ITA_dos()` with new signature (sublattice, ITA_index, orbital, sum_ITAs, concentrations)

**Removed Plotter Functions**:
1. `plot_orbital()` → **REMOVED** - functionality merged into `plot_ITA()`
2. Old `plot_sublattice()` → **REMOVED** - used wrong approach (unweighted ITA summation)

**Renamed Plotter Functions**:
1. `plot_partial()` → **RENAMED** to `plot_sublattice()`
2. `plot_atom()` → **RENAMED** to `plot_ITA()` with new signature (sublattice, ITA_index, orbital)

**Removed Helper Functions**:
1. `list_sublattices()` → **REMOVED** - extract from `list_ITAs()` instead

**Renamed Helper Functions**:
1. `list_atoms()` → **RENAMED** to `list_ITAs()` for correct terminology

**New Functions**:
1. `get_dos()` → Unified IT (sublattice) data access from Total DOS section
2. `verify_ITA_sum()` → Validates concentration-weighted ITA sums match IT column data

### New API Structure

**For IT (Sublattice) data from Total DOS section** (no orbital resolution):
- `get_dos('total')` → Total DOS (column 1)
- `get_dos('nos')` → Number of States (column 2)
- `get_dos('sublattice', sublattice=N)` → Sublattice N (IT N) DOS from IT columns (pre-weighted)

**For ITA (Individual Component) data** (with orbital resolution):
- `get_ITA_dos(sublattice, ITA_index, orbital)` → ITA DOS with orbital selection
  - `sublattice` → Which sublattice/IT (1, 2, 3, ...)
  - `ITA_index` → Which ITA on that sublattice (1, 2, 3, ...)
  - `orbital='total'` → Total DOS for this ITA
  - `orbital='s'` → s-orbital DOS
  - `orbital='p'` → p-orbital DOS
  - `orbital='d'` → d-orbital DOS
  - `sum_ITAs=True, concentrations=[...]` → Concentration-weighted sum for orbital-resolved sublattice DOS

**Key Concept**:
- **IT (Sublattice)** = Pre-weighted total from CPA, no orbital resolution
- **ITA (Interacting Type Atom)** = Individual concentration components, with orbital resolution
- **Relationship**: `sum(c_i * ITA_i) == IT` for correct concentrations

### Why No Backward Compatibility?
- **Terminology correction**: "atom" → "ITA" (Interacting Type Atom) reflects actual CPA structure
- **Data source clarity**: Old `get_sublattice_dos()` summed ITAs without concentration weighting
- **New capability**: Concentration-weighted summation enables orbital-resolved sublattice DOS
- **Correct understanding**: IT columns are pre-weighted CPA results, ITA sections are components
- Old `get_atom_dos()` used opaque sequential atom_number (1, 2, 3, ...)
- New `get_ITA_dos()` uses sublattice + ITA_index (matches file structure and CPA concept)
- File can have same sublattice multiple times (multiple ITAs per IT)
- Different data structures and physics understanding - wrappers would be misleading

---

## Summary

**Critical Priority**:
1. Fix **** handling (data loss issue) - `_read_data_block()`
2. Create unified `get_dos()` function for IT (sublattice) data
3. **RENAME** `get_atom_dos()` → `get_ITA_dos()` with concentration-weighted summation
4. **REMOVE** `get_total_dos()`, `get_sublattice_dos()`, and `get_orbital_dos()` - breaking changes
5. **ADD** `verify_ITA_sum()` function to validate concentration weighting

**High Priority**:
6. Rename `plot_partial()` to `plot_sublattice()` and remove old `plot_sublattice()`
7. Update `plot_total()` to use `get_dos('total')`
8. **RENAME** `plot_atom()` → `plot_ITA()` and merge with `plot_orbital()`
9. **REMOVE** `plot_orbital()` - functionality merged into `plot_ITA()`
10. **RENAME** `list_atoms()` → `list_ITAs()` and remove `list_sublattices()`
11. Add input validation

**Medium Priority**:
12. Update documentation (dos_guide.md) with ITA/IT terminology and concentration examples
13. Add unit tests with concentration weighting edge cases
14. Update convenience function `plot_dos()` to use new API

**Estimated Impact**:
- **BREAKING CHANGES - Data Functions**:
  - 3 functions removed (`get_total_dos`, `get_sublattice_dos`, `get_orbital_dos`)
  - 1 function renamed (`get_atom_dos` → `get_ITA_dos`) with new signature
- **BREAKING CHANGES - Plotter Functions**:
  - 2 functions removed (`plot_orbital`, old `plot_sublattice`)
  - 2 functions renamed (`plot_partial` → `plot_sublattice`, `plot_atom` → `plot_ITA`)
- **BREAKING CHANGES - Helper Functions**:
  - 1 function removed (`list_sublattices()`)
  - 1 function renamed (`list_atoms()` → `list_ITAs()`)
- **NEW FUNCTIONS**:
  - `get_dos()` - unified IT data access
  - `verify_ITA_sum()` - concentration weighting verification
- **Functions modified**: 5 (data: `get_ITA_dos`, `_read_data_block`; plotters: `plot_total`, `plot_sublattice`, `plot_ITA`)
- **Terminology change**: All "atom" → "ITA" (Interacting Type Atom)
- **New capability**: Concentration-weighted orbital-resolved sublattice DOS
- Test files needed: ~5-10 with different ITA counts, concentration weighting, overflow values
- Documentation pages: 1 (dos_guide.md) - extensive updates needed for ITA/IT concepts

**New API After Refactor**:
```python
# ========== IT (Sublattice) Data - Total DOS section (no orbital resolution) ==========
parser.get_dos('total')                    # Total DOS (column 1)
parser.get_dos('nos')                      # Number of States (column 2)
parser.get_dos('sublattice', sublattice=1) # Sublattice 1 (IT1) total DOS (column 3)
parser.get_dos('sublattice', sublattice=2) # Sublattice 2 (IT2) total DOS (column 4)

# ========== ITA (Individual Component) Data - With orbital resolution ==========
# ITA_index specifies which ITA on that sublattice (1st, 2nd, etc.)
parser.get_ITA_dos(sublattice=1, ITA_index=1, orbital='total')  # 1st ITA on sublattice 1
parser.get_ITA_dos(sublattice=1, ITA_index=2, orbital='d')      # 2nd ITA on sublattice 1, d-orbital
parser.get_ITA_dos(sublattice=2, ITA_index=1, orbital='s')      # 1st ITA on sublattice 2, s-orbital
parser.get_ITA_dos(sublattice=1, ITA_index=1, orbital='p')      # 1st ITA on sublattice 1, p-orbital

# ========== Concentration-Weighted Orbital-Resolved Sublattice DOS ==========
# This is the KEY NEW FEATURE - enables orbital-resolved sublattice DOS
parser.get_ITA_dos(sublattice=1, orbital='d', sum_ITAs=True, concentrations=[0.7, 0.3])
# Returns: 0.7 * ITA1_d + 0.3 * ITA2_d (orbital-resolved sublattice DOS)

parser.get_ITA_dos(sublattice=1, orbital='total', sum_ITAs=True, concentrations=[0.7, 0.3])
# Returns: weighted total (should match get_dos('sublattice', sublattice=1) within tolerance)

# ========== Verification ==========
result = parser.verify_ITA_sum(sublattice=1, concentrations=[0.7, 0.3])
# Check that weighted ITA sum matches IT column data

# ========== Plotting Functions ==========
plotter.plot_total()                                        # Uses get_dos('total')
plotter.plot_sublattice()                                   # Plot all sublattices (renamed from plot_partial)
plotter.plot_sublattice(sublattice=1)                      # Plot specific sublattice (IT data)
plotter.plot_ITA(sublattice=1, ITA_index=1)                # Plot total ITA DOS (renamed from plot_atom)
plotter.plot_ITA(sublattice=1, ITA_index=1, orbital='d')   # Plot d-orbital (merged from plot_orbital)
plotter.plot_ITA(sublattice=1, ITA_index=1, orbital_resolved=True)  # Plot s, p, d separately

# ========== Helper Functions ==========
ITAs = parser.list_ITAs()  # Returns [(ITA_num, element, sublattice), ...] - renamed from list_atoms()
sublattices = sorted(set(sub for _, _, sub in ITAs))  # Extract unique sublattices
```
