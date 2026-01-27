# Development Guidelines

This document outlines the core design principles and rules for developing features in the EMTO Input Automation codebase.

## Core Principles

### 1. Centralized Validation in Parser

**Rule**: Any implementation that alters the input file (YAML file or dictionary) should have ALL possible validation checks self-contained inside the parser and not spread out in several files.

**Rationale**:
- Single source of truth for configuration validation
- Easier to maintain and debug
- Prevents inconsistent validation logic across modules
- Users get immediate feedback on configuration errors

**Implementation**:
```python
# ✅ CORRECT: All validation in parser
# File: utils/config_parser.py

def validate_loop_perc_config(config):
    """All loop_perc validation happens here"""
    loop_config = config.get('loop_perc')

    # Validate step
    if loop_config['step'] is not None:
        if loop_config['step'] <= 0 or loop_config['step'] > 100:
            raise ValueError("step must be between 0 and 100")

    # Validate percentages list
    if loop_config['percentages'] is not None:
        n_elements = len(config['sites'][loop_config['site_index']]['elements'])
        for comp in loop_config['percentages']:
            if len(comp) != n_elements:
                raise ValueError(f"Composition {comp} must have {n_elements} elements")
            if abs(sum(comp) - 100.0) > 0.01:
                raise ValueError(f"Composition {comp} must sum to 100%")

    # All other validations...
    return True


# ❌ WRONG: Validation scattered across files
# File: modules/alloy_loop.py
def run_with_percentage_loop(config):
    if config['loop_perc']['step'] <= 0:  # DON'T DO THIS
        raise ValueError("Invalid step")
```

**Location**: All validation should be in `utils/config_parser.py`

---

### 2. Centralized Default Values

**Rule**: Default values are set by the `set_default` function inside the parser and ONLY there.

**Rationale**:
- Single source of truth for defaults
- Prevents "magic values" scattered throughout code
- Easy to change defaults in one place
- Self-documenting configuration

**Implementation**:
```python
# ✅ CORRECT: Defaults set in parser
# File: utils/config_parser.py

def set_defaults(config):
    """Set all default values here"""

    # Existing defaults
    config.setdefault('structure_type', 'param')
    config.setdefault('magnetic', True)
    # ... other defaults ...

    # New feature defaults
    if 'loop_perc' in config and config['loop_perc']['enabled']:
        loop_config = config['loop_perc']
        loop_config.setdefault('step', 10)
        loop_config.setdefault('start', 0)
        loop_config.setdefault('end', 100)
        loop_config.setdefault('site_index', 0)
        loop_config.setdefault('phase_diagram', False)
        loop_config.setdefault('percentages', None)


# ❌ WRONG: Defaults in other modules
# File: modules/alloy_loop.py
def run_with_percentage_loop(config):
    step = config['loop_perc'].get('step', 10)  # DON'T DO THIS
```

**Location**: All defaults must be in the `set_defaults()` function in `utils/config_parser.py`

---

### 3. Explicit Configuration with Null Values

**Rule**: Users should always be able to put all parameters inside the YAML using `null` for when they are not being used. Do NOT check validity by verifying if a key exists - check the VALUE instead.

**Rationale**:
- Explicit configuration is better than implicit
- Users can see all available options in one YAML file
- IDE autocompletion and validation work better
- Self-documenting configuration files

**Implementation**:
```python
# ✅ CORRECT: Check value, not existence
# File: utils/config_parser.py

def validate_loop_perc_config(config):
    loop_config = config['loop_perc']

    # Check if enabled (value check)
    if loop_config['enabled'] is False or loop_config['enabled'] is None:
        return  # Nothing to validate if not enabled

    # Check if percentages provided (value check, not existence)
    if loop_config['percentages'] is not None:
        validate_explicit_compositions(loop_config['percentages'])

    # Check if phase_diagram mode (value check)
    if loop_config['phase_diagram'] is True:
        validate_phase_diagram_params(loop_config)


# ❌ WRONG: Check key existence
def validate_loop_perc_config(config):
    if 'loop_perc' not in config:  # DON'T DO THIS
        return
    if 'percentages' in config['loop_perc']:  # DON'T DO THIS
        validate_explicit_compositions(...)
```

**Example YAML**:
```yaml
# ✅ CORRECT: All parameters explicit, unused ones are null
loop_perc:
  enabled: true
  step: 10
  start: null        # Not used in this mode
  end: null          # Not used in this mode
  site_index: 0
  phase_diagram: false
  percentages: null  # Not used in this mode

# ❌ WRONG: Omitting parameters
loop_perc:
  enabled: true
  step: 10
  # Missing parameters - hard to know what's available
```

---

### 4. Modular Code Organization

**Rule**: When implementing new features, do NOT make a huge file of code. Always split the modules when possible in an organized way.

**Rationale**:
- Easier to understand and maintain
- Facilitates testing individual components
- Reduces merge conflicts
- Improves code reusability

**Implementation Pattern**:
```
modules/
├── alloy_loop/
│   ├── __init__.py           # Public API
│   ├── wrapper.py            # Main loop logic
│   ├── composition.py        # Composition generation
│   └── validation.py         # Additional validations (if needed)
```

**Guidelines**:
- **One file should not exceed ~300 lines** (guideline, not strict rule)
- **Group related functions** into the same module
- **Separate concerns**: validation, generation, execution, formatting
- **Use clear naming** for modules and functions

**Example Structure for Loop Feature**:
```python
# ✅ CORRECT: Organized modules

# File: modules/alloy_loop/__init__.py
"""Alloy percentage loop functionality"""
from .wrapper import run_with_percentage_loop

__all__ = ['run_with_percentage_loop']


# File: modules/alloy_loop/wrapper.py
"""Main loop wrapper that coordinates execution"""
def run_with_percentage_loop(base_config):
    """Main entry point for percentage loop"""
    pass


# File: modules/alloy_loop/composition.py
"""Composition generation for different modes"""
def generate_single_element_sweep(n_elements, elem_idx, start, end, step):
    pass

def generate_phase_diagram_compositions(n_elements, step):
    pass

def generate_binary_compositions(step):
    pass

def generate_ternary_compositions(step):
    pass


# File: modules/alloy_loop/utils.py
"""Utility functions for composition handling"""
def normalize_concentrations(site, varied_index):
    pass

def create_composition_dirname(elements, concentrations):
    pass


# ❌ WRONG: Everything in one huge file
# File: modules/alloy_loop.py (500+ lines)
def run_with_percentage_loop(...):
    # 100 lines

def generate_single_element_sweep(...):
    # 50 lines

def generate_phase_diagram_compositions(...):
    # 100 lines

# ... 10 more functions
```

---

### 5. Template Synchronization

**Rule**: Any change to YAML configuration parameters must be reflected in the configuration template file.

**Rationale**:
- Template serves as the authoritative documentation for all configuration options
- Users rely on the template to discover available features
- Prevents feature documentation drift
- Ensures consistency between code and documentation

**Implementation**:

When adding a new configuration parameter:

1. **Add to parser** (`utils/config_parser.py`):
   ```python
   # Add default value
   def apply_config_defaults(config):
       defaults = {
           # ... existing defaults ...
           'rescale_k': False,  # New parameter
       }

   # Add validation
   def validate_config(config):
       # ... existing validation ...
       if not isinstance(config['rescale_k'], bool):
           raise ConfigValidationError("rescale_k must be boolean")
   ```

2. **Add to template** (`refs/optimization_config_template.yaml`):
   ```yaml
   # K-point rescaling based on lattice parameters (optional)
   rescale_k: false                     # Enable k-point rescaling (default: false)
                                        # When enabled, automatically rescales k-points to maintain
                                        # constant reciprocal-space density across different structures
                                        # Formula: N'_i = (a_ref × N_ref) / a'_i
   ```

3. **Update example files** (optional but recommended):
   - `files/systems/example.yaml` - Add with documentation
   - Test-specific YAML files - Add where relevant

**Location**: Template file is `refs/optimization_config_template.yaml`

**Guidelines**:
- Include the parameter with its default value
- Add clear inline comments explaining the parameter
- Document valid values/ranges
- Explain the formula or behavior if non-trivial
- Group related parameters together in logical sections

---

## File Organization Best Practices

### Parser Structure
```
utils/
└── config_parser.py
    ├── set_defaults()           # All default values
    ├── validate_config()         # Main validation entry
    ├── validate_structure()      # Structure-specific validation
    ├── validate_loop_perc()      # Loop-specific validation
    └── load_and_validate_config()  # Public API
```

### Feature Module Structure
```
modules/
└── feature_name/
    ├── __init__.py       # Public API exports
    ├── core.py           # Main logic
    ├── utils.py          # Utility functions
    └── constants.py      # Constants (if needed)
```

---

## Checklist for New Features

When implementing a new feature, ensure:

- [ ] All validation logic is in `utils/config_parser.py`
- [ ] All default values are set in `apply_config_defaults()` function
- [ ] Configuration checks use `is None` / `is not None` instead of `in dict`
- [ ] YAML examples include ALL parameters (with `null` for unused ones)
- [ ] **Template file updated** (`refs/optimization_config_template.yaml`)
- [ ] Code is split into logical modules (no files > ~300 lines)
- [ ] Each module has a clear, single responsibility
- [ ] Public API is exposed through `__init__.py`

---

## Example: Implementing the Alloy Loop Feature

### Step 1: Add Validation to Parser
```python
# File: utils/config_parser.py

def validate_loop_perc_config(config):
    """Validate loop_perc configuration"""
    # All validation logic here
    pass

def set_defaults(config):
    """Set default values"""
    # Add loop_perc defaults
    if config['loop_perc']['enabled']:
        config['loop_perc'].setdefault('step', 10)
        # ... other defaults
```

### Step 2: Create Modular Implementation
```
modules/alloy_loop/
├── __init__.py           # Export run_with_percentage_loop
├── wrapper.py            # Main loop coordinator
├── composition.py        # Composition generators
└── utils.py              # Helper functions
```

### Step 3: Update Main Entry Point
```python
# File: bin/run_optimization.py

from modules.alloy_loop import run_with_percentage_loop

if config['loop_perc']['enabled']:  # Check value, not existence
    run_with_percentage_loop(config)
else:
    run_single_workflow(config)
```

---

## Anti-Patterns to Avoid

### ❌ Scattered Validation
```python
# DON'T: Validation in multiple files
# File: modules/alloy_loop.py
if step < 0:
    raise ValueError(...)
```

### ❌ Magic Defaults
```python
# DON'T: Defaults scattered in code
step = config.get('step', 10)
```

### ❌ Key Existence Checks
```python
# DON'T: Check if key exists
if 'loop_perc' in config:
    ...
```

### ❌ Monolithic Files
```python
# DON'T: 500+ line files with everything
# File: modules/alloy_loop.py (huge file)
```

---

## Summary

1. **Validation**: Centralized in `utils/config_parser.py`
2. **Defaults**: Only in `apply_config_defaults()` function
3. **Configuration**: Always check VALUES (`is None`), not key existence
4. **Organization**: Split into logical modules (~300 lines max per file)
5. **Template**: Update `refs/optimization_config_template.yaml` for all config changes

Following these guidelines ensures a maintainable, consistent, and user-friendly codebase.
