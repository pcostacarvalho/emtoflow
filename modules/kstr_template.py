"""
KSTR Template Management for Alloys
====================================

Functions for copying and customizing KSTR templates for alloy calculations.
"""

import os
import shutil


def copy_kstr_template(lattice_type, structure, output_path, job_name):
    """
    Copy and customize KSTR template for alloy calculation.

    Reads the appropriate KSTR template (FCC, BCC, or SC), modifies the NL
    parameters based on element electronic structure, and writes to output path.

    Parameters
    ----------
    lattice_type : str
        Lattice type: 'fcc', 'bcc', or 'sc'
    structure : dict
        Structure dictionary containing 'NL' value
    output_path : str
        Output directory path
    job_name : str
        Job name for the KSTR file

    Returns
    -------
    str
        Path to created KSTR file

    Notes
    -----
    Template modifications:
    - NL: Number of orbital layers (from structure dict)
    - NL_mdl: Set to 2*NL + 1 (EMTO requirement)
    - JOBNAM: Set to job_name

    Examples
    --------
    >>> structure = {'NL': 2, 'NQ3': 1, 'lat': 2}
    >>> copy_kstr_template('fcc', structure, './output', 'fept_alloy')
    './output/smx/fept_alloy.dat'
    """
    # Validate lattice type
    valid_lattices = ['fcc', 'bcc', 'sc']
    if lattice_type not in valid_lattices:
        raise ValueError(
            f"Invalid lattice type: '{lattice_type}'. "
            f"Must be one of {valid_lattices}"
        )

    # Get NL from structure
    nl = structure.get('NL', 2)  # Default to 2 if not found
    nl_mdl = 2 * nl + 1

    # Get template path (relative to module location)
    module_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_path = os.path.join(module_dir, 'modules/inputs/templates', 'kstr', f'{lattice_type}.kstr')

    if not os.path.exists(template_path):
        raise FileNotFoundError(
            f"KSTR template not found: {template_path}\n"
            f"Expected template: modules/inputs/templates/kstr/{lattice_type}.kstr"
        )

    # Read template
    with open(template_path, 'r') as f:
        content = f.read()

    # Modify NL and NL_mdl
    # Replace "NL.....= X" with correct value
    import re
    content = re.sub(r'NL\.\.\.\.\.=\s*\d+', f'NL.....= {nl}', content)
    content = re.sub(r'NL_mdl\.=\s*\d+', f'NL_mdl.= {nl_mdl}', content)

    # Replace JOBNAM
    content = re.sub(r'JOBNAM\.\.\.=\w+\s*', f'JOBNAM...={job_name:<10} ', content)

    # Create output directory structure
    os.makedirs(output_path, exist_ok=True)
    smx_path = os.path.join(output_path, 'smx')
    os.makedirs(smx_path, exist_ok=True)

    # Write modified template
    output_file = os.path.join(smx_path, f'{job_name}.dat')
    with open(output_file, 'w') as f:
        f.write(content)

    print(f"✓ KSTR file created: {output_file}")
    print(f"  Lattice: {lattice_type.upper()}, NL={nl}, NL_mdl={nl_mdl}")

    # return output_file


def get_template_info(lattice_type):
    """
    Get information about a KSTR template.

    Parameters
    ----------
    lattice_type : str
        Lattice type: 'fcc', 'bcc', or 'sc'

    Returns
    -------
    dict
        Template information with keys: lat, lattice_name, bsv (primitive vectors)

    Examples
    --------
    >>> info = get_template_info('fcc')
    >>> info['lat']
    2
    >>> info['lattice_name']
    'FCC'
    """
    template_info = {
        'fcc': {
            'lat': 2,
            'lattice_name': 'FCC',
            'bsv': [[0.5, 0.5, 0.0], [0.0, 0.5, 0.5], [0.5, 0.0, 0.5]]
        },
        'bcc': {
            'lat': 3,
            'lattice_name': 'BCC',
            'bsv': [[0.5, 0.5, -0.5], [-0.5, 0.5, 0.5], [0.5, -0.5, 0.5]]
        },
        'sc': {
            'lat': 1,
            'lattice_name': 'SC (Simple Cubic)',
            'bsv': [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        }
    }

    if lattice_type not in template_info:
        raise ValueError(f"Unknown lattice type: {lattice_type}")

    return template_info[lattice_type]
