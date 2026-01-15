"""
EMTO Input Automation Package

This package provides tools for automating EMTO input file creation:
- inputs: Low-level input file generators
- workflows: High-level automation workflows
- parse_cif: CIF file parsing utilities
- dmax_optimizer: DMAX parameter optimization
- eos: Equation of state analysis
"""

from modules.create_input import create_emto_inputs
from modules.dos import DOSParser, DOSPlotter
from modules.optimization_workflow import OptimizationWorkflow

__all__ = [
    'create_emto_inputs',
    'DOSParser',
    'DOSPlotter',
    'OptimizationWorkflow'
]

__version__ = '1.0.0'