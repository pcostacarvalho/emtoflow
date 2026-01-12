"""
Alloy Input Handling for EMTO
==============================

Functions for validating and processing alloy-specific input parameters.
Supports CPA (Coherent Potential Approximation) random alloys on simple
cubic lattices (FCC, BCC, SC).

Main Functions
--------------
- validate_alloy_input: Validate alloy parameters
- create_alloy_structure: Build unified structure dictionary
- determine_nl_from_elements: Auto-detect NL from element electronic structure
"""

from modules.element_database import DEFAULT_MOMENTS


def determine_nl_from_elements(elements):
    """
    Determine NL (orbital basis set size) from element electronic structures.

    NL represents the maximum orbital angular momentum needed:
    - NL=1: s,p orbitals
    - NL=2: s,p,d orbitals
    - NL=3: s,p,d,f orbitals

    For alloys, NL is the maximum required among all elements.

    Parameters
    ----------
    elements : list of str
        Element symbols (e.g., ['Fe', 'Pt', 'Co'])

    Returns
    -------
    int
        NL value (1, 2, or 3)

    Examples
    --------
    >>> determine_nl_from_elements(['Fe', 'Pt'])
    2
    >>> determine_nl_from_elements(['Fe', 'Gd'])  # Gd has f-electrons
    3
    >>> determine_nl_from_elements(['Al', 'Mg'])
    1
    """
    from pymatgen.core import Element

    NLs = []
    for elem_symbol in elements:
        elem = Element(elem_symbol)
        electronic_str = elem.electronic_structure

        # Check for f-orbitals (rare earths, actinides)
        if 'f' in electronic_str:
            NLs.append(3)
        # Check for d-orbitals (transition metals)
        elif 'd' in electronic_str:
            NLs.append(2)
        # Check for p-orbitals (main group)
        elif 'p' in electronic_str:
            NLs.append(1)
        else:
            NLs.append(1)  # Default to s,p

    return max(NLs) if NLs else 2  # Default to 2 if can't determine


def validate_alloy_input(lattice_type, elements, concentrations, sws, nl=None):
    """
    Validate alloy input parameters.

    Performs comprehensive validation checks on all alloy input parameters
    to ensure they meet EMTO and CPA requirements.

    Parameters
    ----------
    lattice_type : str
        Lattice type: 'fcc', 'bcc', or 'sc'
    elements : list of str
        Element symbols (e.g., ['Fe', 'Pt'])
    concentrations : list of float
        Concentrations (must sum to 1.0)
    sws : float
        Wigner-Seitz radius (must be positive)
    nl : int, optional
        Number of orbital layers (1, 2, or 3). If None, auto-determined.

    Raises
    ------
    ValueError
        If any validation check fails

    Examples
    --------
    >>> validate_alloy_input('fcc', ['Fe', 'Pt'], [0.5, 0.5], 2.65)
    # Returns None if valid

    >>> validate_alloy_input('fcc', ['Fe', 'Pt'], [0.5, 0.6], 2.65)
    ValueError: Concentrations must sum to 1.0, got 1.1
    """

    # Check 1: Valid lattice type
    valid_lattices = ['fcc', 'bcc', 'sc']
    if lattice_type not in valid_lattices:
        raise ValueError(
            f"Invalid lattice type: '{lattice_type}'. "
            f"Must be one of {valid_lattices}"
        )

    # Check 2: Length match
    if len(elements) != len(concentrations):
        raise ValueError(
            f"Number of elements ({len(elements)}) must match "
            f"number of concentrations ({len(concentrations)})"
        )

    # Check 3: At least one element
    if len(elements) == 0:
        raise ValueError("Must provide at least one element")

    # Check 4: Concentration sum
    conc_sum = sum(concentrations)
    if abs(conc_sum - 1.0) > 1e-6:
        raise ValueError(
            f"Concentrations must sum to 1.0, got {conc_sum:.8f}"
        )

    # Check 5: Concentration range
    for i, conc in enumerate(concentrations):
        if conc <= 0 or conc > 1:
            raise ValueError(
                f"Concentration for {elements[i]} must be in range (0, 1], "
                f"got {conc}"
            )

    # Check 6: Valid elements
    for elem in elements:
        if elem not in DEFAULT_MOMENTS:
            raise ValueError(
                f"Unsupported element: '{elem}'. "
                f"Element not found in database. "
                f"See modules/element_database.py for supported elements."
            )

    # Check 7: Positive SWS
    if sws <= 0:
        raise ValueError(f"SWS must be positive, got {sws}")

    # Check 8: Valid NL if provided
    if nl is not None:
        if nl not in [1, 2, 3]:
            raise ValueError(f"NL must be 1, 2, or 3, got {nl}")


def create_alloy_structure(lattice_type, elements, concentrations, initial_sws, nl=None):
    """
    Create unified structure dictionary for alloy.

    Builds a structure dictionary compatible with both CIF and alloy workflows.
    Automatically determines NL from element electronic structures unless
    explicitly provided.

    Parameters
    ----------
    lattice_type : str
        Lattice type: 'fcc', 'bcc', or 'sc'
    elements : list of str
        Element symbols (e.g., ['Fe', 'Pt'])
    concentrations : list of float
        Concentrations (must sum to 1.0)
    initial_sws : float
        Initial Wigner-Seitz radius
    nl : int, optional
        Number of orbital layers. If None, auto-determined from elements.

    Returns
    -------
    dict
        Unified structure dictionary with keys:
        - lat: Bravais lattice number (1-14)
        - is_alloy: True
        - lattice_type: 'fcc', 'bcc', or 'sc'
        - initial_sws: Initial SWS value
        - NL: Number of orbital layers
        - atom_info: List of atom dictionaries with IQ, IT, ITA, conc, etc.

    Examples
    --------
    >>> structure = create_alloy_structure('fcc', ['Fe', 'Pt'], [0.5, 0.5], 2.65)
    >>> structure['lat']
    2
    >>> structure['NL']
    2
    >>> len(structure['atom_info'])
    2
    """
    from modules.cif_extraction import a_scr_map, b_scr_map

    # Map lattice type to LAT number
    lat_map = {'sc': 1, 'fcc': 2, 'bcc': 3}
    lat = lat_map[lattice_type]

    # Determine NL from elements if not provided
    if nl is None:
        nl = determine_nl_from_elements(elements)

    # Build atom_info list
    atom_info = []
    for i, (elem, conc) in enumerate(zip(elements, concentrations), start=1):
        atom_info.append({
            'symbol': elem,
            'IQ': 1,  # Single site for all atoms in CPA
            'IT': i,  # Increment for each element
            'ITA': i,  # Same as IT for single-site alloys
            'conc': conc,
            'a_scr': a_scr_map.get(elem, 0.9),  # Default 0.9 if not found
            'b_scr': b_scr_map.get(elem, 1.0),  # Default 1.0 if not found
            'default_moment': DEFAULT_MOMENTS[elem]
        })

    return {
        'lat': lat,
        'is_alloy': True,
        'lattice_type': lattice_type,
        'initial_sws': initial_sws,
        'NL': nl,
        'NQ3': 1,  # Single atom in primitive cell
        'atom_info': atom_info
    }


def generate_job_name(elements, concentrations, max_length=12):
    """
    Generate job name for alloy following EMTO 12-character limit.

    Format: concA_elementA_concB_elementB (e.g., 0.5_Fe_0.5_Pt)
    If > max_length, falls back to element symbols only (e.g., FePt).

    Parameters
    ----------
    elements : list of str
        Element symbols
    concentrations : list of float
        Concentrations
    max_length : int, optional
        Maximum job name length (default: 12 for EMTO)

    Returns
    -------
    str
        Job name suitable for EMTO

    Examples
    --------
    >>> generate_job_name(['Fe', 'Pt'], [0.5, 0.5])
    '0.5_Fe_0.5_Pt'
    >>> generate_job_name(['Fe', 'Pt', 'Co'], [0.5, 0.3, 0.2])
    'FePtCo'  # Falls back to elements only if too long
    """
    # Try full format with concentrations
    parts = []
    for elem, conc in zip(elements, concentrations):
        parts.append(f"{conc:.1f}_{elem}")
    full_name = "_".join(parts)

    if len(full_name) <= max_length:
        return full_name

    # Fall back to elements only
    elem_only = "".join(elements)
    if len(elem_only) <= max_length:
        return elem_only

    # If still too long, truncate
    return elem_only[:max_length]
