#!/usr/bin/env python3
"""
Composition handling for generate_percentages module.

This module provides functions for:
- Determining which site to vary based on structure
- Generating composition lists based on loop_perc mode
- Extracting element information from pymatgen structures
"""

from typing import Dict, Any, List, Tuple

from modules.alloy_loop import (
    generate_single_sweep,
    generate_phase_diagram
)


def determine_loop_site(config: Dict[str, Any],
                       structure_pmg) -> Tuple[int, List[str], List[float]]:
    """
    Determine which site to vary based on config and structure.

    This function extracts element information from the pymatgen structure,
    making it work for both CIF and parameter input methods.

    Parameters
    ----------
    config : dict
        Configuration dictionary with loop_perc settings
    structure_pmg : pymatgen.core.Structure
        Pymatgen structure object

    Returns
    -------
    tuple
        (site_index, elements, base_concentrations)
        - site_index: Index of site to vary
        - elements: List of element symbols at that site
        - base_concentrations: Current concentrations (as fractions 0-1)

    Raises
    ------
    ValueError
        If site is pure element or site_index is invalid
    """
    loop_config = config['loop_perc']
    site_idx = loop_config.get('site_index', 0)

    # Prefer using the YAML-defined alloy specification (sites/substitutions) rather than
    # inspecting pymatgen occupancies. This keeps behavior consistent even when the
    # canonical structure is a primitive standardized cell.

    # Parameter method: sites[] defines the alloy directly
    if config.get('sites') is not None:
        sites = config['sites']
        if site_idx >= len(sites):
            raise ValueError(
                f"site_index {site_idx} is out of range for config['sites'].\n"
                f"sites has length {len(sites)} (0-indexed)."
            )
        site_spec = sites[site_idx]
        elements = site_spec.get('elements', [])
        concentrations = site_spec.get('concentrations', [])

    # CIF method: substitutions define which element(s) are variable; use the structure
    # only to identify which base element sits on the selected site.
    elif config.get('substitutions') is not None:
        if site_idx >= len(structure_pmg.sites):
            raise ValueError(
                f"site_index {site_idx} is out of range for the canonical structure.\n"
                f"Structure has {len(structure_pmg.sites)} sites (0-indexed)."
            )

        site = structure_pmg.sites[site_idx]
        # Determine base element for this site
        if len(site.species) == 1:
            base_element = list(site.species.keys())[0].symbol
        else:
            # Mixed occupancy CIF: choose dominant component as base element for lookup
            base_element = max(site.species.items(), key=lambda kv: kv[1])[0].symbol

        subst = config['substitutions'].get(base_element)
        if subst is None:
            raise ValueError(
                f"Selected site_index {site_idx} corresponds to base element '{base_element}', "
                f"but no substitutions entry was found for it.\n"
                f"Available substitutions: {list(config['substitutions'].keys())}"
            )

        elements = subst.get('elements', [])
        concentrations = subst.get('concentrations', [])

    else:
        raise ValueError(
            "Cannot determine loop site: config must contain either 'sites' (parameter method) "
            "or 'substitutions' (CIF method)."
        )

    # Verify at least 2 elements
    if len(elements) == 1:
        element_symbol = elements[0]
        raise ValueError(
            f"Site {site_idx} is a pure element ({element_symbol}).\n"
            "Cannot vary composition for pure element sites.\n"
            "Use substitutions (CIF) or define alloy in sites (parameters)."
        )
    if len(elements) < 2:
        raise ValueError(
            f"Site {site_idx} must have at least 2 elements for composition loop.\n"
            f"Found: {elements}"
        )

    return site_idx, elements, concentrations


def generate_compositions(loop_config: Dict[str, Any],
                          n_elements: int) -> List[List[float]]:
    """
    Generate composition list based on loop_perc mode.

    Reuses logic from alloy_loop.py for consistency.

    Parameters
    ----------
    loop_config : dict
        loop_perc configuration dictionary
    n_elements : int
        Number of elements in alloy

    Returns
    -------
    list of list
        List of compositions (each composition is list of percentages)

    Notes
    -----
    Three modes:
    1. Explicit list (percentages provided)
    2. Phase diagram (all combinations with step)
    3. Single element sweep (vary one element)
    """
    # Mode 1: Explicit composition list
    if loop_config.get('percentages') is not None:
        compositions = loop_config['percentages']
        print(f"Mode: Explicit composition list")
        return compositions

    # Mode 2: Phase diagram
    elif loop_config.get('phase_diagram') is True:
        step = loop_config.get('step', 10)
        compositions = generate_phase_diagram(n_elements, step)
        print(f"Mode: Phase diagram (step={step})")
        if len(compositions) > 100:
            print(f"⚠ WARNING: This will create {len(compositions)} YAML files!")
        return compositions

    # Mode 3: Single element sweep
    else:
        elem_idx = loop_config.get('element_index', 0)
        start = loop_config.get('start', 0)
        end = loop_config.get('end', 100)
        step = loop_config.get('step', 10)

        compositions = generate_single_sweep(n_elements, elem_idx, start, end, step)
        print(f"Mode: Single element sweep (element {elem_idx}, step={step})")
        return compositions
