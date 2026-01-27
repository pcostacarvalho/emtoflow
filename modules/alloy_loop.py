#!/usr/bin/env python3
"""
Thin wrapper for looping over alloy percentages.

This module provides functionality to automatically generate and run
calculations for different alloy compositions.
"""

import copy
import itertools
from pathlib import Path
from typing import Dict, Any, List


def run_with_percentage_loop(config: Dict[str, Any], workflow_runner):
    """
    Run workflow for multiple alloy compositions.

    Supports varying one or multiple sites simultaneously with the same percentages.
    Use 'site_index' for single site or 'site_indices' (list) for multiple sites.

    Parameters
    ----------
    config : dict
        Base configuration dictionary with loop_perc section
    workflow_runner : callable
        Function that runs the workflow for a single config
        Should accept config dict and return results

    Returns
    -------
    list
        List of results from each composition run
    """
    loop_config = config['loop_perc']
    
    # Determine which sites to vary
    # site_index can be either an integer (single site) or a list (multiple sites)
    if 'site_index' not in loop_config or loop_config['site_index'] is None:
        raise ValueError("site_index must be provided in loop_perc")
    
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
    
    # Validate all sites exist and have same number of elements
    sites = config['sites']
    if sites is None:
        raise ValueError("sites must be defined when using loop_perc")
    
    base_site = sites[site_indices[0]]
    n_elements = len(base_site['elements'])
    base_elements = base_site['elements']
    
    # Validate all sites have same number of elements
    for idx in site_indices:
        if idx < 0 or idx >= len(sites):
            raise ValueError(f"site_index {idx} is out of range. Must be between 0 and {len(sites) - 1}")
        site = sites[idx]
        if len(site['elements']) != n_elements:
            raise ValueError(
                f"All sites must have the same number of elements. "
                f"Site {site_indices[0]} has {n_elements} elements, "
                f"but site {idx} has {len(site['elements'])} elements."
            )
        # Check element order matches (optional but recommended)
        if site['elements'] != base_elements:
            print(f"WARNING: Site {idx} has different element order than site {site_indices[0]}")
            print(f"  Site {site_indices[0]}: {base_elements}")
            print(f"  Site {idx}: {site['elements']}")

    # Determine mode and generate compositions
    if loop_config['percentages'] is not None:
        # Mode 1: Explicit list
        compositions = loop_config['percentages']
        print(f"Mode: Explicit composition list ({len(compositions)} compositions)")

    elif loop_config['phase_diagram'] is True:
        # Mode 2: Phase diagram
        compositions = generate_phase_diagram(n_elements, loop_config['step'])
        print(f"Mode: Phase diagram ({len(compositions)} compositions)")
        if len(compositions) > 100:
            print(f"WARNING: This will create {len(compositions)} calculations!")

    else:
        # Mode 3: Single element sweep
        compositions = generate_single_sweep(
            n_elements,
            loop_config['element_index'],
            loop_config['start'],
            loop_config['end'],
            loop_config['step']
        )
        elem_name = base_site['elements'][loop_config['element_index']]
        print(f"Mode: Single element sweep for {elem_name} ({len(compositions)} compositions)")

    # Print site information
    if len(site_indices) == 1:
        print(f"Varying site {site_indices[0]}: {base_elements}")
    else:
        print(f"Varying {len(site_indices)} sites simultaneously: {site_indices}")
        print(f"Elements: {base_elements}")

    # Create parent directory
    base_output = config['output_path']
    loop_parent = f"{base_output}_alloy_loop"
    Path(loop_parent).mkdir(parents=True, exist_ok=True)

    # Loop over compositions
    results = []
    for i, composition in enumerate(compositions, 1):
        print(f"\n{'='*70}")
        print(f"Composition {i}/{len(compositions)}")

        # Deep copy config
        run_config = copy.deepcopy(config)

        # Modify concentrations for all specified sites
        concentrations = [p / 100.0 for p in composition]
        for site_idx in site_indices:
            run_config['sites'][site_idx]['concentrations'] = concentrations

        # Create subdirectory name (using first site's elements)
        subdir_name = format_composition_name(base_elements, composition)
        run_config['output_path'] = str(Path(loop_parent) / subdir_name)

        # Print composition info
        comp_dict = dict(zip(base_elements, composition))
        print(f"Composition: {subdir_name}")
        for elem, perc in comp_dict.items():
            print(f"  {elem}: {perc}%")
        if len(site_indices) > 1:
            print(f"Applied to sites: {site_indices}")
        print(f"{'='*70}\n")

        # Run workflow for this composition
        result = workflow_runner(run_config)
        results.append({
            'composition': composition,
            'composition_name': subdir_name,
            'result': result
        })

    print(f"\n{'='*70}")
    print(f"All {len(compositions)} compositions completed!")
    print(f"Results in: {loop_parent}")
    print(f"{'='*70}\n")

    return results


def generate_single_sweep(n_elements: int, elem_idx: int, start: float,
                          end: float, step: float) -> List[List[float]]:
    """
    Generate compositions for single element sweep.

    Parameters
    ----------
    n_elements : int
        Number of elements
    elem_idx : int
        Index of element to vary
    start : float
        Start percentage
    end : float
        End percentage
    step : float
        Step size

    Returns
    -------
    list
        List of compositions (each composition is a list of percentages)
    """
    compositions = []
    current = start

    while current <= end + 0.001:  # Small epsilon for floating point
        comp = [0.0] * n_elements
        comp[elem_idx] = current

        if n_elements == 2:
            # Binary: simple complement
            other_idx = 1 - elem_idx
            comp[other_idx] = 100.0 - current
        else:
            # Multi-element: distribute remainder equally
            remaining = 100.0 - current
            per_element = remaining / (n_elements - 1)
            for i in range(n_elements):
                if i != elem_idx:
                    comp[i] = per_element

        compositions.append(comp)
        current += step

    return compositions


def generate_phase_diagram(n_elements: int, step: float) -> List[List[float]]:
    """
    Generate all valid compositions for phase diagram.

    Parameters
    ----------
    n_elements : int
        Number of elements
    step : float
        Step size in percentage

    Returns
    -------
    list
        List of all valid compositions
    """
    if n_elements == 2:
        return generate_binary_phase_diagram(step)
    elif n_elements == 3:
        return generate_ternary_phase_diagram(step)
    else:
        return generate_n_element_phase_diagram(n_elements, step)


def generate_binary_phase_diagram(step: float) -> List[List[float]]:
    """Generate binary phase diagram (1D line)."""
    compositions = []
    for p1 in range(0, 101, int(step)):
        p2 = 100.0 - p1
        compositions.append([float(p1), float(p2)])
    return compositions


def generate_ternary_phase_diagram(step: float) -> List[List[float]]:
    """Generate ternary phase diagram (2D triangle)."""
    compositions = []
    step_int = int(step)

    for p1 in range(0, 101, step_int):
        for p2 in range(0, 101 - p1, step_int):
            p3 = 100.0 - p1 - p2
            if p3 >= 0 and abs(p3 - round(p3 / step) * step) < 0.01:
                compositions.append([float(p1), float(p2), float(p3)])

    return compositions


def generate_n_element_phase_diagram(n_elements: int, step: float) -> List[List[float]]:
    """Generate n-element phase diagram (n-dimensional simplex)."""
    compositions = []
    step_int = int(step)

    def recursive_generate(current, remaining, depth):
        if depth == n_elements - 1:
            # Last element gets all remaining
            current.append(float(remaining))
            compositions.append(current.copy())
            current.pop()
            return

        # Try all valid values for current element
        for value in range(0, remaining + 1, step_int):
            current.append(float(value))
            recursive_generate(current, remaining - value, depth + 1)
            current.pop()

    recursive_generate([], 100, 0)
    return compositions


def format_composition_name(elements: List[str], percentages: List[float]) -> str:
    """
    Format composition as directory name.

    Parameters
    ----------
    elements : list
        List of element symbols
    percentages : list
        List of percentages

    Returns
    -------
    str
        Formatted name like "Cu30_Mg70" or "Fe50_Pt30_Co20"
    """
    parts = []
    for element, percentage in zip(elements, percentages):
        perc_int = int(round(percentage))
        parts.append(f"{element}{perc_int}")
    return "_".join(parts)
