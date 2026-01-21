#!/usr/bin/env python3
"""
Configuration parser and validator for EMTO optimization workflow.

Supports YAML and JSON configuration files with validation.
"""

import yaml
import json
from pathlib import Path
from typing import Dict, Any, Union, Optional


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


# Cubic lattice types (c/a must be 1.0)
CUBIC_LATTICES = [1, 2, 3]  # SC, FCC, BCC


def load_config(config_source: Union[str, Path, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Load configuration from YAML file, JSON file, or dictionary.

    Parameters
    ----------
    config_source : str, Path, or dict
        Either a path to a YAML/JSON file or a configuration dictionary

    Returns
    -------
    dict
        Parsed configuration dictionary

    Raises
    ------
    FileNotFoundError
        If config file doesn't exist
    ConfigValidationError
        If config format is invalid

    Examples
    --------
    >>> # From YAML file
    >>> config = load_config('config.yaml')

    >>> # From dictionary
    >>> config = load_config({'output_path ': 'output', 'job_name': 'test'})
    """
    # If already a dictionary, return it
    if isinstance(config_source, dict):
        return config_source

    # Convert to Path object
    config_path = Path(config_source)

    # Check if file exists
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    # Load based on file extension
    suffix = config_path.suffix.lower()

    try:
        with open(config_path, 'r') as f:
            if suffix in ['.yaml', '.yml']:
                config = yaml.safe_load(f)
            elif suffix == '.json':
                config = json.load(f)
            else:
                raise ConfigValidationError(
                    f"Unsupported config file format: {suffix}. "
                    f"Use .yaml, .yml, or .json"
                )
    except yaml.YAMLError as e:
        raise ConfigValidationError(f"Error parsing YAML file: {e}")
    except json.JSONDecodeError as e:
        raise ConfigValidationError(f"Error parsing JSON file: {e}")

    if not isinstance(config, dict):
        raise ConfigValidationError(
            "Configuration must be a dictionary at the top level"
        )

    return config


def validate_config(config: Dict[str, Any]) -> None:
    """
    Validate configuration dictionary.

    Checks for required fields and valid values.

    Parameters
    ----------
    config : dict
        Configuration dictionary to validate

    Raises
    ------
    ConfigValidationError
        If validation fails

    Examples
    --------
    >>> config = {'output_path': 'output', 'job_name': 'test', 'dmax': 1.52}
    >>> validate_config(config)  # Passes if all required fields present
    """

    config = apply_config_defaults(config)

    # Required fields
    required_fields = ['output_path', 'job_name']

    for field in required_fields:
        if field not in config:
            raise ConfigValidationError(f"Missing required field: {field}")

    # Validate structure input (must have either cif_file OR lattice params)
    has_cif = config.get('cif_file') not in (False, None)
    has_lattice = all(config.get(k) is not None for k in ['lat', 'a', 'sites'])

    # Validate and set angle defaults based on LAT type
    if has_lattice:
        lat = config.get('lat')
        alpha = config.get('alpha')
        beta = config.get('beta')
        gamma = config.get('gamma')

        # LAT 14 (Triclinic): requires alpha, beta, gamma
        if lat == 14:
            if alpha is None or beta is None or gamma is None:
                raise ConfigValidationError(
                    "LAT 14 (triclinic) requires alpha, beta, and gamma angles to be specified"
                )

        # LAT 12, 13 (Monoclinic): requires gamma
        elif lat in [12, 13]:
            if gamma is None:
                raise ConfigValidationError(
                    f"LAT {lat} (monoclinic) requires gamma angle to be specified"
                )
            # Default alpha, beta to 90° for monoclinic
            if alpha is None:
                config['alpha'] = 90
            if beta is None:
                config['beta'] = 90

        # LAT 1-11: default all angles to 90°
        else:
            if alpha is None:
                config['alpha'] = 90
            if beta is None:
                config['beta'] = 90
            if gamma is None:
                config['gamma'] = 90

    if not has_cif and not has_lattice:
        raise ConfigValidationError(
            "Must provide either 'cif_file' OR lattice parameters (lat, a, sites)"
        )

    if has_cif and has_lattice:
        raise ConfigValidationError(
            "Provide either 'cif_file' OR lattice parameters, not both"
        )
    
    if has_lattice and config.get('lat') not in [1, 2, 3, 12]:
        if config.get('c') is None:
            raise ConfigValidationError(
                "Lattice parameter 'c' must be provided for non-cubic lattices"
            )
    

    # Validate magnetic field
    if config['magnetic'] not in ['P', 'F']:
        raise ConfigValidationError(
            f"Invalid magnetic value: {config['magnetic']}. Must be 'P' or 'F'"
        )
    
    # Validate optimization flags if present
    if not isinstance(config['optimize_dmax'], bool):
        raise ConfigValidationError(
            f"optimize_dmax must be boolean, got: {type(config['optimize_dmax'])}"
        )

    if not isinstance(config['optimize_ca'], bool):
        raise ConfigValidationError(
            f"optimize_ca must be boolean, got: {type(config['optimize_ca'])}"
        )

    if not isinstance(config['optimize_sws'], bool):
        raise ConfigValidationError(
            f"optimize_sws must be boolean, got: {type(config['optimize_sws'])}"
        )

    if not isinstance(config['prepare_only'], bool):
        raise ConfigValidationError(
            f"prepare_only must be boolean, got: {type(config['prepare_only'])}"
        )

    # Check for cubic lattices - c/a must be 1.0 (cannot optimize)
    if config.get('lat') in CUBIC_LATTICES:
        if config['optimize_ca']:
            raise ConfigValidationError(
                f"optimize_ca cannot be True for cubic lattices (lat={config['lat']}). "
                "Cubic lattices (SC=1, FCC=2, BCC=3) have c/a = 1.0 by definition."
            )
        # Warn if c/a is provided and not 1.0 for cubic
        if config.get('ca_ratios') is not None:
            ca_list = config['ca_ratios'] if isinstance(config['ca_ratios'], list) else [config['ca_ratios']]
            if any(abs(ca - 1.0) > 0.001 for ca in ca_list):
                raise ConfigValidationError(
                    f"ca_ratios must be 1.0 for cubic lattices (lat={config['lat']}), "
                    f"got: {ca_list}"
                )

    # Validate ca_ratios for c/a optimization
    if config['optimize_ca'] and not config['auto_generate']:
        if config.get('ca_ratios') is not None:
            ca_list = config['ca_ratios'] if isinstance(config['ca_ratios'], list) else [config['ca_ratios']]
            if len(ca_list) <= 1:
                raise ConfigValidationError(
                    "At least two ca_ratios must be provided if optimize_ca is True and auto_generate is False"
                )

    # Validate sws_values for SWS optimization
    if config['optimize_sws'] and not config['auto_generate']:
        if config.get('sws_values') is not None:
            sws_list = config['sws_values'] if isinstance(config['sws_values'], list) else [config['sws_values']]
            if len(sws_list) <= 1:
                raise ConfigValidationError(
                    "At least two sws_values must be provided if optimize_sws is True and auto_generate is False"
                )

    # Validate initial_sws for c/a optimization
    if config['optimize_ca']:
        if config.get('initial_sws') is None:
            raise ConfigValidationError(
                "initial_sws is required when optimize_ca is True"
            )

    # Validate dmax
    if config.get('optimize_dmax'):
        # DMAX optimization requires at least 2 c/a ratios (unless auto_generate)
        if not config.get('auto_generate'):
            if config.get('ca_ratios') is None:
                raise ConfigValidationError(
                    "ca_ratios must be provided when optimize_dmax=True and auto_generate=False. "
                    "Either provide ca_ratios or set auto_generate=True."
                )
            ca_list = config['ca_ratios'] if isinstance(config['ca_ratios'], list) else [config['ca_ratios']]
            if len(ca_list) <= 1:
                raise ConfigValidationError(
                    "At least two ca_ratios must be provided if optimize_dmax is True and auto_generate is False"
                )
    else:
        # If not optimizing DMAX, user must provide it
        if config['dmax'] is None:
            raise ConfigValidationError("dmax must be provided if optimize_dmax is False")
        if not isinstance(config['dmax'], (int, float)) or config['dmax'] <= 0:
                raise ConfigValidationError(
                    f"dmax must be a positive number, got: {config['dmax']}"
                )
    # Validate run_mode 
    if config['run_mode'] not in ['sbatch', 'local']:
        raise ConfigValidationError(
            f"run_mode must be 'sbatch' or 'local', got: {config['run_mode']}"
        )

    # Validate SLURM settings if run_mode is sbatch
    if config.get('run_mode') == 'sbatch':
        slurm_required = ['slurm_account', 'slurm_time']
        for field in slurm_required:
            if field not in config:
                raise ConfigValidationError(
                    f"Missing required SLURM field: {field} (required when run_mode='sbatch')"
                )

    # Validate EOS type if present
    valid_eos_types = ['MO88', 'POLN', 'SPLN', 'MU37', 'ALL']
    if config['eos_type'] not in valid_eos_types:
        raise ConfigValidationError(
            f"Invalid eos_type: {config['eos_type']}. "
            f"Must be one of: {', '.join(valid_eos_types)}"
        )

    # Validate functional type
    valid_functionals = ['GGA', 'LDA', 'LAG']
    if config['functional'] not in valid_functionals:
        raise ConfigValidationError(
            f"Invalid functional: {config['functional']}. "
            f"Must be one of: {', '.join(valid_functionals)}"
        )


    # Validate k-mesh parameters (NKX, NKY, NKZ) if using automatic mesh
    for param_name in ['nkx', 'nky', 'nkz']:
        if param_name in config:
            value = config[param_name]
            if not isinstance(value, int) or value <= 0:
                raise ConfigValidationError(
                    f"{param_name.upper()} must be a positive integer, got: {value}"
                    )

    # Validate eos_executable for optimization workflows
    if config.get('optimize_ca') or config.get('optimize_sws'):
        if config.get('eos_executable') is None:
            raise ConfigValidationError(
                "eos_executable is required when optimize_ca or optimize_sws is True"
            )
        if not isinstance(config['eos_executable'], str) or not config['eos_executable'].strip():
            raise ConfigValidationError(
                f"eos_executable must be a non-empty string path, got: {config['eos_executable']}"
            )

    # Validate ca_ratios and sws_values types if present
    for param_name in ['ca_ratios', 'sws_values']:
        if param_name in config and config[param_name] is not None:
            param = config[param_name]
            # Can be single number or list of numbers
            if isinstance(param, list):
                if not all(isinstance(x, (int, float)) for x in param):
                    raise ConfigValidationError(
                        f"{param_name} list must contain only numbers"
                    )
            elif not isinstance(param, (int, float)):
                raise ConfigValidationError(
                    f"{param_name} must be a number or list of numbers"
                )

    # Validate step sizes if present
    for step_name in ['ca_step', 'sws_step']:
        if step_name in config:
            step = config[step_name]
            if not isinstance(step, (int, float)) or step <= 0:
                raise ConfigValidationError(
                    f"{step_name} must be a positive number, got: {step}"
                )

    # Validate n_points if present
    if 'n_points' in config:
        n = config['n_points']
        if not isinstance(n, int) or n < 3:
            raise ConfigValidationError(
                f"n_points must be an integer >= 3, got: {n}"
            )


    # Validate DMAX optimization parameters if present
    dmax_init = config['dmax_initial']
    if not isinstance(dmax_init, (int, float)) or dmax_init <= 0:
        raise ConfigValidationError(
            f"dmax_initial must be a positive number, got: {dmax_init}"
        )

    target = config['dmax_target_vectors']
    if not isinstance(target, int) or target <= 0:
        raise ConfigValidationError(
            f"dmax_target_vectors must be a positive integer, got: {target}"
        )

    tolerance = config['dmax_vector_tolerance']
    if not isinstance(tolerance, (int, float)) or tolerance < 0:
        raise ConfigValidationError(
            f"dmax_vector_tolerance must be a non-negative number, got: {tolerance}"
        )

    # Validate executables (consolidated validation)
    # kstr_executable needed for: optimize_dmax OR create_job_script
    if config.get('optimize_dmax') or config.get('create_job_script'):
        if config.get('kstr_executable') is None:
            raise ConfigValidationError(
                "kstr_executable is required when optimize_dmax=True or create_job_script=True"
            )
        if not isinstance(config['kstr_executable'], str) or not config['kstr_executable'].strip():
            raise ConfigValidationError(
                f"kstr_executable must be a non-empty string path, got: {config['kstr_executable']}"
            )

    # Other executables needed for: create_job_script
    if config.get('create_job_script'):
        executables = {
            'shape_executable': 'shape_executable',
            'kgrn_executable': 'kgrn_executable',
            'kfcd_executable': 'kfcd_executable'
        }
        for key, name in executables.items():
            if config.get(key) is None:
                raise ConfigValidationError(
                    f"{name} is required when create_job_script=True"
                )
            if not isinstance(config[key], str) or not config[key].strip():
                raise ConfigValidationError(
                    f"{name} must be a non-empty string path, got: {config[key]}"
                )

    # Validate loop_perc configuration
    if config['loop_perc'] is not None and config['loop_perc'].get('enabled') is True:
        validate_loop_perc_config(config)

    # Validate substitutions configuration
    if config.get('substitutions') is not None:
        validate_substitutions_config(config)

def validate_loop_perc_config(config: Dict[str, Any]) -> None:
    """
    Validate loop_perc configuration section.

    Parameters
    ----------
    config : dict
        Configuration dictionary containing loop_perc section

    Raises
    ------
    ConfigValidationError
        If loop_perc validation fails
    """
    loop_config = config['loop_perc']

    # Get number of elements from sites
    has_cif = config.get('cif_file') not in (False, None)
    if has_cif:
        raise ConfigValidationError(
            "loop_perc is not supported with CIF files. "
            "Use parameter-based structure definition (lat, a, sites)."
        )

    site_idx = loop_config['site_index']
    if config.get('sites') is None:
        raise ConfigValidationError(
            "sites must be defined when using loop_perc"
        )

    if site_idx < 0 or site_idx >= len(config['sites']):
        raise ConfigValidationError(
            f"site_index {site_idx} is out of range. "
            f"Must be between 0 and {len(config['sites']) - 1}"
        )

    site = config['sites'][site_idx]
    n_elements = len(site['elements'])

    # Validate step
    if loop_config['step'] is not None:
        step = loop_config['step']
        if not isinstance(step, (int, float)):
            raise ConfigValidationError(
                f"step must be a number, got: {type(step)}"
            )
        if step <= 0 or step > 100:
            raise ConfigValidationError(
                f"step must be between 0 and 100, got: {step}"
            )

    # Validate start/end
    if loop_config['start'] is not None:
        start = loop_config['start']
        if not isinstance(start, (int, float)):
            raise ConfigValidationError(
                f"start must be a number, got: {type(start)}"
            )
        if start < 0 or start > 100:
            raise ConfigValidationError(
                f"start must be between 0 and 100, got: {start}"
            )

    if loop_config['end'] is not None:
        end = loop_config['end']
        if not isinstance(end, (int, float)):
            raise ConfigValidationError(
                f"end must be a number, got: {type(end)}"
            )
        if end < 0 or end > 100:
            raise ConfigValidationError(
                f"end must be between 0 and 100, got: {end}"
            )

    if (loop_config['start'] is not None and loop_config['end'] is not None
        and loop_config['start'] > loop_config['end']):
        raise ConfigValidationError(
            f"start ({loop_config['start']}) must be <= end ({loop_config['end']})"
        )

    # Validate element_index
    if loop_config['element_index'] is not None:
        elem_idx = loop_config['element_index']
        if not isinstance(elem_idx, int):
            raise ConfigValidationError(
                f"element_index must be an integer, got: {type(elem_idx)}"
            )
        if elem_idx < 0 or elem_idx >= n_elements:
            raise ConfigValidationError(
                f"element_index {elem_idx} is out of range. "
                f"Must be between 0 and {n_elements - 1}"
            )

    # Validate percentages list (explicit mode)
    if loop_config['percentages'] is not None:
        percentages = loop_config['percentages']
        if not isinstance(percentages, list):
            raise ConfigValidationError(
                f"percentages must be a list, got: {type(percentages)}"
            )
        if len(percentages) == 0:
            raise ConfigValidationError(
                "percentages list cannot be empty"
            )

        for i, comp in enumerate(percentages):
            if not isinstance(comp, list):
                raise ConfigValidationError(
                    f"percentages[{i}] must be a list, got: {type(comp)}"
                )
            if len(comp) != n_elements:
                raise ConfigValidationError(
                    f"percentages[{i}] has {len(comp)} elements, "
                    f"expected {n_elements} (matching number of elements at site)"
                )

            # Check all are numbers
            if not all(isinstance(p, (int, float)) for p in comp):
                raise ConfigValidationError(
                    f"percentages[{i}] must contain only numbers"
                )

            # Check all non-negative
            if any(p < 0 for p in comp):
                raise ConfigValidationError(
                    f"percentages[{i}] contains negative values"
                )

            # Check sum is 100
            total = sum(comp)
            if abs(total - 100.0) > 0.01:
                raise ConfigValidationError(
                    f"percentages[{i}] must sum to 100%, got: {total}%"
                )

def validate_substitutions_config(config: Dict[str, Any]) -> None:
    """
    Validate substitutions configuration section.
 
    Parameters
    ----------
    config : dict
        Configuration dictionary containing substitutions section
 
    Raises
    ------
    ConfigValidationError
        If substitutions validation fails
    """
    substitutions = config['substitutions']
 
    # Substitutions only work with CIF files
    has_cif = config.get('cif_file') not in (False, None)
    if not has_cif:
        raise ConfigValidationError(
            "substitutions is only supported with CIF files. "
            "If using parameter-based structure (lat, a, sites), define the alloy directly in 'sites'."
        )
 
    # Validate substitutions is a dictionary
    if not isinstance(substitutions, dict):
        raise ConfigValidationError(
            f"substitutions must be a dictionary, got: {type(substitutions)}"
        )
 
    if len(substitutions) == 0:
        raise ConfigValidationError(
            "substitutions dictionary cannot be empty"
        )
 
    # Validate each element substitution
    for element, subst_config in substitutions.items():
        # Check that element name is a string
        if not isinstance(element, str):
            raise ConfigValidationError(
                f"Substitution key must be an element symbol (string), got: {type(element)}"
            )
 
        # Check substitution config structure
        if not isinstance(subst_config, dict):
            raise ConfigValidationError(
                f"Substitution for '{element}' must be a dictionary with 'elements' and 'concentrations', "
                f"got: {type(subst_config)}"
            )
 
        # Check for required keys
        if 'elements' not in subst_config:
            raise ConfigValidationError(
                f"Substitution for '{element}' missing required key 'elements'"
            )
 
        if 'concentrations' not in subst_config:
            raise ConfigValidationError(
                f"Substitution for '{element}' missing required key 'concentrations'"
            )
 
        elements = subst_config['elements']
        concentrations = subst_config['concentrations']
 
        # Validate elements is a list
        if not isinstance(elements, list):
            raise ConfigValidationError(
                f"Substitution for '{element}': 'elements' must be a list, got: {type(elements)}"
            )
 
        if len(elements) == 0:
            raise ConfigValidationError(
                f"Substitution for '{element}': 'elements' list cannot be empty"
            )
 
        # Validate all elements are strings
        if not all(isinstance(e, str) for e in elements):
            raise ConfigValidationError(
                f"Substitution for '{element}': all elements must be strings"
            )
 
        # Validate concentrations is a list
        if not isinstance(concentrations, list):
            raise ConfigValidationError(
                f"Substitution for '{element}': 'concentrations' must be a list, got: {type(concentrations)}"
            )
 
        # Validate lengths match
        if len(elements) != len(concentrations):
            raise ConfigValidationError(
                f"Substitution for '{element}': 'elements' and 'concentrations' must have the same length. "
                f"Got {len(elements)} elements and {len(concentrations)} concentrations"
            )
 
        # Validate all concentrations are numbers
        if not all(isinstance(c, (int, float)) for c in concentrations):
            raise ConfigValidationError(
                f"Substitution for '{element}': all concentrations must be numbers"
            )
 
        # Validate all concentrations are in [0, 1]
        for i, conc in enumerate(concentrations):
            if conc < 0 or conc > 1:
                raise ConfigValidationError(
                    f"Substitution for '{element}': concentration[{i}] = {conc} is out of range [0, 1]"
                )
 
        # Validate concentrations sum to 1.0
        total = sum(concentrations)
        if abs(total - 1.0) > 1e-6:
            raise ConfigValidationError(
                f"Substitution for '{element}': concentrations must sum to 1.0, got: {total}"
            )
 

def load_and_validate_config(
    config_source: Union[str, Path, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Load and validate configuration in one step.

    Convenience function that combines load_config() and validate_config().

    Parameters
    ----------
    config_source : str, Path, or dict
        Configuration file path or dictionary

    Returns
    -------
    dict
        Validated configuration dictionary

    Examples
    --------
    >>> config = load_and_validate_config('optimization_config.yaml')
    >>> print(config['output_path'])
    'my_optimization'
    """
    config = load_config(config_source)
    validate_config(config)
    return config


def apply_config_defaults(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply default values to configuration.

    Parameters
    ----------
    config : dict
        Configuration dictionary

    Returns
    -------
    dict
        Configuration with defaults applied

    Examples
    --------
    >>> config = {'output_path': 'output', 'job_name': 'test'}
    >>> config = apply_config_defaults(config)
    >>> print(config['ca_step'])
    0.02
    """
    defaults = {
        # Structure input defaults
        'cif_file': False,
        'lat': None,
        'a': None,
        'b': None,
        'c': None,
        'alpha': None,  # Set based on LAT in validation
        'beta': None,   # Set based on LAT in validation
        'gamma': None,  # Set based on LAT in validation
        'sites': None,

        # Parameter ranges
        'ca_ratios': None,
        'sws_values': None,
        'initial_sws': None,
        'auto_generate': False,

        # Range generation defaults
        'ca_step': 0.02,
        'sws_step': 0.05,
        'n_points': 7,

        # EMTO calculation parameters
        'magnetic': 'P',
        'user_magnetic_moments': None,
        'dmax': None,

        # Optimization flags
        'optimize_ca': False,
        'optimize_sws': False,

        # DMAX optimization defaults
        'optimize_dmax': False,
        'dmax_initial': 2.0,
        'dmax_target_vectors': 100,
        'dmax_vector_tolerance': 15,

        # Execution defaults
        'run_mode': 'local',
        'prcs': 8,

        # SLURM settings (standardized naming)
        'slurm_account': "naiss2025-1-38",
        'slurm_partition': 'main',
        'slurm_time': '02:00:00',

        # Job script settings
        'create_job_script': True,
        'job_mode': 'serial',

        # Executable paths (with default paths)
        'kstr_executable': "/home/x_pamca/postdoc_proj/emto/bin/kstr.exe",
        'shape_executable': "/home/x_pamca/postdoc_proj/emto/bin/shape.exe",
        'kgrn_executable': "/home/x_pamca/postdoc_proj/emto/bin/kgrn_mpi.x",
        'kfcd_executable': "/home/x_pamca/postdoc_proj/emto/bin/kfcd.exe",
        'eos_executable': "/home/x_pamca/postdoc_proj/emto/bin/eos.exe",

        # EOS defaults
        'eos_type': 'MO88',

        # Energy functional/pseudopotential defaults
        'functional': 'GGA',

        # K-mesh defaults
        'nkx': 21,                       # K-mesh divisions along x (default: 21)
        'nky': 21,                       # K-mesh divisions along y (default: 21)
        'nkz': 21,                       # K-mesh divisions along z (default: 21)

        # Analysis defaults
        'generate_plots': True,
        'export_csv': True,
        'plot_format': 'png',
        'generate_dos': False,
        'dos_plot_range': [-0.8, 0.15],

        # Reference values for percentage calculations
        'reference_ca': None,
        'reference_sws': None,
        'reference_volume': None,

        # Job monitoring defaults
        'poll_interval': 30,
        'max_wait_time': 7200,
        'timeout_action': 'stop',

        # Advanced defaults
        'skip_existing': False,
        'save_intermediate': True,
        'cleanup_temp': False,
        'log_level': 'INFO',

        # Alloy percentage loop defaults
        'loop_perc': None,

        # Input file preparation mode (create files only, don't run calculations)
        'prepare_only': False,
    }

    # Apply defaults for missing keys
    for key, default_value in defaults.items():
        if key not in config:
            config[key] = default_value

    # Apply loop_perc sub-defaults if loop_perc is enabled
    if config['loop_perc'] is not None and config['loop_perc'].get('enabled') is True:
        loop_defaults = {
            'enabled': True,
            'step': 10,
            'start': 0,
            'end': 100,
            'site_index': 0,
            'element_index': 0,
            'phase_diagram': False,
            'percentages': None,
        }
        for key, default_value in loop_defaults.items():
            if key not in config['loop_perc']:
                config['loop_perc'][key] = default_value

    return config

