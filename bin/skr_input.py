#!/usr/bin/env -S python -B
# -*- coding: utf-8 -*-
#
# Copyright ...
# SPDX-License-Identifier: Apache-2.0
#
# ------------------------------------------------------------------------------
# Script for generating EMTO KSTR input files automatically
# ------------------------------------------------------------------------------

import argparse
import os
from pathlib import Path
import sys

# Add project root to Python path
script_path = os.path.abspath(__file__)
bin_dir = os.path.dirname(script_path)
project_root = os.path.dirname(bin_dir)
sys.path.insert(0, project_root)

print(f"DEBUG: Project root: {project_root}")
print(f"DEBUG: sys.path: {sys.path}")

from modules.parse_cif import get_LatticeVectors


def create_kstr_input(output_folder, job_name, NL, NQ3, DMAX, LAT, A, B, C, lattice_vectors, lattice_positions):
    """
    Generate a KSTR input file for EMTO based on the given structural parameters.
    """

    file_path = os.path.join(output_folder, f"{job_name}.smx")

    lines = [
        "KSTR      HP......=N                               xx xxx xx",
        f"JOBNAM...={job_name:<10} MSGL.=  1 MODE...=B STORE..=Y HIGH...=Y",
        "DIR001=./",
        "DIR006=",
        "Slope and Madelung matrices",
        f"NL.....= {NL:>1} NLH...= 9 NLW...= 9 NDER..= 6 ITRANS= 3 NPRN..= 1",
        f"(K*W)^2..=   0.00000 DMAX....=    {DMAX:>6.2f} RWATS...=      0.10",
        f"NQ3...= {NQ3:>2} LAT...= {LAT:>1} IPRIM.= 0 NGHBP.=13 NQR2..= 0        80",
        f"A........= {A:.7f} B.......= {B:.7f} C.......={C:.7f}",
    ]

    # Add lattice vectors
    for vec in lattice_vectors:
        lines.append(f"{vec[0]:.8f}\t{vec[1]:.8f}\t{vec[2]:.8f}")

    # Add lattice positions
    for pos in lattice_positions:
        lines.append(f"\t{pos[0]:.8f}\t{pos[1]:.8f}\t{pos[2]:.8f}")

    # Append the constant section
        # Append fixed section
    for i in range(NQ3):
        lines.append("a/w......= 0.70 0.70 0.70 0.70")

    lines.extend([f"NL_mdl.= {2*NL + 1}",
                "LAMDA....=    2.5000 AMAX....=    4.5000 BMAX....=    4.5000",""])
 

    # Write to file
    os.makedirs(output_folder, exist_ok=True)
    with open(file_path, "w") as f:
        f.write("\n".join(lines))

    print(f"[OK] KSTR input file created: {file_path}")



parser = argparse.ArgumentParser(description="Generate EMTO KSTR input file.")
parser.add_argument("output_folder", 
                    type=str, 
                    help="Folder to save the generated .dat file.")
parser.add_argument("--JobName", 
                    required=True, 
                    type=str, 
                    help="Name of the EMTO job.")
parser.add_argument("--DMAX", 
                    required=True, 
                    type=float, 
                    help="Maximum distance")
parser.add_argument("--LAT", 
                    required=True, 
                    type=int, 
                    help="Bravais lattice type.")
parser.add_argument("--NL", 
                    required=False, 
                    type=int, 
                    help="Maximum number of orbitals")
parser.add_argument("--LAT", 
                    required=False,      # Changed from True
                    default=None,        # Added
                    type=int, 
                    help="Bravais lattice type (1-14). Auto-detected from CIF if not provided.")

args = parser.parse_args()

# Read the cif file and get the lattice parameters and atomic positions
cif_filename = os.path.join(args.output_folder, args.JobName + '.cif')

LatticeVectors, AtomicPositions, a, b, c, atoms = get_LatticeVectors(cif_filename)

# Auto-detect LAT if not provided
if args.LAT is None:
    from modules.lat_detector import detect_lat_from_cif
    lat, lattice_name, crystal_system, centering = detect_lat_from_cif(cif_filename)
    print(f"Auto-detected LAT={lat} ({lattice_name})")
else:
    lat = args.LAT
    print(f"Using provided LAT={lat}")


if not args.NL:
    NLs = []
    for atom in set(atoms):
        if 'f' in atom.electronic_structure:
            NLs.append(3)
        elif 'd' in atom.electronic_structure:
            NLs.append(2) 
        elif 'p' in atom.electronic_structure:      
            NLs.append(1)

    NL = max(NLs)
else:
    NL = args.NL

# Generate file
create_kstr_input(
    output_folder=args.output_folder,
    job_name=args.JobName,
    DMAX=args.DMAX,
    LAT=lat,
    NL=NL,
    NQ3=len(AtomicPositions),
    A=a/a,
    B=b/a,
    C=c/a,
    lattice_vectors=LatticeVectors/a,
    lattice_positions=AtomicPositions/a
)



