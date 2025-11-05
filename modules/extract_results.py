import re
from dataclasses import dataclass
from typing import Dict, List, Optional


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


@dataclass
class EMTOResults:
    """Container for EMTO calculation results."""
    
    # Convergence data
    total_energy: Optional[float] = None
    free_energy: Optional[float] = None
    kinetic_energy: Optional[float] = None
    
    # Iteration history
    iterations: List[IterationData] = None
    
    # Magnetic moments
    magnetic_moments: Dict[str, float] = None  # Per atom type
    total_magnetic_moment: Optional[float] = None
    
    # Energy by functional (from KFCD)
    energies_by_functional: Dict[str, Dict[str, float]] = None
    
    # Additional info
    atoms: List[str] = None
    
    def __post_init__(self):
        if self.iterations is None:
            self.iterations = []
        if self.magnetic_moments is None:
            self.magnetic_moments = {}
        if self.energies_by_functional is None:
            self.energies_by_functional = {}
        if self.atoms is None:
            self.atoms = []


def parse_kgrn(filepath: str) -> EMTOResults:
    """Parse KGRN output file (.prn)."""
    
    results = EMTOResults()
    
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
                if i + 2 < len(lines):
                    magm_line = lines[i + 2]
                    if 'Magm.=' in magm_line:
                        magm_matches = re.findall(r'([-\d.]+)', magm_line.split('Magm.=')[1])
                        magnetic_moments = [float(m) for m in magm_matches]
                    else:
                        magnetic_moments = []
                    
                    # Total magnetic moment
                    if i + 3 < len(lines) and 'Total magm.' in lines[i + 3]:
                        total_match = re.search(r'Total magm\.=\s+([-\d.]+)', lines[i + 3])
                        if total_match:
                            total_magm = float(total_match.group(1))
                
                iter_data = IterationData(
                    iteration=iteration,
                    energy=energy,
                    error=error,
                    fermi_energy=fermi_energy,
                    dos_ef=dos_ef,
                    magnetic_moments=magnetic_moments,
                    total_magnetic_moment=total_magm
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
    
    # Extract final magnetic moments per atom
    atom_section = re.finditer(r'Atom:(\w+)\s+.*?Magn\. mom\.\s+=\s+([-\d.]+)', content, re.DOTALL)
    for match in atom_section:
        atom = match.group(1)
        mag_moment = float(match.group(2))
        results.magnetic_moments[atom] = mag_moment
        if atom not in results.atoms:
            results.atoms.append(atom)
    
    return results


def parse_kfcd(filepath: str) -> EMTOResults:
    """Parse KFCD output file (.prn)."""
    
    results = EMTOResults()
    
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    # Extract magnetic moments per IQ
    for i, line in enumerate(lines):
        if 'Magnetic moment for IQ' in line:
            match = re.search(r'IQ\s+=\s+(\d+)\s+is\s+([-\d.]+)', line)
            if match:
                iq = int(match.group(1))
                mag_moment = float(match.group(2))
                results.magnetic_moments[f'IQ{iq}'] = mag_moment
    
    # Extract total FCD magnetic moment
    for line in lines:
        if 'Total FCD magnetic moment per unit cell' in line:
            match = re.search(r'([-\d.]+)\s+mu_B', line)
            if match:
                results.total_magnetic_moment = float(match.group(1))
    
    # Extract energy by functional for each atom
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Look for atom section headers
        if 'IQ =' in line and 'ITA =' in line and 'CONC =' in line:
            # Extract atom name
            atom_match = re.search(r'\((\w+)\s*\)', line)
            if atom_match:
                atom = atom_match.group(1)
                iq_match = re.search(r'IQ\s+=\s+(\d+)', line)
                iq = iq_match.group(1) if iq_match else 'unknown'
                
                if atom not in results.atoms:
                    results.atoms.append(atom)
                
                # Parse energy values
                atom_key = f'{atom}_IQ{iq}'
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
        
        # Per-atom magnetic moment evolution
        report.append("\n### MAGNETIC MOMENT EVOLUTION PER ATOM")
        report.append("-"*80)
        
        # Determine number of atoms from first iteration
        if kgrn_results.iterations and kgrn_results.iterations[0].magnetic_moments:
            n_atoms = len(kgrn_results.iterations[0].magnetic_moments)
            
            # Header
            header = f"{'Iter':>4} "
            for i in range(n_atoms):
                header += f"{'Atom'+str(i+1)+' (μB)':>14} "
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
    
    # Final Convergence Information
    report.append("\n### FINAL CONVERGENCE VALUES (KGRN)")
    report.append("-"*80)
    if kgrn_results.total_energy:
        report.append(f"Total Energy:    {kgrn_results.total_energy:15.6f} Ry/site")
    if kgrn_results.free_energy:
        report.append(f"Free Energy:     {kgrn_results.free_energy:15.6f} Ry/site")
    if kgrn_results.kinetic_energy:
        report.append(f"Kinetic Energy:  {kgrn_results.kinetic_energy:15.6f} Ry")
    
    # Final Magnetic Moments
    report.append("\n### FINAL MAGNETIC MOMENTS")
    report.append("-"*80)
    
    if kgrn_results.magnetic_moments:
        report.append("\nFrom KGRN (per atom type):")
        for atom, moment in kgrn_results.magnetic_moments.items():
            report.append(f"  {atom:>6s}: {moment:8.4f} μB")
    
    if kfcd_results.magnetic_moments:
        report.append("\nFrom KFCD (per site):")
        for site, moment in kfcd_results.magnetic_moments.items():
            report.append(f"  {site:>6s}: {moment:8.4f} μB")
    
    if kfcd_results.total_magnetic_moment:
        report.append(f"\nTotal Magnetic Moment (KFCD): {kfcd_results.total_magnetic_moment:8.4f} μB")
    
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
    for site, functionals in kfcd_results.energies_by_functional.items():
        if site != 'system':
            report.append(f"\n  {site}:")
            for functional, energy in functionals.items():
                report.append(f"    {functional:>6s}: {energy:15.6f} Ry")
    
    # Atoms present
    report.append("\n### SYSTEM COMPOSITION")
    report.append("-"*80)
    all_atoms = sorted(set(kgrn_results.atoms + kfcd_results.atoms))
    report.append(f"Atoms: {', '.join(all_atoms)}")
    
    report.append("\n" + "="*80)
    report.append("\n")
    
    return "\n".join(report)


def parse_emto_output(kgrn_file: str, kfcd_file: str) -> str:
    """
    Main function to parse EMTO output files and generate report.
    
    Args:
        kgrn_file: Path to KGRN .prn output file
        kfcd_file: Path to KFCD .prn output file
    
    Returns:
        Formatted report string
    """
    kgrn_results = parse_kgrn(kgrn_file)
    kfcd_results = parse_kfcd(kfcd_file)
    
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
    report = parse_emto_output(kgrn_file, kfcd_file)
    print(report)
    
    # Save to file
    # save_report(report, "emto_report.txt")