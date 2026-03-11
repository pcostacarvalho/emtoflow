"""
Public-facing import shim for the main optimization workflow.

This allows users to write:

from emtoflow.modules.optimization_workflow import OptimizationWorkflow

while the implementation lives in ``emtoflow.modules.optimization_workflow``.
"""

from emtoflow.modules.optimization_workflow import OptimizationWorkflow

__all__ = ["OptimizationWorkflow"]

