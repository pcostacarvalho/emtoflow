# %%
from mp_api.client import MPRester
import json

# Replace with your actual API key
API_KEY = "vhdPJ1STyEi4znoIbrdg6s1j2Q03BQdH"

# %%
# Read ICSD entries
with open('full_icsd_entries.txt', 'r') as f:
    icsd_entries = [line.strip() for line in f]



# %%
# Build ICSD to MP mapping
with MPRester(API_KEY) as mpr:
    mp_docs = mpr.materials.summary.search(        
        theoretical=False,
        fields=["database_IDs", "material_id"])

# %%

# Build ICSD to MP mapping
with MPRester(API_KEY) as mpr:

    icsd_to_mpid = {}
    for mp_doc in mp_docs:
        mpid = str(mp_doc.material_id)
        for icsd_id in mp_doc.database_IDs.get("icsd", []):
            if icsd_id not in icsd_to_mpid:
                id = icsd_id.replace('icsd-','').zfill(6)
                icsd_to_mpid[id] = []
            icsd_to_mpid[id].append(mpid)

# %%
# Find matches
found = []
not_found = []

for icsd in icsd_entries:
    if icsd in icsd_to_mpid:
        found.append((icsd, icsd_to_mpid[icsd]))
    else:
        not_found.append(icsd)

# Save results
with open('mp_found.txt', 'w') as f:
    for icsd, mpids in found:
        f.write(f"{icsd}: {','.join(mpids)}\n")

with open('mp_full_icsd.txt', 'w') as f:
    for icsd, mpids in icsd_to_mpid.items():
        f.write(f"{icsd}: {','.join(mpids)}\n")


print(f"Found in MP: {len(found)}")
print(f"Not found: {len(not_found)}")


# %%

# Invert the dictionary - use ONLY found entries
mpid_to_icsd = {}
for icsd_id, mp_ids in found:
    for mp_id in mp_ids:
        if mp_id not in mpid_to_icsd:
            mpid_to_icsd[mp_id] = []
        mpid_to_icsd[mp_id].append(icsd_id)

# Filter for MP IDs with only one ICSD entry
filtered_mpid_to_icsd = {
    mp_id: icsd_ids 
    for mp_id, icsd_ids in mpid_to_icsd.items() 
    if len(icsd_ids) == 1
}

# Save results
with open('only_one_entry.txt', 'w') as f:
    for mpids, icsd in filtered_mpid_to_icsd.items():
        f.write(f"{mpids}: {icsd[0]}\n")

# %% [markdown]
# # Parsing the theoretical structures from Materials Project

# %%

with MPRester(API_KEY) as mpr:
    # Get structures for ICSD IDs
    docs = mpr.materials.summary.search(
        theoretical=False,
        fields=["material_id", "database_IDs", "structure", 'nsites', 
                'elements', 'nelements', 'composition', 'composition_reduced', 
                'formula_pretty', 'formula_anonymous', 'chemsys', 'volume', 'density', 
                'density_atomic', 'symmetry', 'origins', 'task_ids', 'formation_energy_per_atom', 
                'is_stable', 'band_gap', 'cbm', 'vbm', 'efermi', 'is_gap_direct', 'is_metal', 
                 'is_magnetic', 'ordering', 'total_magnetization', 
                 'theoretical'])

# %%
selected_icsd = [i[0] for i in filtered_mpid_to_icsd.values()]

with open('icsd_structures.json', 'r') as f:
    experimental = json.load(f)

with MPRester(API_KEY) as mpr:

    selected_docs = {}
    for doc in docs:
        for icsd_id in doc.database_IDs.get("icsd", []):
            id = icsd_id.replace('icsd-','').zfill(6)

            if id in selected_icsd:
                selected_docs[id] = {'MP': {}, 'ICSD': {}}
                selected_docs[id]['MP'] = doc
                selected_docs[id]['ICSD'] = experimental[id]



# %%
import json

# Convert MP objects to dictionaries
selected_docs_serializable = {}
for icsd_id, data in selected_docs.items():
    selected_docs_serializable[icsd_id] = {
        'MP': data['MP'].dict() if hasattr(data['MP'], 'dict') else data['MP'],
        'ICSD': data['ICSD']
    }

# Save to JSON
with open('theoretical_experimental_structures.json', 'w') as f:
    json.dump(selected_docs_serializable, f, indent=2)

# %%
selected_docs_serializable

# %%



