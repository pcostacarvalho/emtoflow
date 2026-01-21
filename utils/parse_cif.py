from pymatgen.core import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
import numpy as np


def get_LatticeVectors(cif_file):
    # Load structure from CIF
    # IMPORTANT: EMTO requires CONVENTIONAL cell, not primitive!
    structure = Structure.from_file(cif_file)
    sga = SpacegroupAnalyzer(structure)
    conventional_structure = sga.get_conventional_standard_structure()  # NOT get_primitive_standard_structure()

    a = conventional_structure.lattice.a
    b = conventional_structure.lattice.b
    c = conventional_structure.lattice.c
    matrix = conventional_structure.lattice.matrix
    cart_coords = np.array([i.coords for i in conventional_structure.sites])
    atoms = [i.specie for i in conventional_structure.sites]

    return matrix, cart_coords, a, b, c, atoms