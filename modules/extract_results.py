import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class IterationData:
    """Data for a single iteration."""
    iteration: int
    energy: float
    error: float
    fermi_energy: float
    dos_ef: float
    magnetic_moments: List[float]  # Per atom
    total_magnetic_moment: float
    # New: weighted magnetic moments per unique IQ
    weighted_magnetic_moments: Dict[int, float] = None
    
    def __post_init__(self):
        if self.weighted_magnetic_moments is None:
            self.weighted_magnetic_moments = {}


@dataclass
class EMTOResults:
    """Container for EMTO calculation results."""
    
    # Convergence data
    total_energy: Optional[float] = None
    free_energy: Optional[float] = None
    kinetic_energy: Optional[float] = None
    
    # Iteration history
    iterations: List[IterationData] = None
    
    # Magnetic moments - now keyed by (IQ, ITA, atom_name)
    magnetic_moments: Dict[Tuple[int, int, str], float] = None
    total_magnetic_moment: Optional[float] = None
    
    # Concentrations - keyed by (IQ, ITA)
    concentrations: Dict[Tuple[int, int], float] = None
    
    # Weighted magnetic moments per IQ (sum over ITAs weighted by concentration)
    weighted_magnetic_moments: Dict[int, float] = None
    
    # Energy by functional - now keyed by (IQ, ITA, atom_name)
    energies_by_functional: Dict[Tuple, Dict[str, float]] = None
    
    # IQ to element mapping
    iq_to_element: Dict[int, str] = None
    
    # Additional info
    atoms: List[Tuple[int, int, str]] = None  # List of (IQ, ITA, atom_name)
    
    def __post_init__(self):
        if self.iterations is None:
            self.iterations = []
        if self.magnetic_moments is None:
            self.magnetic_moments = {}
        if self.concentrations is None:
            self.concentrations = {}
        if self.weighted_magnetic_moments is None:
            self.weighted_magnetic_moments = {}
        if self.energies_by_functional is None:
            self.energies_by_functional = {}
        if self.iq_to_element is None:
            self.iq_to_element = {}
        if self.atoms is None:
            self.atoms = []


def parse_kgrn(filepath: str, concentrations: Dict[Tuple[int, int], float],
               iq_to_element: Dict[int, str], atoms: List[Tuple[int, int, str]]) -> EMTOResults:
    """Parse KGRN output file (.prn).

    Args:
        filepath: Path to KGRN output file
        concentrations: Dict of (IQ, ITA) -> concentration from KFCD
        iq_to_element: Dict of IQ -> element name mapping from KFCD
        atoms: List of (IQ, ITA, atom_name) tuples from KFCD
    """

    results = EMTOResults()

    # Note: concentrations, iq_to_element, and atoms are passed as parameters
    # for calculations but NOT stored in KGRN results (only in KFCD results)

    with open(filepath, 'r') as f:
        lines = f.readlines()

    content = ''.join(lines)
    
    # Extract iteration convergence data
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Look for iteration lines
        if 'Wmsg: Iteration' in line and 'Etot' in line:
            match = re.search(r'Iteration\s+(\d+)\s+Etot\s+=\s+([-\d.]+)\s+err\s+=\s+([-\d.]+)', line)
            if match:
                iteration = int(match.group(1))
                energy = float(match.group(2))
                error = float(match.group(3))
                
                # Extract Fermi energy and DOS from next line
                fermi_energy = 0.0
                dos_ef = 0.0
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    ef_match = re.search(r'EF\s+=\s+([-\d.]+)', next_line)
                    dos_match = re.search(r'DOS\(E_F\)=\s+([-\d.]+)', next_line)
                    if ef_match:
                        fermi_energy = float(ef_match.group(1))
                    if dos_match:
                        dos_ef = float(dos_match.group(1))
                
                # Extract magnetic moments from next lines
                magm_line = None
                total_magm = 0.0
                magnetic_moments = []
                
                if i + 2 < len(lines):
                    magm_line = lines[i + 2]
                    if 'Magm.=' in magm_line:
                        magm_matches = re.findall(r'([-\d.]+)', magm_line.split('Magm.=')[1])
                        magnetic_moments = [float(m) for m in magm_matches]
                    
                    # Total magnetic moment
                    if i + 3 < len(lines) and 'Total magm.' in lines[i + 3]:
                        total_match = re.search(r'Total magm\.=\s+([-\d.]+)', lines[i + 3])
                        if total_match:
                            total_magm = float(total_match.group(1))
                
                # Calculate weighted magnetic moments per unique IQ
                weighted_magm = {}
                if magnetic_moments and concentrations:
                    # Group magnetic moments by IQ
                    # Assuming magnetic_moments list corresponds to IQ ordering with multiple ITAs
                    n_iqs = len(magnetic_moments) // 2  # Assuming 2 ITAs per IQ

                    for idx, magm in enumerate(magnetic_moments):
                        # Determine IQ and ITA from position
                        # This assumes ordering: IQ1-ITA1, IQ1-ITA2, IQ2-ITA1, IQ2-ITA2, ...
                        iq = (idx // 2) + 1
                        ita = (idx % 2) + 1

                        conc = concentrations.get((iq, ita), 0.0)

                        if iq not in weighted_magm:
                            weighted_magm[iq] = 0.0
                        weighted_magm[iq] += magm * conc
                
                iter_data = IterationData(
                    iteration=iteration,
                    energy=energy,
                    error=error,
                    fermi_energy=fermi_energy,
                    dos_ef=dos_ef,
                    magnetic_moments=magnetic_moments,
                    total_magnetic_moment=total_magm,
                    weighted_magnetic_moments=weighted_magm
                )
                results.iterations.append(iter_data)
        
        i += 1
    
    # Extract final total energies
    total_energy_match = re.search(r'Total energy\s+([-\d.]+)', content)
    if total_energy_match:
        results.total_energy = float(total_energy_match.group(1))
    
    free_energy_match = re.search(r'Free\s+energy\s+([-\d.]+)', content)
    if free_energy_match:
        results.free_energy = float(free_energy_match.group(1))
    
    kinetic_match = re.search(r'Kinetic energy\s+([-\d.]+)', content, re.MULTILINE)
    if kinetic_match:
        results.kinetic_energy = float(kinetic_match.group(1))

    return results


def parse_kfcd(filepath: str) -> EMTOResults:
    """Parse KFCD output file (.prn)."""
    
    results = EMTOResults()
    
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    # Extract concentrations and build (IQ,ITA) -> atom mapping
    iq_ita_to_atom = {}  # mapping of (IQ, ITA) -> atom name
    for line in lines:
        if 'IQ =' in line and 'ITA =' in line and 'CONC =' in line:
            iq_match = re.search(r'IQ\s+=\s+(\d+)', line)
            ita_match = re.search(r'ITA\s+=\s+(\d+)', line)
            conc_match = re.search(r'CONC\s+=\s+([\d.]+)', line)
            atom_match = re.search(r'\((\w+)\s*\)', line)

            if iq_match and ita_match and conc_match:
                iq = int(iq_match.group(1))
                ita = int(ita_match.group(1))
                conc = float(conc_match.group(1))
                results.concentrations[(iq, ita)] = conc

                # Also extract atom name for this IQ, ITA combination
                if atom_match:
                    atom = atom_match.group(1)
                    iq_ita_to_atom[(iq, ita)] = atom
                    # Build IQ to element mapping
                    if iq not in results.iq_to_element:
                        results.iq_to_element[iq] = atom

    # Extract magnetic moments per IQ with ITA context
    current_ita = None  # Only need to track ITA

    for i, line in enumerate(lines):
        # Track current ITA from section headers
        if 'IQ =' in line and 'ITA =' in line:
            ita_match = re.search(r'ITA\s+=\s+(\d+)', line)
            if ita_match:
                current_ita = int(ita_match.group(1))

        # Extract magnetic moment using the IQ,ITA -> atom mapping
        if 'Magnetic moment for IQ' in line:
            match = re.search(r'IQ\s+=\s+(\d+)\s+is\s+([-\d.]+)', line)
            if match:
                iq = int(match.group(1))
                mag_moment = float(match.group(2))

                # Look up atom name from the mapping we built earlier
                if current_ita is not None and (iq, current_ita) in iq_ita_to_atom:
                    atom = iq_ita_to_atom[(iq, current_ita)]
                    key = (iq, current_ita, atom)
                    results.magnetic_moments[key] = mag_moment

                    if key not in results.atoms:
                        results.atoms.append(key)
    
    # Build IQ to element mapping from atoms
    for (iq, ita, atom) in results.atoms:
        if iq not in results.iq_to_element:
            results.iq_to_element[iq] = atom
    
    # Calculate weighted magnetic moments per IQ
    for (iq, ita, atom), magm in results.magnetic_moments.items():
        conc = results.concentrations.get((iq, ita), 0.0)
        if iq not in results.weighted_magnetic_moments:
            results.weighted_magnetic_moments[iq] = 0.0
        results.weighted_magnetic_moments[iq] += magm * conc
    
    # Extract total FCD magnetic moment
    for line in lines:
        if 'Total FCD magnetic moment per unit cell' in line:
            match = re.search(r'([-\d.]+)\s+mu_B', line)
            if match:
                results.total_magnetic_moment = float(match.group(1))
    
    # Extract energy by functional for each atom with IQ and ITA
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Look for atom section headers
        if 'IQ =' in line and 'ITA =' in line and 'CONC =' in line:
            # Extract IQ, ITA, and atom name
            iq_match = re.search(r'IQ\s+=\s+(\d+)', line)
            ita_match = re.search(r'ITA\s+=\s+(\d+)', line)
            atom_match = re.search(r'\((\w+)\s*\)', line)
            
            if iq_match and ita_match and atom_match:
                iq = int(iq_match.group(1))
                ita = int(ita_match.group(1))
                atom = atom_match.group(1)
                
                atom_key = (iq, ita, atom)
                
                # Parse energy values
                results.energies_by_functional[atom_key] = {}
                
                # Look ahead for energy lines
                for j in range(i+1, min(i+20, len(lines))):
                    energy_line = lines[j]
                    
                    # Extract LDA, GGA, LAG total energies
                    if 'Tot LDA' in energy_line:
                        match = re.search(r'Tot LDA\s+([-\d.]+)', energy_line)
                        if match:
                            results.energies_by_functional[atom_key]['LDA'] = float(match.group(1))
                    
                    elif 'Tot GGA' in energy_line:
                        match = re.search(r'Tot GGA\s+([-\d.]+)', energy_line)
                        if match:
                            results.energies_by_functional[atom_key]['GGA'] = float(match.group(1))
                    
                    elif 'Tot LAG' in energy_line:
                        match = re.search(r'Tot LAG\s+([-\d.]+)', energy_line)
                        if match:
                            results.energies_by_functional[atom_key]['LAG'] = float(match.group(1))
        
        # Extract total system energies
        if '*Total energy:' in line:
            for j in range(i+1, min(i+15, len(lines))):
                energy_line = lines[j]
                
                if 'TOT-LDA' in energy_line:
                    match = re.search(r'TOT-LDA\s+([-\d.]+)', energy_line)
                    if match:
                        if 'system' not in results.energies_by_functional:
                            results.energies_by_functional['system'] = {}
                        results.energies_by_functional['system']['LDA'] = float(match.group(1))
                
                elif 'TOT-GGA' in energy_line:
                    match = re.search(r'TOT-GGA\s+([-\d.]+)', energy_line)
                    if match:
                        if 'system' not in results.energies_by_functional:
                            results.energies_by_functional['system'] = {}
                        results.energies_by_functional['system']['GGA'] = float(match.group(1))
                
                elif 'TOT-LAG' in energy_line:
                    match = re.search(r'TOT-LAG\s+([-\d.]+)', energy_line)
                    if match:
                        if 'system' not in results.energies_by_functional:
                            results.energies_by_functional['system'] = {}
                        results.energies_by_functional['system']['LAG'] = float(match.group(1))
        
        i += 1
    
    return results


def generate_report(kgrn_results: EMTOResults, kfcd_results: EMTOResults) -> str:
    """Generate a comprehensive report from KGRN and KFCD results."""
    
    report = []
    report.append("="*80)
    report.append("EMTO CALCULATION RESULTS REPORT")
    report.append("="*80)
    
    # IQ to Element mapping (from KFCD)
    if kfcd_results.iq_to_element:
        report.append("\n### IQ TO ELEMENT MAPPING")
        report.append("-"*80)
        for iq, element in sorted(kfcd_results.iq_to_element.items()):
            report.append(f"IQ={iq}: {element}")

    # Concentrations (from KFCD)
    if kfcd_results.concentrations:
        report.append("\n### CONCENTRATIONS")
        report.append("-"*80)
        for (iq, ita), conc_val in sorted(kfcd_results.concentrations.items()):
            element = kfcd_results.iq_to_element.get(iq, "?")
            report.append(f"IQ={iq} ({element}), ITA={ita}: {conc_val:.4f}")
    
    # Convergence History
    if kgrn_results.iterations:
        report.append("\n### CONVERGENCE HISTORY (KGRN)")
        report.append("-"*80)
        report.append(f"\n{'Iter':>4} {'Energy (Ry/site)':>18} {'Error':>12} {'EF (Ry)':>10} "
                     f"{'Total Magm (μB)':>16}")
        report.append("-"*80)
        
        for iter_data in kgrn_results.iterations:
            report.append(f"{iter_data.iteration:>4} {iter_data.energy:>18.8f} "
                         f"{iter_data.error:>12.8f} {iter_data.fermi_energy:>10.6f} "
                         f"{iter_data.total_magnetic_moment:>16.4f}")
        
        # Summary statistics
        if len(kgrn_results.iterations) > 0:
            first_iter = kgrn_results.iterations[0]
            last_iter = kgrn_results.iterations[-1]
            energy_change = last_iter.energy - first_iter.energy
            magm_change = last_iter.total_magnetic_moment - first_iter.total_magnetic_moment
            
            report.append("-"*80)
            report.append(f"Total iterations: {len(kgrn_results.iterations)}")
            report.append(f"Energy change:    {energy_change:18.8f} Ry/site")
            report.append(f"Magm change:      {magm_change:18.4f} μB")
            report.append(f"Final error:      {last_iter.error:18.8f}")
        
        # Per-atom magnetic moment evolution (raw values)
        report.append("\n### MAGNETIC MOMENT EVOLUTION (RAW VALUES)")
        report.append("-"*80)
        
        if kgrn_results.iterations and kgrn_results.iterations[0].magnetic_moments:
            n_atoms = len(kgrn_results.iterations[0].magnetic_moments)
            
            # Header
            header = f"{'Iter':>4} "
            for i in range(n_atoms):
                header += f"{'Site'+str(i+1)+' (μB)':>14} "
            header += f"{'Total (μB)':>14}"
            report.append(header)
            report.append("-"*80)
            
            # Data rows
            for iter_data in kgrn_results.iterations:
                row = f"{iter_data.iteration:>4} "
                for magm in iter_data.magnetic_moments:
                    row += f"{magm:>14.4f} "
                row += f"{iter_data.total_magnetic_moment:>14.4f}"
                report.append(row)
        
        # Weighted magnetic moment evolution per unique IQ
        if kgrn_results.iterations and kgrn_results.iterations[0].weighted_magnetic_moments:
            report.append("\n### WEIGHTED MAGNETIC MOMENT EVOLUTION PER IQ")
            report.append("-"*80)

            # Get all unique IQs
            all_iqs = sorted(set(iq for iter_data in kgrn_results.iterations
                               for iq in iter_data.weighted_magnetic_moments.keys()))

            # Header
            header = f"{'Iter':>4} "
            for iq in all_iqs:
                element = kfcd_results.iq_to_element.get(iq, "?")
                header += f"{'IQ'+str(iq)+f' ({element})':>18} "
            report.append(header)
            report.append("-"*80)

            # Data rows
            for iter_data in kgrn_results.iterations:
                row = f"{iter_data.iteration:>4} "
                for iq in all_iqs:
                    magm = iter_data.weighted_magnetic_moments.get(iq, 0.0)
                    row += f"{magm:>18.4f} "
                report.append(row)
    
    # Final Convergence Information
    report.append("\n### FINAL CONVERGENCE VALUES (KGRN)")
    report.append("-"*80)
    if kgrn_results.total_energy:
        report.append(f"Total Energy:    {kgrn_results.total_energy:15.6f} Ry/site")
    if kgrn_results.free_energy:
        report.append(f"Free Energy:     {kgrn_results.free_energy:15.6f} Ry/site")
    if kgrn_results.kinetic_energy:
        report.append(f"Kinetic Energy:  {kgrn_results.kinetic_energy:15.6f} Ry")
    
    # Final Magnetic Moments (from KFCD)
    report.append("\n### FINAL MAGNETIC MOMENTS")
    report.append("-"*80)

    if kfcd_results.magnetic_moments:
        report.append("\nPer IQ, ITA, atom:")
        for (iq, ita, atom), moment in sorted(kfcd_results.magnetic_moments.items()):
            conc = kfcd_results.concentrations.get((iq, ita), 0.0)
            report.append(f"  IQ={iq}, ITA={ita} ({atom:>2s}), CONC={conc:.2f}: {moment:8.4f} μB")

    if kfcd_results.weighted_magnetic_moments:
        report.append("\nWeighted Magnetic Moments per IQ:")
        for iq, moment in sorted(kfcd_results.weighted_magnetic_moments.items()):
            element = kfcd_results.iq_to_element.get(iq, "?")
            report.append(f"  IQ={iq} ({element}): {moment:8.4f} μB")
    
    if kfcd_results.total_magnetic_moment:
        report.append(f"\nTotal Magnetic Moment (KFCD): {kfcd_results.total_magnetic_moment:8.4f} μB")
        
        # Verify calculation
        if kfcd_results.weighted_magnetic_moments:
            calculated_total = sum(kfcd_results.weighted_magnetic_moments.values())
            report.append(f"Calculated from weighted sum:  {calculated_total:8.4f} μB")
    
    # Energy by Functional
    report.append("\n### ENERGIES BY FUNCTIONAL (KFCD)")
    report.append("-"*80)
    
    # System total energies
    if 'system' in kfcd_results.energies_by_functional:
        report.append("\nTotal System Energies:")
        for functional, energy in kfcd_results.energies_by_functional['system'].items():
            report.append(f"  {functional:>6s}: {energy:15.6f} Ry")
    
    # Per-atom energies
    report.append("\nPer-Site Energies:")
    
    # Separate system energies from atom energies
    atom_energies = {k: v for k, v in kfcd_results.energies_by_functional.items() 
                     if k != 'system' and isinstance(k, tuple)}
    
    for key in sorted(atom_energies.keys()):
        functionals = atom_energies[key]
        if len(key) == 3:
            iq, ita, atom = key
            report.append(f"\n  IQ={iq}, ITA={ita} ({atom}):")
        else:
            report.append(f"\n  {key}:")
        for functional, energy in functionals.items():
            report.append(f"    {functional:>6s}: {energy:15.6f} Ry")
    
    # System Composition (from KFCD)
    report.append("\n### SYSTEM COMPOSITION")
    report.append("-"*80)
    if kfcd_results.atoms:
        for iq, ita, atom in sorted(kfcd_results.atoms):
            conc = kfcd_results.concentrations.get((iq, ita), 0.0)
            report.append(f"  IQ={iq}, ITA={ita}: {atom} (CONC={conc:.2f})")
    
    report.append("\n" + "="*80)
    report.append("\n")
    
    return "\n".join(report)


def parse_emto_output(kgrn_file: str, kfcd_file: str):
    """
    Main function to parse EMTO output files and generate report.
    
    Args:
        kgrn_file: Path to KGRN .prn output file
        kfcd_file: Path to KFCD .prn output file
    
    Returns:
        Tuple of (report string, kgrn_results, kfcd_results)
    """
    # Parse KFCD first to get concentrations, atoms, and IQ->element mapping
    kfcd_results = parse_kfcd(kfcd_file)

    # Parse KGRN with data from KFCD
    kgrn_results = parse_kgrn(kgrn_file,
                              concentrations=kfcd_results.concentrations,
                              iq_to_element=kfcd_results.iq_to_element,
                              atoms=kfcd_results.atoms)
    
    return generate_report(kgrn_results, kfcd_results), kgrn_results, kfcd_results


def save_report(report: str, output_file: str) -> None:
    """
    Save the report to a file.
    
    Args:
        report: Report string to save
        output_file: Path to output file
    """
    with open(output_file, 'w') as f:
        f.write(report)
    print(f"Report saved to: {output_file}")


if __name__ == "__main__":
    # Example usage
    kgrn_file = "fept_opt_kgrn.prn"
    kfcd_file = "fept_opt_fcd.prn"
    
    # Generate and print report
    report, kgrn, kfcd = parse_emto_output(kgrn_file, kfcd_file)
    print(report)
    
    # Save to file
    # save_report(report, "emto_report.txt")