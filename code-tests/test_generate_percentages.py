#!/usr/bin/env python3
"""
Tests for generate_percentages module.

Tests cover:
- Composition generation (all modes)
- CIF + substitutions workflow
- Parameters + sites workflow
- Zero concentration handling
- YAML file generation
- Validation
"""

import pytest
import yaml
import tempfile
from pathlib import Path

from modules.generate_percentages import generate_percentage_configs
from modules.generate_percentages.composition import determine_loop_site, generate_compositions
from modules.generate_percentages.yaml_writer import (
    create_yaml_for_composition,
    update_substitutions,
    write_yaml_file
)
from modules.alloy_loop import format_composition_name
from modules.structure_builder import create_emto_structure
from utils.config_parser import validate_generate_percentages_config


class TestCompositionGeneration:
    """Test composition generation for all modes."""

    def test_explicit_list_mode(self):
        """Test Mode 1: Explicit composition list."""
        loop_config = {
            'percentages': [[0, 100], [25, 75], [50, 50], [75, 25], [100, 0]]
        }
        compositions = generate_compositions(loop_config, n_elements=2)

        assert len(compositions) == 5
        assert compositions[0] == [0, 100]
        assert compositions[2] == [50, 50]
        assert compositions[4] == [100, 0]

    def test_phase_diagram_binary(self):
        """Test Mode 2: Binary phase diagram."""
        loop_config = {
            'phase_diagram': True,
            'step': 25
        }
        compositions = generate_compositions(loop_config, n_elements=2)

        # Binary with step=25: 0, 25, 50, 75, 100 = 5 compositions
        assert len(compositions) == 5
        assert compositions[0] == [0.0, 100.0]
        assert compositions[-1] == [100.0, 0.0]

    def test_phase_diagram_ternary(self):
        """Test Mode 2: Ternary phase diagram."""
        loop_config = {
            'phase_diagram': True,
            'step': 50
        }
        compositions = generate_compositions(loop_config, n_elements=3)

        # Ternary with step=50: should have 6 compositions
        # (0,0,100), (0,50,50), (0,100,0), (50,0,50), (50,50,0), (100,0,0)
        assert len(compositions) == 6

        # Verify all sum to 100%
        for comp in compositions:
            assert abs(sum(comp) - 100.0) < 0.01

    def test_single_element_sweep(self):
        """Test Mode 3: Single element sweep."""
        loop_config = {
            'element_index': 0,
            'start': 0,
            'end': 100,
            'step': 20
        }
        compositions = generate_compositions(loop_config, n_elements=2)

        # 0, 20, 40, 60, 80, 100 = 6 compositions
        assert len(compositions) == 6
        assert compositions[0][0] == 0.0  # First element at 0%
        assert compositions[-1][0] == 100.0  # First element at 100%

        # Verify second element is complement
        for comp in compositions:
            assert abs(sum(comp) - 100.0) < 0.01


class TestStructureDetection:
    """Test site and element detection from structures."""

    def test_parameters_alloy_detection(self):
        """Test detection from parameter-based alloy."""
        config = {
            'lat': 2,  # FCC
            'a': 3.7,
            'sites': [
                {
                    'position': [0, 0, 0],
                    'elements': ['Cu', 'Mg'],
                    'concentrations': [0.5, 0.5]
                }
            ],
            'loop_perc': {'site_index': 0}
        }

        structure_pmg, _ = create_emto_structure(
            lat=config['lat'],
            a=config['a'],
            sites=config['sites']
        )

        site_idx, elements, concentrations = determine_loop_site(config, structure_pmg)

        assert site_idx == 0
        assert set(elements) == {'Cu', 'Mg'}
        assert len(concentrations) == 2
        assert abs(sum(concentrations) - 1.0) < 0.01

    def test_pure_element_raises_error(self):
        """Test that pure element site raises error."""
        config = {
            'lat': 2,
            'a': 3.7,
            'sites': [
                {
                    'position': [0, 0, 0],
                    'elements': ['Cu'],
                    'concentrations': [1.0]
                }
            ],
            'loop_perc': {'site_index': 0}
        }

        structure_pmg, _ = create_emto_structure(
            lat=config['lat'],
            a=config['a'],
            sites=config['sites']
        )

        with pytest.raises(ValueError, match="pure element"):
            determine_loop_site(config, structure_pmg)


class TestSubstitutionsUpdate:
    """Test updating substitutions for CIF-based configs."""

    def test_update_binary_substitution(self):
        """Test updating binary substitution."""
        config = {
            'substitutions': {
                'Fe': {
                    'elements': ['Fe', 'Co'],
                    'concentrations': [0.5, 0.5]
                }
            }
        }

        new_config = update_substitutions(
            config,
            elements=['Fe', 'Co'],
            concentrations=[0.25, 0.75]
        )

        assert new_config['substitutions']['Fe']['concentrations'] == [0.25, 0.75]

    def test_update_preserves_order(self):
        """Test that element order is preserved."""
        config = {
            'substitutions': {
                'X': {
                    'elements': ['B', 'A'],  # Non-alphabetical order
                    'concentrations': [0.5, 0.5]
                }
            }
        }

        # Input in different order
        new_config = update_substitutions(
            config,
            elements=['A', 'B'],
            concentrations=[0.3, 0.7]
        )

        # Should map correctly: B=0.7, A=0.3
        subst = new_config['substitutions']['X']
        assert subst['elements'] == ['B', 'A']  # Order preserved
        assert subst['concentrations'] == [0.7, 0.3]  # Mapped correctly

    def test_zero_concentration(self):
        """Test zero concentration is preserved."""
        config = {
            'substitutions': {
                'Fe': {
                    'elements': ['Fe', 'Pt'],
                    'concentrations': [0.5, 0.5]
                }
            }
        }

        new_config = update_substitutions(
            config,
            elements=['Fe', 'Pt'],
            concentrations=[0.0, 1.0]
        )

        assert new_config['substitutions']['Fe']['concentrations'] == [0.0, 1.0]


class TestYAMLGeneration:
    """Test YAML file creation and writing."""

    def test_create_yaml_parameters_method(self):
        """Test creating YAML for parameters method."""
        base_config = {
            'output_path': 'CuMg_study',
            'lat': 2,
            'a': 3.7,
            'sites': [
                {
                    'position': [0, 0, 0],
                    'elements': ['Cu', 'Mg'],
                    'concentrations': [0.5, 0.5]
                }
            ],
            'loop_perc': {'enabled': True},
            'dmax': 1.5,
            'magnetic': 'F'
        }

        structure_pmg, _ = create_emto_structure(
            lat=base_config['lat'],
            a=base_config['a'],
            sites=base_config['sites']
        )

        new_config = create_yaml_for_composition(
            base_config=base_config,
            composition=[75, 25],
            composition_name='Cu75_Mg25',
            structure_pmg=structure_pmg,
            site_idx=0,
            elements=['Cu', 'Mg'],
            is_cif_method=False
        )

        # Check concentrations updated
        assert new_config['sites'][0]['concentrations'] == [0.75, 0.25]

        # Check output_path updated
        assert new_config['output_path'] == 'CuMg_study/Cu75_Mg25'

        # Check loop_perc disabled
        assert new_config['loop_perc']['enabled'] is False

        # Check other settings preserved
        assert new_config['lat'] == 2
        assert new_config['dmax'] == 1.5
        assert new_config['magnetic'] == 'F'

    def test_create_yaml_cif_method(self):
        """Test creating YAML for CIF method."""
        base_config = {
            'output_path': 'FePt_study',
            'cif_file': 'FePt.cif',
            'substitutions': {
                'Fe': {
                    'elements': ['Fe', 'Co'],
                    'concentrations': [0.5, 0.5]
                }
            },
            'loop_perc': {'enabled': True},
            'dmax': 1.5
        }

        # For testing, create a simple structure
        structure_pmg, _ = create_emto_structure(
            lat=2,
            a=3.7,
            sites=[{
                'position': [0, 0, 0],
                'elements': ['Fe', 'Co'],
                'concentrations': [0.5, 0.5]
            }]
        )

        new_config = create_yaml_for_composition(
            base_config=base_config,
            composition=[25, 75],
            composition_name='Fe25_Co75',
            structure_pmg=structure_pmg,
            site_idx=0,
            elements=['Fe', 'Co'],
            is_cif_method=True
        )

        # Check substitutions updated
        assert new_config['substitutions']['Fe']['concentrations'] == [0.25, 0.75]

        # Check output_path updated
        assert new_config['output_path'] == 'FePt_study/Fe25_Co75'

        # Check loop_perc disabled
        assert new_config['loop_perc']['enabled'] is False

        # Check CIF path preserved
        assert new_config['cif_file'] == 'FePt.cif'

    def test_write_yaml_file(self):
        """Test writing YAML file."""
        config = {
            'output_path': 'test_output',
            'lat': 2,
            'a': 3.7,
            'sites': [
                {
                    'position': [0, 0, 0],
                    'elements': ['Cu', 'Mg'],
                    'concentrations': [0.5, 0.5]
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / 'test_config.yaml'
            write_yaml_file(config, str(yaml_path))

            # Check file exists
            assert yaml_path.exists()

            # Check file can be loaded
            with open(yaml_path, 'r') as f:
                loaded_config = yaml.safe_load(f)

            assert loaded_config['lat'] == 2
            assert loaded_config['a'] == 3.7
            assert loaded_config['sites'][0]['elements'] == ['Cu', 'Mg']


class TestValidation:
    """Test configuration validation."""

    def test_validate_missing_loop_perc(self):
        """Test validation fails if loop_perc missing."""
        config = {'output_path': 'test'}

        with pytest.raises(ValueError, match="loop_perc section is missing"):
            validate_generate_percentages_config(config)

    def test_validate_loop_perc_disabled(self):
        """Test validation fails if loop_perc disabled."""
        config = {
            'loop_perc': {'enabled': False}
        }

        with pytest.raises(ValueError, match="loop_perc.enabled must be true"):
            validate_generate_percentages_config(config)

    def test_validate_missing_structure_input(self):
        """Test validation fails if no structure input."""
        config = {
            'loop_perc': {'enabled': True}
        }

        with pytest.raises(ValueError, match="Invalid structure input"):
            validate_generate_percentages_config(config)

    def test_validate_cif_without_substitutions(self):
        """Test validation fails if CIF without substitutions."""
        config = {
            'loop_perc': {'enabled': True},
            'cif_file': 'test.cif'
        }

        with pytest.raises(ValueError, match="requires 'substitutions'"):
            validate_generate_percentages_config(config)


class TestCompositionNaming:
    """Test composition naming convention."""

    def test_binary_naming(self):
        """Test binary alloy naming."""
        name = format_composition_name(['Fe', 'Pt'], [50.0, 50.0])
        assert name == 'Fe50_Pt50'

        name = format_composition_name(['Cu', 'Mg'], [75.3, 24.7])
        assert name == 'Cu75_Mg25'  # Rounded

    def test_ternary_naming(self):
        """Test ternary alloy naming."""
        name = format_composition_name(['Fe', 'Pt', 'Co'], [50, 30, 20])
        assert name == 'Fe50_Pt30_Co20'

    def test_zero_concentration_naming(self):
        """Test naming with zero concentration."""
        name = format_composition_name(['Fe', 'Pt'], [0, 100])
        assert name == 'Fe0_Pt100'

        name = format_composition_name(['Cu', 'Mg'], [100, 0])
        assert name == 'Cu100_Mg0'


class TestIntegration:
    """Integration tests for full workflow."""

    def test_generate_configs_parameters_method(self):
        """Test full generation with parameters method."""
        # Create temporary master config
        master_config = {
            'output_path': 'CuMg_test',
            'job_name': 'CuMg',
            'lat': 2,
            'a': 3.61,
            'sites': [
                {
                    'position': [0, 0, 0],
                    'elements': ['Cu', 'Mg'],
                    'concentrations': [0.5, 0.5]
                }
            ],
            'loop_perc': {
                'enabled': True,
                'step': 50,  # Only 3 compositions: 0, 50, 100
                'site_index': 0,
                'element_index': 0,
                'start': 0,
                'end': 100,
                'phase_diagram': False
            },
            'dmax': 1.5,
            'magnetic': 'F',
            'optimize_ca': False,
            'optimize_sws': True
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            # Write master config
            master_path = Path(tmpdir) / 'master.yaml'
            write_yaml_file(master_config, str(master_path))

            # Generate configs
            generated_files = generate_percentage_configs(
                str(master_path),
                output_dir=tmpdir
            )

            # Should generate 3 files
            assert len(generated_files) == 3

            # Check filenames
            filenames = [Path(f).name for f in generated_files]
            assert 'Cu0_Mg100.yaml' in filenames
            assert 'Cu50_Mg50.yaml' in filenames
            assert 'Cu100_Mg0.yaml' in filenames

            # Load and check one file
            cu50_path = Path(tmpdir) / 'Cu50_Mg50.yaml'
            with open(cu50_path, 'r') as f:
                cu50_config = yaml.safe_load(f)

            # Check concentrations
            assert cu50_config['sites'][0]['concentrations'] == [0.5, 0.5]

            # Check loop_perc disabled
            assert cu50_config['loop_perc']['enabled'] is False

            # Check output_path updated
            assert 'Cu50_Mg50' in cu50_config['output_path']

            # Check other settings preserved
            assert cu50_config['lat'] == 2
            assert cu50_config['dmax'] == 1.5
            assert cu50_config['optimize_sws'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
