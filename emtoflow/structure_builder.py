"""
Public-facing import shim for the structure builder.

This allows:

    from emtoflow.structure_builder import create_emto_structure, lattice_param_to_sws
"""

from emtoflow.modules.structure_builder import create_emto_structure, lattice_param_to_sws

__all__ = ["create_emto_structure", "lattice_param_to_sws"]

