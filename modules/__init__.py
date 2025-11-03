"""
EMTO Input Automation Package

This package provides tools for automating EMTO input file creation:
- inputs: Low-level input file generators
- workflows: High-level automation workflows
- parse_cif: CIF file parsing utilities
- dmax_optimizer: DMAX parameter optimization
- eos: Equation of state analysis
"""

from .workflows import create_emto_inputs

__all__ = [
    'create_emto_inputs',
]

__version__ = '1.0.0'