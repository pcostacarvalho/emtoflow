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
    # Required fields
    required_fields = ['output_path', 'job_name', 'dmax', 'magnetic']

    for field in required_fields:
        if field not in config:
            raise ConfigValidationError(f"Missing required field: {field}")

    # Validate structure input (must have either cif_file OR lattice params)
    has_cif = config.get('cif_file') is not None
    has_lattice = all(k in config for k in ['lat', 'a', 'sites'])

    if not has_cif and not has_lattice:
        raise ConfigValidationError(
            "Must provide either 'cif_file' OR lattice parameters (lat, a, sites)"
        )

    if has_cif and has_lattice:
        raise ConfigValidationError(
            "Provide either 'cif_file' OR lattice parameters, not both"
        )

    # Validate magnetic field
    if config['magnetic'] not in ['P', 'F']:
        raise ConfigValidationError(
            f"Invalid magnetic value: {config['magnetic']}. Must be 'P' or 'F'"
        )

    # Validate dmax
    if not isinstance(config['dmax'], (int, float)) or config['dmax'] <= 0:
        raise ConfigValidationError(
            f"dmax must be a positive number, got: {config['dmax']}"
        )

    # Validate optimization flags if present
    if 'optimize_ca' in config and not isinstance(config['optimize_ca'], bool):
        raise ConfigValidationError(
            f"optimize_ca must be boolean, got: {type(config['optimize_ca'])}"
        )

    if 'optimize_sws' in config and not isinstance(config['optimize_sws'], bool):
        raise ConfigValidationError(
            f"optimize_sws must be boolean, got: {type(config['optimize_sws'])}"
        )

    # Validate run_mode if present
    if 'run_mode' in config:
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
    if 'eos_type' in config:
        valid_eos_types = ['MO88', 'POLN', 'SPLN', 'MU37', 'ALL']
        if config['eos_type'] not in valid_eos_types:
            raise ConfigValidationError(
                f"Invalid eos_type: {config['eos_type']}. "
                f"Must be one of: {', '.join(valid_eos_types)}"
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
        # Range generation defaults
        'ca_step': 0.02,
        'sws_step': 0.05,
        'n_points': 7,

        # Optimization flags
        'optimize_ca': True,
        'optimize_sws': True,

        # Execution defaults
        'run_mode': 'sbatch',
        'prcs': 8,
        'slurm_partition': 'main',
        'slurm_time': '02:00:00',

        # EOS defaults
        'eos_type': 'MO88',

        # Analysis defaults
        'generate_plots': True,
        'export_csv': True,
        'plot_format': 'png',

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


if __name__ == '__main__':
    # Example usage
    import sys

    if len(sys.argv) < 2:
        print("Usage: python config_parser.py <config_file>")
        sys.exit(1)

    config_file = sys.argv[1]

    try:
        config = load_and_validate_config(config_file)
        config = apply_config_defaults(config)
        print("Configuration loaded and validated successfully!")
        print(f"\nOutput path: {config['output_path']}")
        print(f"Job name: {config['job_name']}")
        print(f"Magnetic: {config['magnetic']}")
        print(f"DMAX: {config['dmax']}")
    except (FileNotFoundError, ConfigValidationError) as e:
        print(f"Error: {e}")
        sys.exit(1)
