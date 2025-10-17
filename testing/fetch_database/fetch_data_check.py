from mp_api.client import MPRester
from pymatgen.analysis.magnetism import Ordering
import pandas as pd

# Replace with your actual API key
API_KEY = "vhdPJ1STyEi4znoIbrdg6s1j2Q03BQdH"

with MPRester(API_KEY) as mpr:
    
    # Step 1: Query materials with PBE calculations only
    # ===================================================
    
    excluded_elements = ["Pu", "U", "Th", "Ra", "Ac"]
    
    print("Querying materials with PBE calculations...")
    print("This will take a moment as we're filtering by calculation type...")
    print()
    
    # First get all non-magnetic materials
    initial_docs = mpr.materials.summary.search(
        magnetic_ordering=Ordering("NM"),
        theoretical=False,  # Only experimentally observed
        num_elements=(2, None),
        exclude_elements=excluded_elements,
        fields=["material_id"]
    )
    
    print(f"Found {len(initial_docs)} experimental non-magnetic materials")
    print("Now filtering for PBE calculations...")
    print()
    
    # Step 2: Filter for materials with GGA/PBE calculations
    # =======================================================
    
    mp_ids = [doc.material_id for doc in initial_docs]
    pbe_materials = []
    
    batch_size = 200
    for i in range(0, len(mp_ids), batch_size):
        batch_ids = mp_ids[i:i+batch_size]
        
        # Query calc_types to check for PBE/GGA
        calc_docs = mpr.materials.search(
            material_ids=batch_ids,
            fields=["material_id", "calc_types"]
        )
        
        for doc in calc_docs:
            if doc.calc_types:
                # Check if any calculation is GGA/PBE
                # calc_types values are CalcType enums, need to convert to string
                has_pbe = any("GGA" in str(calc_type) for calc_type in doc.calc_types.values())
                if has_pbe:
                    # Get the PBE task ID
                    pbe_task_id = next(
                        (tid for tid, ctype in doc.calc_types.items() if "GGA" in str(ctype)),
                        None
                    )
                    pbe_materials.append({
                        "material_id": doc.material_id,
                        "pbe_task_id": pbe_task_id
                    })
        
        print(f"  Checked {min(i+batch_size, len(mp_ids))}/{len(mp_ids)} materials... "
              f"Found {len(pbe_materials)} with PBE")
    
    print(f"\nFiltered to {len(pbe_materials)} materials with PBE calculations")
    
    
    # Step 3: Get full data for PBE materials only
    # =============================================
    
    print("\nRetrieving full data for PBE materials...")
    
    pbe_mp_ids = [mat["material_id"] for mat in pbe_materials]
    pbe_task_dict = {mat["material_id"]: mat["pbe_task_id"] for mat in pbe_materials}
    
    # Get summary data
    full_data = []
    batch_size = 200
    
    for i in range(0, len(pbe_mp_ids), batch_size):
        batch_ids = pbe_mp_ids[i:i+batch_size]
        
        docs = mpr.materials.summary.search(
            material_ids=batch_ids,
            fields=["material_id", "formula_pretty", "structure", "volume", 
                    "nsites", "database_IDs", "is_stable", "energy_above_hull",
                    "band_gap", "density", "symmetry"]
        )
        
        for doc in docs:
            icsd_ids = doc.database_IDs.get("icsd", []) if doc.database_IDs else []
            
            full_data.append({
                "mp_id": str(doc.material_id),
                "formula": doc.formula_pretty,
                "volume_theo_pbe": doc.volume,  # This is from PBE calculation
                "nsites": doc.nsites,
                "density": doc.density,
                "band_gap": doc.band_gap,
                "space_group": doc.symmetry.symbol if doc.symmetry else None,
                "crystal_system": doc.symmetry.crystal_system if doc.symmetry else None,
                "is_stable": doc.is_stable,
                "energy_above_hull": doc.energy_above_hull,
                "icsd_ids": icsd_ids,
                "num_icsd_ids": len(icsd_ids),
                "pbe_task_id": pbe_task_dict.get(doc.material_id)
            })
        
        print(f"  Retrieved {min(i+batch_size, len(pbe_mp_ids))}/{len(pbe_mp_ids)} materials...")
    
    df = pd.DataFrame(full_data)
    
    
    # Step 4: Display statistics and samples
    # =======================================
    
    print("\n" + "="*80)
    print("DATABASE SUMMARY")
    print("="*80)
    print(f"\nTotal materials with PBE calculations: {len(df)}")
    print(f"Materials with ICSD IDs: {(df['num_icsd_ids'] > 0).sum()}")
    print(f"Stable materials: {df['is_stable'].sum()}")
    
    print("\n" + "-"*80)
    print("Distribution by crystal system:")
    print("-"*80)
    print(df['crystal_system'].value_counts())
    
    print("\n" + "-"*80)
    print("Volume statistics:")
    print("-"*80)
    print(f"Mean volume: {df['volume_theo_pbe'].mean():.2f} Å³")
    print(f"Median volume: {df['volume_theo_pbe'].median():.2f} Å³")
    print(f"Min volume: {df['volume_theo_pbe'].min():.2f} Å³")
    print(f"Max volume: {df['volume_theo_pbe'].max():.2f} Å³")
    
    
    # Step 5: Show sample materials with ICSD IDs
    # ============================================
    
    print("\n" + "="*80)
    print("SAMPLE MATERIALS WITH ICSD IDs (First 20)")
    print("="*80 + "\n")
    
    with_icsd = df[df['num_icsd_ids'] > 0].head(20)
    
    for idx, row in with_icsd.iterrows():
        print(f"{row['mp_id']}: {row['formula']}")
        print(f"  Crystal System: {row['crystal_system']}, Space Group: {row['space_group']}")
        print(f"  PBE Volume: {row['volume_theo_pbe']:.2f} Å³ ({row['nsites']} atoms)")
        print(f"  Band Gap: {row['band_gap']:.2f} eV, Density: {row['density']:.3f} g/cm³")
        print(f"  Stable: {row['is_stable']}, E_hull: {row['energy_above_hull']:.3f} eV/atom")
        print(f"  ICSD IDs: {row['icsd_ids']}")
        print(f"  PBE Task ID: {row['pbe_task_id']}")
        print()
    
    
    # Step 6: Export databases
    # =========================
    
    print("="*80)
    print("EXPORTING DATA")
    print("="*80 + "\n")
    
    # Export full database
    df_sorted = df.sort_values('formula')
    df_sorted.to_csv("mp_pbe_volume_database.csv", index=False)
    print(f"✓ Saved full PBE database to: mp_pbe_volume_database.csv")
    print(f"  Contains {len(df_sorted)} materials")
    
    # Export materials with ICSD IDs
    icsd_df = df[df['num_icsd_ids'] > 0].copy()
    icsd_df_sorted = icsd_df.sort_values('formula')
    icsd_df_sorted.to_csv("mp_pbe_with_icsd.csv", index=False)
    print(f"\n✓ Saved materials with ICSD to: mp_pbe_with_icsd.csv")
    print(f"  Contains {len(icsd_df_sorted)} materials")
    
    # Export expanded ICSD mapping (one row per ICSD ID)
    icsd_expanded = []
    for idx, row in icsd_df.iterrows():
        for icsd_id in row['icsd_ids']:
            icsd_expanded.append({
                "icsd_id": icsd_id,
                "mp_id": row['mp_id'],
                "formula": row['formula'],
                "volume_theo_pbe": row['volume_theo_pbe'],
                "nsites": row['nsites'],
                "density": row['density'],
                "band_gap": row['band_gap'],
                "space_group": row['space_group'],
                "crystal_system": row['crystal_system'],
                "is_stable": row['is_stable'],
                "pbe_task_id": row['pbe_task_id']
            })
    
    icsd_expanded_df = pd.DataFrame(icsd_expanded)
    icsd_expanded_df_sorted = icsd_expanded_df.sort_values('icsd_id')
    icsd_expanded_df_sorted.to_csv("icsd_to_mp_mapping.csv", index=False)
    print(f"\n✓ Saved ICSD mapping to: icsd_to_mp_mapping.csv")
    print(f"  Contains {len(icsd_expanded_df_sorted)} ICSD entries")
    
    # Export summary statistics
    summary_stats = {
        "total_materials": len(df),
        "materials_with_icsd": len(icsd_df),
        "total_icsd_entries": len(icsd_expanded_df),
        "stable_materials": df['is_stable'].sum(),
        "mean_volume": df['volume_theo_pbe'].mean(),
        "median_volume": df['volume_theo_pbe'].median(),
        "mean_band_gap": df['band_gap'].mean(),
        "median_band_gap": df['band_gap'].median(),
    }
    
    stats_df = pd.DataFrame([summary_stats])
    stats_df.to_csv("database_statistics.csv", index=False)
    print(f"\n✓ Saved statistics to: database_statistics.csv")
    
    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print("\n1. Use 'icsd_to_mp_mapping.csv' to query ICSD for experimental volumes")
    print("2. Match ICSD experimental volumes with MP PBE theoretical volumes")
    print("3. All theoretical volumes in the database are from PBE calculations")
    print("\nThe 'volume_theo_pbe' column contains volumes from PBE/GGA calculations.")
    print("You can now compare these with experimental volumes from ICSD.")