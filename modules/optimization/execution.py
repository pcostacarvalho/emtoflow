#!/usr/bin/env python3
"""
Execution and validation functions for EMTO workflow.

Handles running calculations and validating outputs.
"""

import time
from pathlib import Path
from typing import Union, List, Dict, Any, Optional

from utils.running_bash import run_sbatch, chmod_and_run


def run_calculations(
    calculation_path: Union[str, Path],
    script_name: str,
    config: Dict[str, Any],
    run_mode: Optional[str] = None
) -> bool:
    """
    Execute EMTO calculations using configured run mode.

    Parameters
    ----------
    calculation_path : str or Path
        Directory containing run script
    script_name : str
        Name of the run script (e.g., 'run_fept.sh')
    config : dict
        Configuration dictionary
    run_mode : str, optional
        "sbatch" → submit with SLURM
        "local" → run locally
        If None, uses config['run_mode']

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
    

    if run_mode is None:
        run_mode = config.get('run_mode', 'local')

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


def _check_calculation_failed(content: str) -> tuple[bool, Optional[str]]:
    """
    Check if a calculation output indicates failure.
    
    Parameters
    ----------
    content : str
        Content of the output file
        
    Returns
    -------
    tuple of (bool, Optional[str])
        (is_failed, failure_reason) where is_failed is True if calculation failed,
        and failure_reason describes why (None if not failed)
    """
    # Check for "Stop:" pattern (general failure indicator)
    if "Stop:" in content:
        return True, "contains 'Stop:' message"
    
    # Check for non-converged KGRN
    if "KGRN: NC  Finished at:" in content:
        return True, "KGRN did not converge (NC)"
    
    return False, None


def validate_calculations(
    phase_path: Union[str, Path],
    ca_ratios: List[float],
    sws_values: List[float],
    job_name: str,
    strict: bool = True
) -> None:
    """
    Validate that EMTO calculations completed successfully.

    Checks that output files exist and contain success indicators:
    - KSTR: "KSTR:     Finished at:"
    - KGRN: "KGRN: OK  Finished at:"
    - KFCD: "KFCD: OK  Finished at:"
    
    Also detects and skips failed calculations:
    - Files containing "Stop:" message
    - Files with "KGRN: NC  Finished at:" (non-converged)

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
    strict : bool, optional
        If True, raise RuntimeError on missing files (user-provided values).
        If False, only warn on missing files (auto-generated values).
        Default: True

    Raises
    ------
    RuntimeError
        If strict=True and any calculation failed or output files are missing/incomplete
    """
    phase_path = Path(phase_path)

    print(f"\n{'='*70}")
    print(f"VALIDATING CALCULATIONS")
    if not strict:
        print(f"(Lenient mode: missing values will be skipped)")
    print(f"{'='*70}")

    errors = []
    warnings = []

    # For each c/a ratio, check KSTR and SHAPE outputs
    for ca_ratio in ca_ratios:
        file_id = f"{job_name}_{ca_ratio:.2f}"

        # Check KSTR output in smx directory
        kstr_out = phase_path / f"smx/{file_id}.prn"
        if not kstr_out.exists():
            msg = f"Missing KSTR output: {kstr_out}"
            if strict:
                errors.append(msg)
            else:
                warnings.append(msg)
        else:
            # Check for success indicator
            with open(kstr_out, 'r') as f:
                content = f.read()
                # Check for failure patterns
                is_failed, failure_reason = _check_calculation_failed(content)
                if is_failed:
                    msg = f"KSTR failed ({failure_reason}): {kstr_out}"
                    if strict:
                        errors.append(msg)
                    else:
                        warnings.append(msg)
                elif "KSTR:     Finished at:" not in content:
                    msg = f"KSTR did not complete successfully: {kstr_out}"
                    if strict:
                        errors.append(msg)
                    else:
                        warnings.append(msg)
                else:
                    print(f"✓ KSTR completed for c/a={ca_ratio:.2f}")

    # For each (c/a, sws) pair, check KGRN and KFCD outputs
    for ca_ratio in ca_ratios:
        for sws in sws_values:
            file_id = f"{job_name}_{ca_ratio:.2f}_{sws:.2f}"

            # Check KGRN output
            kgrn_out = phase_path / f"{file_id}.prn"
            if not kgrn_out.exists():
                msg = f"Missing KGRN output: {kgrn_out}"
                if strict:
                    errors.append(msg)
                else:
                    warnings.append(msg)
            else:
                # Check for success indicator and failure patterns
                with open(kgrn_out, 'r') as f:
                    content = f.read()
                    # Check for failure patterns first
                    is_failed, failure_reason = _check_calculation_failed(content)
                    if is_failed:
                        msg = f"KGRN failed ({failure_reason}): {kgrn_out}"
                        if strict:
                            errors.append(msg)
                        else:
                            warnings.append(msg)
                    elif "KGRN: OK  Finished at:" not in content:
                        msg = f"KGRN did not complete successfully: {kgrn_out}"
                        if strict:
                            errors.append(msg)
                        else:
                            warnings.append(msg)
                    else:
                        print(f"✓ KGRN completed for c/a={ca_ratio:.2f}, SWS={sws:.2f}")

            # Check KFCD output
            kfcd_out = phase_path / f"fcd/{file_id}.prn"
            if not kfcd_out.exists():
                msg = f"Missing KFCD output: {kfcd_out}"
                if strict:
                    errors.append(msg)
                else:
                    warnings.append(msg)
            else:
                # Check for success indicator
                with open(kfcd_out, 'r') as f:
                    content = f.read()
                    # Check for failure patterns
                    is_failed, failure_reason = _check_calculation_failed(content)
                    if is_failed:
                        msg = f"KFCD failed ({failure_reason}): {kfcd_out}"
                        if strict:
                            errors.append(msg)
                        else:
                            warnings.append(msg)
                    elif "KFCD: OK  Finished at:" not in content:
                        msg = f"KFCD did not complete successfully: {kfcd_out}"
                        if strict:
                            errors.append(msg)
                        else:
                            warnings.append(msg)
                    else:
                        print(f"✓ KFCD completed for c/a={ca_ratio:.2f}, SWS={sws:.2f}")

    print(f"{'='*70}\n")

    # Print warnings if any (lenient mode)
    if warnings:
        print(f"⚠ Warning: {len(warnings)} calculation(s) missing or incomplete:")
        for warning in warnings:
            print(f"  - {warning}")
        print("  These will be skipped during result extraction.\n")

    # Raise errors if any (strict mode)
    if errors:
        error_msg = "\n".join(errors)
        raise RuntimeError(
            f"Calculation validation failed with {len(errors)} error(s):\n{error_msg}\n\n"
            f"Please check the calculation logs in: {phase_path}"
        )

    if not warnings and not errors:
        print("✓ All calculations validated successfully\n")
