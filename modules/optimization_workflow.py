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
from modules.workflows import create_emto_inputs
from modules.inputs.eos_emto import create_eos_input, parse_eos_output
from utils.running_bash import run_sbatch, chmod_and_run
from utils.config_parser import load_and_validate_config, apply_config_defaults


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
        config_file: Optional[Union[str, Path]] = None,
        config_dict: Optional[Dict[str, Any]] = None,
        eos_executable: Optional[str] = None
    ):
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
        if config_file is not None:
            self.config = load_and_validate_config(config_file)
        elif config_dict is not None:
            self.config = load_and_validate_config(config_dict)
        else:
            raise ValueError("Must provide either config_file or config_dict")

        # Apply defaults
        self.config = apply_config_defaults(self.config)

        # Set EOS executable (parameter overrides config)
        if eos_executable is not None:
            self.config['eos_executable'] = eos_executable

        # Validate EOS executable if optimization is enabled
        if self.config.get('optimize_ca') or self.config.get('optimize_sws'):
            if 'eos_executable' not in self.config or self.config['eos_executable'] is None:
                raise ValueError("eos_executable is required for optimization workflow")

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
        if run_mode is None:
            run_mode = self.config.get('run_mode', 'sbatch')

        if poll_interval is None:
            poll_interval = self.config.get('poll_interval', 30)

        if max_wait_time is None:
            max_wait_time = self.config.get('max_wait_time', 7200)

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

        else:
            raise ValueError(f"Invalid run_mode: {run_mode}. Must be 'sbatch' or 'local'")

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
        if eos_type is None:
            eos_type = self.config.get('eos_type', 'MO88')

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


def main():
    """
    Example usage of OptimizationWorkflow class.
    """
    import sys

    if len(sys.argv) < 2:
        print("Usage: python optimization_workflow.py <config_file>")
        sys.exit(1)

    config_file = sys.argv[1]

    try:
        workflow = OptimizationWorkflow(config_file=config_file)

        print("Optimization workflow initialized successfully!")
        print(f"Base path: {workflow.base_path}")
        print(f"Optimize c/a: {workflow.config['optimize_ca']}")
        print(f"Optimize SWS: {workflow.config['optimize_sws']}")

        # Test parameter preparation
        ca_ratios = workflow.config.get('ca_ratios')
        sws_values = workflow.config.get('sws_values')

        ca_list, sws_list = workflow._prepare_ranges(ca_ratios, sws_values)

        print(f"\nPrepared ranges:")
        print(f"  c/a ratios: {ca_list}")
        print(f"  SWS values: {sws_list}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
