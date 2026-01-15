#!/usr/bin/env python3
"""
Optimization workflow for EMTO calculations.

Implements automated c/a ratio and SWS optimization workflow.
"""

import os
import sys
import subprocess
import time
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Union, Optional, Tuple

from modules.structure_builder import create_emto_structure, lattice_param_to_sws
from modules.create_input import create_emto_inputs
from modules.inputs.eos_emto import create_eos_input, parse_eos_output
from utils.running_bash import run_sbatch, chmod_and_run
from utils.config_parser import load_and_validate_config, apply_config_defaults
from utils.aux_lists import prepare_ranges


class OptimizationWorkflow:
    """
    Manages complete optimization workflow for EMTO calculations.

    Workflow (configurable):
    1. c/a ratio optimization (optional)
    2. SWS optimization (optional)
    3. Optimized structure calculation
    4. Results parsing
    5. DOS analysis
    6. Visualization and reporting
    """

    def __init__(
        self,
        config):
        """
        Initialize optimization workflow.

        Parameters
        ----------
        config_file : str or Path, optional
            Path to YAML/JSON configuration file
        config_dict : dict, optional
            Configuration dictionary (alternative to file)
        eos_executable : str, optional
            Path to EMTO EOS executable (can also be in config)

        Raises
        ------
        ValueError
            If neither config_file nor config_dict is provided
        """
        # Load and validate configuration
        if config is not None:
            self.config = load_and_validate_config(config)
        else:
            raise ValueError("Must provide either config_file or config_dict")

        # Apply defaults
        self.config = apply_config_defaults(self.config)


        # Create base output directory
        self.base_path = Path(self.config['output_path'])
        self.base_path.mkdir(parents=True, exist_ok=True)

        # Storage for workflow results
        self.results = {}

    def _prepare_ranges(
        self,
        ca_ratios: Optional[Union[float, List[float]]],
        sws_values: Optional[Union[float, List[float]]],
        structure: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[float], List[float]]:
        """
        Auto-generate c/a and SWS ranges if needed.

        Handles three cases for each parameter:
        1. List provided → use as-is
        2. Single value → create range around it (±3*step, n_points)
        3. None → calculate from structure, then create range

        Parameters
        ----------
        ca_ratios : float, list of float, or None
            c/a ratio value(s)
        sws_values : float, list of float, or None
            SWS value(s)
        structure : dict, optional
            Structure dictionary from create_emto_structure()
            Required if ca_ratios or sws_values is None

        Returns
        -------
        tuple of (list, list)
            (ca_ratios_list, sws_values_list)

        Notes
        -----
        Uses config parameters:
        - ca_step: Step size for c/a range (default: 0.02)
        - sws_step: Step size for SWS range (default: 0.05)
        - n_points: Number of points in range (default: 7)
        """
        ca_step = self.config.get('ca_step', 0.02)
        sws_step = self.config.get('sws_step', 0.05)
        n_points = self.config.get('n_points', 7)

        # Process c/a ratios
        if ca_ratios is None:
            # Calculate from structure
            if structure is None:
                raise ValueError("structure is required when ca_ratios is None")

            # Get c/a from structure
            if structure.get('coa') is not None:
                ca_center = structure['coa']
            else:
                ca_center = 1.0  # Cubic structures

            # Generate range
            ca_min = ca_center - 3 * ca_step
            ca_max = ca_center + 3 * ca_step
            ca_list = list(np.linspace(ca_min, ca_max, n_points))

            print(f"Auto-generated c/a ratios around {ca_center:.4f}: {ca_list}")

        elif isinstance(ca_ratios, (int, float)):
            # Single value → generate range
            ca_center = float(ca_ratios)
            ca_min = ca_center - 3 * ca_step
            ca_max = ca_center + 3 * ca_step
            ca_list = list(np.linspace(ca_min, ca_max, n_points))

            print(f"Auto-generated c/a ratios around {ca_center:.4f}: {ca_list}")

        elif isinstance(ca_ratios, list):
            # Use as-is
            ca_list = ca_ratios
            print(f"Using provided c/a ratios: {ca_list}")

        else:
            raise TypeError(f"ca_ratios must be float, list, or None, got {type(ca_ratios)}")

        # Process SWS values
        if sws_values is None:
            # Calculate from structure
            if structure is None:
                raise ValueError("structure is required when sws_values is None")

            # Get pymatgen structure to calculate SWS
            if 'structure_pmg' in structure:
                structure_pmg = structure['structure_pmg']
            else:
                # Need to recreate structure
                if 'cif_file' in self.config:
                    from modules.lat_detector import parse_emto_structure
                    temp_struct = parse_emto_structure(self.config['cif_file'])
                    structure_pmg = temp_struct['structure_pmg']
                else:
                    # Create from parameters
                    temp_struct = create_emto_structure(
                        lat=self.config['lat'],
                        a=self.config['a'],
                        sites=self.config['sites'],
                        b=self.config.get('b'),
                        c=self.config.get('c'),
                        alpha=self.config.get('alpha', 90),
                        beta=self.config.get('beta', 90),
                        gamma=self.config.get('gamma', 90)
                    )
                    structure_pmg = temp_struct['structure_pmg']

            # Calculate SWS
            sws_center = lattice_param_to_sws(structure_pmg)

            # Generate range
            sws_min = sws_center - 3 * sws_step
            sws_max = sws_center + 3 * sws_step
            sws_list = list(np.linspace(sws_min, sws_max, n_points))

            print(f"Auto-generated SWS values around {sws_center:.4f}: {sws_list}")

        elif isinstance(sws_values, (int, float)):
            # Single value → generate range
            sws_center = float(sws_values)
            sws_min = sws_center - 3 * sws_step
            sws_max = sws_center + 3 * sws_step
            sws_list = list(np.linspace(sws_min, sws_max, n_points))

            print(f"Auto-generated SWS values around {sws_center:.4f}: {sws_list}")

        elif isinstance(sws_values, list):
            # Use as-is
            sws_list = sws_values
            print(f"Using provided SWS values: {sws_list}")

        else:
            raise TypeError(f"sws_values must be float, list, or None, got {type(sws_values)}")

        return ca_list, sws_list

    def _run_calculations(
        self,
        calculation_path: Union[str, Path],
        script_name: str,
        run_mode: Optional[str] = None,
        poll_interval: Optional[int] = None,
        max_wait_time: Optional[int] = None
    ) -> bool:
        """
        Execute EMTO calculations using configured run mode.

        Parameters
        ----------
        calculation_path : str or Path
            Directory containing run script
        script_name : str
            Name of the run script (e.g., 'run_fept.sh')
        run_mode : str, optional
            "sbatch" → submit with SLURM
            "local" → run locally
            If None, uses config['run_mode']
        poll_interval : int, optional
            Seconds between status checks (default: from config)
        max_wait_time : int, optional
            Maximum wait time in seconds (default: from config)

        Returns
        -------
        bool
            True if calculations completed successfully

        Raises
        ------
        RuntimeError
            If calculations fail or timeout
        """
 

        calculation_path = Path(calculation_path)

        print(f"\n{'='*70}")
        print(f"RUNNING CALCULATIONS")
        print(f"{'='*70}")
        print(f"Mode: {run_mode}")
        print(f"Path: {calculation_path}")
        print(f"Script: {script_name}")
        print(f"{'='*70}\n")

        if run_mode == 'sbatch':
            # Submit with SLURM
            try:
                run_sbatch(script_name, str(calculation_path))
                print(f"\n✓ Job submitted successfully")

                # For sbatch mode, we don't wait for completion in this function
                # The user will need to check job status separately
                print(f"Note: Job submitted to SLURM. Check status with 'squeue -u $USER'")
                return True

            except Exception as e:
                raise RuntimeError(f"SLURM submission failed: {e}")

        elif run_mode == 'local':
            # Run locally
            try:
                print(f"Starting local execution...")
                start_time = time.time()

                chmod_and_run(
                    script_name,
                    str(calculation_path),
                    stdout_file="output.log",
                    stderr_file="error.log"
                )

                elapsed = time.time() - start_time
                print(f"\n✓ Calculations completed in {elapsed:.1f} seconds")
                return True

            except Exception as e:
                raise RuntimeError(f"Local execution failed: {e}")



    def _validate_calculations(
        self,
        phase_path: Union[str, Path],
        ca_ratios: List[float],
        sws_values: List[float],
        job_name: str
    ) -> None:
        """
        Validate that EMTO calculations completed successfully.

        Checks that output files exist and contain success indicators:
        - KSTR: "KSTR:     Finished at:"
        - KGRN: "KGRN: OK  Finished at:"
        - KFCD: "KFCD: OK  Finished at:"

        Parameters
        ----------
        phase_path : str or Path
            Directory containing calculation outputs
        ca_ratios : list of float
            c/a ratios that were calculated
        sws_values : list of float
            SWS values that were calculated
        job_name : str
            Job identifier used in filenames

        Raises
        ------
        RuntimeError
            If any calculation failed or output files are missing/incomplete
        """
        phase_path = Path(phase_path)

        print(f"\n{'='*70}")
        print(f"VALIDATING CALCULATIONS")
        print(f"{'='*70}")

        errors = []

        # For each c/a ratio, check KSTR and SHAPE outputs
        for ca_ratio in ca_ratios:
            file_id = f"{job_name}_{ca_ratio:.2f}"

            # Check KSTR output in smx directory
            kstr_out = phase_path / f"smx/{file_id}.prn"
            if not kstr_out.exists():
                errors.append(f"Missing KSTR output: {kstr_out}")
            else:
                # Check for success indicator
                with open(kstr_out, 'r') as f:
                    content = f.read()
                    if "KSTR:     Finished at:" not in content:
                        errors.append(f"KSTR did not complete successfully: {kstr_out}")
                    else:
                        print(f"✓ KSTR completed for c/a={ca_ratio:.2f}")

        # For each (c/a, sws) pair, check KGRN and KFCD outputs
        for ca_ratio in ca_ratios:
            for sws in sws_values:
                file_id = f"{job_name}_{ca_ratio:.2f}_{sws:.2f}"

                # Check KGRN output
                kgrn_out = phase_path / f"{file_id}.prn"
                if not kgrn_out.exists():
                    errors.append(f"Missing KGRN output: {kgrn_out}")
                else:
                    # Check for success indicator
                    with open(kgrn_out, 'r') as f:
                        content = f.read()
                        if "KGRN: OK  Finished at:" not in content:
                            errors.append(f"KGRN did not complete successfully: {kgrn_out}")
                        else:
                            print(f"✓ KGRN completed for c/a={ca_ratio:.2f}, SWS={sws:.2f}")

                # Check KFCD output
                kfcd_out = phase_path / f"fcd/{file_id}.prn"
                if not kfcd_out.exists():
                    errors.append(f"Missing KFCD output: {kfcd_out}")
                else:
                    # Check for success indicator
                    with open(kfcd_out, 'r') as f:
                        content = f.read()
                        if "KFCD: OK  Finished at:" not in content:
                            errors.append(f"KFCD did not complete successfully: {kfcd_out}")
                        else:
                            print(f"✓ KFCD completed for c/a={ca_ratio:.2f}, SWS={sws:.2f}")

        print(f"{'='*70}\n")

        if errors:
            error_msg = "\n".join(errors)
            raise RuntimeError(
                f"Calculation validation failed with {len(errors)} error(s):\n{error_msg}\n\n"
                f"Please check the calculation logs in: {phase_path}"
            )

        print("✓ All calculations validated successfully\n")

    def _run_eos_fit(
        self,
        r_or_v_data: List[float],
        energy_data: List[float],
        output_path: Union[str, Path],
        job_name: str,
        comment: str,
        eos_type: Optional[str] = None
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Run EMTO EOS executable and parse results.

        Steps:
        1. Create EOS input file using create_eos_input()
        2. Run EOS executable: subprocess.run(eos_executable + ' < eos.dat')
        3. Parse output using parse_eos_output()
        4. Extract optimal parameter (rwseq)

        Parameters
        ----------
        r_or_v_data : list of float
            R or V values (independent variable)
        energy_data : list of float
            Energy values (dependent variable)
        output_path : str or Path
            Directory where EOS files will be created
        job_name : str
            Job identifier
        comment : str
            Comment for EOS input
        eos_type : str, optional
            EOS fit type (MO88, POLN, SPLN, MU37, ALL)
            If None, uses config['eos_type']

        Returns
        -------
        tuple of (float, dict)
            optimal_value : Optimal parameter (rwseq) from primary fit
            results : Dictionary of all EOS fit results

        Raises
        ------
        RuntimeError
            If EOS executable fails or parsing fails
        """

        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)

        eos_input_file = output_path / "eos.dat"
        eos_output_file = output_path / "eos.out"

        print(f"\n{'='*70}")
        print(f"RUNNING EOS FIT")
        print(f"{'='*70}")
        print(f"Type: {eos_type}")
        print(f"Data points: {len(r_or_v_data)}")
        print(f"Output: {output_path}")
        print(f"{'='*70}\n")

        # Step 1: Create EOS input file
        try:
            create_eos_input(
                filename=str(eos_input_file),
                job_name=job_name,
                comment=comment,
                R_or_V_data=r_or_v_data,
                Energy_data=energy_data,
                fit_type=eos_type
            )
        except Exception as e:
            raise RuntimeError(f"Failed to create EOS input: {e}")

        # Step 2: Run EOS executable
        eos_executable = self.config['eos_executable']

        try:
            print(f"Running EOS executable: {eos_executable}")

            with open(eos_input_file, 'r') as f_in:
                with open(eos_output_file, 'w') as f_out:
                    result = subprocess.run(
                        [eos_executable],
                        stdin=f_in,
                        stdout=f_out,
                        stderr=subprocess.PIPE,
                        cwd=str(output_path),
                        text=True,
                        timeout=300  # 5 minute timeout
                    )

            if result.returncode != 0:
                raise RuntimeError(
                    f"EOS executable failed with return code {result.returncode}\n"
                    f"stderr: {result.stderr}"
                )

            print(f"✓ EOS executable completed successfully")

        except subprocess.TimeoutExpired:
            raise RuntimeError("EOS executable timed out after 5 minutes")
        except Exception as e:
            raise RuntimeError(f"Failed to run EOS executable: {e}")

        # Step 3: Parse EOS output
        try:
            results = parse_eos_output(str(eos_output_file))

            if not results:
                raise RuntimeError("No results found in EOS output")

            print(f"\nParsed {len(results)} EOS fit(s):")
            for fit_name, params in results.items():
                print(f"  {fit_name}: rwseq = {params.rwseq:.6f}, eeq = {params.eeq:.6f} Ry")

        except Exception as e:
            raise RuntimeError(f"Failed to parse EOS output: {e}")

        # Step 4: Extract optimal parameter from primary fit
        # Priority: morse > birch_murnaghan > murnaghan > polynomial > spline
        if 'morse' in results:
            primary_fit = 'morse'
        elif 'birch_murnaghan' in results:
            primary_fit = 'birch_murnaghan'
        elif 'murnaghan' in results:
            primary_fit = 'murnaghan'
        elif 'polynomial' in results:
            primary_fit = 'polynomial'
        elif 'spline' in results:
            primary_fit = 'spline'
        else:
            raise RuntimeError("No valid EOS fit found in results")

        optimal_value = results[primary_fit].rwseq

        print(f"\n✓ Using {primary_fit} fit: optimal value = {optimal_value:.6f}")
        print(f"{'='*70}\n")

        return optimal_value, results

    def optimize_ca_ratio(
        self,
        structure: Dict[str, Any],
        ca_ratios: List[float],
        initial_sws: Union[float, List[float]]
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Phase 1: c/a ratio optimization.

        Creates EMTO inputs, runs calculations, parses energies, fits EOS,
        and extracts optimal c/a ratio.

        Parameters
        ----------
        structure : dict
            Structure dictionary from create_emto_structure()
        ca_ratios : list of float
            List of c/a ratios to test
        initial_sws : float or list of float
            Initial SWS value(s) for c/a optimization
            If float, uses same value for all c/a ratios
            If list, must have same length as ca_ratios

        Returns
        -------
        tuple of (float, dict)
            optimal_ca : Optimal c/a ratio from EOS fit
            results : Dictionary with EOS results and energy data

        Raises
        ------
        RuntimeError
            If calculations fail or output files not found
        """
        print(f"\n{'#'*70}")
        print("# PHASE 1: c/a RATIO OPTIMIZATION")
        print(f"{'#'*70}\n")

        # Validate initial_sws
        if isinstance(initial_sws, (int, float)):
            sws_list = [float(initial_sws)] * len(ca_ratios)
        elif isinstance(initial_sws, list):
            if len(initial_sws) != len(ca_ratios):
                raise ValueError(
                    f"initial_sws list length ({len(initial_sws)}) must match "
                    f"ca_ratios length ({len(ca_ratios)})"
                )
            sws_list = initial_sws
        else:
            raise TypeError("initial_sws must be float or list of float")

        # Create phase subdirectory
        phase_path = self.base_path / "phase1_ca_optimization"
        phase_path.mkdir(parents=True, exist_ok=True)

        print(f"Creating EMTO inputs for {len(ca_ratios)} c/a ratios...")
        print(f"  c/a ratios: {ca_ratios}")
        print(f"  SWS values: {sws_list}")
        print(f"  Output path: {phase_path}\n")

        # Create EMTO inputs
        try:
            phase_config = {
                **self.config,  # All validated defaults from constructor
                'output_path': str(phase_path),  # Override for this phase
                'ca_ratios': ca_ratios,
                'sws_values': sws_list,
                # Only override what's different for this phase
            }

            create_emto_inputs(phase_config)

        except Exception as e:
            raise RuntimeError(f"Failed to create EMTO inputs: {e}")

        # Run calculations
        script_name = f"run_{self.config['job_name']}.sh"
        self._run_calculations(
            calculation_path=phase_path,
            script_name=script_name
        )

        # Validate calculations completed successfully
        self._validate_calculations(
            phase_path=phase_path,
            ca_ratios=ca_ratios,
            sws_values=sws_list,
            job_name=self.config['job_name']
        )

        # Parse energies from KFCD outputs
        print("\nParsing energies from KFCD outputs...")
        ca_values = []
        energy_values = []

        from modules.extract_results import parse_kfcd

        for i, (ca, sws) in enumerate(zip(ca_ratios, sws_list)):
            file_id = f"{self.config['job_name']}_{ca:.2f}_{sws:.2f}"
            kfcd_file = phase_path / "fcd" / f"{file_id}.prn"

            if not kfcd_file.exists():
                raise RuntimeError(
                    f"KFCD output not found: {kfcd_file}\n"
                    f"Calculation may have failed. Check log files in {phase_path}"
                )

            try:
                results = parse_kfcd(str(kfcd_file))
                if results.total_energy is None:
                    raise RuntimeError(f"No total energy found in {kfcd_file}")

                ca_values.append(ca)
                energy_values.append(results.total_energy)

                print(f"  c/a = {ca:.4f}: E = {results.total_energy:.6f} Ry")

            except Exception as e:
                raise RuntimeError(f"Failed to parse {kfcd_file}: {e}")

        # Run EOS fit
        optimal_ca, eos_results = self._run_eos_fit(
            r_or_v_data=ca_values,
            energy_data=energy_values,
            output_path=phase_path,
            job_name=f"{self.config['job_name']}_ca",
            comment=f"c/a optimization for {self.config['job_name']}",
            eos_type=self.config.get('eos_type', 'MO88')
        )

        # Save results
        import json

        results_dict = {
            'optimal_ca': optimal_ca,
            'ca_values': ca_values,
            'energy_values': energy_values,
            'eos_type': self.config.get('eos_type', 'MO88'),
            'eos_fits': {
                name: {
                    'rwseq': params.rwseq,
                    'v_eq': params.v_eq,
                    'eeq': params.eeq,
                    'bulk_modulus': params.bulk_modulus
                }
                for name, params in eos_results.items()
            }
        }

        results_file = phase_path / "ca_optimization_results.json"
        with open(results_file, 'w') as f:
            json.dump(results_dict, f, indent=2)

        print(f"\n✓ c/a optimization results saved to: {results_file}")
        print(f"✓ Optimal c/a ratio: {optimal_ca:.6f}")

        # Store in workflow results
        self.results['phase1_ca_optimization'] = results_dict

        return optimal_ca, results_dict

    def optimize_sws(
        self,
        structure: Dict[str, Any],
        sws_values: List[float],
        optimal_ca: float
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Phase 2: SWS optimization at optimal c/a ratio.

        Creates EMTO inputs, runs calculations, parses energies, fits EOS,
        extracts optimal SWS, and calculates derived parameters.

        Parameters
        ----------
        structure : dict
            Structure dictionary from create_emto_structure()
        sws_values : list of float
            List of SWS values to test
        optimal_ca : float
            Optimal c/a ratio from Phase 1

        Returns
        -------
        tuple of (float, dict)
            optimal_sws : Optimal SWS value from EOS fit
            results : Dictionary with EOS results, energy data, and derived parameters

        Raises
        ------
        RuntimeError
            If calculations fail or output files not found
        """
        print(f"\n{'#'*70}")
        print("# PHASE 2: SWS OPTIMIZATION")
        print(f"{'#'*70}\n")

        # Create phase subdirectory
        phase_path = self.base_path / "phase2_sws_optimization"
        phase_path.mkdir(parents=True, exist_ok=True)

        print(f"Creating EMTO inputs for {len(sws_values)} SWS values...")
        print(f"  Optimal c/a: {optimal_ca:.6f}")
        print(f"  SWS values: {sws_values}")
        print(f"  Output path: {phase_path}\n")

        # Create EMTO inputs with optimal c/a
        try:
            phase_config = {
                **self.config,  # All validated defaults from constructor
                'output_path': str(phase_path),  # Override for this phase
                'ca_ratios': [optimal_ca],
                'sws_values': sws_values,
                # Only override what's different for this phase
            }

            create_emto_inputs(phase_config)
        except Exception as e:
            raise RuntimeError(f"Failed to create EMTO inputs: {e}")

        # Run calculations
        script_name = f"run_{self.config['job_name']}.sh"
        self._run_calculations(
            calculation_path=phase_path,
            script_name=script_name
        )

        # Validate calculations completed successfully
        self._validate_calculations(
            phase_path=phase_path,
            ca_ratios=[optimal_ca],
            sws_values=sws_values,
            job_name=self.config['job_name']
        )

        # Parse energies from KFCD outputs
        print("\nParsing energies from KFCD outputs...")
        sws_parsed = []
        energy_values = []

        from modules.extract_results import parse_kfcd

        for sws in sws_values:
            file_id = f"{self.config['job_name']}_{optimal_ca:.2f}_{sws:.2f}"
            kfcd_file = phase_path / "fcd" / f"{file_id}.prn"

            if not kfcd_file.exists():
                raise RuntimeError(
                    f"KFCD output not found: {kfcd_file}\n"
                    f"Calculation may have failed. Check log files in {phase_path}"
                )

            try:
                results = parse_kfcd(str(kfcd_file))
                if results.total_energy is None:
                    raise RuntimeError(f"No total energy found in {kfcd_file}")

                sws_parsed.append(sws)
                energy_values.append(results.total_energy)

                print(f"  SWS = {sws:.4f}: E = {results.total_energy:.6f} Ry")

            except Exception as e:
                raise RuntimeError(f"Failed to parse {kfcd_file}: {e}")

        # Run EOS fit
        optimal_sws, eos_results = self._run_eos_fit(
            r_or_v_data=sws_parsed,
            energy_data=energy_values,
            output_path=phase_path,
            job_name=f"{self.config['job_name']}_sws",
            comment=f"SWS optimization for {self.config['job_name']} at c/a={optimal_ca:.4f}",
            eos_type=self.config.get('eos_type', 'MO88')
        )

        # Calculate derived parameters
        # SWS is in atomic units (Bohr), convert to lattice parameters in Angstroms
        bohr_to_angstrom = 0.529177210903

        # Volume per atom in Bohr^3
        volume_per_atom = (4/3) * np.pi * optimal_sws**3

        # Total unit cell volume in Bohr^3
        total_volume_bohr = volume_per_atom * structure['NQ3']

        # Convert to Angstrom^3
        total_volume_angstrom = total_volume_bohr * (bohr_to_angstrom**3)

        # Calculate lattice parameters based on lattice type
        lat_type = structure['lat']

        if lat_type in [1, 2, 3]:  # SC, FCC, BCC (cubic)
            # For cubic: V = a^3
            a_optimal = total_volume_angstrom ** (1/3)
            c_optimal = a_optimal
        elif lat_type == 4:  # HCP
            # For HCP: V = a^2 * c * sqrt(3)/2
            # With c/a ratio: c = a * c/a
            # V = a^3 * c/a * sqrt(3)/2
            # a = (V * 2 / (c/a * sqrt(3)))^(1/3)
            a_optimal = (total_volume_angstrom * 2 / (optimal_ca * np.sqrt(3))) ** (1/3)
            c_optimal = a_optimal * optimal_ca
        elif lat_type == 5:  # BCT
            # For BCT: V = a^2 * c
            # With c/a ratio: c = a * c/a
            # V = a^3 * c/a
            # a = (V / c/a)^(1/3)
            a_optimal = (total_volume_angstrom / optimal_ca) ** (1/3)
            c_optimal = a_optimal * optimal_ca
        else:
            # Generic tetragonal approximation
            a_optimal = (total_volume_angstrom / optimal_ca) ** (1/3)
            c_optimal = a_optimal * optimal_ca

        derived_params = {
            'optimal_sws_bohr': optimal_sws,
            'optimal_ca': optimal_ca,
            'volume_per_atom_bohr3': volume_per_atom,
            'total_volume_angstrom3': total_volume_angstrom,
            'a_angstrom': a_optimal,
            'c_angstrom': c_optimal,
            'lattice_type': lat_type,
            'lattice_name': structure.get('lattice_name', 'Unknown')
        }

        # Save results
        import json

        results_dict = {
            'optimal_sws': optimal_sws,
            'optimal_ca': optimal_ca,
            'sws_values': sws_parsed,
            'energy_values': energy_values,
            'eos_type': self.config.get('eos_type', 'MO88'),
            'eos_fits': {
                name: {
                    'rwseq': params.rwseq,
                    'v_eq': params.v_eq,
                    'eeq': params.eeq,
                    'bulk_modulus': params.bulk_modulus
                }
                for name, params in eos_results.items()
            },
            'derived_parameters': derived_params
        }

        results_file = phase_path / "sws_optimization_results.json"
        with open(results_file, 'w') as f:
            json.dump(results_dict, f, indent=2)

        print(f"\n✓ SWS optimization results saved to: {results_file}")
        print(f"✓ Optimal SWS: {optimal_sws:.6f} Bohr")
        print(f"\nDerived lattice parameters:")
        print(f"  a = {a_optimal:.6f} Å")
        print(f"  c = {c_optimal:.6f} Å")
        print(f"  c/a = {optimal_ca:.6f}")
        print(f"  Volume = {total_volume_angstrom:.6f} Å³")

        # Store in workflow results
        self.results['phase2_sws_optimization'] = results_dict

        return optimal_sws, results_dict

    def run_optimized_calculation(
        self,
        structure: Dict[str, Any],
        optimal_ca: float,
        optimal_sws: float
    ) -> Dict[str, Any]:
        """
        Phase 3: Run final calculation with optimized parameters.

        Creates EMTO inputs with optimal c/a and SWS, runs calculation,
        and parses results.

        Parameters
        ----------
        structure : dict
            Structure dictionary from create_emto_structure()
        optimal_ca : float
            Optimal c/a ratio from Phase 1
        optimal_sws : float
            Optimal SWS value from Phase 2

        Returns
        -------
        dict
            Dictionary with final calculation results

        Raises
        ------
        RuntimeError
            If calculation fails or output files not found
        """
        print(f"\n{'#'*70}")
        print("# PHASE 3: OPTIMIZED STRUCTURE CALCULATION")
        print(f"{'#'*70}\n")

        # Create phase subdirectory
        phase_path = self.base_path / "phase3_optimized_calculation"
        phase_path.mkdir(parents=True, exist_ok=True)

        print(f"Creating EMTO inputs with optimized parameters...")
        print(f"  Optimal c/a: {optimal_ca:.6f}")
        print(f"  Optimal SWS: {optimal_sws:.6f} Bohr")
        print(f"  Output path: {phase_path}\n")

        # Create EMTO inputs with optimal parameters
        try:
            phase_config = {
                **self.config,  # All validated defaults from constructor
                'output_path': str(phase_path),  # Override for this phase
                'ca_ratios': [optimal_ca],
                'sws_values': [optimal_sws],
                # Only override what's different for this phase
            }

            create_emto_inputs(phase_config)
        except Exception as e:
            raise RuntimeError(f"Failed to create EMTO inputs: {e}")

        # Run calculation
        script_name = f"run_{self.config['job_name']}.sh"
        self._run_calculations(
            calculation_path=phase_path,
            script_name=script_name
        )

        # Validate calculations completed successfully
        self._validate_calculations(
            phase_path=phase_path,
            ca_ratios=[optimal_ca],
            sws_values=[optimal_sws],
            job_name=self.config['job_name']
        )

        # Parse results from KFCD and KGRN outputs
        print("\nParsing optimized calculation results...")

        from modules.extract_results import parse_kfcd, parse_kgrn

        file_id = f"{self.config['job_name']}_{optimal_ca:.2f}_{optimal_sws:.2f}"
        kfcd_file = phase_path / "fcd" / f"{file_id}.prn"
        kgrn_file = phase_path / "pot" / f"{file_id}.prn"

        if not kfcd_file.exists():
            raise RuntimeError(
                f"KFCD output not found: {kfcd_file}\n"
                f"Calculation may have failed. Check log files in {phase_path}"
            )

        # Parse KFCD
        try:
            kfcd_results = parse_kfcd(str(kfcd_file))
            print(f"\n✓ KFCD results parsed")
            print(f"  Total energy: {kfcd_results.total_energy:.6f} Ry")
        except Exception as e:
            raise RuntimeError(f"Failed to parse {kfcd_file}: {e}")

        # Parse KGRN if available
        kgrn_results = None
        if kgrn_file.exists():
            try:
                kgrn_results = parse_kgrn(
                    str(kgrn_file),
                    kfcd_results.concentrations,
                    kfcd_results.iq_to_element,
                    kfcd_results.atoms
                )
                print(f"✓ KGRN results parsed")
                if kgrn_results.total_energy:
                    print(f"  Total energy: {kgrn_results.total_energy:.6f} Ry")
            except Exception as e:
                print(f"Warning: Failed to parse KGRN output: {e}")

        # Save results
        import json

        results_dict = {
            'optimal_ca': optimal_ca,
            'optimal_sws': optimal_sws,
            'kfcd_total_energy': kfcd_results.total_energy,
            'kgrn_total_energy': kgrn_results.total_energy if kgrn_results else None,
            'magnetic_moments': {
                f"IQ{iq}_ITA{ita}_{atom}": moment
                for (iq, ita, atom), moment in kfcd_results.magnetic_moments.items()
            } if kfcd_results.magnetic_moments else {},
            'total_magnetic_moment': kfcd_results.total_magnetic_moment,
            'file_id': file_id
        }

        results_file = phase_path / "optimized_results.json"
        with open(results_file, 'w') as f:
            json.dump(results_dict, f, indent=2)

        print(f"\n✓ Optimized calculation results saved to: {results_file}")

        # Store in workflow results
        self.results['phase3_optimized_calculation'] = results_dict

        return results_dict

    def generate_dos_analysis(
        self,
        phase_path: Union[str, Path],
        file_id: str,
        plot_range: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Generate DOS analysis and plots.

        Parameters
        ----------
        phase_path : str or Path
            Path to calculation directory
        file_id : str
            File identifier for DOS files
        plot_range : list of float, optional
            Energy range for DOS plots [E_min, E_max] in eV
            If None, uses config['dos_plot_range'] or [-0.8, 0.15]

        Returns
        -------
        dict
            Dictionary with DOS analysis results

        Notes
        -----
        Looks for DOS files in phase_path/pot/{file_id}.dos
        Generates plots and saves to phase_path/dos_analysis/
        """
        from modules.dos import DOSParser

        phase_path = Path(phase_path)
        dos_file = phase_path / "pot" / f"{file_id}.dos"

        if not dos_file.exists():
            print(f"Warning: DOS file not found: {dos_file}")
            return {'status': 'not_found', 'file': str(dos_file)}

        print(f"\n{'='*70}")
        print("DOS ANALYSIS")
        print(f"{'='*70}")
        print(f"DOS file: {dos_file}")

        # Create DOS analysis directory
        dos_output_dir = phase_path / "dos_analysis"
        dos_output_dir.mkdir(parents=True, exist_ok=True)

        # Parse DOS
        try:
            parser = DOSParser(str(dos_file))
            print(f"✓ DOS file parsed successfully")
        except Exception as e:
            print(f"✗ Failed to parse DOS file: {e}")
            return {'status': 'parse_error', 'error': str(e)}

        # Get plot range
        if plot_range is None:
            plot_range = self.config['dos_plot_range']
        # Generate plots
        try:
            # Total DOS
            total_plot = dos_output_dir / "dos_total.png"
            parser.plot_total(
                spin_polarized=True,
                save=str(total_plot),
                show=False
            )
            print(f"✓ Total DOS plot saved: {total_plot}")

            # Sublattice DOS (if available)
            sublattice_plots = []
            if parser.atom_info:
                # Get unique sublattices
                sublattices = sorted(set(info[2] for info in parser.atom_info))

                for sublat in sublattices:
                    sublat_plot = dos_output_dir / f"dos_sublattice_{sublat}.png"
                    parser.plot_sublattice(
                        sublattice=sublat,
                        spin_polarized=True,
                        save=str(sublat_plot),
                        show=False
                    )
                    sublattice_plots.append(str(sublat_plot))
                    print(f"✓ Sublattice {sublat} DOS plot saved")

        except Exception as e:
            print(f"Warning: Failed to generate some DOS plots: {e}")

        results = {
            'status': 'success',
            'dos_file': str(dos_file),
            'total_plot': str(total_plot) if 'total_plot' in locals() else None,
            'sublattice_plots': sublattice_plots if 'sublattice_plots' in locals() else [],
            'plot_range': plot_range,
            'atom_info': [
                {'atom_number': num, 'element': elem, 'sublattice': sublat}
                for num, elem, sublat in parser.atom_info
            ]
        }

        print(f"{'='*70}\n")

        return results

    def generate_summary_report(self) -> str:
        """
        Generate comprehensive summary report of optimization workflow.

        Returns
        -------
        str
            Formatted summary report

        Notes
        -----
        Report includes all phases executed and their results.
        Saved to workflow_summary.txt in base_path.
        """
        report = []
        report.append("=" * 80)
        report.append("OPTIMIZATION WORKFLOW SUMMARY")
        report.append("=" * 80)
        report.append(f"\nJob name: {self.config['job_name']}")
        report.append(f"Output path: {self.base_path}")
        report.append(f"Run mode: {self.config.get('run_mode', 'sbatch')}")

        # Configuration
        report.append("\n" + "-" * 80)
        report.append("CONFIGURATION")
        report.append("-" * 80)
        report.append(f"Lattice type: {self.config.get('lat')}")
        report.append(f"DMAX: {self.config.get('dmax')}")
        report.append(f"Magnetic: {self.config.get('magnetic')}")
        report.append(f"EOS type: {self.config.get('eos_type', 'MO88')}")

        # Phase 1: c/a optimization
        if 'phase1_ca_optimization' in self.results:
            phase1 = self.results['phase1_ca_optimization']
            report.append("\n" + "-" * 80)
            report.append("PHASE 1: c/a RATIO OPTIMIZATION")
            report.append("-" * 80)
            report.append(f"Optimal c/a: {phase1['optimal_ca']:.6f}")
            report.append(f"Number of c/a points: {len(phase1['ca_values'])}")
            report.append(f"c/a range: [{min(phase1['ca_values']):.4f}, {max(phase1['ca_values']):.4f}]")
            report.append(f"Energy range: [{min(phase1['energy_values']):.6f}, {max(phase1['energy_values']):.6f}] Ry")

            # EOS fit info
            if 'eos_fits' in phase1:
                for fit_name, params in phase1['eos_fits'].items():
                    report.append(f"\n  {fit_name.upper()} fit:")
                    report.append(f"    Equilibrium energy: {params['eeq']:.6f} Ry")
                    report.append(f"    Bulk modulus: {params['bulk_modulus']:.3f} GPa")

        # Phase 2: SWS optimization
        if 'phase2_sws_optimization' in self.results:
            phase2 = self.results['phase2_sws_optimization']
            report.append("\n" + "-" * 80)
            report.append("PHASE 2: SWS OPTIMIZATION")
            report.append("-" * 80)
            report.append(f"Optimal SWS: {phase2['optimal_sws']:.6f} Bohr")
            report.append(f"Number of SWS points: {len(phase2['sws_values'])}")
            report.append(f"SWS range: [{min(phase2['sws_values']):.4f}, {max(phase2['sws_values']):.4f}] Bohr")
            report.append(f"Energy range: [{min(phase2['energy_values']):.6f}, {max(phase2['energy_values']):.6f}] Ry")

            # Derived parameters
            if 'derived_parameters' in phase2:
                params = phase2['derived_parameters']
                report.append("\n  Derived lattice parameters:")
                report.append(f"    a = {params['a_angstrom']:.6f} Å")
                report.append(f"    c = {params['c_angstrom']:.6f} Å")
                report.append(f"    c/a = {params['optimal_ca']:.6f}")
                report.append(f"    Volume = {params['total_volume_angstrom3']:.6f} Å³")
                report.append(f"    Lattice: {params['lattice_name']} (type {params['lattice_type']})")

        # Phase 3: Optimized calculation
        if 'phase3_optimized_calculation' in self.results:
            phase3 = self.results['phase3_optimized_calculation']
            report.append("\n" + "-" * 80)
            report.append("PHASE 3: OPTIMIZED STRUCTURE CALCULATION")
            report.append("-" * 80)
            report.append(f"Optimal c/a: {phase3['optimal_ca']:.6f}")
            report.append(f"Optimal SWS: {phase3['optimal_sws']:.6f} Bohr")
            report.append(f"KFCD total energy: {phase3['kfcd_total_energy']:.6f} Ry")

            if phase3['kgrn_total_energy'] is not None:
                report.append(f"KGRN total energy: {phase3['kgrn_total_energy']:.6f} Ry")

            if phase3.get('total_magnetic_moment') is not None:
                report.append(f"Total magnetic moment: {phase3['total_magnetic_moment']:.4f} μB")

            if phase3.get('magnetic_moments'):
                report.append("\n  Magnetic moments:")
                for site, moment in phase3['magnetic_moments'].items():
                    report.append(f"    {site}: {moment:.4f} μB")

        # DOS analysis
        if 'dos_analysis' in self.results:
            dos = self.results['dos_analysis']
            if dos.get('status') == 'success':
                report.append("\n" + "-" * 80)
                report.append("DOS ANALYSIS")
                report.append("-" * 80)
                report.append(f"DOS plots generated: {len(dos.get('sublattice_plots', [])) + 1}")
                report.append(f"Plot range: {dos.get('plot_range')} eV")

        report.append("\n" + "=" * 80)
        report.append("END OF REPORT")
        report.append("=" * 80)

        # Save report
        report_text = "\n".join(report)
        report_file = self.base_path / "workflow_summary.txt"
        with open(report_file, 'w') as f:
            f.write(report_text)

        print(f"\n✓ Summary report saved to: {report_file}\n")

        return report_text

    def run(self) -> Dict[str, Any]:
        """
        Execute complete optimization workflow.

        Orchestrates all phases based on configuration:
        1. Structure creation
        2. Parameter range preparation
        3. c/a optimization (if optimize_ca=True)
        4. SWS optimization (if optimize_sws=True)
        5. Optimized calculation
        6. DOS analysis (if generate_dos=True)
        7. Summary report generation

        Returns
        -------
        dict
            Complete workflow results

        Raises
        ------
        RuntimeError
            If critical phase fails

        Notes
        -----
        This is the main entry point for automated optimization workflows.
        All intermediate results are saved and workflow can be resumed if interrupted.
        """
        print("\n" + "#" * 80)
        print("# COMPLETE OPTIMIZATION WORKFLOW")
        print("#" * 80)
        print(f"\nJob: {self.config['job_name']}")
        print(f"Output: {self.base_path}")
        print(f"c/a optimization: {self.config.get('optimize_ca', False)}")
        print(f"SWS optimization: {self.config.get('optimize_sws', False)}")
        print(f"DOS analysis: {self.config.get('generate_dos', False)}")

        # Step 1: Create structure
        print("\n" + "=" * 80)
        print("STEP 1: STRUCTURE CREATION")
        print("=" * 80)

        try:
            if self.config.get('cif_file'):
                from modules.lat_detector import parse_emto_structure
                print(f"Creating structure from CIF: {self.config['cif_file']}")
                structure = parse_emto_structure(self.config['cif_file'])
            else:
                from modules.structure_builder import create_emto_structure
                print(f"Creating structure from parameters...")
                structure = create_emto_structure(
                    lat=self.config['lat'],
                    a=self.config['a'],
                    sites=self.config['sites'],
                    b=self.config.get('b'),
                    c=self.config.get('c'),
                    alpha=self.config.get('alpha', 90),
                    beta=self.config.get('beta', 90),
                    gamma=self.config.get('gamma', 90),
                    user_magnetic_moments=self.config.get('user_magnetic_moments')
                )

            print(f"✓ Structure created")
            print(f"  Lattice: {structure['lattice_name']} (type {structure['lat']})")
            print(f"  Atoms: {structure['NQ3']}")

        except Exception as e:
            raise RuntimeError(f"Failed to create structure: {e}")

        # Step 2: Prepare parameter ranges
        print("\n" + "=" * 80)
        print("STEP 2: PARAMETER PREPARATION")
        print("=" * 80)

        try:
            ca_list, sws_list = self._prepare_ranges(
                self.config.get('ca_ratios'),
                self.config.get('sws_values'),
                structure=structure
            )
        except Exception as e:
            raise RuntimeError(f"Failed to prepare parameter ranges: {e}")

        # Step 3: c/a optimization (optional)
        optimal_ca = None
        if self.config.get('optimize_ca', False):
            try:
                initial_sws = self.config.get('initial_sws', [sws_list[len(sws_list)//2]])
                optimal_ca, ca_results = self.optimize_ca_ratio(
                    structure=structure,
                    ca_ratios=ca_list,
                    initial_sws=initial_sws
                )
            except Exception as e:
                raise RuntimeError(f"c/a optimization failed: {e}")
        else:
            optimal_ca = ca_list[0] if ca_list else structure.get('coa', 1.0)
            print(f"\nSkipping c/a optimization, using: {optimal_ca:.6f}")

        # Step 4: SWS optimization (optional)
        optimal_sws = None
        if self.config.get('optimize_sws', False):
            try:
                optimal_sws, sws_results = self.optimize_sws(
                    structure=structure,
                    sws_values=sws_list,
                    optimal_ca=optimal_ca
                )
            except Exception as e:
                raise RuntimeError(f"SWS optimization failed: {e}")
        else:
            optimal_sws = sws_list[0] if sws_list else None
            if optimal_sws is None:
                raise ValueError("SWS value required but not provided")
            print(f"\nSkipping SWS optimization, using: {optimal_sws:.6f} Bohr")

        # Step 5: Optimized calculation
        try:
            final_results = self.run_optimized_calculation(
                structure=structure,
                optimal_ca=optimal_ca,
                optimal_sws=optimal_sws
            )
        except Exception as e:
            raise RuntimeError(f"Optimized calculation failed: {e}")

        # Step 6: DOS analysis (optional)
        if self.config.get('generate_dos', False):
            try:
                file_id = final_results['file_id']
                phase_path = self.base_path / "phase3_optimized_calculation"

                dos_results = self.generate_dos_analysis(
                    phase_path=phase_path,
                    file_id=file_id,
                    plot_range=self.config.get('dos_plot_range')
                )

                self.results['dos_analysis'] = dos_results

            except Exception as e:
                print(f"Warning: DOS analysis failed: {e}")

        # Step 7: Generate summary report
        try:
            summary = self.generate_summary_report()
            print("\n" + summary)
        except Exception as e:
            print(f"Warning: Failed to generate summary report: {e}")

        # Save complete workflow results
        import json

        workflow_results = {
            'job_name': self.config['job_name'],
            'optimal_ca': optimal_ca,
            'optimal_sws': optimal_sws,
            'phases_completed': list(self.results.keys()),
            'final_energy': final_results.get('kfcd_total_energy'),
            'structure_info': {
                'lattice_type': structure['lat'],
                'lattice_name': structure.get('lattice_name', 'Unknown'),
                'num_atoms': structure['NQ3']
            }
        }

        results_file = self.base_path / "workflow_results.json"
        with open(results_file, 'w') as f:
            json.dump(workflow_results, f, indent=2)

        print(f"\n✓ Complete workflow results saved to: {results_file}")

        print("\n" + "#" * 80)
        print("# WORKFLOW COMPLETED SUCCESSFULLY")
        print("#" * 80)
        print(f"\nOptimal c/a: {optimal_ca:.6f}")
        print(f"Optimal SWS: {optimal_sws:.6f} Bohr")
        print(f"Final energy: {final_results.get('kfcd_total_energy'):.6f} Ry")
        print(f"\nAll results saved in: {self.base_path}")
        print("#" * 80 + "\n")

        return self.results


def main():
    """
    Example usage: Run complete optimization workflow from config file.

    Usage:
        python optimization_workflow.py <config_file.yaml>

    The config file should contain all necessary parameters for the workflow.
    See files/systems/optimization_*.yaml for examples.
    """
    import sys

    if len(sys.argv) < 2:
        print("=" * 80)
        print("EMTO Optimization Workflow")
        print("=" * 80)
        print("\nUsage: python optimization_workflow.py <config_file.yaml>")
        print("\nExample:")
        print("  python optimization_workflow.py config.yaml")
        print("\nThe config file should specify:")
        print("  - Structure (CIF file or lattice parameters)")
        print("  - Optimization flags (optimize_ca, optimize_sws)")
        print("  - Parameter ranges (ca_ratios, sws_values)")
        print("  - EMTO parameters (dmax, magnetic)")
        print("  - Execution settings (run_mode, account, etc.)")
        print("\nSee files/systems/optimization_*.yaml for example configurations.")
        print("=" * 80)
        sys.exit(1)

    config_file = sys.argv[1]

    try:
        print("\n" + "=" * 80)
        print("Initializing Optimization Workflow")
        print("=" * 80)
        print(f"Config file: {config_file}\n")

        # Initialize workflow
        workflow = OptimizationWorkflow(config_file=config_file)

        print("✓ Workflow initialized successfully!")
        print(f"  Job name: {workflow.config['job_name']}")
        print(f"  Output path: {workflow.base_path}")
        print(f"  c/a optimization: {workflow.config.get('optimize_ca', False)}")
        print(f"  SWS optimization: {workflow.config.get('optimize_sws', False)}")
        print(f"  DOS analysis: {workflow.config.get('generate_dos', False)}")

        # Run complete workflow
        results = workflow.run()

        print("\n" + "=" * 80)
        print("Workflow completed successfully!")
        print("=" * 80)
        print(f"\nResults saved in: {workflow.base_path}")
        print(f"  - workflow_summary.txt: Human-readable summary")
        print(f"  - workflow_results.json: Machine-readable results")
        print(f"  - phase1_ca_optimization/: c/a optimization results")
        print(f"  - phase2_sws_optimization/: SWS optimization results")
        print(f"  - phase3_optimized_calculation/: Final optimized results")

        if workflow.config.get('generate_dos', False):
            print(f"  - phase3_optimized_calculation/dos_analysis/: DOS plots")

        print("\n" + "=" * 80)

    except FileNotFoundError as e:
        print(f"\n✗ Error: Config file not found: {config_file}")
        print(f"  {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
