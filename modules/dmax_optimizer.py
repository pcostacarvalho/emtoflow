import re
import os
from itertools import product

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


def match_shells_across_ratios(all_candidates, shell_tolerance=1, target_vectors=100):
    """
    Find combination of D values where all ratios have compatible shell numbers.
    
    Parameters:
    -----------
    all_candidates : dict
        {ratio: [(D, shell, vectors), ...]} for each ratio
    shell_tolerance : int
        Maximum difference in shell numbers between ratios
    target_vectors : int
        Target number of vectors
    
    Returns:
    --------
    dict: {ratio: (D_value, shell_number, vector_count)} or None if no solution
    """
    ratios = list(all_candidates.keys())
    
    # Generate all combinations
    candidate_lists = [all_candidates[r] for r in ratios]
    
    best_solution = None
    best_score = float('inf')
    
    for combo in product(*candidate_lists):
        # combo is a tuple of (D, shell, vectors) for each ratio
        shells = [c[1] for c in combo]
        vectors = [c[2] for c in combo]
        
        # Check if shells are within tolerance
        min_shell = min(shells)
        max_shell = max(shells)
        
        if max_shell - min_shell <= shell_tolerance:
            # Calculate score: deviation from target vectors
            score = sum(abs(v - target_vectors) for v in vectors)
            
            if score < best_score:
                best_score = score
                best_solution = {ratios[i]: combo[i] for i in range(len(ratios))}
    
    return best_solution


def find_optimal_dmax(prn_files_dict, target_vectors=100, shell_tolerance=1, vector_tolerance=10):
    """
    Find optimal DMAX for each ratio.
    
    Parameters:
    -----------
    prn_files_dict : dict
        {ratio: filepath} mapping, e.g., {0.92: "path/to/file.prn"}
    target_vectors : int
        Target number of vectors (default 100)
    shell_tolerance : int
        Maximum difference in shell numbers between ratios (default 1)
    vector_tolerance : int
        Acceptable range around target_vectors when finding candidates
    
    Returns:
    --------
    dict: {ratio: {'DMAX': value, 'shells': n, 'vectors': m}}
    """
    # Parse all files
    all_shell_data = {}
    for ratio, filepath in prn_files_dict.items():
        all_shell_data[ratio] = parse_prn_file(filepath)
    
    # Get candidates for each ratio
    all_candidates = {}
    for ratio, shell_data in all_shell_data.items():
        all_candidates[ratio] = get_dmax_candidates(
            shell_data, 
            target_vectors=target_vectors,
            tolerance=vector_tolerance
        )
    
    # Find best matching combination
    solution = match_shells_across_ratios(
        all_candidates, 
        shell_tolerance=shell_tolerance,
        target_vectors=target_vectors
    )
    
    if solution is None:
        print("Warning: No solution found with given tolerances.")
        return None
    
    # Format output
    result = {}
    for ratio, (dmax, shells, vectors) in solution.items():
        result[ratio] = {
            'DMAX': dmax,
            'shells': shells,
            'vectors': vectors
        }
    
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
        shell_tolerance=1,
        vector_tolerance=15
    )
    
    print_optimization_summary(optimal_dmax)
    
    # Update the KSTR input files
    # update_kstr_files("./test", optimal_dmax, "fept")