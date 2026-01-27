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

    The config uses 'site_index' which can be either an integer (single site)
    or a list of integers (multiple sites). This function always returns a list
    internally for consistent handling.

    Parameters
    ----------
    config : dict
        Configuration dictionary with loop_perc settings
        Must contain 'site_index' (int or list of ints)
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
    # site_index can be either an integer (single site) or a list (multiple sites)
    if 'site_index' not in loop_config or loop_config.get('site_index') is None:
        # Default to site 0 for backward compatibility
        site_indices = [0]
    else:
        site_index_val = loop_config['site_index']
        if isinstance(site_index_val, int):
            site_indices = [site_index_val]
        elif isinstance(site_index_val, list):
            if len(site_index_val) == 0:
                raise ValueError("site_index list cannot be empty")
            if not all(isinstance(idx, int) for idx in site_index_val):
                raise ValueError("All values in site_index list must be integers")
            site_indices = site_index_val
        else:
            raise ValueError(
                f"site_index must be an integer or a list of integers, got: {type(site_index_val)}"
            )
    
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

    # CIF method: substitutions define which element(s) are variable
    elif config.get('substitutions') is not None:
        loop_config = config['loop_perc']
        
        # Check if elements are specified directly (preferred for substitutions)
        if 'substitution_elements' in loop_config and loop_config['substitution_elements'] is not None:
            # Direct element specification - clearer for substitutions
            # For substitutions, we don't need site_indices (substitutions apply to all sites of that element)
            substitution_elements = loop_config['substitution_elements']
            if not isinstance(substitution_elements, list):
                substitution_elements = [substitution_elements]
            
            # Validate all specified elements have substitutions
            for elem in substitution_elements:
                if elem not in config['substitutions']:
                    raise ValueError(
                        f"Element '{elem}' specified in substitution_elements "
                        f"but no substitutions entry found for it.\n"
                        f"Available substitutions: {list(config['substitutions'].keys())}"
                    )
            
            # Get first substitution to get element info
            first_subst = config['substitutions'][substitution_elements[0]]
            elements = first_subst.get('elements', [])
            concentrations = first_subst.get('concentrations', [])
            
            # Verify all substitutions have same elements
            for elem in substitution_elements[1:]:
                other_subst = config['substitutions'][elem]
                other_elements = set(other_subst.get('elements', []))
                if other_elements != set(elements):
                    raise ValueError(
                        f"All substitutions must have the same elements. "
                        f"Substitution '{substitution_elements[0]}' has elements {list(elements)}, "
                        f"but substitution '{elem}' has elements {list(other_elements)}."
                    )
            
            # For substitutions, site_indices is not meaningful (substitutions apply to all sites)
            # Return empty list to indicate we're using substitution_elements
            site_indices = []
        
        else:
            # Legacy: use site_index to identify elements (backward compatibility)
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
                    f"Available substitutions: {list(config['substitutions'].keys())}.\n"
                    f"Tip: Use 'substitution_elements' to specify elements directly."
                )

            elements = subst.get('elements', [])
            concentrations = subst.get('concentrations', [])
            
            # For CIF method with multiple sites, verify all sites have substitutions
            # with matching elements (can have different base elements, e.g., Cu and Mg)
            for idx in site_indices[1:]:
                other_site = structure_pmg.sites[idx]
                if len(other_site.species) == 1:
                    other_base = list(other_site.species.keys())[0].symbol
                else:
                    other_base = max(other_site.species.items(), key=lambda kv: kv[1])[0].symbol
                
                other_subst = config['substitutions'].get(other_base)
                if other_subst is None:
                    raise ValueError(
                        f"Selected site_index {idx} corresponds to base element '{other_base}', "
                        f"but no substitutions entry was found for it.\n"
                        f"Available substitutions: {list(config['substitutions'].keys())}.\n"
                        f"Tip: Use 'substitution_elements' to specify elements directly."
                    )
                
                # Verify substitution has same elements (order-independent)
                other_elements = set(other_subst.get('elements', []))
                if other_elements != set(elements):
                    raise ValueError(
                        f"For CIF method with multiple sites, all substitutions must have the same elements. "
                        f"Site {site_idx} (base '{base_element}') has elements {list(elements)}, "
                        f"but site {idx} (base '{other_base}') has elements {list(other_elements)}."
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
        # Always varies first element (index 0) - concentrations always match element order
        elem_idx = 0
        start = loop_config.get('start', 0)
        end = loop_config.get('end', 100)
        step = loop_config.get('step', 10)

        compositions = generate_single_sweep(n_elements, elem_idx, start, end, step)
        print(f"Mode: Single element sweep (element {elem_idx}, step={step})")
        return compositions
