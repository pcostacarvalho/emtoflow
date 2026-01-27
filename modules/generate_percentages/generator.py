#!/usr/bin/env python3
"""
Main generation logic for generate_percentages module.

This module provides the high-level functions:
- generate_percentage_configs: Generate all YAML files
- preview_compositions: Preview compositions without generating files
"""

from pathlib import Path
from typing import List

from modules.structure_builder import create_emto_structure
from modules.alloy_loop import format_composition_name
from modules.inputs.jobs_tetralith import create_master_job_scripts
from utils.config_parser import (
    load_and_validate_config,
    validate_generate_percentages_config
)

from .composition import determine_loop_site, generate_compositions
from .yaml_writer import create_yaml_for_composition, write_yaml_file


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
    # Load and validate master config (includes all validation - better to catch errors early)
    master_config = load_and_validate_config(master_config_path)

    # Additional validation specific to generate_percentages workflow
    validate_generate_percentages_config(master_config)

    # Determine output directory
    if output_dir is None:
        output_dir = Path(master_config_path).parent
    else:
        output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create canonical structure to analyze.
    # Structure creation (including alloy definition via substitutions/sites) lives in structure_builder.
    cif_file_val = master_config.get('cif_file')
    cif_file_arg = cif_file_val if cif_file_val not in (None, False) else None

    if cif_file_arg is not None:
        structure_pmg, _ = create_emto_structure(
            cif_file=cif_file_arg,
            substitutions=master_config.get('substitutions'),
            user_magnetic_moments=master_config.get('user_magnetic_moments')
        )
    else:
        structure_pmg, _ = create_emto_structure(
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

    # Determine which site(s) to vary and get element information
    site_indices, elements, base_concentrations = determine_loop_site(
        master_config, structure_pmg
    )

    n_elements = len(elements)

    # Generate compositions based on loop_perc mode
    compositions = generate_compositions(master_config['loop_perc'], n_elements)

    # Extract base folder from master config's output_path
    base_output = master_config.get('output_path', 'output')
    base_folder = base_output

    # Create base folder structure inside output_dir
    base_folder_path = output_dir / base_folder
    base_folder_path.mkdir(parents=True, exist_ok=True)

    print(f"\nGenerating YAML files for {len(compositions)} compositions")
    print(f"Elements: {elements}")
    if len(site_indices) == 1:
        print(f"Site index: {site_indices[0]}")
    else:
        print(f"Site indices: {site_indices} (same percentages applied to all)")
    print(f"Base folder: {base_folder}")
    print(f"Output directory: {base_folder_path}")
    print("-" * 70)

    # Determine input method (CIF vs parameters)
    # Check for truthy value (not False, not None, not empty string)
    is_cif_method = bool(master_config.get('cif_file'))

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
            site_indices=site_indices,
            elements=elements,
            is_cif_method=is_cif_method,
            base_folder=base_folder
        )

        # Generate filename with composition
        yaml_filename = f"{composition_name}.yaml"
        yaml_path = base_folder_path / yaml_filename

        # Write YAML file
        write_yaml_file(composition_config, str(yaml_path))

        generated_files.append(str(yaml_path))

        # Print progress
        comp_str = ", ".join([f"{elem}={perc:.0f}%"
                             for elem, perc in zip(elements, composition)])
        print(f"  [{i:3d}/{len(compositions)}] {yaml_filename:30s} ({comp_str})")

    print("-" * 70)
    print(f"✓ Generated {len(generated_files)} YAML files in {base_folder_path}\n")

    # Create job scripts if requested
    if master_config.get('create_master_job_script', False):
        create_master_job_scripts(
            generated_files=generated_files,
            master_config=master_config,
            output_dir=base_folder_path
        )

    return generated_files


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
    # Load and validate config
    master_config = load_and_validate_config(master_config_path)
    validate_generate_percentages_config(master_config)

    # Create canonical structure (primitive for CIF workflows).
    cif_file_val = master_config.get('cif_file')
    cif_file_arg = cif_file_val if cif_file_val not in (None, False) else None

    if cif_file_arg is not None:
        structure_pmg, _ = create_emto_structure(
            cif_file=cif_file_arg,
            substitutions=master_config.get('substitutions'),
            user_magnetic_moments=master_config.get('user_magnetic_moments')
        )
    else:
        structure_pmg, _ = create_emto_structure(
            lat=master_config.get('lat'),
            a=master_config.get('a'),
            b=master_config.get('b'),
            c=master_config.get('c'),
            sites=master_config.get('sites'),
            user_magnetic_moments=master_config.get('user_magnetic_moments')
        )

    # Determine site(s) and elements
    site_indices, elements, _ = determine_loop_site(master_config, structure_pmg)
    n_elements = len(elements)

    # Generate compositions
    compositions = generate_compositions(master_config['loop_perc'], n_elements)

    # Print preview
    print(f"\nWill generate {len(compositions)} compositions:")
    print(f"Elements: {elements}")
    if len(site_indices) == 1:
        print(f"Site index: {site_indices[0]}")
    else:
        print(f"Site indices: {site_indices} (same percentages applied to all)")
    print("-" * 70)

    for i, comp in enumerate(compositions, 1):
        comp_name = format_composition_name(elements, comp)
        comp_str = ", ".join([f"{elem}={perc:.0f}%"
                             for elem, perc in zip(elements, comp)])
        print(f"  {i:3d}. {comp_name:20s} ({comp_str})")

    print("-" * 70)
    print(f"Total: {len(compositions)} YAML files would be created\n")
