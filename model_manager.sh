#!/bin/bash

# Ensure we're in the project root
cd "$(dirname "$0")"

# Source conda init to make sure 'conda activate' works in the script
source "$(conda info --base)/etc/profile.d/conda.sh"

echo "Activating docoracle environment..."
conda activate docoracle

echo "Running Model Manager..."
python ai/model_manager.py
