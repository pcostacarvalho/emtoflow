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
        'alpha': 90,
        'beta': 90,
        'gamma': 90,
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

        # Analysis defaults
        'generate_plots': True,
        'export_csv': True,
        'plot_format': 'png',
        'generate_dos': False,
        'dos_plot_range': None,

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
    }

    # Apply defaults for missing keys
    for key, default_value in defaults.items():
        if key not in config:
            config[key] = default_value

    return config

