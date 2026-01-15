"""
Input file generators for EMTO.

This module provides functions to create input files for different EMTO programs:
- KSTR: Slope and Madelung matrices
- SHAPE: Atomic sphere radii
- KGRN: Self-consistent KKR calculations
- KFCD: Full charge density calculations
- EOS: Equation of state input
- Jobs: SLURM batch scripts
"""

from .kstr import create_kstr_input
from .shape import create_shape_input
from .kgrn import create_kgrn_input
from .kfcd import create_kfcd_input
from .eos_emto import create_eos_input, parse_eos_output, morse_energy
from .jobs_tetralith import (
    write_serial_sbatch,
    write_parallel_sbatch
)

__all__ = [
    'create_kstr_input',
    'create_shape_input',
    'create_kgrn_input',
    'create_kfcd_input',
    'create_eos_input',
    'write_serial_sbatch',
    'write_parallel_sbatch',
    'parse_eos_output',
    'morse_energy'
]