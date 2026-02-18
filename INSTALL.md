# Installation Guide

This guide will help you install all dependencies needed to run the EMTO Input Automation toolkit.

## Prerequisites

- **Python**: Version 3.7 or higher
- **pip**: Python package installer (usually comes with Python)
- **Optional**: conda/miniconda (for conda-based installation)

## Installation Methods

### Method 1: Using pip (Recommended)

1. **Clone or download this repository**:
   ```bash
   git clone <repository-url>
   cd EMTO_input_automation
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

   Or install directly:
   ```bash
   pip install numpy scipy pymatgen pandas matplotlib pyyaml
   ```

### Method 2: Using conda

1. **Create a new conda environment**:
   ```bash
   conda env create -f environment.yml
   ```

2. **Activate the environment**:
   ```bash
   conda activate emto-input-automation
   ```

3. **Verify installation**:
   ```bash
   python -c "import numpy, scipy, pymatgen, pandas, matplotlib, yaml; print('All packages installed successfully!')"
   ```

### Method 3: Manual Installation

If you prefer to install packages individually:

```bash
pip install numpy>=1.19.0
pip install scipy>=1.5.0
pip install pymatgen>=2022.0.0
pip install pandas>=1.3.0
pip install matplotlib>=3.3.0
pip install pyyaml>=5.4.0
```

## Required Packages

| Package | Purpose | Minimum Version |
|---------|---------|----------------|
| **numpy** | Numerical computing and array operations | 1.19.0 |
| **scipy** | Scientific computing (optimization, interpolation) | 1.5.0 |
| **pymatgen** | Materials science and crystal structure handling | 2022.0.0 |
| **pandas** | Data manipulation and analysis | 1.3.0 |
| **matplotlib** | Plotting and visualization | 3.3.0 |
| **pyyaml** | YAML configuration file parsing | 5.4.0 |

## Verification

After installation, verify that all packages are correctly installed:

```bash
python -c "
import numpy as np
import scipy
import pymatgen
import pandas as pd
import matplotlib.pyplot as plt
import yaml

print('✓ numpy:', np.__version__)
print('✓ scipy:', scipy.__version__)
print('✓ pymatgen:', pymatgen.__version__)
print('✓ pandas:', pd.__version__)
print('✓ matplotlib:', plt.matplotlib.__version__)
print('✓ pyyaml:', yaml.__version__)
print('\nAll dependencies installed successfully!')
"
```

## Troubleshooting

### Issue: `pymatgen` installation fails

**Solution**: Install pymatgen using conda instead:
```bash
conda install -c conda-forge pymatgen
```

Or install with additional dependencies:
```bash
pip install pymatgen[ase,vis,electronic_structure]
```

### Issue: Import errors after installation

**Solution**: Make sure you're using the correct Python environment:
```bash
# Check Python version
python --version

# Check if packages are installed
pip list | grep -E "numpy|scipy|pymatgen|pandas|matplotlib|pyyaml"
```

### Issue: Permission errors during installation

**Solution**: Use `--user` flag or a virtual environment:
```bash
# Option 1: Install for current user only
pip install --user -r requirements.txt

# Option 2: Use virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Next Steps

After installation, you can:

1. **Read the main README.md** for usage instructions
2. **Check the configuration template**: `docs/optimization_config_template.yaml`
3. **Run a test calculation** to verify everything works

## Additional Notes

- **EMTO executables**: This toolkit generates input files for EMTO calculations. You'll need the EMTO binaries (kstr.exe, shape.exe, kgrn_mpi.x, kfcd.exe, eos.exe) separately to run actual calculations.
- **System requirements**: The toolkit works on Linux, macOS, and Windows (with WSL recommended for Windows).
- **Python version**: Python 3.7+ is required. Python 3.8+ is recommended for best compatibility.
