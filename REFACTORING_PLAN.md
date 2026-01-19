# Optimization Workflow Refactoring Plan

## Current State
- **File**: `modules/optimization_workflow.py`
- **Lines**: 1685 lines ❌ (too large!)
- **Structure**: Single monolithic class

## Target Structure

```
modules/optimization/
├── __init__.py              (~20 lines)
│   └── Exports: OptimizationWorkflow
│
├── workflow.py              (~300 lines) ⭐ Main orchestrator
│   └── OptimizationWorkflow class
│       ├── __init__()
│       └── run()
│
├── execution.py             (~210 lines) ✅ DONE
│   ├── run_calculations()
│   └── validate_calculations()
│
├── analysis.py              (~400 lines)
│   ├── run_eos_fit()
│   ├── generate_dos_analysis()
│   └── generate_summary_report()
│
├── phase_execution.py       (~500 lines)
│   ├── optimize_ca_ratio()
│   ├── optimize_sws()
│   └── run_optimized_calculation()
│
└── prepare_only.py          (~200 lines)
    └── run_prepare_only_mode()
```

## File Sizes
- execution.py: ~210 lines ✅
- prepare_only.py: ~200 lines ✅
- workflow.py: ~300 lines ✅
- analysis.py: ~400 lines ✅
- phase_execution.py: ~500 lines (will split if needed)

All under 500 lines, following guidelines!

## Benefits
✅ Easy to navigate (~200-400 lines per file)
✅ Clear separation of concerns
✅ Easy to test individual modules
✅ Easy to maintain and extend
✅ Follows DEVELOPMENT_GUIDELINES.md

## Migration
1. Create all new modules ✅ (execution.py done)
2. Update imports in workflow.py
3. Update `bin/run_optimization.py` to import from new location
4. Remove old `optimization_workflow.py`
5. Test with existing configs

## Breaking Changes
- Import path changes from:
  ```python
  from modules.optimization_workflow import OptimizationWorkflow
  ```
  To:
  ```python
  from modules.optimization import OptimizationWorkflow
  ```

This is acceptable since backward compatibility is not required.
