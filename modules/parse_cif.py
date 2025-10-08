from pymatgen.core import Structure
import numpy as np


def get_LatticeVectors(cif_file):
    # Load structure from CIF
    structure = Structure.from_file(cif_file)

    a = structure.lattice.a
    b = structure.lattice.b
    c = structure.lattice.c
    matrix = structure.lattice.matrix
    cart_coords = np.array([i.coords for i in structure.sites])

    return matrix, cart_coords, a, b, c