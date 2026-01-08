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

### 2. **CRITICAL: get_sublattice_dos() Using Wrong Data Source**
**Location**: `modules/dos.py:208-257`

**Problem**:
- Currently sums individual atom DOS data (lines 239-249)
- Individual atom DOS sections may be **incorrectly calculated** by EMTO output
- Should read directly from "Total DOS and NOS and partial (IT)" sections which contain accurate sublattice contributions

**Current Implementation**:
```python
# Wrong: Summing potentially incorrect atom data
for atom_num in atoms_on_sublattice:
    dos_down, dos_up = self.get_atom_dos(atom_num, spin_polarized=True)
    dos_down_sum[:, 1:] += dos_down[:, 1:]
```

**Correct Implementation**:
```python
# Should read directly from total_down/total_up columns:
# Column structure: [E, Total, NOS, IT1, IT2, IT3, ...]
# For sublattice N: column_index = 2 + N
dos_down = self.data['total_down'][:, [0, 2+sublattice]]  # [E, sublattice_DOS]
dos_up = self.data['total_up'][:, [0, 2+sublattice]]
```

**Impact**:
- All sublattice DOS calculations are potentially **incorrect**
- Affects downstream analysis and plots
- Users relying on sublattice data get wrong results

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

#### Task 1.2: Refactor get_sublattice_dos()
**File**: `modules/dos.py:208-257`
**New Implementation**:
```python
def get_sublattice_dos(self, sublattice: int, spin_polarized: bool = True) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """
    Get DOS for a specific sublattice (IT) from the Total DOS section.

    Reads directly from 'Total DOS and NOS and partial (IT)' sections.
    Column structure: [E, Total, NOS, IT1, IT2, IT3, ...]
    For sublattice N: column index = 2 + N

    Parameters
    ----------
    sublattice : int
        Sublattice index (1, 2, 3, ...)
    spin_polarized : bool
        If True, return separate spin channels. If False, sum them.

    Returns
    -------
    dos_down : np.ndarray
        Spin down DOS, columns: [E, sublattice_DOS]
    dos_up : np.ndarray or None
        Spin up DOS (None if spin_polarized=False)
    """
    # Validate sublattice exists
    num_sublattices = self.data['total_down'].shape[1] - 3  # Subtract E, Total, NOS
    if sublattice < 1 or sublattice > num_sublattices:
        raise KeyError(f"Sublattice {sublattice} not found. Available: 1-{num_sublattices}")

    # Column index for this sublattice: 2 (skip E, Total, NOS) + sublattice
    col_idx = 2 + sublattice

    # Extract energy and sublattice columns
    dos_down = np.column_stack([
        self.data['total_down'][:, 0],  # Energy
        self.data['total_down'][:, col_idx]  # Sublattice DOS
    ])

    dos_up = None
    if self.data['total_up'] is not None:
        dos_up = np.column_stack([
            self.data['total_up'][:, 0],  # Energy
            self.data['total_up'][:, col_idx]  # Sublattice DOS
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
- Changes return value structure from `[E, Total, s, p, d]` to `[E, sublattice_DOS]`
- **BREAKS COMPATIBILITY** with existing code expecting orbital-resolved data
- Must update `plot_sublattice()` accordingly

---

### Phase 2: Major Improvements

#### Task 2.1: Fix plot_partial() for Dynamic Sublattices
**File**: `modules/dos.py:331-373`
**Changes**:
- Auto-detect number of sublattices from data shape
- Loop through all IT columns
- Dynamic legend labels

---

#### Task 2.2: Add get_nos() Function
**File**: `modules/dos.py` (new function)
**Purpose**: Extract NOS (Number of States) data from column 2

---

#### Task 2.3: Add get_total_dos() Options
**File**: `modules/dos.py:111-133`
**Purpose**: Add parameter to select Total, NOS, or specific sublattice from total_down/up data

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

### Breaking Changes Alert
The `get_sublattice_dos()` refactor **changes the return format**:
- **Old**: Returns `[E, Total, s, p, d]` by summing atom data
- **New**: Returns `[E, sublattice_DOS]` from IT columns

### Compatibility Options:
1. **Hard Break**: Change function behavior, document in CHANGELOG
2. **New Function**: Create `get_sublattice_dos_from_it()` and deprecate old one
3. **Parameter Switch**: Add `source='it'` or `source='atoms'` parameter

**Recommendation**: Option 2 (new function) for safety

---

## Summary

**Critical Priority**:
1. Fix **** handling (data loss issue)
2. Fix get_sublattice_dos() to use IT columns (correctness issue)

**High Priority**:
3. Fix plot_partial() hardcoding
4. Add input validation

**Medium Priority**:
5. Add NOS access functions
6. Update documentation
7. Add unit tests

**Estimated Impact**:
- Functions affected: 4 (get_sublattice_dos, plot_sublattice, plot_partial, _read_data_block)
- Test files needed: ~5-10 with different sublattice counts and overflow values
- Documentation pages: 1 (dos_guide.md)
