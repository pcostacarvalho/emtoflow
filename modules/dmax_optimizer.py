import re
import os
import math
import subprocess
import time
from modules.inputs import create_kstr_input

def parse_prn_file(filepath):
    """
    Parse a .prn file and extract neighbor shell information for IQ = 1 only.
    
    Parameters:
    -----------
    filepath : str
        Path to the .prn file
    
    Returns:
    --------
    list of dict: Each entry contains:
        - 'D': distance value (float)
        - 'shell': shell number (int)
        - 'cumulative_vectors': total number of vectors up to this shell (int)
    """
    with open(filepath, 'r') as f:
        content = f.read()
    
    lines = content.split('\n')

    # Use dictionary to track shells - will keep last neighbor's data for each shell
    shell_dict = {}
    cumulative_vectors = 0

    # Flag to track if we're in the IQ = 1 section
    in_iq1_section = False

    for line in lines:
        # Start capturing when we find "IQ =  1"
        if 'IQ =  1' in line and 'QP' in line:
            in_iq1_section = True
            continue

        # Stop capturing when we find the next "IQ =" (IQ = 2, 3, etc.)
        if in_iq1_section and re.search(r'IQ\s*=\s*[2-9]', line):
            break

        # Pattern to match data lines: IS IN IR JQ D ...
        if in_iq1_section:
            pattern = r'^\s+(\d+)\s+\d+\s+\d+\s+\d+\s+([\d.]+)\s+'
            match = re.match(pattern, line)

            if match:
                shell_num = int(match.group(1))
                d_value = float(match.group(2))

                # Each line represents one neighbor (vector)
                cumulative_vectors += 1

                # Update entry for this shell (keeps last neighbor's data)
                shell_dict[shell_num] = {
                    'D': d_value,
                    'cumulative_vectors': cumulative_vectors
                }

    # Convert dictionary to sorted list
    shell_data = [
        {
            'D': data['D'],
            'shell': shell,
            'cumulative_vectors': data['cumulative_vectors']
        }
        for shell, data in sorted(shell_dict.items())
    ]

    return shell_data


def get_dmax_candidates(shell_data, target_vectors=100, tolerance=10):
    """
    For a single ratio, find D values that give vectors close to target.
    
    Parameters:
    -----------
    shell_data : list of dict
        Output from parse_prn_file
    target_vectors : int
        Target number of vectors
    tolerance : int
        Acceptable range around target_vectors
    
    Returns:
    --------
    list of tuples: (D_value, shell_number, vector_count)
    """
    candidates = []
    
    for entry in shell_data:
        if abs(entry['cumulative_vectors'] - target_vectors) <= tolerance:
            candidates.append((
                entry['D'],
                entry['shell'],
                entry['cumulative_vectors']
            ))
    
    # If no candidates within tolerance, return closest ones
    if not candidates:
        # Sort by distance to target and return top 3
        sorted_data = sorted(shell_data, 
                           key=lambda x: abs(x['cumulative_vectors'] - target_vectors))
        for entry in sorted_data[:3]:
            candidates.append((
                entry['D'],
                entry['shell'],
                entry['cumulative_vectors']
            ))
    
    return candidates


def find_optimal_dmax(prn_files_dict, target_vectors=100, vector_tolerance=10):
    """
    Simplified DMAX optimization: Use largest c/a ratio as reference.

    Strategy:
    1. Parse largest c/a ratio's output (most demanding case)
    2. Find DMAX for ~target_vectors
    3. Use that shell number as reference
    4. For other ratios, find DMAX giving same shell number

    Note: Using largest c/a as reference ensures that if dmax_initial
    is sufficient for the most demanding case, the reference shell will
    be available in all smaller c/a ratios.

    Parameters:
    -----------
    prn_files_dict : dict
        {ratio: filepath} mapping, e.g., {0.92: "path/to/file.prn"}
    target_vectors : int
        Target number of vectors for reference ratio (default 100)
    vector_tolerance : int
        Acceptable range around target_vectors (default 10)

    Returns:
    --------
    dict: {ratio: {'DMAX': value, 'shells': n, 'vectors': m}}
    """
    # Sort ratios in descending order (largest c/a first)
    ratios = sorted(prn_files_dict.keys(), reverse=True)

    if not ratios:
        print("Error: No ratios provided")
        return None

    # STEP 1: Parse largest ratio and establish reference shell
    print(f"\nStep 1: Analyzing reference ratio (c/a = {ratios[0]:.2f}, largest)...")
    first_ratio = ratios[0]
    first_prn = prn_files_dict[first_ratio]

    first_shell_data = parse_prn_file(first_prn)
    if not first_shell_data:
        print(f"Error: Could not parse {first_prn}")
        return None

    # Find DMAX for target vectors in first ratio
    candidates = get_dmax_candidates(
        first_shell_data,
        target_vectors=target_vectors,
        tolerance=vector_tolerance
    )

    if not candidates:
        print(f"Warning: No candidates found for target={target_vectors}±{vector_tolerance}")
        print(f"Using closest available shell")
        # Get closest to target
        candidates = get_dmax_candidates(first_shell_data, target_vectors=target_vectors, tolerance=999)

    # Use first (best) candidate as reference
    ref_dmax, ref_shell, ref_vectors = candidates[0]

    print(f"  Reference: DMAX={ref_dmax:.6f}, Shell={ref_shell}, Vectors={ref_vectors}")

    # Check if the found shell is within tolerance
    distance_from_target = abs(ref_vectors - target_vectors)
    if distance_from_target > vector_tolerance:
        print(f"\n  ✗ ERROR: Tolerance not satisfied!")
        print(f"  Closest available shell ({ref_shell}) has {ref_vectors} vectors.")
        print(f"  Target was {target_vectors} ± {vector_tolerance} vectors.")
        print(f"  Distance from target: {distance_from_target} vectors (exceeds tolerance: {vector_tolerance})")
        print(f"\n  SUGGESTION: Increase 'dmax_initial' to reach higher shells with more vectors.")
        print(f"  Current dmax_initial captured up to DMAX={ref_dmax:.3f}")
        print(f"  Try increasing to dmax_initial={ref_dmax * 1.5:.1f} or higher.\n")
        return None

    print(f"  Using Shell {ref_shell} as target for all ratios\n")

    # Initialize results with first ratio
    result = {
        first_ratio: {
            'DMAX': ref_dmax,
            'shells': ref_shell,
            'vectors': ref_vectors
        }
    }

    # STEP 2: For each remaining ratio, find DMAX that gives ref_shell
    print(f"Step 2: Finding DMAX for remaining ratios (target: Shell {ref_shell})...")

    for ratio in ratios[1:]:
        prn_file = prn_files_dict[ratio]

        print(f"  Processing c/a = {ratio:.2f}...", end=" ")

        shell_data = parse_prn_file(prn_file)
        if not shell_data:
            print(f"ERROR: Could not parse {prn_file}")
            continue

        # Find the entry matching ref_shell
        matching_entry = None
        for entry in shell_data:
            if entry['shell'] == ref_shell:
                matching_entry = entry
                break

        if matching_entry:
            result[ratio] = {
                'DMAX': matching_entry['D'],
                'shells': matching_entry['shell'],
                'vectors': matching_entry['cumulative_vectors']
            }
            print(f"DMAX={matching_entry['D']:.6f}, Vectors={matching_entry['cumulative_vectors']}")
        else:
            print(f"ERROR: Shell {ref_shell} not found in output")

    # CHECK: Did all ratios succeed?
    if len(result) != len(ratios):
        print(f"\n  ✗ ERROR: Could not find Shell {ref_shell} for all ratios!")
        print(f"  Successfully optimized: {len(result)}/{len(ratios)} ratios")
        print(f"  Failed ratios: {[r for r in ratios if r not in result]}")
        print(f"\n  SOLUTION: Increase 'dmax_initial' parameter to capture higher shells.")
        print(f"  Current dmax_initial captured up to DMAX={ref_dmax:.3f} for c/a={first_ratio:.2f}")
        print(f"  Suggestion: Try dmax_initial={ref_dmax * 1.5:.1f} or higher.\n")
        return None

    # STEP 3: Round DMAX values to 3 decimals (round up)
    print(f"\nStep 3: Rounding DMAX values to 3 decimals...")

    for ratio in result.keys():
        original_dmax = result[ratio]['DMAX']
        # Round up to 3 decimals using ceiling
        rounded_dmax = math.ceil(original_dmax * 1000) / 1000.0
        result[ratio]['DMAX'] = rounded_dmax

        if abs(original_dmax - rounded_dmax) > 0.0001:
            print(f"  c/a = {ratio:.2f}: {original_dmax:.6f} → {rounded_dmax:.3f}")
        else:
            print(f"  c/a = {ratio:.2f}: {rounded_dmax:.3f} (no change)")

    return result


def update_kstr_files(path, ratio_dmax_dict, name_id):
    """
    Update existing KSTR .dat files with optimized DMAX values.
    
    Parameters:
    -----------
    path : str
        Base path containing smx folder
    ratio_dmax_dict : dict
        Output from find_optimal_dmax: {ratio: {'DMAX': value, ...}}
    name_id : str
        Job name identifier (e.g., 'fept')
    """
    for ratio, values in ratio_dmax_dict.items():
        filename = f"{path}/smx/{name_id}_{ratio:.2f}.dat"
        
        if not os.path.exists(filename):
            print(f"Warning: File {filename} not found, skipping.")
            continue
        
        # Read file
        with open(filename, 'r') as f:
            content = f.read()
        
        # Replace DMAX value using regex
        # Pattern: DMAX....=    X.XXX (3 decimal places)
        dmax_value = values['DMAX']
        new_dmax_str = f"{dmax_value:>6.3f}"

        pattern = r'(DMAX....=\s+)([\d.]+)'
        updated_content = re.sub(pattern, rf'\g<1>{new_dmax_str}', content)

        # Write back
        with open(filename, 'w') as f:
            f.write(updated_content)

        print(f"Updated {filename}: DMAX = {dmax_value:.3f} "
              f"(shells={values['shells']}, vectors={values['vectors']})")


def print_optimization_summary(optimal_dmax):
    """
    Print a summary table of the optimization results.
    
    Parameters:
    -----------
    optimal_dmax : dict
        Output from find_optimal_dmax
    """
    if optimal_dmax is None:
        print("No optimization results to display.")
        return
    
    print("\n" + "="*70)
    print("DMAX OPTIMIZATION RESULTS")
    print("="*70)
    print(f"{'Ratio (c/a)':<15} {'DMAX':<12} {'Shells':<10} {'Vectors':<10}")
    print("-"*70)
    
    for ratio in sorted(optimal_dmax.keys()):
        values = optimal_dmax[ratio]
        print(f"{ratio:<15.2f} {values['DMAX']:<12.3f} {values['shells']:<10} {values['vectors']:<10}")
    
    print("="*70)
    
    # Check consistency
    shells = [v['shells'] for v in optimal_dmax.values()]
    vectors = [v['vectors'] for v in optimal_dmax.values()]
    
    print(f"\nShell range: {min(shells)} - {max(shells)} (difference: {max(shells) - min(shells)})")
    print(f"Vector range: {min(vectors)} - {max(vectors)}")
    print(f"Average vectors: {sum(vectors)/len(vectors):.1f}")
    print()


def save_dmax_optimization_log(optimal_dmax, log_path, job_name, target_vectors):
    """
    Save DMAX optimization results to a log file.

    Parameters:
    -----------
    optimal_dmax : dict
        Output from find_optimal_dmax
    log_path : str
        Base output directory (log will be saved in log_path/smx/logs/)
    job_name : str
        Job name for log filename
    target_vectors : int
        Target vector count used

    Returns:
    --------
    str: Path to created log file
    """
    from datetime import datetime

    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(log_path, "smx", "logs")
    os.makedirs(logs_dir, exist_ok=True)

    log_file = os.path.join(logs_dir, f"{job_name}_dmax_optimization.log")

    with open(log_file, 'w') as f:
        f.write("="*70 + "\n")
        f.write("DMAX OPTIMIZATION LOG\n")
        f.write("="*70 + "\n")
        f.write(f"Job Name: {job_name}\n")
        f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Target Vectors: {target_vectors}\n")
        f.write(f"Number of Ratios: {len(optimal_dmax)}\n")
        f.write("\n")

        f.write("="*70 + "\n")
        f.write("OPTIMIZED DMAX VALUES\n")
        f.write("="*70 + "\n")
        f.write(f"{'Ratio (c/a)':<15} {'DMAX':<12} {'Shells':<10} {'Vectors':<10}\n")
        f.write("-"*70 + "\n")

        for ratio in sorted(optimal_dmax.keys()):
            values = optimal_dmax[ratio]
            f.write(f"{ratio:<15.2f} {values['DMAX']:<12.3f} "
                   f"{values['shells']:<10} {values['vectors']:<10}\n")

        f.write("="*70 + "\n")

        # Statistics
        dmaxes = [v['DMAX'] for v in optimal_dmax.values()]
        shells = [v['shells'] for v in optimal_dmax.values()]
        vectors = [v['vectors'] for v in optimal_dmax.values()]

        f.write("\nSTATISTICS\n")
        f.write("-"*70 + "\n")
        f.write(f"DMAX Range: {min(dmaxes):.3f} - {max(dmaxes):.3f} "
               f"(Δ={max(dmaxes)-min(dmaxes):.3f})\n")
        f.write(f"Shell Range: {min(shells)} - {max(shells)} "
               f"(Δ={max(shells)-min(shells)})\n")
        f.write(f"Vector Range: {min(vectors)} - {max(vectors)} "
               f"(Δ={max(vectors)-min(vectors)})\n")
        f.write(f"Average Vectors: {sum(vectors)/len(vectors):.1f}\n")
        f.write("\n")

        # Check consistency
        if max(shells) - min(shells) == 0:
            f.write("✓ Perfect shell consistency across all ratios\n")
        else:
            f.write("⚠ Shell numbers vary across ratios\n")

    print(f"✓ Optimization log saved: {log_file}")
    return log_file


def _check_prn_iq1_complete(prn_file_path):
    """
    Check if .prn file exists and has complete IQ=1 section.

    The IQ=1 section starts with "IQ =  1" and ends when we see either:
    - "IQ =  2" (next section)
    - A blank line followed by other content

    Parameters
    ----------
    prn_file_path : str
        Path to the .prn file

    Returns
    -------
    bool: True if IQ=1 section is complete, False otherwise
    """
    if not os.path.exists(prn_file_path):
        return False

    try:
        with open(prn_file_path, 'r') as f:
            content = f.read()

        # Check if IQ=1 section exists
        if 'IQ =  1' not in content:
            return False

        lines = content.split('\n')
        in_iq1_section = False
        found_data_lines = False

        for line in lines:
            # Start of IQ=1 section
            if 'IQ =  1' in line:
                in_iq1_section = True
                continue

            # If we're in IQ=1 section, look for data lines
            if in_iq1_section:
                # Check for data lines (IS IN IR JQ D ...)
                if re.match(r'^\s+\d+\s+\d+\s+\d+\s+\d+\s+[\d.]+', line):
                    found_data_lines = True

                # Check for next IQ section (indicates completion)
                if re.search(r'IQ\s*=\s*[2-9]', line):
                    return found_data_lines

                # Check for end of IQ=1 section (empty line after data)
                # This is a more robust check
                if found_data_lines and line.strip() == '':
                    # Peek ahead to see if we're truly done
                    # If next non-empty line doesn't have IS IN IR pattern, we're done
                    return True

        # If we're still in IQ=1 section at end of file, it's incomplete
        return False

    except Exception:
        return False


def _check_kstr_success(stdout, stderr, log_file=None):
    """
    Check if KSTR execution succeeded by analyzing output.

    KSTR can return exit code 0 even when it fails, so we need to check
    the actual output for success/failure indicators.

    Parameters
    ----------
    stdout : str
        Standard output from KSTR
    stderr : str
        Standard error from KSTR
    log_file : str, optional
        Path to .log file to check (if available)

    Returns
    -------
    tuple: (success: bool, error_message: str or None)

    Success indicators:
    - Contains "KSTR: OK  Finished at:"

    Failure indicators:
    - Contains "Stop:" or "DMAX =" with "too small"
    - Files deleted messages (tfm, tfh, mdl)
    """
    # Combine stdout and stderr for checking
    output = stdout + "\n" + stderr

    # Check log file if provided
    if log_file and os.path.exists(log_file):
        with open(log_file, 'r') as f:
            output += "\n" + f.read()

    # Check for success indicator
    if "KSTR: OK" in output and "Finished at:" in output:
        return True, None

    # Check for failure indicators
    if "Stop:" in output:
        # Extract error details
        lines = output.split('\n')
        error_lines = []
        for i, line in enumerate(lines):
            if "Stop:" in line:
                # Get the next few lines for context
                error_lines = lines[i:min(i+5, len(lines))]
                break

        error_msg = "\n".join(error_lines)

        # Check if it's a DMAX too small error
        if "DMAX" in error_msg and "too small" in error_msg:
            return False, "DMAX_TOO_SMALL: " + error_msg
        else:
            return False, "KSTR_ERROR: " + error_msg

    # If we reach here, no clear success indicator was found
    return False, "KSTR did not complete successfully (no 'KSTR: OK' found)"


def _run_dmax_optimization(output_path, job_name, structure, ca_ratios,
                          dmax_initial, target_vectors, vector_tolerance,
                          kstr_executable):
    """
    Run DMAX optimization workflow.

    Workflow:
    1. Sort c/a ratios in descending order (largest first)
    2. Create KSTR inputs with dmax_initial for all ratios
    3. Run KSTR executable for each ratio (starting with largest c/a)
    4. Parse .prn outputs
    5. Optimize DMAX values
    6. Save log file

    Note: Processing largest c/a ratio first ensures that if dmax_initial
    is sufficient for the most demanding case (largest c/a), it will
    definitely be sufficient for smaller ratios.

    Parameters
    ----------
    output_path : str
        Base output directory
    job_name : str
        Job identifier
    structure : dict
        Structure dictionary from create_emto_structure()
    ca_ratios : list of float
        c/a ratios to optimize
    dmax_initial : float
        Initial DMAX guess (should be large enough for the largest c/a ratio)
    target_vectors : int
        Target number of k-vectors
    vector_tolerance : int
        Acceptable deviation from target
    kstr_executable : str
        Path to KSTR executable

    Returns
    -------
    dict or None
        {ratio: optimized_dmax_value} or None if failed
    """

    # Sort ratios in descending order (largest c/a first)
    # This ensures dmax_initial is tested on the most demanding case first
    ca_ratios_sorted = sorted(ca_ratios, reverse=True)

    print(f"\nStep 1: Creating initial KSTR inputs (DMAX={dmax_initial})...")
    print(f"Processing c/a ratios in descending order: {[f'{r:.2f}' for r in ca_ratios_sorted]}")

    # Create directory structure
    smx_dir = os.path.join(output_path, "smx")
    os.makedirs(smx_dir, exist_ok=True)

    # Create KSTR inputs for all ratios with initial DMAX
    for ratio in ca_ratios_sorted:
        file_id_ratio = f"{job_name}_{ratio:.2f}"
        create_kstr_input(
            structure=structure,
            output_path=output_path,
            id_ratio=file_id_ratio,
            dmax=dmax_initial,
            ca_ratio=ratio
        )

    print(f"✓ Created {len(ca_ratios_sorted)} KSTR input files")

    # Step 2: Run KSTR for all ratios
    print(f"\nStep 2: Running KSTR calculations...")

    failed_ratios = []
    dmax_too_small_errors = []

    for ratio in ca_ratios_sorted:
        input_file = f"{job_name}_{ratio:.2f}.dat"
        input_path = os.path.join(smx_dir, input_file)
        log_file = os.path.join(smx_dir, f"{job_name}_{ratio:.2f}.log")
        stdout_file = os.path.join(smx_dir, f"{job_name}_{ratio:.2f}_stdout.log")
        prn_file = os.path.join(smx_dir, f"{job_name}_{ratio:.2f}.prn")

        print(f"  Running KSTR for c/a = {ratio:.2f}...", end=" ", flush=True)

        process = None
        stdin_file = None
        stdout_f = None

        try:
            # Open file handles (must stay open for subprocess)
            stdin_file = open(input_path, 'r')
            stdout_f = open(stdout_file, 'w')

            # Start KSTR process (non-blocking)
            process = subprocess.Popen(
                [kstr_executable],
                stdin=stdin_file,
                stdout=stdout_f,
                stderr=subprocess.PIPE,
                cwd=smx_dir,
                text=True
            )

            # Give process a moment to start and check it's running
            time.sleep(0.1)

            # Check if process started successfully
            initial_poll = process.poll()
            if initial_poll is not None:
                # Process already ended - this is suspicious
                stdout_f.flush()
                stdout_f.close()
                stdin_file.close()

                with open(stdout_file, 'r') as f:
                    early_stdout = f.read()

                _, early_stderr = process.communicate(timeout=1)

                print(f"✗ (process ended immediately, code {initial_poll})")
                if early_stderr:
                    print(f"    stderr: {early_stderr[:200]}")
                if early_stdout:
                    print(f"    stdout: {early_stdout[:200]}")
                failed_ratios.append(ratio)
                continue

            # Poll for .prn file with IQ=1 section complete
            poll_interval = 0.1  # seconds
            max_wait_time = 60  # seconds (much shorter than before)
            elapsed_time = 0
            prn_complete = False

            while elapsed_time < max_wait_time:
                # Flush stdout to disk so we can see output even if process is killed
                if stdout_f and not stdout_f.closed:
                    stdout_f.flush()

                # Check if process is still running
                poll_result = process.poll()

                # Check if .prn file has complete IQ=1 section
                if _check_prn_iq1_complete(prn_file):
                    prn_complete = True
                    print(f"✓ (data extracted in {elapsed_time:.1f}s)")

                    # Terminate the process since we have what we need
                    if poll_result is None:  # Process still running
                        process.terminate()
                        try:
                            process.wait(timeout=2)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()
                    break

                # If process finished naturally, check for completion
                if poll_result is not None:
                    # Flush and close files to ensure everything is written
                    if stdout_f and not stdout_f.closed:
                        stdout_f.flush()

                    if _check_prn_iq1_complete(prn_file):
                        prn_complete = True
                        print(f"✓ (completed in {elapsed_time:.1f}s)")
                    else:
                        # Check what files were actually created
                        import glob
                        created_files = glob.glob(os.path.join(smx_dir, f"{job_name}_{ratio:.2f}.*"))
                        print(f"✗ (process ended without complete data, created {len(created_files)} files)")
                    break

                time.sleep(poll_interval)
                elapsed_time += poll_interval

            # Close file handles before reading outputs
            if stdin_file:
                stdin_file.close()
            if stdout_f:
                stdout_f.close()

            # If we timed out waiting for .prn data
            if not prn_complete:
                print(f"✗ (timeout waiting for .prn data)")
                failed_ratios.append(ratio)
                if process and process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                continue

            # Read stderr and check for errors
            stderr_output = ""
            if process:
                _, stderr_output = process.communicate(timeout=1)
                if stderr_output:
                    with open(stdout_file, 'a') as f:
                        f.write("\n\n=== STDERR ===\n")
                        f.write(stderr_output)

            # Read stdout for validation
            with open(stdout_file, 'r') as f:
                stdout_output = f.read()

            # Even if we got the .prn data, check for serious errors
            success, error_msg = _check_kstr_success(
                stdout_output,
                stderr_output,
                log_file
            )

            # For optimization, we only care if we got the .prn data
            # Warnings are OK as long as we have the neighbor shell info
            if not prn_complete:
                failed_ratios.append(ratio)
                if error_msg and "DMAX_TOO_SMALL" in error_msg:
                    print(f"    {error_msg.split(':')[0]}")
                    dmax_too_small_errors.append((ratio, error_msg))

        except subprocess.TimeoutExpired:
            print("✗ (timeout)")
            failed_ratios.append(ratio)
            if process and process.poll() is None:
                process.kill()
                process.wait()
        except Exception as e:
            print(f"✗ (error: {e})")
            failed_ratios.append(ratio)
            if process and process.poll() is None:
                process.kill()
                process.wait()
        finally:
            # Ensure file handles are closed
            if stdin_file and not stdin_file.closed:
                stdin_file.close()
            if stdout_f and not stdout_f.closed:
                stdout_f.close()

    # Check if any KSTR runs failed
    if failed_ratios:
        print(f"\n✗ ERROR: KSTR failed for {len(failed_ratios)}/{len(ca_ratios_sorted)} ratios")
        print(f"  Failed ratios: {failed_ratios}")

        if dmax_too_small_errors:
            print("\n  DMAX TOO SMALL detected:")
            for ratio, error_msg in dmax_too_small_errors:
                # Extract suggested DMAX if available
                if "Try DMAX =" in error_msg:
                    match = re.search(r'Try DMAX\s*=\s*([\d.]+)', error_msg)
                    if match:
                        suggested_dmax = float(match.group(1))
                        print(f"    c/a = {ratio:.2f}: Increase dmax_initial to at least {suggested_dmax:.2f}")

            print(f"\n  SOLUTION: Increase 'dmax_initial' parameter (currently {dmax_initial:.2f})")
            print(f"  Suggestion: Try dmax_initial={dmax_initial * 1.5:.2f} or higher")

        return None

    # Step 2b: Organize KSTR output files
    print(f"\nStep 2b: Organizing KSTR output files...")

    # Create logs directory inside smx
    logs_dir = os.path.join(smx_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Move KSTR output files to logs
    output_extensions = ['.log', '.mdl', '.prn', '.tfh', '.tfm']
    moved_files = 0

    for ratio in ca_ratios_sorted:
        # Move output files
        for ext in output_extensions:
            filename = f"{job_name}_{ratio:.2f}{ext}"
            src = os.path.join(smx_dir, filename)
            dst = os.path.join(logs_dir, filename)

            if os.path.exists(src):
                os.rename(src, dst)
                moved_files += 1

        # Move stdout log file
        stdout_filename = f"{job_name}_{ratio:.2f}_stdout.log"
        stdout_src = os.path.join(smx_dir, stdout_filename)
        stdout_dst = os.path.join(logs_dir, stdout_filename)
        if os.path.exists(stdout_src):
            os.rename(stdout_src, stdout_dst)
            moved_files += 1

        # Move initial .dat file (with dmax_initial) to logs with descriptive name
        dat_filename = f"{job_name}_{ratio:.2f}.dat"
        dat_src = os.path.join(smx_dir, dat_filename)
        dat_dst = os.path.join(logs_dir, f"{job_name}_{ratio:.2f}_dmax_initial_{dmax_initial:.2f}.dat")
        if os.path.exists(dat_src):
            os.rename(dat_src, dat_dst)
            moved_files += 1

    print(f"  ✓ Moved {moved_files} files to smx/logs/ (outputs + initial .dat files)")

    # Step 3: Parse .prn outputs
    print(f"\nStep 3: Parsing KSTR outputs...")

    prn_files = {}
    for ratio in ca_ratios_sorted:
        # Now look for .prn files in logs directory
        prn_file = os.path.join(logs_dir, f"{job_name}_{ratio:.2f}.prn")
        if os.path.exists(prn_file):
            prn_files[ratio] = prn_file
        else:
            print(f"  Warning: {prn_file} not found")

    if len(prn_files) != len(ca_ratios_sorted):
        print(f"  ⚠ Only {len(prn_files)}/{len(ca_ratios_sorted)} .prn files found")

    if not prn_files:
        print("✗ No .prn files found - DMAX optimization failed")
        return None

    # Step 4: Optimize DMAX
    print(f"\nStep 4: Optimizing DMAX values...")

    optimal_dmax = find_optimal_dmax(
        prn_files,
        target_vectors=target_vectors,
        vector_tolerance=vector_tolerance
    )

    if optimal_dmax is None:
        print("✗ DMAX optimization failed")
        return None

    # Print summary
    print_optimization_summary(optimal_dmax)

    # Step 5: Save log
    save_dmax_optimization_log(
        optimal_dmax,
        output_path,
        job_name,
        target_vectors
    )

    # Convert to simple dict {ratio: DMAX_value}
    dmax_dict = {ratio: values['DMAX'] for ratio, values in optimal_dmax.items()}

    # Check if all ratios were successfully optimized
    missing_ratios = [r for r in ca_ratios_sorted if r not in dmax_dict]
    if missing_ratios:
        print("\n" + "="*70)
        print("⚠ WARNING: DMAX optimization incomplete")
        print("="*70)
        print(f"Failed to optimize DMAX for c/a ratios: {missing_ratios}")
        print("\nPossible causes:")
        print("  1. dmax_initial too small - increase it and try again")
        print("  2. Target shell not achievable for these geometries")
        print("  3. KSTR calculation failed for these ratios")
        print("\nAborting workflow - please check the optimization log.")
        print("="*70)
        return None

    print("\n" + "="*70)
    print("DMAX OPTIMIZATION COMPLETE")
    print("="*70)

    return dmax_dict

