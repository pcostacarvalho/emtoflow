#!/usr/bin/env python3
"""
Test script to debug DOS plotting functionality.
"""

import os
import sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt

from modules.dos import DOSParser, DOSPlotter
from modules.optimization.analysis import generate_dos_analysis

# Test file
dos_file = Path("files/examples/dos/fept_0.96_2.86_k21.dos")

print("="*70)
print("TESTING DOS PLOTTING")
print("="*70)
print(f"\nDOS file: {dos_file}")
print(f"File exists: {dos_file.exists()}")
if dos_file.exists():
    print(f"File size: {dos_file.stat().st_size} bytes")

# Test parsing
print("\n" + "-"*70)
print("STEP 1: Parsing DOS file")
print("-"*70)
try:
    parser = DOSParser(str(dos_file))
    print(f"✓ DOS file parsed successfully")
    print(f"  Atom info count: {len(parser.atom_info)}")
    print(f"  Atom info: {parser.atom_info}")
    print(f"  Has total_down: {parser.data.get('total_down') is not None}")
    if parser.data.get('total_down') is not None:
        print(f"    Shape: {parser.data['total_down'].shape}")
    print(f"  Has total_up: {parser.data.get('total_up') is not None}")
    if parser.data.get('total_up') is not None:
        print(f"    Shape: {parser.data['total_up'].shape}")
except Exception as e:
    import traceback
    print(f"✗ Failed to parse DOS file: {e}")
    traceback.print_exc()
    sys.exit(1)

# Test plotting directly
print("\n" + "-"*70)
print("STEP 2: Testing plot_total() directly")
print("-"*70)
try:
    plotter = DOSPlotter(parser)
    print("✓ DOSPlotter created")
    
    # Create test output directory
    test_output_dir = Path("test_dos_output")
    test_output_dir.mkdir(exist_ok=True)
    print(f"Test output directory: {test_output_dir}")
    print(f"  Directory exists: {test_output_dir.exists()}")
    print(f"  Directory is writable: {os.access(test_output_dir, os.W_OK)}")
    
    # Try plotting
    test_plot = test_output_dir / "test_total_dos.png"
    print(f"\nAttempting to create plot: {test_plot}")
    
    fig, ax = plotter.plot_total(
        spin_polarized=True,
        save=None,
        show=False,
    )
    print("✓ plot_total() returned figure and axes")
    
    ax.set_xlim(-0.8, 0.15)
    print("✓ Set xlim")
    
    print(f"Calling fig.savefig({test_plot})...")
    fig.savefig(test_plot, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print("✓ savefig() completed, figure closed")
    
    # Check if file exists
    if test_plot.exists():
        file_size = test_plot.stat().st_size
        print(f"✓ Plot file created successfully!")
        print(f"  File: {test_plot}")
        print(f"  Size: {file_size} bytes")
    else:
        print(f"✗ Plot file was NOT created!")
        print(f"  Expected: {test_plot}")
        print(f"  Absolute path: {test_plot.absolute()}")
        
except Exception as e:
    import traceback
    print(f"✗ Error during plotting: {e}")
    traceback.print_exc()

# Test using generate_dos_analysis function
print("\n" + "-"*70)
print("STEP 3: Testing generate_dos_analysis() function")
print("-"*70)
try:
    # Create a test phase directory
    test_phase_dir = Path("test_phase3")
    test_phase_dir.mkdir(exist_ok=True)
    
    # Copy DOS file to test phase directory (simulating Phase 3)
    import shutil
    test_dos_copy = test_phase_dir / "fept_0.96_2.86_k21.dos"
    shutil.copy(dos_file, test_dos_copy)
    print(f"Copied DOS file to: {test_dos_copy}")
    
    # Run the analysis function
    results = generate_dos_analysis(
        phase_path=str(test_phase_dir),
        file_id="fept_0.96_2.86_k21",
        dos_plot_range=[-0.8, 0.15]
    )
    
    print(f"\nResults:")
    print(f"  Status: {results.get('status')}")
    print(f"  Total plot: {results.get('total_plot')}")
    print(f"  Sublattice plots: {results.get('sublattice_plots')}")
    
    # Check if plots actually exist
    if results.get('total_plot'):
        total_plot_path = Path(results['total_plot'])
        if total_plot_path.exists():
            print(f"  ✓ Total plot exists: {total_plot_path}")
        else:
            print(f"  ✗ Total plot missing: {total_plot_path}")
    
    for sublat_plot in results.get('sublattice_plots', []):
        sublat_path = Path(sublat_plot)
        if sublat_path.exists():
            print(f"  ✓ Sublattice plot exists: {sublat_path}")
        else:
            print(f"  ✗ Sublattice plot missing: {sublat_path}")
            
except Exception as e:
    import traceback
    print(f"✗ Error during generate_dos_analysis: {e}")
    traceback.print_exc()

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70)
