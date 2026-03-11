#!/usr/bin/env bash

# Example workflow for Cu2Mg Laves phase:
# 1) Generate composition-specific YAMLs from the master config
# 2) Run prepare-only input generation for a selected composition (Cu60_Mg40)


echo "=== Step 1: Generate composition YAMLs ==="
emtoflow-generate-percentages Cu2Mg_laves_example.yaml

echo
echo "=== Step 2: Run prepare-only workflow for Cu60_Mg40 ==="
emtoflow-opt emto_inputs_Cu2Mg_laves/Cu60_Mg40.yaml

echo
echo "Done. Check the Cu60_Mg40 output directory for generated EMTO input files."