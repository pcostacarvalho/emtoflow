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
        self.is_paramagnetic = False  # Flag to track paramagnetic vs spin-polarized
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
            
            # Total DOS UP+DOWN (paramagnetic)
            elif 'Total DOS and NOS and partial (IT) DOSUP+DOWN' in line:
                i += 4
                data['total_down'] = self._read_data_block(lines, i)
                data['total_up'] = None  # Mark as paramagnetic
                self.is_paramagnetic = True
            
            # Generic sublattice parsing: "Sublattice  X Atom YY   spin DOWN/UP/UP+DOWN"
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
                    # Handle paramagnetic case: 'up+down' -> treat as 'down' for consistency
                    if spin == 'up+down':
                        spin = 'down'
                        self.is_paramagnetic = True
                    
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
                # Convert **** (Fortran overflow) to NaN instead of breaking
                converted = []
                for x in vals:
                    if '*' in x:  # Handle ****, *********, etc.
                        converted.append(np.nan)
                    else:
                        converted.append(float(x))
                data.append(converted)
            except (ValueError, IndexError) as e:
                # Log warning but continue parsing
                import warnings
                warnings.warn(f"Error parsing line {i}: {line[:50]}... - {e}")
                break
            i += 1
        return np.array(data) if data else None

    def get_dos(self, data_type: str = 'total', sublattice: Optional[int] = None,
                spin_polarized: bool = True) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Get DOS data from the Total DOS sections.

        Reads directly from 'Total DOS and NOS and partial (IT)' sections.
        Column structure: [E, Total, NOS, IT1, IT2, IT3, ...]

        Parameters
        ----------
        data_type : str
            Type of data to extract:
            - 'total': Total DOS (column 1)
            - 'nos': Number of States (column 2)
            - 'sublattice': Sublattice/IT DOS (requires sublattice parameter)
        sublattice : int, optional
            Sublattice index (1, 2, 3, ...) - required when data_type='sublattice'
        spin_polarized : bool
            If True, return separate spin channels. If False, sum them.

        Returns
        -------
        dos_down : np.ndarray
            Spin down data, columns: [E, DOS_value]
        dos_up : np.ndarray or None
            Spin up data (None if spin_polarized=False)

        Examples
        --------
        >>> parser.get_dos('total')  # Get total DOS
        >>> parser.get_dos('nos')     # Get number of states
        >>> parser.get_dos('sublattice', sublattice=1)  # Get sublattice 1 DOS
        >>> parser.get_dos('sublattice', sublattice=2)  # Get sublattice 2 DOS
        """
        # Determine column index
        if data_type == 'total':
            col_idx = 1
        elif data_type == 'nos':
            col_idx = 2
        elif data_type == 'sublattice':
            if sublattice is None:
                raise ValueError("Must specify sublattice when data_type='sublattice'")
            # Validate data exists
            if self.data['total_down'] is None:
                raise ValueError("No DOS data found. File may be empty or unparseable.")
            # Validate sublattice exists
            num_sublattices = self.data['total_down'].shape[1] - 3  # Subtract E, Total, NOS
            if sublattice < 1 or sublattice > num_sublattices:
                raise KeyError(f"Sublattice {sublattice} not found. Available: 1-{num_sublattices}")
            # Column index: 2 (skip E, Total, NOS) + sublattice
            col_idx = 2 + sublattice
        else:
            raise ValueError(f"data_type must be 'total', 'nos', or 'sublattice', got '{data_type}'")

        # Validate data exists before accessing
        if self.data['total_down'] is None:
            raise ValueError("No DOS data found. File may be empty or unparseable.")

        # Extract energy and data columns
        dos_down = np.column_stack([
            self.data['total_down'][:, 0],      # Energy
            self.data['total_down'][:, col_idx]  # DOS value
        ])

        dos_up = None
        if self.data['total_up'] is not None:
            dos_up = np.column_stack([
                self.data['total_up'][:, 0],      # Energy
                self.data['total_up'][:, col_idx]  # DOS value
            ])

        if spin_polarized:
            return dos_down, dos_up
        else:
            total = dos_down.copy()
            if dos_up is not None:
                total[:, 1] += dos_up[:, 1]
            return total, None

    def get_ITA_dos(self, sublattice: int, ITA_index: int = 1, orbital: str = 'total',
                    sum_ITAs: bool = False, concentrations: Optional[List[float]] = None,
                    spin_polarized: bool = True) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Get DOS for a specific ITA (Interacting Type Atom) with orbital selection.

        Reads from ITA-specific sections:
        'Sublattice X Atom ELEMENT spin DOWN/UP'
        Column structure: [E, Total, s, p, d]

        Note: Each sublattice (IT) can have multiple ITAs representing different concentration
        components within the CPA. Use ITA_index to specify which ITA (1, 2, ...), or use
        sum_ITAs=True to compute concentration-weighted orbital-resolved sublattice DOS.

        Parameters
        ----------
        sublattice : int
            Sublattice (IT) index (1, 2, 3, ...)
        ITA_index : int
            Which ITA on this sublattice (1 = first occurrence, 2 = second, etc.)
            Ignored if sum_ITAs=True. Default: 1
        orbital : str
            Orbital to extract:
            - 'total': Total DOS for this ITA (column 1)
            - 's': s-orbital DOS (column 2)
            - 'p': p-orbital DOS (column 3)
            - 'd': d-orbital DOS (column 4)
        sum_ITAs : bool
            If True, compute concentration-weighted sum over all ITAs on this sublattice.
            Requires concentrations parameter. Default: False
        concentrations : list of float, optional
            Concentration weights for each ITA when sum_ITAs=True.
            Must sum to 1.0 and have length equal to number of ITAs on this sublattice.
            Required when sum_ITAs=True.
            Example: [0.7, 0.3] for 2 ITAs on sublattice
        spin_polarized : bool
            If True, return separate spin channels. If False, sum them.

        Returns
        -------
        dos_down : np.ndarray
            Spin down data, columns: [E, DOS_value]
        dos_up : np.ndarray or None
            Spin up data (None if spin_polarized=False)

        Examples
        --------
        >>> parser.get_ITA_dos(sublattice=1, ITA_index=1, orbital='d')  # 1st Pt ITA, d-orbital
        >>> parser.get_ITA_dos(sublattice=1, ITA_index=2, orbital='d')  # 2nd Pt ITA, d-orbital
        >>> parser.get_ITA_dos(sublattice=2, ITA_index=1, orbital='s')  # 1st Fe ITA, s-orbital

        # Orbital-resolved sublattice DOS (weighted sum)
        >>> parser.get_ITA_dos(sublattice=1, orbital='d', sum_ITAs=True, concentrations=[0.7, 0.3])

        Notes
        -----
        When sum_ITAs=True and orbital='total', the weighted sum should match:
        get_dos('sublattice', sublattice=N) within numerical precision.
        """
        # Find all ITAs on this sublattice
        ITAs_on_sublattice = [(atom_num, elem) for atom_num, elem, sub in self.atom_info if sub == sublattice]

        if not ITAs_on_sublattice:
            available_sublattices = sorted(set(sub for _, _, sub in self.atom_info))
            raise KeyError(f"Sublattice {sublattice} not found. Available sublattices: {available_sublattices}")

        # Determine column index for orbital
        orbital_map = {
            'total': 1,
            's': 2,
            'p': 3,
            'd': 4
        }

        if orbital not in orbital_map:
            raise ValueError(f"orbital must be 'total', 's', 'p', or 'd', got '{orbital}'")

        col_idx = orbital_map[orbital]

        if sum_ITAs:
            # Concentration-weighted sum over all ITAs on this sublattice
            if concentrations is None:
                raise ValueError(
                    f"concentrations parameter is required when sum_ITAs=True. "
                    f"Sublattice {sublattice} has {len(ITAs_on_sublattice)} ITA(s)."
                )

            if len(concentrations) != len(ITAs_on_sublattice):
                raise ValueError(
                    f"concentrations length ({len(concentrations)}) must match number of ITAs "
                    f"on sublattice {sublattice} ({len(ITAs_on_sublattice)})"
                )

            if not np.isclose(sum(concentrations), 1.0):
                raise ValueError(
                    f"concentrations must sum to 1.0, got {sum(concentrations)}"
                )

            dos_down_sum = None
            dos_up_sum = None

            for (atom_num, _), conc in zip(ITAs_on_sublattice, concentrations):
                down_key = f'atom_{atom_num}_down'
                up_key = f'atom_{atom_num}_up'

                # Check for paramagnetic case: only 'down' key exists (contains combined data)
                if down_key not in self.data:
                    continue

                if dos_down_sum is None:
                    dos_down_sum = np.column_stack([
                        self.data[down_key][:, 0],
                        conc * self.data[down_key][:, col_idx]
                    ])
                    # For paramagnetic, up_key won't exist or will be None
                    if up_key in self.data and self.data[up_key] is not None:
                        dos_up_sum = np.column_stack([
                            self.data[up_key][:, 0],
                            conc * self.data[up_key][:, col_idx]
                        ])
                else:
                    dos_down_sum[:, 1] += conc * self.data[down_key][:, col_idx]
                    if up_key in self.data and self.data[up_key] is not None and dos_up_sum is not None:
                        dos_up_sum[:, 1] += conc * self.data[up_key][:, col_idx]

            if spin_polarized:
                return dos_down_sum, dos_up_sum
            else:
                total = dos_down_sum.copy()
                if dos_up_sum is not None:
                    total[:, 1] += dos_up_sum[:, 1]
                return total, None

        else:
            # Get single ITA
            if ITA_index < 1 or ITA_index > len(ITAs_on_sublattice):
                raise KeyError(
                    f"ITA_index {ITA_index} out of range. "
                    f"Sublattice {sublattice} has {len(ITAs_on_sublattice)} ITA(s)"
                )

            # Get the sequential atom_number for this sublattice and ITA_index
            atom_number = ITAs_on_sublattice[ITA_index - 1][0]  # -1 because ITA_index is 1-based

            # Get the ITA data
            # For paramagnetic, data is stored under 'down' key (contains combined spin data)
            down_key = f'atom_{atom_number}_down'
            up_key = f'atom_{atom_number}_up'

            if down_key not in self.data:
                raise KeyError(f"Data for sublattice {sublattice}, ITA {ITA_index} not found")

            # Extract energy and orbital columns
            dos_down = np.column_stack([
                self.data[down_key][:, 0],      # Energy
                self.data[down_key][:, col_idx]  # Orbital DOS
            ])

            dos_up = None
            if up_key in self.data and self.data[up_key] is not None:
                dos_up = np.column_stack([
                    self.data[up_key][:, 0],      # Energy
                    self.data[up_key][:, col_idx]  # Orbital DOS
                ])

            if spin_polarized:
                return dos_down, dos_up
            else:
                total = dos_down.copy()
                if dos_up is not None:
                    total[:, 1] += dos_up[:, 1]
                return total, None

    def verify_ITA_sum(self, sublattice: int, concentrations: List[float],
                       tolerance: float = 1e-6) -> Dict[str, bool]:
        """
        Verify that concentration-weighted ITA sum matches IT column data.

        This function checks the relationship:
        sum(c_i * ITA_i_total) == IT_total (within tolerance)

        Parameters
        ----------
        sublattice : int
            Sublattice (IT) index to verify
        concentrations : list of float
            Concentration weights for each ITA (must sum to 1.0)
        tolerance : float
            Numerical tolerance for comparison. Default: 1e-6

        Returns
        -------
        dict
            Dictionary with verification results:
            {
                'spin_down_match': bool,
                'spin_up_match': bool,
                'max_diff_down': float,
                'max_diff_up': float
            }

        Examples
        --------
        >>> result = parser.verify_ITA_sum(sublattice=1, concentrations=[0.7, 0.3])
        >>> if result['spin_down_match']:
        ...     print("Verification passed!")
        """
        # Get IT column data
        it_dos_down, it_dos_up = self.get_dos('sublattice', sublattice=sublattice,
                                               spin_polarized=True)

        # Get weighted ITA sum
        ita_sum_down, ita_sum_up = self.get_ITA_dos(sublattice=sublattice, orbital='total',
                                                      sum_ITAs=True, concentrations=concentrations,
                                                      spin_polarized=True)

        # Compare
        max_diff_down = np.max(np.abs(it_dos_down[:, 1] - ita_sum_down[:, 1]))
        spin_down_match = max_diff_down < tolerance

        max_diff_up = 0.0
        spin_up_match = True
        if it_dos_up is not None and ita_sum_up is not None:
            max_diff_up = np.max(np.abs(it_dos_up[:, 1] - ita_sum_up[:, 1]))
            spin_up_match = max_diff_up < tolerance

        return {
            'spin_down_match': spin_down_match,
            'spin_up_match': spin_up_match,
            'max_diff_down': max_diff_down,
            'max_diff_up': max_diff_up
        }

    def list_ITAs(self) -> List[Tuple[int, str, int]]:
        """
        Return list of ITAs (Interacting Type Atoms) with their info.

        Returns
        -------
        list of tuples
            Each tuple is (ITA_number, element, sublattice)
            ITA_number is the internal sequential numbering (1, 2, 3, ...)
            For access by sublattice, use sublattice and ITA_index parameters in get_ITA_dos()

        Examples
        --------
        >>> parser.list_ITAs()
        [(1, 'pt', 1), (2, 'pt', 1), (3, 'fe', 2), (4, 'fe', 2)]

        # Extract unique sublattices
        >>> ITAs = parser.list_ITAs()
        >>> sublattices = sorted(set(sub for _, _, sub in ITAs))
        """
        return self.atom_info


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
        dos_down, dos_up = self.parser.get_dos('total', spin_polarized=spin_polarized)

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
    
    def plot_sublattice(self, sublattice: Optional[int] = None, spin_polarized: bool = True,
                        figsize: Tuple[float, float] = (8, 6), save: Optional[str] = None,
                        show: bool = True):
        """
        Plot sublattice DOS (IT contributions).

        Uses get_dos() to extract sublattice data from IT columns.
        If sublattice is None, plots all sublattices.

        Parameters
        ----------
        sublattice : int, optional
            Specific sublattice to plot. If None, plots all sublattices.
        spin_polarized : bool
            If True, plot spin-up and spin-down separately
        figsize : tuple
            Figure size (width, height)
        save : str, optional
            Filename to save plot
        show : bool
            Whether to display the plot
        """
        # Auto-detect number of sublattices
        if self.parser.data['total_down'] is None:
            raise ValueError("No DOS data found. File may be empty or unparseable.")
        
        num_sublattices = self.parser.data['total_down'].shape[1] - 3  # Subtract E, Total, NOS

        if num_sublattices < 1:
            raise ValueError("No sublattice data found in DOS file")

        # Determine which sublattices to plot
        if sublattice is not None:
            if sublattice < 1 or sublattice > num_sublattices:
                raise ValueError(f"Sublattice {sublattice} not found. Available: 1-{num_sublattices}")
            sublattices_to_plot = [sublattice]
            title = f'Sublattice {sublattice} DOS'
        else:
            sublattices_to_plot = list(range(1, num_sublattices + 1))
            title = f'Sublattice DOS ({num_sublattices} sublattices)'

        fig, ax = plt.subplots(figsize=figsize)

        # Plot each sublattice
        colors = plt.cm.tab10.colors  # Use color cycle
        for sublat in sublattices_to_plot:
            dos_down, dos_up = self.parser.get_dos('sublattice', sublattice=sublat,
                                                     spin_polarized=True)
            color = colors[(sublat - 1) % len(colors)]
            label = f'Sublattice {sublat}' if len(sublattices_to_plot) > 1 else 'DOS'

            if spin_polarized and dos_up is not None:
                ax.plot(dos_up[:, 0], dos_up[:, 1], label=label,
                       linestyle='-', color=color)
                ax.plot(dos_down[:, 0], -dos_down[:, 1],
                       linestyle='--', color=color)
            else:
                dos_total = dos_down[:, 1] + (dos_up[:, 1] if dos_up is not None else 0)
                ax.plot(dos_down[:, 0], dos_total, label=label, color=color)

        if spin_polarized:
            ax.axhline(0, color='black', linewidth=0.5)

        ax.axvline(0, color='gray', linestyle='--', alpha=0.5, label='E_F')
        ax.set_xlabel('Energy (Ry)')
        ax.set_ylabel('DOS (states/Ry)')
        ax.legend()
        ax.set_title(title)
        plt.tight_layout()

        if save:
            plt.savefig(save, dpi=300)
        if show:
            plt.show()

        return fig, ax
    
    def plot_ITA(self, sublattice: int, ITA_index: int = 1, orbital: str = 'total',
                 orbital_resolved: bool = False, spin_polarized: bool = True,
                 figsize: Tuple[float, float] = (8, 6),
                 save: Optional[str] = None, show: bool = True):
        """
        Plot ITA (Interacting Type Atom) DOS with optional orbital selection.

        This function combines atom-resolved and orbital-resolved plotting.
        Use orbital parameter to select specific orbitals, or orbital_resolved=True
        to show all orbitals separately.

        Parameters
        ----------
        sublattice : int
            Sublattice (IT) index (1, 2, 3, ...)
        ITA_index : int
            Which ITA on this sublattice (1 = first, 2 = second, etc.). Default: 1
        orbital : str
            Orbital to plot: 'total', 's', 'p', or 'd'. Default: 'total'
            - 'total': Plot total DOS (optionally with orbital_resolved)
            - 's'/'p'/'d': Plot only that specific orbital
        orbital_resolved : bool
            Only applies when orbital='total'. If True, plot s, p, d separately.
            If False, plot total DOS only. Default: False
        spin_polarized : bool
            If True, plot spin-up and spin-down separately
        figsize : tuple
            Figure size (width, height)
        save : str, optional
            Filename to save plot
        show : bool
            Whether to display the plot

        Examples
        --------
        >>> plotter.plot_ITA(sublattice=1, ITA_index=1)  # Total DOS
        >>> plotter.plot_ITA(sublattice=1, ITA_index=1, orbital='d')  # d-orbital only
        >>> plotter.plot_ITA(sublattice=1, ITA_index=1, orbital_resolved=True)  # s, p, d separately
        """
        # Get ITA info for title
        ITAs_on_sublattice = [(num, elem) for num, elem, sub in self.parser.atom_info
                              if sub == sublattice]
        if ITA_index < 1 or ITA_index > len(ITAs_on_sublattice):
            raise ValueError(f"ITA_index {ITA_index} out of range for sublattice {sublattice}")

        _, element = ITAs_on_sublattice[ITA_index - 1]

        fig, ax = plt.subplots(figsize=figsize)

        if orbital == 'total' and orbital_resolved:
            # Plot s, p, d separately
            orbitals = ['s', 'p', 'd']
            colors = ['C0', 'C1', 'C2']

            for orb, color in zip(orbitals, colors):
                dos_down, dos_up = self.parser.get_ITA_dos(
                    sublattice=sublattice, ITA_index=ITA_index, orbital=orb,
                    spin_polarized=spin_polarized
                )

                if spin_polarized and dos_up is not None:
                    ax.plot(dos_up[:, 0], dos_up[:, 1], label=orb, linestyle='-', color=color)
                    ax.plot(dos_down[:, 0], -dos_down[:, 1], linestyle='--', color=color)
                else:
                    ax.plot(dos_down[:, 0], dos_down[:, 1], label=orb, color=color)

            if spin_polarized:
                ax.axhline(0, color='black', linewidth=0.5)
            title_orbital = '(s, p, d orbitals)'

        else:
            # Plot single orbital (total, s, p, or d)
            dos_down, dos_up = self.parser.get_ITA_dos(
                sublattice=sublattice, ITA_index=ITA_index, orbital=orbital,
                spin_polarized=spin_polarized
            )

            label = orbital if orbital != 'total' else 'Total'

            if spin_polarized and dos_up is not None:
                ax.plot(dos_up[:, 0], dos_up[:, 1], label=label, color='blue', linestyle='-')
                ax.plot(dos_down[:, 0], -dos_down[:, 1], color='blue', linestyle='--')
                ax.axhline(0, color='black', linewidth=0.5)
            else:
                ax.plot(dos_down[:, 0], dos_down[:, 1], label=label, color='black')

            title_orbital = f'({orbital}-orbital)' if orbital != 'total' else ''

        ax.axvline(0, color='gray', linestyle='--', alpha=0.5, label='E_F')
        ax.set_xlabel('Energy (Ry)')
        ax.set_ylabel('DOS (states/Ry)')
        ax.legend()
        ax.set_title(f'ITA {ITA_index} ({element.upper()}, sublattice {sublattice}) {title_orbital} DOS'.strip())
        plt.tight_layout()

        if save:
            plt.savefig(save, dpi=300)
        if show:
            plt.show()

        return fig, ax


# Convenience function
def plot_dos(filename: str, plot_type: str = 'total',
             sublattice: Optional[int] = None,
             ITA_index: Optional[int] = None,
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
        Type of plot:
        - 'total': Total DOS
        - 'sublattice': Sublattice (IT) DOS
        - 'ITA': ITA (Interacting Type Atom) DOS
    sublattice : int, optional
        Sublattice index (1, 2, 3, ...). Required for 'sublattice' and 'ITA' plot types.
    ITA_index : int, optional
        ITA index on the specified sublattice (1, 2, ...). Required for 'ITA' plot type.
        Default: 1
    orbital : str, optional
        For ITA plots: 'total', 's', 'p', or 'd'. Default: 'total'
    orbital_resolved : bool
        For ITA plots when orbital='total': show s, p, d separately. Default: False
    spin_polarized : bool
        Plot spin channels separately. Default: True
    figsize : tuple
        Figure size (width, height)
    save : str, optional
        Save filename
    show : bool
        Display plot

    Returns
    -------
    fig, ax : matplotlib figure and axes

    Examples
    --------
    >>> plot_dos('dos.dat', 'total')
    >>> plot_dos('dos.dat', 'sublattice', sublattice=1)
    >>> plot_dos('dos.dat', 'ITA', sublattice=1, ITA_index=1)
    >>> plot_dos('dos.dat', 'ITA', sublattice=1, ITA_index=1, orbital='d')
    >>> plot_dos('dos.dat', 'ITA', sublattice=1, ITA_index=1, orbital_resolved=True)
    """
    parser = DOSParser(filename)
    plotter = DOSPlotter(parser)

    if plot_type == 'total':
        return plotter.plot_total(spin_polarized, figsize, save, show)

    elif plot_type == 'sublattice':
        return plotter.plot_sublattice(sublattice, spin_polarized, figsize, save, show)

    elif plot_type == 'ITA':
        if sublattice is None:
            raise ValueError(
                f"Must specify sublattice for ITA plots. "
                f"Available ITAs: {parser.list_ITAs()}"
            )
        if ITA_index is None:
            ITA_index = 1
        if orbital is None:
            orbital = 'total'

        return plotter.plot_ITA(
            sublattice=sublattice,
            ITA_index=ITA_index,
            orbital=orbital,
            orbital_resolved=orbital_resolved,
            spin_polarized=spin_polarized,
            figsize=figsize,
            save=save,
            show=show
        )

    else:
        raise ValueError(
            f"Unknown plot_type: '{plot_type}'. "
            f"Use 'total', 'sublattice', or 'ITA'"
        )