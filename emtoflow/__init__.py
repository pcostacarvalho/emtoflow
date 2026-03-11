"""
emtoflow
========

High-level Python API for EMTO input generation and optimization workflows.

This package exposes a small public surface that wraps the existing
implementation in ``modules/`` and ``utils/`` so users can do:

    from emtoflow import OptimizationWorkflow, create_emto_structure, create_emto_inputs
    from emtoflow import load_and_validate_config
"""

from __future__ import annotations

from importlib.metadata import version, PackageNotFoundError

from emtoflow.optimization_workflow import OptimizationWorkflow
from emtoflow.structure_builder import create_emto_structure
from emtoflow.create_input import create_emto_inputs
from emtoflow.utils import (
    load_config,
    validate_config,
    load_and_validate_config,
    apply_config_defaults,
    ConfigValidationError,
)

try:
    __version__ = version("emtoflow")
except PackageNotFoundError:  # pragma: no cover - during local, editable use
    __version__ = "0.0.0"

__all__ = [
    "OptimizationWorkflow",
    "create_emto_structure",
    "create_emto_inputs",
    "load_config",
    "validate_config",
    "load_and_validate_config",
    "apply_config_defaults",
    "ConfigValidationError",
    "__version__",
]

