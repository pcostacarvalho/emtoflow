import pathlib

from modules.structure_builder import create_emto_structure


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_create_emto_structure_fept_parameter_workflow():
    """
    Simple smoke test: create L1_0 FePt structure from parameters.

    This does not require any EMTO executables and only verifies that
    the structure dictionary is built consistently.
    """
    sites = [
        {
            "position": [0.0, 0.0, 0.0],
            "elements": ["Fe"],
            "concentrations": [1.0],
        },
        {
            "position": [0.5, 0.5, 0.5],
            "elements": ["Pt"],
            "concentrations": [1.0],
        },
    ]

    structure_pmg, structure_dict = create_emto_structure(
        lat=5,
        a=3.70,
        c=3.552,
        sites=sites,
    )

    assert structure_pmg is not None
    assert isinstance(structure_dict, dict)

    # Basic sanity checks on structure_dict
    assert structure_dict["lat"] == 5
    assert structure_dict["lattice_name"]
    assert structure_dict["NQ3"] == 2
    assert "atom_info" in structure_dict
    assert len(structure_dict["atom_info"]) == 2

