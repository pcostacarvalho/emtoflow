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
                       structure_pmg) -> Tuple[List[int], List[str], List[float]]:
    """
    Determine which site(s) to vary based on config and structure.

    This function extracts element information from the pymatgen structure,
    making it work for both CIF and parameter input methods.

    Supports both single site (site_index) and multiple sites (site_indices)
    with the same percentages applied to all sites.

    Parameters
    ----------
    config : dict
        Configuration dictionary with loop_perc settings
    structure_pmg : pymatgen.core.Structure
        Pymatgen structure object

    Returns
    -------
    tuple
        (site_indices, elements, base_concentrations)
        - site_indices: List of site indices to vary (always a list, even if single site)
        - elements: List of element symbols at the first site
        - base_concentrations: Current concentrations (as fractions 0-1) from first site

    Raises
    ------
    ValueError
        If site is pure element, site_index is invalid, or sites have different numbers of elements
    """
    loop_config = config['loop_perc']
    
    # Determine which sites to vary
    # Support both 'site_indices' (list) and 'site_index' (single) for backward compatibility
    if 'site_indices' in loop_config and loop_config['site_indices'] is not None:
        site_indices = loop_config['site_indices']
        if not isinstance(site_indices, list):
            raise ValueError("site_indices must be a list of integers")
        if len(site_indices) == 0:
            raise ValueError("site_indices cannot be empty")
    elif 'site_index' in loop_config and loop_config.get('site_index') is not None:
        site_indices = [loop_config['site_index']]
    else:
        # Default to site 0 for backward compatibility
        site_indices = [0]
    
    # Use first site index for element extraction
    site_idx = site_indices[0]

    # Prefer using the YAML-defined alloy specification (sites/substitutions) rather than
    # inspecting pymatgen occupancies. This keeps behavior consistent even when the
    # canonical structure is a primitive standardized cell.

    # Parameter method: sites[] defines the alloy directly
    if config.get('sites') is not None:
        sites = config['sites']
        
        # Validate all site indices
        for idx in site_indices:
            if idx >= len(sites):
                raise ValueError(
                    f"site_index {idx} is out of range for config['sites'].\n"
                    f"sites has length {len(sites)} (0-indexed)."
                )
        
        # Get first site for element information
        site_spec = sites[site_idx]
        elements = site_spec.get('elements', [])
        concentrations = site_spec.get('concentrations', [])
        
        # Validate all sites have same number of elements
        n_elements = len(elements)
        for idx in site_indices:
            if len(sites[idx]['elements']) != n_elements:
                raise ValueError(
                    f"All sites must have the same number of elements. "
                    f"Site {site_idx} has {n_elements} elements, "
                    f"but site {idx} has {len(sites[idx]['elements'])} elements."
                )

    # CIF method: substitutions define which element(s) are variable; use the structure
    # only to identify which base element sits on the selected site.
    elif config.get('substitutions') is not None:
        # Validate all site indices
        for idx in site_indices:
            if idx >= len(structure_pmg.sites):
                raise ValueError(
                    f"site_index {idx} is out of range for the canonical structure.\n"
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
        
        # For CIF method with multiple sites, verify all sites correspond to same substitution
        # (This is a limitation - all sites must have the same base element)
        for idx in site_indices[1:]:
            other_site = structure_pmg.sites[idx]
            if len(other_site.species) == 1:
                other_base = list(other_site.species.keys())[0].symbol
            else:
                other_base = max(other_site.species.items(), key=lambda kv: kv[1])[0].symbol
            
            if other_base != base_element:
                raise ValueError(
                    f"For CIF method with multiple sites, all sites must correspond to the same "
                    f"substitution element. Site {site_idx} has '{base_element}', "
                    f"but site {idx} has '{other_base}'."
                )

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

    return site_indices, elements, concentrations


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
