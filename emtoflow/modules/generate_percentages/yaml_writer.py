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
                                site_indices: List[int],
                                elements: List[str],
                                is_cif_method: bool,
                                base_folder: str) -> Dict[str, Any]:
    """
    Create modified config for a specific composition.

    Steps:
    1. Deep copy base config
    2. Update concentrations (in substitutions or sites) for all specified sites
    3. Update output_path to just composition name (base_folder is handled by directory structure)
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
    site_indices : list
        List of site indices being varied (same percentages applied to all)
        Note: This is an internal parameter - config uses 'site_index' (int or list)
    elements : list
        Element symbols at varied site
    is_cif_method : bool
        True if using CIF + substitutions, False if using parameters
    base_folder : str
        Base folder name from master config's output_path (e.g., "CuMg_fcc")

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
        # Updates ALL substitution entries with matching elements
        # This allows varying multiple base elements (e.g., Cu and Mg) simultaneously
        new_config = update_substitutions(new_config, elements, concentrations)
    else:
        # Parameter method (lat, a, sites)
        # Apply same concentrations to all specified sites
        for site_idx in site_indices:
            new_config['sites'][site_idx]['concentrations'] = concentrations

    # Set output_path to just the composition name
    # The base_folder directory structure is created by generate_percentage_configs
    # and YAML files are placed inside it, so output_path should be relative
    new_config['output_path'] = composition_name

    # Disable loop_perc in generated config
    if new_config.get('loop_perc'):
        new_config['loop_perc']['enabled'] = False

    return new_config


def update_substitutions(config: Dict[str, Any],
                        elements: List[str],
                        concentrations: List[float]) -> Dict[str, Any]:
    """
    Update substitutions section for CIF-based configs.

    Updates ALL substitution entries that have matching elements.
    This allows varying multiple base elements (e.g., Cu and Mg) simultaneously
    when they have the same substitution elements.

    Parameters
    ----------
    config : dict
        Configuration with substitutions section
    elements : list
        Elements being varied (e.g., ['Cu', 'Mg'])
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

    # Find ALL matching substitution entries
    # Match is when substitution elements equal our elements (order-independent)
    elements_set = set(elements)
    matched_keys = []

    for elem_key, subst_dict in config['substitutions'].items():
        subst_elements = set(subst_dict.get('elements', []))

        if subst_elements == elements_set:
            # Found match - will update concentrations
            matched_keys.append(elem_key)

    if not matched_keys:
        raise ValueError(
            f"No substitution found for elements {elements}.\n"
            f"Available substitutions: {list(config['substitutions'].keys())}"
        )

    # Update all matching substitutions
    for elem_key in matched_keys:
        subst_dict = config['substitutions'][elem_key]
        subst_elem_list = subst_dict['elements']

        # Create mapping from element to new concentration
        elem_to_conc = {elem: conc for elem, conc in zip(elements, concentrations)}

        # Update in correct order
        new_concentrations = [elem_to_conc[elem] for elem in subst_elem_list]
        config['substitutions'][elem_key]['concentrations'] = new_concentrations

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
    - Custom Dumper to disable YAML anchors/aliases for cleaner output
    """
    output_path = Path(output_path)

    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Custom Dumper class that disables anchors/aliases
    class NoAliasDumper(yaml.SafeDumper):
        def ignore_aliases(self, data):
            return True

    # Write YAML with nice formatting (no anchors/aliases)
    with open(output_path, 'w') as f:
        yaml.dump(
            config,
            f,
            Dumper=NoAliasDumper,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            indent=2
        )
