#!/usr/bin/env python3
"""
Generate YAML Files for Alloy Composition Percentages
======================================================

This module creates multiple YAML configuration files from a master YAML,
each representing a different alloy composition. Users can then submit
these files individually to run_optimization.py.

The module separates file generation from workflow execution, giving users
full control over when to submit calculations.

Public API
----------
generate_percentage_configs : Main function to generate YAML files
preview_compositions : Preview compositions without creating files

Usage Examples
--------------
From Python:
    from modules.generate_percentages import generate_percentage_configs

    generated_files = generate_percentage_configs("master_config.yaml")

From command line:
    python bin/generate_percentages.py master_config.yaml

Design
------
This module follows the development guidelines:
- Validation is in utils/config_parser.py (validate_generate_percentages_config)
- Code split into logical modules (<300 lines each)
- Clear separation of concerns
"""

from .generator import generate_percentage_configs, preview_compositions

__all__ = ['generate_percentage_configs', 'preview_compositions']

__version__ = '1.0.0'
