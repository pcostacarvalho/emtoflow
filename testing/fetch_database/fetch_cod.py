"""
Workflow to filter COD structures via OPTIMADE and estimate MP matching candidates
Step 1: Query COD via OPTIMADE API
Step 2: Pre-filter MP database
Step 3: Estimate matching workload
"""

from mp_api.client import MPRester
from pymatgen.ext.optimade import OptimadeRester
from pymatgen.core import Composition
from pymatgen.analysis.magnetism import Ordering
import pandas as pd
import time

# Configuration
MP_API_KEY = "vhdPJ1STyEi4znoIbrdg6s1j2Q03BQdH"
TARGET_COD_COUNT = 1000

# Elements to exclude
RARE_EARTHS = ["La", "Ce", "Pr", "Nd", "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", 
               "Ho", "Er", "Tm", "Yb", "Lu", "Sc", "Y"]
EXCLUDED_ELEMENTS = RARE_EARTHS + ["O"]  # Excluding rare earths and oxygen (oxides)


# ============================================================================
# STEP 1: Query COD Structures via OPTIMADE
# ============================================================================

print("="*80)
print("STEP 1: QUERYING COD VIA OPTIMADE API")
print("="*80)
print()

print("Filters:")
print(f"  - Number of elements: 2-4")
print(f"  - Exclude rare earths: {', '.join(RARE_EARTHS)}")
print(f"  - Exclude oxygen (no oxides)")
print(f"  - Target count: {TARGET_COD_COUNT}")
print()

# Initialize COD client - try direct REST API instead of OPTIMADE
print("Connecting to COD via REST API...")

# COD REST API endpoints
COD_SEARCH_URL = "https://www.crystallography.net/cod/result"
COD_CIF_URL = "https://www.crystallography.net/cod/"

import requests
from io import StringIO

def query_cod_by_elements(included_elements=None, excluded_elements=None, max_results=2000):
    """
    Query COD using their REST API
    """
    params = {}
    
    # Build element filter
    if excluded_elements:
        for el in excluded_elements:
            params[f'nel{el}'] = '0'  # Exclude element
    
    # Set format
    params['format'] = 'csv'
    
    try:
        print(f"  Querying COD with excluded elements: {excluded_elements}")
        response = requests.get(COD_SEARCH_URL, params=params, timeout=30)
        response.raise_for_status()
        
        # Parse CSV response
        import csv
        csv_data = StringIO(response.text)
        reader = csv.DictReader(csv_data)
        
        results = []
        for row in reader:
            results.append(row)
            if len(results) >= max_results:
                break
        
        return results
    
    except Exception as e:
        print(f"  Error: {e}")
        return []

def get_cod_structure(cod_id):
    """
    Download CIF file and parse structure
    """
    try:
        cif_url = f"{COD_CIF_URL}{cod_id}.cif"
        response = requests.get(cif_url, timeout=10)
        response.raise_for_status()
        
        # Parse CIF
        from pymatgen.core import Structure
        cif_string = StringIO(response.text)
        structure = Structure.from_str(response.text, fmt="cif")
        
        return structure
    except Exception as e:
        return None

# Query COD using REST API
print("Querying COD database...")
print("(This may take several minutes)")
print()

cod_results = query_cod_by_elements(excluded_elements=EXCLUDED_ELEMENTS, max_results=5000)

print(f"Retrieved {len(cod_results)} entries from COD")
print()

# Process COD results
print("Downloading and processing structures...")
print("(Downloading CIF files from COD)")
print()

filtered_cod = []
downloaded = 0
errors = 0

for i, result in enumerate(cod_results):
    try:
        cod_id = result.get('file', '').replace('.cif', '')
        formula = result.get('formula', '')
        
        if not cod_id or not formula:
            continue
        
        # Check formula has 2-4 elements (rough filter before downloading)
        from pymatgen.core import Composition
        try:
            comp = Composition(formula)
            elements = [str(el) for el in comp.elements]
            num_species = len(elements)
            
            # Pre-filter before downloading
            if num_species < 2 or num_species > 4:
                continue
            if any(el in EXCLUDED_ELEMENTS for el in elements):
                continue
        except:
            continue
        
        # Download structure
        structure = get_cod_structure(cod_id)
        
        if structure is None:
            errors += 1
            continue
        
        downloaded += 1
        
        # Re-validate with actual structure
        comp = structure.composition
        elements = [str(el) for el in comp.elements]
        num_species = len(elements)
        
        if num_species < 2 or num_species > 4:
            continue
        if any(el in EXCLUDED_ELEMENTS for el in elements):
            continue
        
        # Extract metadata
        formula = comp.reduced_formula
        
        try:
            space_group_info = structure.get_space_group_info()
            space_group = space_group_info[1]  # Space group number
        except:
            space_group = None
        
        volume = structure.volume
        nsites = len(structure)
        
        filtered_cod.append({
            "cod_id": cod_id,
            "formula": formula,
            "elements": elements,
            "num_species": num_species,
            "space_group": space_group,
            "volume": volume,
            "nsites": nsites,
            "lattice_a": structure.lattice.a,
            "lattice_b": structure.lattice.b,
            "lattice_c": structure.lattice.c,
            "structure": structure  # Store structure object for later matching
        })
        
        # Progress update
        if downloaded % 50 == 0:
            print(f"  Downloaded {downloaded} structures... "
                  f"Kept {len(filtered_cod)} after filtering")
        
        # Stop when we reach target
        if len(filtered_cod) >= TARGET_COD_COUNT:
            print(f"\nReached target of {TARGET_COD_COUNT} structures!")
            break
    
    except Exception as e:
        errors += 1
        continue

print()
print(f"Download complete!")
print(f"  Structures downloaded: {downloaded}")
print(f"  Structures passing all filters: {len(filtered_cod)}")
print(f"  Download errors: {errors}")
print()

if len(filtered_cod) == 0:
    print("ERROR: No structures passed filters!")
    print("Try adjusting your filters or check COD connectivity.")
    exit()

# Create DataFrame
cod_df = pd.DataFrame([{k: v for k, v in item.items() if k != 'structure'} 
                       for item in filtered_cod])

# Show statistics
print("-"*80)
print("COD Filtered Dataset Statistics")
print("-"*80)
print(f"Total structures: {len(cod_df)}")
print()
print("Distribution by number of species:")
print(cod_df['num_species'].value_counts().sort_index())
print()
print("Top 10 most common formulas:")
print(cod_df['formula'].value_counts().head(10))
print()
print("Space group distribution (top 10):")
if cod_df['space_group'].notna().any():
    print(cod_df['space_group'].value_counts().head(10))
else:
    print("  (Space group info not available)")
print()

# Save COD filtered dataset
cod_df.to_csv("cod_filtered_structures.csv", index=False)
print("✓ Saved to: cod_filtered_structures.csv")
print()


# ============================================================================
# STEP 2: Pre-filter Materials Project Database
# ============================================================================

print("="*80)
print("STEP 2: PRE-FILTERING MATERIALS PROJECT DATABASE")
print("="*80)
print()

# Get unique formulas from COD dataset
unique_formulas = cod_df['formula'].unique()
print(f"Unique formulas in COD dataset: {len(unique_formulas)}")
print()

# Query MP for each formula
print("Querying Materials Project for matching formulas...")
print("(This will take a few minutes)")
print()

mp_candidates = []

with MPRester(MP_API_KEY) as mpr:
    
    # Process formulas in batches
    batch_size = 50
    for i in range(0, len(unique_formulas), batch_size):
        batch = unique_formulas[i:i+batch_size]
        
        # Query MP for these formulas
        for formula in batch:
            try:
                docs = mpr.materials.summary.search(
                    formula=formula,
                    magnetic_ordering=Ordering("NM"),  # Non-magnetic
                    theoretical=False,  # Experimental origin
                    fields=["material_id", "formula_pretty", "symmetry", "nsites", 
                            "volume", "database_IDs"]
                )
                
                for doc in docs:
                    space_group = doc.symmetry.number if doc.symmetry else None
                    
                    mp_candidates.append({
                        "mp_id": str(doc.material_id),
                        "formula": doc.formula_pretty,
                        "space_group": space_group,
                        "nsites": doc.nsites,
                        "volume": doc.volume,
                        "has_icsd": bool(doc.database_IDs and doc.database_IDs.get("icsd", [])),
                        "source_cod_formula": formula
                    })
                
            except Exception as e:
                print(f"  Error querying formula {formula}: {e}")
                continue
        
        print(f"  Processed {min(i+batch_size, len(unique_formulas))}/{len(unique_formulas)} formulas... "
              f"Found {len(mp_candidates)} MP candidates")
        
        time.sleep(0.1)  # Small delay to be nice to the API

print()
print(f"Pre-filtering complete!")
print(f"  MP candidates found: {len(mp_candidates)}")
print()

# Create DataFrame
mp_df = pd.DataFrame(mp_candidates)

if len(mp_df) > 0:
    # Show statistics
    print("-"*80)
    print("Materials Project Candidates Statistics")
    print("-"*80)
    print(f"Total MP materials: {len(mp_df)}")
    print(f"Materials with ICSD IDs: {mp_df['has_icsd'].sum()}")
    print()
    print("Distribution by formula (top 10):")
    print(mp_df['formula'].value_counts().head(10))
    print()
    print("Space group distribution (top 10):")
    print(mp_df['space_group'].value_counts().head(10))
    print()
    
    # Save MP candidates
    mp_df.to_csv("mp_candidate_structures.csv", index=False)
    print("✓ Saved to: mp_candidate_structures.csv")
    print()


# ============================================================================
# STEP 3: Estimate Matching Workload
# ============================================================================

print("="*80)
print("STEP 3: MATCHING WORKLOAD ESTIMATION")
print("="*80)
print()

if len(mp_df) == 0:
    print("WARNING: No MP candidates found!")
    print("This means none of your COD structures have matching formulas in MP.")
    print("Consider:")
    print("  - Relaxing filters (include more element types)")
    print("  - Checking if COD formulas are in reduced form")
    print("  - Trying different COD structures")
else:
    # For each COD structure, count how many MP candidates share the same formula
    matching_stats = []
    
    for _, cod_row in cod_df.iterrows():
        formula = cod_row['formula']
        space_group = cod_row['space_group']
        
        # Count MP candidates with same formula
        formula_matches = mp_df[mp_df['source_cod_formula'] == formula]
        n_formula_matches = len(formula_matches)
        
        # Count MP candidates with same formula AND space group
        if pd.notna(space_group):
            sg_matches = formula_matches[formula_matches['space_group'] == space_group]
            n_sg_matches = len(sg_matches)
        else:
            n_sg_matches = n_formula_matches  # Can't filter by SG if we don't have it
        
        matching_stats.append({
            "cod_id": cod_row['cod_id'],
            "formula": formula,
            "space_group": space_group,
            "mp_formula_matches": n_formula_matches,
            "mp_sg_matches": n_sg_matches
        })
    
    stats_df = pd.DataFrame(matching_stats)
    
    # Calculate totals
    total_formula_comparisons = stats_df['mp_formula_matches'].sum()
    total_sg_comparisons = stats_df['mp_sg_matches'].sum()
    
    avg_formula_matches = stats_df['mp_formula_matches'].mean()
    avg_sg_matches = stats_df['mp_sg_matches'].mean()
    
    # Count how many COD structures have at least one MP candidate
    cod_with_matches = (stats_df['mp_sg_matches'] > 0).sum()
    
    print("Matching Requirements:")
    print("-"*80)
    print(f"COD structures total: {len(cod_df)}")
    print(f"COD structures with MP candidates: {cod_with_matches} ({cod_with_matches/len(cod_df)*100:.1f}%)")
    print(f"MP candidate structures: {len(mp_df)}")
    print()
    print("Without pre-filtering (formula only):")
    print(f"  Total comparisons needed: {total_formula_comparisons:,}")
    print(f"  Average candidates per COD structure: {avg_formula_matches:.1f}")
    print()
    print("With space group pre-filtering:")
    print(f"  Total comparisons needed: {total_sg_comparisons:,}")
    print(f"  Average candidates per COD structure: {avg_sg_matches:.1f}")
    print()
    
    # Time estimates
    time_per_comparison = 0.2  # seconds (conservative estimate)
    
    print("Time Estimates (at 0.2 sec per structure comparison):")
    print("-"*80)
    print("With space group filtering:")
    time_serial = total_sg_comparisons * time_per_comparison
    print(f"  Serial (1 core): {time_serial/60:.1f} minutes ({time_serial/3600:.2f} hours)")
    print(f"  Parallel (4 cores): {time_serial/(4*60):.1f} minutes")
    print(f"  Parallel (10 cores): {time_serial/(10*60):.1f} minutes")
    print()
    
    # Show some examples
    print("Example matching cases (structures with most MP candidates):")
    print("-"*80)
    print(stats_df.nlargest(5, 'mp_sg_matches')[['cod_id', 'formula', 'space_group', 'mp_sg_matches']])
    print()
    
    print("Example matching cases (structures with fewest MP candidates):")
    print("-"*80)
    subset = stats_df[stats_df['mp_sg_matches'] > 0]
    if len(subset) > 0:
        print(subset.nsmallest(5, 'mp_sg_matches')[['cod_id', 'formula', 'space_group', 'mp_sg_matches']])
    else:
        print("  (No structures with matches)")
    print()
    
    # Save statistics
    stats_df.to_csv("matching_statistics.csv", index=False)
    print("✓ Saved to: matching_statistics.csv")
    print()
    
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print(f"✓ Retrieved {len(cod_df)} COD structures via OPTIMADE")
    print(f"✓ Found {len(mp_df)} MP candidate structures")
    print(f"✓ {cod_with_matches} COD structures have potential MP matches")
    print(f"✓ Estimated {total_sg_comparisons:,} structure comparisons needed")
    if total_sg_comparisons > 0:
        print(f"✓ Estimated time: ~{time_serial/(10*60):.0f} minutes (10 cores)")
    print()
    print("Next step: Run structure matching to build COD-MP mapping")