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
from utils.config_parser import load_and_validate_config, apply_config_defaults, CUBIC_LATTICES
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
        lat = self.config.get('lat')

        # Process c/a ratios
        # For cubic lattices, c/a must be 1.0 (no range generation)
        if lat is not None and lat in CUBIC_LATTICES:
            ca_list = [1.0]
            print(f"Cubic lattice (lat={lat}): Using c/a = 1.0 (fixed)")
        elif ca_ratios is None:
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
            structure_pmg = structure['structure_pmg']

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
            run_mode = self.config.get('run_mode', 'local')
 

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

        Delegates to the analysis module for implementation.

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
        """
        from modules.optimization.analysis import run_eos_fit

        if eos_type is None:
            eos_type = self.config.get('eos_type', 'MO88')

        return run_eos_fit(
            r_or_v_data=r_or_v_data,
            energy_data=energy_data,
            output_path=output_path,
            job_name=job_name,
            comment=comment,
            eos_executable=self.config['eos_executable'],
            eos_type=eos_type
        )

    def optimize_ca_ratio(
        self,
        structure: Dict[str, Any],
        ca_ratios: List[float],
        initial_sws: Union[float, List[float]]
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Phase 1: c/a ratio optimization.

        Delegates to the phase_execution module for implementation.

        Parameters
        ----------
        structure : dict
            Structure dictionary from create_emto_structure()
        ca_ratios : list of float
            List of c/a ratios to test
        initial_sws : float or list of float
            Initial SWS value(s) for c/a optimization

        Returns
        -------
        tuple of (float, dict)
            optimal_ca : Optimal c/a ratio from EOS fit
            results : Dictionary with EOS results and energy data
        """
        from modules.optimization.phase_execution import optimize_ca_ratio

        return optimize_ca_ratio(
            structure=structure,
            ca_ratios=ca_ratios,
            initial_sws=initial_sws,
            config=self.config,
            base_path=self.base_path,
            run_calculations_func=self._run_calculations,
            validate_calculations_func=self._validate_calculations,
            run_eos_fit_func=self._run_eos_fit,
            results_dict=self.results
        )

    def optimize_sws(
        self,
        structure: Dict[str, Any],
        sws_values: List[float],
        optimal_ca: float
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Phase 2: SWS optimization at optimal c/a ratio.

        Delegates to the phase_execution module for implementation.

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
        """
        from modules.optimization.phase_execution import optimize_sws

        return optimize_sws(
            structure=structure,
            sws_values=sws_values,
            optimal_ca=optimal_ca,
            config=self.config,
            base_path=self.base_path,
            run_calculations_func=self._run_calculations,
            validate_calculations_func=self._validate_calculations,
            run_eos_fit_func=self._run_eos_fit,
            results_dict=self.results
        )

    def run_optimized_calculation(
        self,
        structure: Dict[str, Any],
        optimal_ca: float,
        optimal_sws: float
    ) -> Dict[str, Any]:
        """
        Phase 3: Run final calculation with optimized parameters.

        Delegates to the phase_execution module for implementation.

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
        """
        from modules.optimization.phase_execution import run_optimized_calculation

        return run_optimized_calculation(
            structure=structure,
            optimal_ca=optimal_ca,
            optimal_sws=optimal_sws,
            config=self.config,
            base_path=self.base_path,
            run_calculations_func=self._run_calculations,
            validate_calculations_func=self._validate_calculations,
            results_dict=self.results
        )

    def generate_dos_analysis(
        self,
        phase_path: Union[str, Path],
        file_id: str,
        plot_range: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Generate DOS analysis and plots.

        Delegates to the analysis module for implementation.

        Parameters
        ----------
        phase_path : str or Path
            Path to calculation directory
        file_id : str
            File identifier for DOS files
        plot_range : list of float, optional
            Energy range for DOS plots [E_min, E_max] in eV
            If None, uses config['dos_plot_range']

        Returns
        -------
        dict
            Dictionary with DOS analysis results
        """
        from modules.optimization.analysis import generate_dos_analysis

        if plot_range is None:
            plot_range = self.config.get('dos_plot_range')

        return generate_dos_analysis(
            phase_path=phase_path,
            file_id=file_id,
            dos_plot_range=plot_range
        )

    def generate_summary_report(self) -> str:
        """
        Generate comprehensive summary report of optimization workflow.

        Delegates to the analysis module for implementation.

        Returns
        -------
        str
            Formatted summary report
        """
        from modules.optimization.analysis import generate_summary_report

        return generate_summary_report(
            config=self.config,
            base_path=self.base_path,
            results=self.results
        )

    def _run_prepare_only_mode(self) -> Dict[str, Any]:
        """
        Prepare-only mode: Create input files for Phase 1 & 2, skip Phase 3.

        Delegates to the prepare_only module for implementation.

        Returns
        -------
        dict
            Empty results dictionary with prepare_only flag set
        """
        from modules.optimization.prepare_only import run_prepare_only_mode

        return run_prepare_only_mode(
            config=self.config,
            base_path=self.base_path,
            prepare_ranges_func=self._prepare_ranges
        )

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
        # Single check: Route to prepare-only mode if flag is set
        if self.config.get('prepare_only', False):
            return self._run_prepare_only_mode()

        # Normal full workflow (no prepare_only checks needed below)
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
            from modules.structure_builder import create_emto_structure

            if self.config.get('cif_file'):
                print(f"Creating structure from CIF: {self.config['cif_file']}")
                structure_pmg, structure = create_emto_structure(
                    cif_file=self.config['cif_file'],
                    user_magnetic_moments=self.config.get('user_magnetic_moments')
                )
            else:
                print(f"Creating structure from parameters...")
                structure_pmg, structure = create_emto_structure(
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

            # Store structure_pmg in structure dict for later use
            structure['structure_pmg'] = structure_pmg

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
