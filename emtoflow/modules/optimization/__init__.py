#!/usr/bin/env python3
"""
Optimization workflow package for EMTO calculations.

This package provides modular components for running and analyzing EMTO optimization workflows:
- prepare_only: Input file generation without running calculations
- execution: Running and validating calculations
- analysis: EOS fitting, DOS analysis, and report generation
- phase_execution: Phase 1 (c/a), Phase 2 (SWS), Phase 3 (optimized) execution

The main entry point is OptimizationWorkflow (currently in optimization_workflow.py).
This will be migrated to this package structure in a future refactoring.
"""

# Public API exports
# These imports make the modules easily accessible as:
#   from modules.optimization import prepare_only, execution, analysis, phase_execution

from . import prepare_only
from . import execution
from . import analysis
from . import phase_execution

__all__ = [
    'prepare_only',
    'execution',
    'analysis',
    'phase_execution',
]

__version__ = '0.1.0'
