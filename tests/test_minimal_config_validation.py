from utils.config_parser import load_and_validate_config


def test_minimal_parameter_config_validation():
    """
    Minimal in-memory config that should validate successfully.

    This uses the parameter workflow (lat, a, sites) and avoids any
    dependency on EMTO executables by setting create_job_script=False
    and not enabling optimization features that require eos/kstr paths.
    """
    config_dict = {
        "output_path": "./test_output",
        "job_name": "test_job",
        "lat": 2,  # FCC
        "a": 3.6,
        "sites": [
            {
                "position": [0.0, 0.0, 0.0],
                "elements": ["Cu"],
                "concentrations": [1.0],
            }
        ],
        "dmax": 1.8,
        "optimize_ca": False,
        "optimize_sws": False,
        "optimize_dmax": False,
        "create_job_script": False,
    }

    # Should not raise and should return a dict with defaults applied
    validated = load_and_validate_config(config_dict)

    assert validated["output_path"] == "./test_output"
    assert validated["job_name"] == "test_job"
    assert validated["lat"] == 2
    assert validated["dmax"] == 1.8
    # Defaults from apply_config_defaults should be present
    assert "functional" in validated
    assert "eos_type" in validated

