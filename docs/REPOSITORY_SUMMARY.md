# EMTO Input Automation - Repository Summary

## Overview

Python toolkit for automating EMTO (Exact Muffin-Tin Orbitals) input file generation and optimization workflows for electronic structure calculations. Supports both ordered structures and random alloys (CPA) with comprehensive optimization capabilities.

## Core Capabilities

- **Structure Input**: CIF files or lattice parameters with site specifications
- **All 14 EMTO Lattice Types**: Cubic, tetragonal, hexagonal, orthorhombic, monoclinic, rhombohedral, triclinic
- **Alloy Support**: Random alloys (CPA) and ordered intermetallics (L10, L12, B2, Heusler, etc.)
- **Optimization Workflow**: Automated c/a ratio and SWS (volume) optimization with EOS fitting
- **DMAX Optimization**: Automatic cutoff distance optimization (300-600x speedup)
- **Composition Loops**: Systematic composition variation for phase diagrams
- **SLURM Integration**: Automatic job script generation for HPC clusters

## Main Entry Points

### Command Line Tools

1. **`bin/run_optimization.py`** - Main optimization workflow
   ```bash
   python bin/run_optimization.py config.yaml
   ```

2. **`bin/generate_percentages.py`** - Generate YAML files for composition loops
   ```bash
   python bin/generate_percentages.py master_config.yaml
   ```

### Python API

```python
from modules.optimization_workflow import OptimizationWorkflow
from modules.create_input import create_emto_inputs
from modules.structure_builder import create_emto_structure
```

## Module Architecture

### Core Modules

- **`structure_builder.py`**: Unified structure creation from CIF or parameters
- **`create_input.py`**: EMTO input file generation (KSTR, SHAPE, KGRN, KFCD)
- **`optimization_workflow.py`**: Complete optimization workflow orchestrator
- **`dmax_optimizer.py`**: DMAX cutoff optimization with early termination
- **`dos.py`**: DOS parsing and plotting
- **`extract_results.py`**: Results parsing from EMTO output files

### Optimization Submodules (`modules/optimization/`)

- **`execution.py`**: Calculation execution and validation
- **`phase_execution.py`**: Phase 1-3 execution (c/a opt, SWS opt, final calc)
- **`analysis.py`**: EOS fitting, DOS analysis, reporting
- **`prepare_only.py`**: Input generation without execution

### Alloy Modules

- **`alloy_loop.py`**: Legacy automatic composition loop
- **`generate_percentages/`**: YAML file generation for composition loops
  - `generator.py`: Main generation logic
  - `composition.py`: Composition grid generation
  - `yaml_writer.py`: YAML file writing

### Input Generators (`modules/inputs/`)

- **`kstr.py`**: Structure input files
- **`kgrn.py`**: Green's function input files
- **`shape.py`**: Shape function input files
- **`kfcd.py`**: Charge density input files
- **`eos_emto.py`**: Equation of state input/output
- **`jobs_tetralith.py`**: SLURM job script generation

### Utilities (`utils/`)

- **`config_parser.py`**: Configuration validation and defaults
- **`aux_lists.py`**: K-point rescaling based on lattice parameters
- **`running_bash.py`**: Job execution (SLURM/local)
- **`file_io.py`**: File utilities

## Workflow

### Single-Point Calculation

1. Create structure (CIF or parameters)
2. Generate EMTO input files
3. (Optional) Run calculations
4. Parse results

### Optimization Workflow

1. **Phase 1**: c/a ratio optimization (optional)
   - Sweep c/a ratios at fixed SWS
   - Fit equation of state
   - Find optimal c/a

2. **Phase 2**: SWS optimization (optional)
   - Sweep SWS values at optimal c/a
   - Fit equation of state
   - Find optimal SWS (volume)

3. **Phase 3**: Final calculation
   - Run with optimized parameters
   - Parse results

4. **Analysis**: DOS analysis, reporting, visualization

## Configuration

All workflows use YAML configuration files. See `refs/optimization_config_template.yaml` for complete template.

Key configuration sections:
- Structure input (CIF or parameters)
- EMTO calculation parameters
- Optimization settings
- Execution settings (SLURM/local)
- Analysis settings

## Key Features

### Smart Defaults
- Auto-generates c/a and SWS ranges from single values
- Calculates parameters from structure if not provided
- Automatic lattice type detection from CIF files

### Unified Interface
- Single entry point for CIF and parameter-based structures
- Same structure dictionary format for all workflows
- Consistent API across all modules

### Performance Optimizations
- DMAX optimization with early termination (300-600x speedup)
- Parallel execution support
- Efficient file I/O

### Error Handling
- Comprehensive validation at all stages
- Graceful failure handling
- Intermediate results preservation

## Testing

Test suite in `code-tests/`:
- Unit tests for individual modules
- Integration tests for workflows
- Example configurations in `files/systems/`

## Development

See `refs/DEVELOPMENT_GUIDELINES.md` for:
- Centralized validation and defaults
- Modular code organization
- Template synchronization
- Configuration best practices

## Dependencies

- Python 3.7+
- pymatgen (structure manipulation)
- numpy (numerical operations)
- matplotlib (plotting)

## License

MIT License

## Status

✅ **Production Ready**: All core features implemented and tested
- Structure creation (CIF and parameters)
- Input file generation
- Optimization workflows
- Alloy support (CPA and ordered)
- DMAX optimization
- Composition loops
- DOS analysis
- Results parsing
