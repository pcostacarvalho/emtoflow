#!/usr/bin/env python3
"""
Test script for paramagnetic DOS parsing functionality.
Tests the implementation with CuMg_1.00_2.70.dos (paramagnetic file).
"""

import os
import sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt

# Import DOS modules directly (avoid __init__.py which imports other dependencies)
sys.path.insert(0, str(Path(__file__).parent))
import importlib.util
dos_module_path = Path(__file__).parent / "modules" / "dos.py"
spec = importlib.util.spec_from_file_location("dos", dos_module_path)
dos_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dos_module)
DOSParser = dos_module.DOSParser
DOSPlotter = dos_module.DOSPlotter

# Test file
dos_file = Path("Cu100_Mg0/phase3_optimized_calculation/CuMg_1.00_2.70.dos")

print("="*70)
print("TESTING PARAMAGNETIC DOS PARSING")
print("="*70)
print(f"\nDOS file: {dos_file}")
print(f"File exists: {dos_file.exists()}")

if not dos_file.exists():
    print(f"✗ ERROR: DOS file not found: {dos_file}")
    sys.exit(1)

print(f"File size: {dos_file.stat().st_size} bytes")

# Test 1: Parse DOS file
print("\n" + "-"*70)
print("TEST 1: Parsing DOS file")
print("-"*70)
try:
    parser = DOSParser(str(dos_file))
    print(f"✓ DOS file parsed successfully")
    print(f"  Is paramagnetic: {parser.is_paramagnetic}")
    print(f"  Atom info count: {len(parser.atom_info)}")
    print(f"  Atom info: {parser.atom_info}")
    print(f"  Has total_down: {parser.data.get('total_down') is not None}")
    if parser.data.get('total_down') is not None:
        print(f"    Shape: {parser.data['total_down'].shape}")
        print(f"    First few rows:\n{parser.data['total_down'][:5]}")
    print(f"  Has total_up: {parser.data.get('total_up') is not None}")
    if parser.data.get('total_up') is not None:
        print(f"    Shape: {parser.data['total_up'].shape}")
    
    # Verify paramagnetic detection
    if not parser.is_paramagnetic:
        print("✗ WARNING: File should be detected as paramagnetic but is_paramagnetic=False")
    else:
        print("✓ Correctly detected as paramagnetic file")
    
    if parser.data.get('total_up') is not None:
        print("✗ ERROR: total_up should be None for paramagnetic files")
    else:
        print("✓ total_up is None (correct for paramagnetic)")
        
except Exception as e:
    import traceback
    print(f"✗ Failed to parse DOS file: {e}")
    traceback.print_exc()
    sys.exit(1)

# Test 2: Get DOS data
print("\n" + "-"*70)
print("TEST 2: Getting DOS data")
print("-"*70)
try:
    # Test get_dos('total')
    dos_down, dos_up = parser.get_dos('total', spin_polarized=True)
    print(f"✓ get_dos('total') returned data")
    print(f"  dos_down shape: {dos_down.shape}")
    print(f"  dos_up: {dos_up}")
    print(f"  First few energy values: {dos_down[:5, 0]}")
    print(f"  First few DOS values: {dos_down[:5, 1]}")
    
    if dos_up is not None:
        print("✗ ERROR: dos_up should be None for paramagnetic files")
    else:
        print("✓ dos_up is None (correct for paramagnetic)")
    
    # Test get_dos('total', spin_polarized=False)
    dos_total, _ = parser.get_dos('total', spin_polarized=False)
    print(f"\n✓ get_dos('total', spin_polarized=False) returned data")
    print(f"  dos_total shape: {dos_total.shape}")
    
    # Test sublattice DOS if available
    if parser.data['total_down'] is not None:
        num_sublattices = parser.data['total_down'].shape[1] - 3
        if num_sublattices > 0:
            print(f"\n  Testing sublattice DOS (found {num_sublattices} sublattices)")
            for sublat in range(1, min(num_sublattices + 1, 3)):  # Test first 2 sublattices
                try:
                    sublat_down, sublat_up = parser.get_dos('sublattice', sublattice=sublat, spin_polarized=True)
                    print(f"    Sublattice {sublat}: shape={sublat_down.shape}, dos_up={sublat_up}")
                except Exception as e:
                    print(f"    ✗ Error getting sublattice {sublat} DOS: {e}")
    
except Exception as e:
    import traceback
    print(f"✗ Error getting DOS data: {e}")
    traceback.print_exc()
    sys.exit(1)

# Test 3: Test plotting
print("\n" + "-"*70)
print("TEST 3: Testing plotting functionality")
print("-"*70)
try:
    plotter = DOSPlotter(parser)
    print("✓ DOSPlotter created")
    
    # Create test output directory
    test_output_dir = Path("test_paramagnetic_dos_output")
    test_output_dir.mkdir(exist_ok=True)
    print(f"Test output directory: {test_output_dir}")
    
    # Test plot_total
    print("\n  Testing plot_total()...")
    fig, ax = plotter.plot_total(
        spin_polarized=True,
        save=None,
        show=False,
    )
    print("✓ plot_total() returned figure and axes")
    
    # Save the plot
    total_plot = test_output_dir / "dos_total.png"
    ax.set_xlim(-0.8, 0.15)
    fig.savefig(total_plot, dpi=300, bbox_inches='tight')
    plt.close(fig)
    
    if total_plot.exists():
        file_size = total_plot.stat().st_size
        print(f"✓ Total DOS plot saved: {total_plot} ({file_size} bytes)")
    else:
        print(f"✗ Total DOS plot was NOT created")
    
    # Test plot_sublattice if sublattices exist
    if parser.data['total_down'] is not None:
        num_sublattices = parser.data['total_down'].shape[1] - 3
        if num_sublattices > 0:
            print(f"\n  Testing plot_sublattice() (found {num_sublattices} sublattices)...")
            try:
                fig, ax = plotter.plot_sublattice(
                    sublattice=1,
                    spin_polarized=True,
                    save=None,
                    show=False,
                )
                sublat_plot = test_output_dir / "dos_sublattice_1.png"
                ax.set_xlim(-0.8, 0.15)
                fig.savefig(sublat_plot, dpi=300, bbox_inches='tight')
                plt.close(fig)
                
                if sublat_plot.exists():
                    file_size = sublat_plot.stat().st_size
                    print(f"✓ Sublattice DOS plot saved: {sublat_plot} ({file_size} bytes)")
                else:
                    print(f"✗ Sublattice DOS plot was NOT created")
            except Exception as e:
                print(f"✗ Error plotting sublattice DOS: {e}")
                import traceback
                traceback.print_exc()
    
except Exception as e:
    import traceback
    print(f"✗ Error during plotting: {e}")
    traceback.print_exc()
    sys.exit(1)

# Test 4: Test ITA DOS if available
print("\n" + "-"*70)
print("TEST 4: Testing ITA DOS (if available)")
print("-"*70)
if parser.atom_info:
    print(f"Found {len(parser.atom_info)} ITA(s)")
    for atom_num, element, sublattice in parser.atom_info[:3]:  # Test first 3
        try:
            print(f"\n  Testing ITA {atom_num} ({element}, sublattice {sublattice})...")
            dos_down, dos_up = parser.get_ITA_dos(
                sublattice=sublattice,
                ITA_index=1,
                orbital='total',
                spin_polarized=True
            )
            print(f"    ✓ get_ITA_dos() returned data: shape={dos_down.shape}, dos_up={dos_up}")
        except Exception as e:
            print(f"    ✗ Error getting ITA DOS: {e}")
            import traceback
            traceback.print_exc()
else:
    print("No ITA info found (this is OK for simple structures)")

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70)
print(f"\nOutput files saved to: {test_output_dir}")
if test_output_dir.exists():
    print("Files created:")
    for f in test_output_dir.iterdir():
        print(f"  - {f.name} ({f.stat().st_size} bytes)")
