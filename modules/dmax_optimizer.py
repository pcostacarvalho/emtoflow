import re
import os

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
    
    shell_data = []
    cumulative_vectors = 0
    current_shell = 0
    
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
                
                # When shell number changes, record the shell
                if shell_num != current_shell:
                    current_shell = shell_num
                    shell_data.append({
                        'D': d_value,
                        'shell': shell_num,
                        'cumulative_vectors': cumulative_vectors
                    })
    
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
            # This shouldn't happen if DMAX_initial was large enough

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
        # Pattern: DMAX....=    X.XXXXXX
        dmax_value = values['DMAX']
        new_dmax_str = f"{dmax_value:>6.6f}"
        
        pattern = r'(DMAX....=\s+)([\d.]+)'
        updated_content = re.sub(pattern, rf'\g<1>{new_dmax_str}', content)
        
        # Write back
        with open(filename, 'w') as f:
            f.write(updated_content)
        
        print(f"Updated {filename}: DMAX = {dmax_value:.6f} "
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
        print(f"{ratio:<15.2f} {values['DMAX']:<12.6f} {values['shells']:<10} {values['vectors']:<10}")
    
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
            f.write(f"{ratio:<15.2f} {values['DMAX']:<12.6f} "
                   f"{values['shells']:<10} {values['vectors']:<10}\n")

        f.write("="*70 + "\n")

        # Statistics
        dmaxes = [v['DMAX'] for v in optimal_dmax.values()]
        shells = [v['shells'] for v in optimal_dmax.values()]
        vectors = [v['vectors'] for v in optimal_dmax.values()]

        f.write("\nSTATISTICS\n")
        f.write("-"*70 + "\n")
        f.write(f"DMAX Range: {min(dmaxes):.6f} - {max(dmaxes):.6f} "
               f"(Δ={max(dmaxes)-min(dmaxes):.6f})\n")
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


# Example usage
if __name__ == "__main__":
    # Example: After running KSTR with initial DMAX guess
    prn_files = {
        0.92: "./test/smx/fept_0.92.prn",
        0.96: "./test/smx/fept_0.96.prn",
        1.00: "./test/smx/fept_1.00.prn",
    }
    
    optimal_dmax = find_optimal_dmax(
        prn_files,
        target_vectors=100,
        vector_tolerance=10
    )
    
    print_optimization_summary(optimal_dmax)
    
    # Update the KSTR input files
    # update_kstr_files("./test", optimal_dmax, "fept")