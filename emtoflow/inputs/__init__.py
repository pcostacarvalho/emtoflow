"""
Public-facing import shim for low-level EMTO input generators.

Usage:

    from emtoflow.inputs import (
        create_kstr_input,
        create_shape_input,
        create_kgrn_input,
        create_kfcd_input,
    )
"""

from emtoflow.modules.inputs import (
    create_kstr_input,
    create_shape_input,
    create_kgrn_input,
    create_kfcd_input,
)

__all__ = [
    "create_kstr_input",
    "create_shape_input",
    "create_kgrn_input",
    "create_kfcd_input",
]

