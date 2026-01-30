#!/bin/bash
# Extract phase 3 energies and calculate formation energies for Cu-Mg alloys

OUTPUT_RAW="energies_raw.dat"
OUTPUT_FORM="formation_energies.dat"

echo "Extracting phase 3 energies from workflow_results.json files..."
echo ""

# Create header for raw energies file
echo "# Cu_percent  Energy(Ry)" > $OUTPUT_RAW

# Array to store energies
declare -A energies

# Check if jq is available
USE_JQ=false
if command -v jq &> /dev/null; then
    USE_JQ=true
fi

# Loop through all composition folders
for dir in Cu*_Mg*/; do
    # Remove trailing slash
    dir=${dir%/}
    
    # Extract Cu and Mg percentages from folder name
    if [[ $dir =~ Cu([0-9]+)_Mg([0-9]+) ]]; then
        cu_percent=${BASH_REMATCH[1]}
        mg_percent=${BASH_REMATCH[2]}
        
        # Look for workflow_results.json file
        json_file="$dir/workflow_results.json"
        
        if [ -f "$json_file" ]; then
            if [ "$USE_JQ" = true ]; then
                # Use jq to extract energy (try final_energy first, then fallbacks)
                energy=$(jq -r '.final_energy // .total_energy // .energy // empty' "$json_file" 2>/dev/null)
            else
                # Fallback: use grep and sed (less robust but works without jq)
                # Look for final_energy specifically
                energy=$(grep -o '"final_energy"[[:space:]]*:[[:space:]]*[-+0-9.eE]*' "$json_file" | grep -Eo '[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?' | head -1)
                
                # If not found, try generic energy field
                if [ -z "$energy" ]; then
                    energy=$(grep -o '"energy"[[:space:]]*:[[:space:]]*[-+0-9.eE]*' "$json_file" | grep -Eo '[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?' | head -1)
                fi
            fi
            
            if [ -n "$energy" ] && [ "$energy" != "null" ]; then
                energies[$cu_percent]=$energy
                printf "%-15s Cu: %3d%%  Energy: %12.6f Ry\n" "$dir" "$cu_percent" "$energy"
                echo "$cu_percent  $energy" >> $OUTPUT_RAW
            else
                echo "$dir: Energy not found in $json_file"
            fi
        else
            echo "$dir: No workflow_results.json file found"
        fi
    fi
done

# Sort the raw energies file
sort -n $OUTPUT_RAW -o $OUTPUT_RAW

echo ""
echo "Raw energies saved to: $OUTPUT_RAW"

# Check if we have pure element energies
if [ -z "${energies[0]}" ] || [ -z "${energies[100]}" ]; then
    echo ""
    echo "Warning: Missing pure element energies (Cu0_Mg100 or Cu100_Mg0)"
    echo "Cannot calculate formation energies without reference states."
    exit 1
fi

# Get reference energies
E_Cu=${energies[100]}
E_Mg=${energies[0]}

echo ""
echo "========================================================"
echo "Reference energies:"
echo "  E(Cu 100%) = $E_Cu Ry"
echo "  E(Mg 100%) = $E_Mg Ry"
echo "========================================================"
echo ""
echo "Formation Energies:"
echo "--------------------------------------------------------"

# Calculate formation energies
echo "# Cu_percent  FormationEnergy(Ry)" > $OUTPUT_FORM

for cu_percent in "${!energies[@]}"; do
    mg_percent=$((100 - cu_percent))
    conc_Cu=$(echo "scale=6; $cu_percent / 100" | bc)
    conc_Mg=$(echo "scale=6; $mg_percent / 100" | bc)
    
    E_alloy=${energies[$cu_percent]}
    
    # Calculate formation energy: E(Cu,Mg) - E(Cu)*conc_Cu - E(Mg)*conc_Mg
    E_form=$(echo "scale=8; $E_alloy - $E_Cu * $conc_Cu - $E_Mg * $conc_Mg" | bc)
    
    printf "Cu%3d_Mg%3d  E_form = %12.8f Ry\n" "$cu_percent" "$mg_percent" "$E_form"
    echo "$cu_percent  $E_form" >> $OUTPUT_FORM
done

# Sort the formation energies file
sort -n $OUTPUT_FORM -o $OUTPUT_FORM

echo ""
echo "Formation energies saved to: $OUTPUT_FORM"
echo ""
echo "To plot the results, run the Python script:"
echo "  python plot_formation_energy.py"
