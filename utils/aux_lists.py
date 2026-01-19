import numpy as np
from typing import Tuple, List, Optional

# Cubic lattice types (c/a must be 1.0)
CUBIC_LATTICES = [1, 2, 3]  # SC, FCC, BCC

def prepare_ranges(ca_ratios, sws_values, ca_step, sws_step, n_points, lat=None) -> Tuple[List[float], List[float]]:
        """
        Auto-generate c/a and SWS ranges if needed.

        Handles three cases for each parameter:
        1. List provided → use as-is
        2. Single value → create range around it (±3*step, n_points)
        3. None → calculate from structure, then create range

        For cubic lattices (lat=1,2,3), c/a is always 1.0 and no range is generated.

        Parameters
        ----------
        ca_ratios : float, list of float, or None
            c/a ratio value(s)
        sws_values : float, list of float, or None
            SWS value(s)
        ca_step : float
            Step size for c/a range
        sws_step : float
            Step size for SWS range
        n_points : int
            Number of points in range
        lat : int, optional
            Lattice type (1-14). If cubic (1,2,3), c/a is fixed at 1.0

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

        # Process c/a ratios
        # For cubic lattices, c/a must be 1.0 (no range generation)
        if lat is not None and lat in CUBIC_LATTICES:
            ca_list = [1.0]
            print(f"Cubic lattice (lat={lat}): Using c/a = 1.0 (fixed)")
        elif len(ca_ratios) == 1:

            ca_center = float(ca_ratios[0])
            # Generate range
            ca_min = ca_center - 3 * ca_step
            ca_max = ca_center + 3 * ca_step
            ca_list = list(np.linspace(ca_min, ca_max, n_points))

            print(f"Auto-generated c/a ratios around {ca_center:.4f}: {ca_list}")


        elif len(ca_ratios) > 1:
            # Use as-is
            ca_list = ca_ratios
            print(f"Using provided c/a ratios: {ca_list}")

        else:
            raise TypeError(f"ca_ratios must be float, list, or None, got {type(ca_ratios)}")


        # Process SWS values
        if len(sws_values) == 1:

            sws_center = float(sws_values[0])
            # Generate range
            sws_min = sws_center - 3 * sws_step
            sws_max = sws_center + 3 * sws_step
            sws_list = list(np.linspace(sws_min, sws_max, n_points))

            print(f"Auto-generated SWS values around {sws_center:.4f}: {sws_list}")


        elif len(sws_values) > 1:
            # Use as-is
            sws_list = sws_values
            print(f"Using provided SWS values: {sws_list}")

        else:
            raise TypeError(f"sws_values must be float, list, or None, got {type(sws_values)}")

        return ca_list, sws_list