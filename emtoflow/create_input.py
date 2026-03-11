"""
Public-facing import shim for EMTO input generation.

This allows:

    from emtoflow.create_input import create_emto_inputs
"""

from emtoflow.modules.create_input import create_emto_inputs

__all__ = ["create_emto_inputs"]

