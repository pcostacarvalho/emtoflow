#!/usr/bin/env python3
"""
Generate YAML Files for Alloy Composition Percentages
======================================================

This module creates multiple YAML configuration files from a master YAML,
each representing a different alloy composition. Users can then submit
these files individually to run_optimization.py.

The module separates file generation from workflow execution, giving users
full control over when to submit calculations.

Usage:
    from modules.generate_percentages import generate_percentage_configs

    generated_files = generate_percentage_configs("master_config.yaml")

Or from command line:
    python bin/generate_percentages.py master_config.yaml
"""

import copy
import yaml
from pathlib import Path
from typing import Dict, Any, List, Tuple

from pymatgen.core import Structure

from modules.structure_builder import create_emto_structure
from modules.alloy_loop import (
    generate_single_sweep,
    generate_phase_diagram,
    format_composition_name
)
from utils.config_parser import load_and_validate_config


def generate_percentage_configs(master_config_path: str,
                                output_dir: str = None) -> List[str]:
    """
    Generate YAML files for all compositions from master config.

    This is the main entry point that orchestrates the entire generation process.

    Parameters
    ----------
    master_config_path : str
        Path to master YAML with loop_perc configuration
    output_dir : str, optional
        Directory for generated YAMLs (default: same directory as master YAML)

    Returns
    -------
    list of str
        List of generated YAML file paths

    Raises
    ------
    ValueError
        If loop_perc is not enabled or configuration is invalid

    Examples
    --------
    >>> files = generate_percentage_configs("FePt_master.yaml")
    >>> print(f"Generated {len(files)} YAML files")
    Generated 11 YAML files

    >>> # With custom output directory
    >>> files = generate_percentage_configs("master.yaml", "./configs/")
    """
    # Load and validate master config
    master_config = load_and_validate_config(master_config_path)

    # Validate that loop_perc is enabled
    validate_master_config(master_config)

    # Determine output directory
    if output_dir is None:
        output_dir = Path(master_config_path).parent
    else:
        output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create structure to analyze (structure-agnostic approach)
    structure_pmg, _ = create_emto_structure(
        cif_file=master_config.get('cif_file'),
        substitutions=master_config.get('substitutions'),
        lat=master_config.get('lat'),
        a=master_config.get('a'),
        b=master_config.get('b'),
        c=master_config.get('c'),
        alpha=master_config.get('alpha'),
        beta=master_config.get('beta'),
        gamma=master_config.get('gamma'),
        sites=master_config.get('sites'),
        user_magnetic_moments=master_config.get('user_magnetic_moments')
    )

    # Determine which site to vary and get element information
    site_idx, elements, base_concentrations = determine_loop_site(
        master_config, structure_pmg
    )

    n_elements = len(elements)

    # Generate compositions based on loop_perc mode
    compositions = generate_compositions(master_config['loop_perc'], n_elements)

    print(f"\nGenerating YAML files for {len(compositions)} compositions")
    print(f"Elements: {elements}")
    print(f"Site index: {site_idx}")
    print(f"Output directory: {output_dir}")
    print("-" * 70)

    # Determine input method (CIF vs parameters)
    is_cif_method = master_config.get('cif_file') is not None

    # Generate YAML file for each composition
    generated_files = []

    for i, composition in enumerate(compositions, 1):
        # Format composition name for filename and directory
        composition_name = format_composition_name(elements, composition)

        # Create modified config for this composition
        composition_config = create_yaml_for_composition(
            base_config=master_config,
            composition=composition,
            composition_name=composition_name,
            structure_pmg=structure_pmg,
            site_idx=site_idx,
            elements=elements,
            is_cif_method=is_cif_method
        )

        # Generate filename with composition
        yaml_filename = f"{composition_name}.yaml"
        yaml_path = output_dir / yaml_filename

        # Write YAML file
        write_yaml_file(composition_config, str(yaml_path))

        generated_files.append(str(yaml_path))

        # Print progress
        comp_str = ", ".join([f"{elem}={perc:.0f}%"
                             for elem, perc in zip(elements, composition)])
        print(f"  [{i:3d}/{len(compositions)}] {yaml_filename:30s} ({comp_str})")

    print("-" * 70)
    print(f"✓ Generated {len(generated_files)} YAML files in {output_dir}\n")

    return generated_files


def validate_master_config(config: Dict[str, Any]) -> None:
    """
    Validate master config for percentage generation.

    Parameters
    ----------
    config : dict
        Master configuration dictionary

    Raises
    ------
    ValueError
        If configuration is invalid for percentage generation
    """
    # Check loop_perc is enabled
    if not config.get('loop_perc'):
        raise ValueError(
            "loop_perc section is missing in master config.\n"
            "Add loop_perc configuration to enable percentage generation."
        )

    if not config['loop_perc'].get('enabled'):
        raise ValueError(
            "loop_perc.enabled must be true in master config.\n"
            "Set loop_perc.enabled: true to generate percentage files."
        )

    # Check structure input is valid
    has_cif = config.get('cif_file') is not None
    has_params = all([
        config.get('lat') is not None,
        config.get('a') is not None,
        config.get('sites') is not None
    ])

    if not (has_cif or has_params):
        raise ValueError(
            "Invalid structure input.\n"
            "Must provide either:\n"
            "  1. cif_file + substitutions (for CIF-based alloys)\n"
            "  2. lat, a, sites (for parameter-based alloys)"
        )

    # For CIF method, require substitutions if loop is enabled
    if has_cif and not config.get('substitutions'):
        raise ValueError(
            "CIF input requires 'substitutions' section when using loop_perc.\n"
            "Substitutions define which elements to vary in the composition loop."
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

    # Check site_idx is valid
    if site_idx >= len(structure_pmg.sites):
        raise ValueError(
            f"site_index {site_idx} is out of range.\n"
            f"Structure has {len(structure_pmg.sites)} sites (0-indexed)."
        )

    site = structure_pmg.sites[site_idx]

    # Extract elements and concentrations from site
    if hasattr(site.specie, 'symbol'):
        # Pure element site - cannot vary composition
        raise ValueError(
            f"Site {site_idx} is a pure element ({site.specie.symbol}).\n"
            "Cannot vary composition for pure element sites.\n"
            "Use substitutions (CIF) or define alloy in sites (parameters)."
        )
    else:
        # Alloy site with partial occupancy
        species_dict = site.species.as_dict()
        elements = [elem for elem in species_dict.keys()]
        concentrations = [species_dict[elem] for elem in elements]

    # Verify at least 2 elements
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


# ==================== CONVENIENCE FUNCTIONS ====================

def preview_compositions(master_config_path: str) -> None:
    """
    Preview compositions that would be generated without creating files.

    Useful for checking how many compositions will be created before
    actually generating all the YAML files.

    Parameters
    ----------
    master_config_path : str
        Path to master YAML configuration

    Examples
    --------
    >>> preview_compositions("FePt_master.yaml")
    Mode: Phase diagram (step=10)
    Will generate 11 compositions:
      1. Fe0_Pt100   (Fe=0%, Pt=100%)
      2. Fe10_Pt90   (Fe=10%, Pt=90%)
      3. Fe20_Pt80   (Fe=20%, Pt=80%)
      ...
    """
    # Load config
    master_config = load_and_validate_config(master_config_path)
    validate_master_config(master_config)

    # Create structure
    structure_pmg, _ = create_emto_structure(
        cif_file=master_config.get('cif_file'),
        substitutions=master_config.get('substitutions'),
        lat=master_config.get('lat'),
        a=master_config.get('a'),
        b=master_config.get('b'),
        c=master_config.get('c'),
        sites=master_config.get('sites')
    )

    # Determine site and elements
    site_idx, elements, _ = determine_loop_site(master_config, structure_pmg)
    n_elements = len(elements)

    # Generate compositions
    compositions = generate_compositions(master_config['loop_perc'], n_elements)

    # Print preview
    print(f"\nWill generate {len(compositions)} compositions:")
    print(f"Elements: {elements}")
    print(f"Site index: {site_idx}")
    print("-" * 70)

    for i, comp in enumerate(compositions, 1):
        comp_name = format_composition_name(elements, comp)
        comp_str = ", ".join([f"{elem}={perc:.0f}%"
                             for elem, perc in zip(elements, comp)])
        print(f"  {i:3d}. {comp_name:20s} ({comp_str})")

    print("-" * 70)
    print(f"Total: {len(compositions)} YAML files would be created\n")


if __name__ == '__main__':
    # Simple test when run directly
    import sys

    if len(sys.argv) > 1:
        config_file = sys.argv[1]

        if '--preview' in sys.argv:
            preview_compositions(config_file)
        else:
            generated = generate_percentage_configs(config_file)
            print(f"\n✓ Successfully generated {len(generated)} YAML files")
    else:
        print("Usage:")
        print("  python modules/generate_percentages.py config.yaml")
        print("  python modules/generate_percentages.py config.yaml --preview")
