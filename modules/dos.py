"""
DOS Parser and Plotter Module

Parse and plot Density of States (DOS) data from EMTO output files.
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, Optional, List, Tuple


class DOSParser:
    """Parser for DOS files from EMTO calculations."""
    
    def __init__(self, filename: str):
        """
        Initialize parser with DOS file.
        
        Parameters
        ----------
        filename : str
            Path to the DOS file
        """
        self.filename = filename
        self.atom_info = []  # Will store (atom_number, element, sublattice) tuples
        self.data = self._parse_file()
    
    def _parse_file(self) -> Dict:
        """Parse the entire DOS file and organize data."""
        with open(self.filename, 'r') as f:
            lines = f.readlines()
        
        data = {
            'total_down': None,
            'total_up': None,
        }
        
        atom_counter_down = 0  # Counter for DOWN spin atoms
        atom_counter_up = 0    # Counter for UP spin atoms (should match down)
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Total DOS DOWN
            if 'Total DOS and NOS and partial (IT) DOSDOWN' in line:
                i += 4  # Skip to data (header + empty line)
                data['total_down'] = self._read_data_block(lines, i)
            
            # Total DOS UP
            elif 'Total DOS and NOS and partial (IT) DOSUP' in line:
                i += 4
                data['total_up'] = self._read_data_block(lines, i)
                # Reset counter for UP spin section
                atom_counter_up = 0
            
            # Generic sublattice parsing: "Sublattice  X Atom YY   spin DOWN/UP"
            elif 'Sublattice' in line and 'Atom' in line:
                parts = line.split()
                sublattice_num = None
                atom_name = None
                spin = None
                
                # Parse: Sublattice  1 Atom Pt   spin DOWN
                for idx, part in enumerate(parts):
                    if part == 'Sublattice' and idx + 1 < len(parts):
                        try:
                            sublattice_num = int(parts[idx + 1])
                        except ValueError:
                            pass
                    if part == 'Atom' and idx + 1 < len(parts):
                        atom_name = parts[idx + 1].lower()
                    if part == 'spin' and idx + 1 < len(parts):
                        spin = parts[idx + 1].lower()
                
                if atom_name and spin and sublattice_num:
                    # Increment appropriate counter
                    if spin == 'down':
                        atom_counter_down += 1
                        current_atom = atom_counter_down
                        self.atom_info.append((current_atom, atom_name, sublattice_num))
                    else:  # spin == 'up'
                        atom_counter_up += 1
                        current_atom = atom_counter_up
                    
                    key = f'atom_{current_atom}_{spin}'
                    
                    i += 4  # Skip header lines + empty line
                    data[key] = self._read_data_block(lines, i)
            
            i += 1
        
        return data
    
    def _read_data_block(self, lines: List[str], start_idx: int) -> np.ndarray:
        """Read a data block until empty line or TNOS."""
        data = []
        i = start_idx
        while i < len(lines):
            line = lines[i].strip()
            if not line or 'TNOS' in line or 'Sublattice' in line or 'Total DOS' in line:
                break
            try:
                vals = line.split()
                data.append([float(x) for x in vals])
            except (ValueError, IndexError):
                break
            i += 1
        return np.array(data) if data else None
    
    def get_total_dos(self, spin_polarized: bool = True) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Get total DOS.
        
        Parameters
        ----------
        spin_polarized : bool
            If True, return separate spin channels. If False, sum them.
        
        Returns
        -------
        dos_down : np.ndarray
            Spin down DOS (or total if spin_polarized=False)
        dos_up : np.ndarray or None
            Spin up DOS (None if spin_polarized=False)
        """
        if spin_polarized:
            return self.data['total_down'], self.data['total_up']
        else:
            total = self.data['total_down'].copy()
            if self.data['total_up'] is not None:
                total[:, 1:] += self.data['total_up'][:, 1:]
            return total, None
    
    def get_atom_dos(self, atom_number: int, spin_polarized: bool = True) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Get atom-resolved DOS by sequential atom number.
        
        Parameters
        ----------
        atom_number : int
            Sequential atom number (1, 2, 3, 4...)
        spin_polarized : bool
            If True, return separate spin channels. If False, sum them.
        
        Returns
        -------
        dos_down : np.ndarray
            Spin down DOS (or total if spin_polarized=False)
            Columns: [E, Total, s, p, d]
        dos_up : np.ndarray or None
            Spin up DOS (None if spin_polarized=False)
            Columns: [E, Total, s, p, d]
        """
        down_key = f'atom_{atom_number}_down'
        up_key = f'atom_{atom_number}_up'
        
        if down_key not in self.data:
            available = [info[0] for info in self.atom_info]
            raise KeyError(f"Atom {atom_number} not found. Available atoms: {available}")
        
        if spin_polarized:
            return self.data[down_key], self.data.get(up_key, None)
        else:
            total = self.data[down_key].copy()
            if up_key in self.data and self.data[up_key] is not None:
                total[:, 1:] += self.data[up_key][:, 1:]
            return total, None
    
    def get_orbital_dos(self, atom_number: int, orbital: str = 's', 
                       spin_polarized: bool = True) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Get orbital-resolved DOS for a specific atom.
        
        Parameters
        ----------
        atom_number : int
            Sequential atom number (1, 2, 3, 4...)
        orbital : str
            Orbital: 's', 'p', or 'd'
        spin_polarized : bool
            If True, return separate spin channels. If False, sum them.
        
        Returns
        -------
        dos_down : np.ndarray
            Spin down DOS, columns: [E, orbital_DOS]
        dos_up : np.ndarray or None
            Spin up DOS (None if spin_polarized=False)
        """
        dos_down, dos_up = self.get_atom_dos(atom_number, spin_polarized=True)
        
        orbital_map = {'s': 2, 'p': 3, 'd': 4}
        if orbital not in orbital_map:
            raise ValueError(f"Orbital must be 's', 'p', or 'd', got '{orbital}'")
        
        idx = orbital_map[orbital]
        
        if spin_polarized and dos_up is not None:
            return np.column_stack([dos_down[:, 0], dos_down[:, idx]]), \
                   np.column_stack([dos_up[:, 0], dos_up[:, idx]])
        else:
            orbital_sum = dos_down[:, idx].copy()
            if dos_up is not None:
                orbital_sum += dos_up[:, idx]
            return np.column_stack([dos_down[:, 0], orbital_sum]), None
    
    def get_sublattice_dos(self, sublattice: int, spin_polarized: bool = True) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Get DOS summed over all atoms on the same sublattice.
        
        Parameters
        ----------
        sublattice : int
            Sublattice index (1, 2, ...)
        spin_polarized : bool
            If True, return separate spin channels. If False, sum them.
        
        Returns
        -------
        dos_down : np.ndarray
            Spin down DOS (or total if spin_polarized=False)
            Columns: [E, Total, s, p, d]
        dos_up : np.ndarray or None
            Spin up DOS (None if spin_polarized=False)
            Columns: [E, Total, s, p, d]
        """
        # Find all atoms on this sublattice
        atoms_on_sublattice = [atom_num for atom_num, elem, sub in self.atom_info if sub == sublattice]
        
        if not atoms_on_sublattice:
            available_sublattices = sorted(set(sub for _, _, sub in self.atom_info))
            raise KeyError(f"Sublattice {sublattice} not found. Available sublattices: {available_sublattices}")
        
        # Sum over all atoms on this sublattice
        dos_down_sum = None
        dos_up_sum = None
        
        for atom_num in atoms_on_sublattice:
            dos_down, dos_up = self.get_atom_dos(atom_num, spin_polarized=True)
            
            if dos_down_sum is None:
                dos_down_sum = dos_down.copy()
                if dos_up is not None:
                    dos_up_sum = dos_up.copy()
            else:
                dos_down_sum[:, 1:] += dos_down[:, 1:]
                if dos_up is not None and dos_up_sum is not None:
                    dos_up_sum[:, 1:] += dos_up[:, 1:]
        
        if spin_polarized:
            return dos_down_sum, dos_up_sum
        else:
            total = dos_down_sum.copy()
            if dos_up_sum is not None:
                total[:, 1:] += dos_up_sum[:, 1:]
            return total, None
    
    def list_atoms(self) -> List[Tuple[int, str, int]]:
        """
        Return list of atoms with their info.
        
        Returns
        -------
        list of tuples
            Each tuple is (atom_number, element, sublattice)
        """
        return self.atom_info
    
    def list_sublattices(self) -> List[int]:
        """Return list of unique sublattice indices."""
        return sorted(set(sub for _, _, sub in self.atom_info))


class DOSPlotter:
    """Plotter for DOS data."""
    
    def __init__(self, parser: DOSParser):
        """
        Initialize plotter with parsed data.
        
        Parameters
        ----------
        parser : DOSParser
            Parsed DOS data
        """
        self.parser = parser
    
    def plot_total(self, spin_polarized: bool = True, figsize: Tuple[float, float] = (8, 6),
                   save: Optional[str] = None, show: bool = True):
        """
        Plot total DOS.
        
        Parameters
        ----------
        spin_polarized : bool
            If True, plot spin-up and spin-down separately
        figsize : tuple
            Figure size (width, height)
        save : str, optional
            Filename to save plot
        show : bool
            Whether to display the plot
        """
        dos_down, dos_up = self.parser.get_total_dos(spin_polarized)
        
        fig, ax = plt.subplots(figsize=figsize)
        
        if spin_polarized and dos_up is not None:
            ax.plot(dos_up[:, 0], dos_up[:, 1], label='Total', color='blue', linestyle='-')
            ax.plot(dos_down[:, 0], -dos_down[:, 1], color='blue', linestyle='--')
            ax.axhline(0, color='black', linewidth=0.5)
            ax.set_ylabel('DOS (states/Ry)')
        else:
            ax.plot(dos_down[:, 0], dos_down[:, 1], label='Total', color='black')
            ax.set_ylabel('DOS (states/Ry)')
        
        ax.axvline(0, color='gray', linestyle='--', alpha=0.5, label='E_F')
        ax.set_xlabel('Energy (Ry)')
        ax.legend()
        ax.set_title('Total DOS')
        plt.tight_layout()
        
        if save:
            plt.savefig(save, dpi=300)
        if show:
            plt.show()
        
        return fig, ax
    
    def plot_partial(self, spin_polarized: bool = True, figsize: Tuple[float, float] = (8, 6),
                     save: Optional[str] = None, show: bool = True):
        """
        Plot partial DOS (IT contributions).
        
        Parameters
        ----------
        spin_polarized : bool
            If True, plot spin-up and spin-down separately
        figsize : tuple
            Figure size (width, height)
        save : str, optional
            Filename to save plot
        show : bool
            Whether to display the plot
        """
        dos_down, dos_up = self.parser.get_total_dos(spin_polarized)
        
        fig, ax = plt.subplots(figsize=figsize)
        
        if spin_polarized and dos_up is not None:
            ax.plot(dos_up[:, 0], dos_up[:, 3], label='IT 1', linestyle='-', color='C0')
            ax.plot(dos_up[:, 0], dos_up[:, 4], label='IT 2', linestyle='-', color='C1')
            ax.plot(dos_down[:, 0], -dos_down[:, 3], linestyle='--', color='C0')
            ax.plot(dos_down[:, 0], -dos_down[:, 4], linestyle='--', color='C1')
            ax.axhline(0, color='black', linewidth=0.5)
        else:
            ax.plot(dos_down[:, 0], dos_down[:, 3], label='IT 1', color='C0')
            ax.plot(dos_down[:, 0], dos_down[:, 4], label='IT 2', color='C1')
        
        ax.axvline(0, color='gray', linestyle='--', alpha=0.5, label='E_F')
        ax.set_xlabel('Energy (Ry)')
        ax.set_ylabel('DOS (states/Ry)')
        ax.legend()
        ax.set_title('Partial DOS (IT contributions)')
        plt.tight_layout()
        
        if save:
            plt.savefig(save, dpi=300)
        if show:
            plt.show()
        
        return fig, ax
    
    def plot_atom(self, atom_number: int, orbital_resolved: bool = False, 
                  spin_polarized: bool = True, figsize: Tuple[float, float] = (8, 6),
                  save: Optional[str] = None, show: bool = True):
        """
        Plot atom-resolved DOS.
        
        Parameters
        ----------
        atom_number : int
            Sequential atom number (1, 2, 3, 4...)
        orbital_resolved : bool
            If True, plot s, p, d orbitals separately
        spin_polarized : bool
            If True, plot spin-up and spin-down separately
        figsize : tuple
            Figure size (width, height)
        save : str, optional
            Filename to save plot
        show : bool
            Whether to display the plot
        """
        dos_down, dos_up = self.parser.get_atom_dos(atom_number, spin_polarized)
        
        # Get atom info for title
        atom_info = [info for info in self.parser.atom_info if info[0] == atom_number][0]
        _, element, sublattice = atom_info
        
        fig, ax = plt.subplots(figsize=figsize)
        
        if orbital_resolved:
            orbitals = ['s', 'p', 'd']
            colors = ['C0', 'C1', 'C2']
            if spin_polarized and dos_up is not None:
                for i, (orb, color) in enumerate(zip(orbitals, colors), start=2):
                    ax.plot(dos_up[:, 0], dos_up[:, i], label=orb, linestyle='-', color=color)
                    ax.plot(dos_down[:, 0], -dos_down[:, i], linestyle='--', color=color)
                ax.axhline(0, color='black', linewidth=0.5)
            else:
                for i, orb in enumerate(orbitals, start=2):
                    ax.plot(dos_down[:, 0], dos_down[:, i], label=orb)
        else:
            if spin_polarized and dos_up is not None:
                ax.plot(dos_up[:, 0], dos_up[:, 1], label='Total', color='blue', linestyle='-')
                ax.plot(dos_down[:, 0], -dos_down[:, 1], color='blue', linestyle='--')
                ax.axhline(0, color='black', linewidth=0.5)
            else:
                ax.plot(dos_down[:, 0], dos_down[:, 1], label='Total', color='black')
        
        ax.axvline(0, color='gray', linestyle='--', alpha=0.5, label='E_F')
        ax.set_xlabel('Energy (Ry)')
        ax.set_ylabel('DOS (states/Ry)')
        ax.legend()
        ax.set_title(f'Atom {atom_number} ({element.upper()}, sublattice {sublattice}) DOS')
        plt.tight_layout()
        
        if save:
            plt.savefig(save, dpi=300)
        if show:
            plt.show()
        
        return fig, ax
    
    def plot_orbital(self, atom_number: int, orbital: str = 's',
                    spin_polarized: bool = True, figsize: Tuple[float, float] = (8, 6),
                    save: Optional[str] = None, show: bool = True):
        """
        Plot specific orbital DOS.
        
        Parameters
        ----------
        atom_number : int
            Sequential atom number (1, 2, 3, 4...)
        orbital : str
            Orbital: 's', 'p', or 'd'
        spin_polarized : bool
            If True, plot spin-up and spin-down separately
        figsize : tuple
            Figure size (width, height)
        save : str, optional
            Filename to save plot
        show : bool
            Whether to display the plot
        """
        dos_down, dos_up = self.parser.get_orbital_dos(atom_number, orbital, spin_polarized)
        
        # Get atom info for title
        atom_info = [info for info in self.parser.atom_info if info[0] == atom_number][0]
        _, element, sublattice = atom_info
        
        fig, ax = plt.subplots(figsize=figsize)
        
        if spin_polarized and dos_up is not None:
            ax.plot(dos_up[:, 0], dos_up[:, 1], label=f'{orbital}', color='blue', linestyle='-')
            ax.plot(dos_down[:, 0], -dos_down[:, 1], color='blue', linestyle='--')
            ax.axhline(0, color='black', linewidth=0.5)
        else:
            ax.plot(dos_down[:, 0], dos_down[:, 1], label=f'{orbital}', color='black')
        
        ax.axvline(0, color='gray', linestyle='--', alpha=0.5, label='E_F')
        ax.set_xlabel('Energy (Ry)')
        ax.set_ylabel('DOS (states/Ry)')
        ax.legend()
        ax.set_title(f'Atom {atom_number} ({element.upper()}) {orbital}-orbital DOS')
        plt.tight_layout()
        
        if save:
            plt.savefig(save, dpi=300)
        if show:
            plt.show()
        
        return fig, ax
    
    def plot_sublattice(self, sublattice: int, orbital_resolved: bool = False,
                    spin_polarized: bool = True, figsize: Tuple[float, float] = (8, 6),
                    save: Optional[str] = None, show: bool = True):
        """
        Plot DOS summed over all atoms on the same sublattice.
        
        Parameters
        ----------
        sublattice : int
            Sublattice index (1, 2, ...)
        orbital_resolved : bool
            If True, plot s, p, d orbitals separately
        spin_polarized : bool
            If True, plot spin-up and spin-down separately
        figsize : tuple
            Figure size (width, height)
        save : str, optional
            Filename to save plot
        show : bool
            Whether to display the plot
        """
        dos_down, dos_up = self.parser.get_sublattice_dos(sublattice, spin_polarized=True)
        
        fig, ax = plt.subplots(figsize=figsize)
        
        if orbital_resolved:
            orbitals = ['s', 'p', 'd']
            colors = ['C0', 'C1', 'C2']
            if spin_polarized and dos_up is not None:
                for i, (orb, color) in enumerate(zip(orbitals, colors), start=2):
                    ax.plot(dos_up[:, 0], dos_up[:, i], label=orb, linestyle='-', color=color)
                    ax.plot(dos_down[:, 0], -dos_down[:, i], linestyle='--', color=color)
                ax.axhline(0, color='black', linewidth=0.5)
            else:
                for i, orb in enumerate(orbitals, start=2):
                    ax.plot(dos_down[:, 0], dos_down[:, i], label=orb)
        else:
            if spin_polarized and dos_up is not None:
                ax.plot(dos_up[:, 0], dos_up[:, 1], label='Total', color='blue', linestyle='-')
                ax.plot(dos_down[:, 0], -dos_down[:, 1], color='blue', linestyle='--')
                ax.axhline(0, color='black', linewidth=0.5)
            else:
                ax.plot(dos_down[:, 0], dos_down[:, 1], label='Total', color='black')
        
        ax.axvline(0, color='gray', linestyle='--', alpha=0.5, label='E_F')
        ax.set_xlabel('Energy (Ry)')
        ax.set_ylabel('DOS (states/Ry)')
        ax.legend()
        ax.set_title(f'Sublattice {sublattice} DOS (all atoms)')
        plt.tight_layout()
        
        if save:
            plt.savefig(save, dpi=300)
        if show:
            plt.show()
        
        return fig, ax


# Convenience function
def plot_dos(filename: str, plot_type: str = 'total', atom_number: Optional[int] = None,
             sublattice: Optional[int] = None, 
             orbital: Optional[str] = None, orbital_resolved: bool = False, 
             spin_polarized: bool = True, figsize: Tuple[float, float] = (8, 6), 
             save: Optional[str] = None, show: bool = True):
    """
    Convenience function to parse and plot DOS in one call.
    
    Parameters
    ----------
    filename : str
        Path to DOS file
    plot_type : str
        'total', 'partial', 'atom', 'sublattice', or 'orbital'
    atom_number : int, optional
        For atom/orbital plots: sequential atom number (1, 2, 3, 4...)
    sublattice : int, optional
        For sublattice plots: sublattice index (sums all atoms on sublattice)
    orbital : str, optional
        For orbital plots: 's', 'p', or 'd'
    orbital_resolved : bool
        For atom/sublattice plots: show s, p, d separately
    spin_polarized : bool
        Plot spin channels separately
    figsize : tuple
        Figure size
    save : str, optional
        Save filename
    show : bool
        Display plot
    
    Returns
    -------
    fig, ax : matplotlib figure and axes
    """
    parser = DOSParser(filename)
    plotter = DOSPlotter(parser)
    
    if plot_type == 'total':
        return plotter.plot_total(spin_polarized, figsize, save, show)
    elif plot_type == 'partial':
        return plotter.plot_partial(spin_polarized, figsize, save, show)
    elif plot_type == 'atom':
        if atom_number is None:
            raise ValueError(f"Must specify atom_number. Available atoms: {parser.list_atoms()}")
        return plotter.plot_atom(atom_number, orbital_resolved, spin_polarized, figsize, save, show)
    elif plot_type == 'sublattice':
        if sublattice is None:
            raise ValueError(f"Must specify sublattice. Available sublattices: {parser.list_sublattices()}")
        return plotter.plot_sublattice(sublattice, orbital_resolved, spin_polarized, figsize, save, show)
    elif plot_type == 'orbital':
        if atom_number is None or orbital is None:
            raise ValueError(f"Must specify both atom_number and orbital. Available atoms: {parser.list_atoms()}")
        return plotter.plot_orbital(atom_number, orbital, spin_polarized, figsize, save, show)
    else:
        raise ValueError(f"Unknown plot_type: {plot_type}. Use 'total', 'partial', 'atom', 'sublattice', or 'orbital'")