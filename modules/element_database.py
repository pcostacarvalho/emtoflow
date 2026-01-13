"""
Element Database for EMTO Calculations
========================================

Centralized database of element-specific parameters for EMTO input generation.

This module contains default magnetic moments for elements commonly used in
EMTO calculations. These values serve as initial guesses for self-consistent
calculations.

Usage
-----
    from modules.element_database import DEFAULT_MOMENTS

    moment = DEFAULT_MOMENTS.get('Fe', DEFAULT_MOMENT_FALLBACK)
"""

# ==================== MAGNETIC MOMENT DATABASE ====================
# Default magnetic moments for common elements (in Bohr magnetons)
# These are initial guesses that will be refined during SCF calculations
DEFAULT_MOMENTS = {
    # 3d transition metals
    'Fe': 2.0,
    'Co': 1.5,
    'Ni': 0.6,
    'Mn': 3.0,
    'Cr': 2.5,
    'V': 2.0,
    'Ti': 1.5,
    'Sc': 1.0,

    # 4d transition metals
    'Ru': 1.0,
    'Rh': 0.5,
    'Pd': 0.3,
    'Tc': 1.5,
    'Mo': 1.0,
    'Nb': 1.0,
    'Zr': 1.0,
    'Y': 1.0,

    # 5d transition metals
    'Pt': 0.4,
    'Ir': 0.3,
    'Os': 0.5,
    'Re': 1.0,
    'W': 0.5,
    'Ta': 0.5,
    'Hf': 0.5,

    # Rare earths
    'Gd': 7.0,
    'Tb': 6.0,
    'Dy': 5.0,
    'Ho': 4.0,
    'Er': 3.0,
    'Tm': 2.0,
    'Nd': 3.0,
    'Sm': 5.0,

    # Actinides
    'U': 2.0,
    'Pu': 5.0,
}

# Default fallback for elements not in database
DEFAULT_MOMENT_FALLBACK = 0.1


def get_default_moment(element_symbol):
    """
    Get default magnetic moment for an element.

    Parameters
    ----------
    element_symbol : str
        Chemical symbol (e.g., 'Fe', 'Pt', 'Co')

    Returns
    -------
    float
        Default magnetic moment in Bohr magnetons

    Examples
    --------
    >>> get_default_moment('Fe')
    2.0
    >>> get_default_moment('Pt')
    0.4
    >>> get_default_moment('Xx')  # Unknown element
    0.1
    """
    return DEFAULT_MOMENTS.get(element_symbol.capitalize(), DEFAULT_MOMENT_FALLBACK)


def is_element_supported(element_symbol):
    """
    Check if an element is in the database.

    Parameters
    ----------
    element_symbol : str
        Chemical symbol (e.g., 'Fe', 'Pt', 'Co')

    Returns
    -------
    bool
        True if element is in database, False otherwise

    Examples
    --------
    >>> is_element_supported('Fe')
    True
    >>> is_element_supported('Xx')
    False
    """
    return element_symbol.capitalize() in DEFAULT_MOMENTS


def get_supported_elements():
    """
    Get list of all supported elements.

    Returns
    -------
    list of str
        Sorted list of element symbols

    Examples
    --------
    >>> elements = get_supported_elements()
    >>> 'Fe' in elements
    True
    >>> 'Pt' in elements
    True
    """
    return sorted(DEFAULT_MOMENTS.keys())
