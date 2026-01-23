#!/usr/bin/env python3
"""
Simple test script to debug DOS plotting functionality.
"""

import os
import sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt

# Import DOS modules directly
sys.path.insert(0, str(Path(__file__).parent))
from modules.dos import DOSParser, DOSPlotter

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
        print(f"    First few rows:\n{parser.data['total_down'][:5]}")
    print(f"  Has total_up: {parser.data.get('total_up') is not None}")
    if parser.data.get('total_up') is not None:
        print(f"    Shape: {parser.data['total_up'].shape}")
        print(f"    First few rows:\n{parser.data['total_up'][:5]}")
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
    print(f"  Absolute path: {test_output_dir.absolute()}")
    
    # Try plotting
    test_plot = test_output_dir / "test_total_dos.png"
    print(f"\nAttempting to create plot: {test_plot}")
    print(f"  Absolute path: {test_plot.absolute()}")
    
    print("\nCalling plotter.plot_total()...")
    fig, ax = plotter.plot_total(
        spin_polarized=True,
        save=None,
        show=False,
    )
    print("✓ plot_total() returned figure and axes")
    print(f"  Figure type: {type(fig)}")
    print(f"  Axes type: {type(ax)}")
    
    print("\nSetting xlim to [-0.8, 0.15]...")
    ax.set_xlim(-0.8, 0.15)
    print("✓ Set xlim")
    
    print(f"\nCalling fig.savefig({test_plot})...")
    print(f"  Backend: {matplotlib.get_backend()}")
    fig.savefig(test_plot, dpi=300, bbox_inches='tight')
    print("✓ savefig() completed")
    
    plt.close(fig)
    print("✓ Figure closed")
    
    # Check if file exists
    print(f"\nChecking if file exists...")
    if test_plot.exists():
        file_size = test_plot.stat().st_size
        print(f"✓ Plot file created successfully!")
        print(f"  File: {test_plot}")
        print(f"  Absolute: {test_plot.absolute()}")
        print(f"  Size: {file_size} bytes")
        
        # List directory contents
        print(f"\nDirectory contents:")
        for f in test_output_dir.iterdir():
            print(f"  - {f.name} ({f.stat().st_size} bytes)")
    else:
        print(f"✗ Plot file was NOT created!")
        print(f"  Expected: {test_plot}")
        print(f"  Absolute path: {test_plot.absolute()}")
        print(f"\nDirectory contents:")
        for f in test_output_dir.iterdir():
            print(f"  - {f.name}")
        
except Exception as e:
    import traceback
    print(f"✗ Error during plotting: {e}")
    traceback.print_exc()

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70)
