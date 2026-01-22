#!/usr/bin/env python3
"""
YAML file writing operations for generate_percentages module.

This module provides functions for:
- Creating modified configs for specific compositions
- Updating substitutions or sites with new concentrations
- Writing YAML files with proper formatting
"""

import copy
import yaml
from pathlib import Path
from typing import Dict, Any, List


def create_yaml_for_composition(base_config: Dict[str, Any],
                                composition: List[float],
                                composition_name: str,
                                structure_pmg,
                                site_idx: int,
                                elements: List[str],
                                is_cif_method: bool) -> Dict[str, Any]:
    """
    Create modified config for a specific composition.

    Steps:
    1. Deep copy base config
    2. Update concentrations (in substitutions or sites)
    3. Update output_path with composition subdirectory
    4. Disable loop_perc
    5. Preserve all other settings

    Parameters
    ----------
    base_config : dict
        Original master configuration
    composition : list
        Composition as percentages (e.g., [50, 50])
    composition_name : str
        Formatted name (e.g., "Fe50_Pt50")
    structure_pmg : pymatgen.core.Structure
        Structure object (for reference)
    site_idx : int
        Index of site being varied
    elements : list
        Element symbols at varied site
    is_cif_method : bool
        True if using CIF + substitutions, False if using parameters

    Returns
    -------
    dict
        Modified configuration for this composition
    """
    # Deep copy to avoid modifying original
    new_config = copy.deepcopy(base_config)

    # Convert percentages to fractions (0-1 range)
    concentrations = [p / 100.0 for p in composition]

    # Update concentrations based on input method
    if is_cif_method:
        # CIF + substitutions method
        new_config = update_substitutions(new_config, elements, concentrations)
    else:
        # Parameter method (lat, a, sites)
        new_config['sites'][site_idx]['concentrations'] = concentrations

    # Update output_path with composition subdirectory
    base_output = base_config.get('output_path', 'output')
    new_config['output_path'] = f"{base_output}/{composition_name}"

    # Disable loop_perc in generated config
    if new_config.get('loop_perc'):
        new_config['loop_perc']['enabled'] = False

    return new_config


def update_substitutions(config: Dict[str, Any],
                        elements: List[str],
                        concentrations: List[float]) -> Dict[str, Any]:
    """
    Update substitutions section for CIF-based configs.

    Find which substitution entry corresponds to the elements being varied
    and update its concentrations.

    Parameters
    ----------
    config : dict
        Configuration with substitutions section
    elements : list
        Elements being varied (e.g., ['Fe', 'Co'])
    concentrations : list
        New concentrations (fractions 0-1)

    Returns
    -------
    dict
        Config with updated substitutions

    Raises
    ------
    ValueError
        If no matching substitution found for elements
    """
    if not config.get('substitutions'):
        raise ValueError("Config must have substitutions section for CIF method")

    # Find matching substitution entry
    # Match is when substitution elements equal our elements (order-independent)
    elements_set = set(elements)
    matched = False

    for elem_key, subst_dict in config['substitutions'].items():
        subst_elements = set(subst_dict.get('elements', []))

        if subst_elements == elements_set:
            # Found match - update concentrations
            # Need to match order of elements in substitution
            subst_elem_list = subst_dict['elements']

            # Create mapping from element to new concentration
            elem_to_conc = {elem: conc for elem, conc in zip(elements, concentrations)}

            # Update in correct order
            new_concentrations = [elem_to_conc[elem] for elem in subst_elem_list]
            config['substitutions'][elem_key]['concentrations'] = new_concentrations

            matched = True
            break

    if not matched:
        raise ValueError(
            f"No substitution found for elements {elements}.\n"
            f"Available substitutions: {list(config['substitutions'].keys())}"
        )

    return config


def write_yaml_file(config: Dict[str, Any], output_path: str) -> None:
    """
    Write config dictionary to YAML file with proper formatting.

    Parameters
    ----------
    config : dict
        Configuration dictionary to write
    output_path : str
        Path where YAML file will be written

    Notes
    -----
    Uses PyYAML with:
    - default_flow_style=False for readable formatting
    - sort_keys=False to preserve order
    - allow_unicode=True for special characters
    """
    output_path = Path(output_path)

    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write YAML with nice formatting
    with open(output_path, 'w') as f:
        yaml.dump(
            config,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            indent=2
        )
