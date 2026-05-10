#!/bin/bash

set -e

ENV_FILE="environment.yml"
ENV_NAME="docoracle"

echo "🚀 DocOracle Environment Setup"
echo "================================"

# ─────────────────────────────────────────────
# 1. Check Conda
# ─────────────────────────────────────────────
if ! command -v conda &> /dev/null; then
    echo "❌ Conda is not installed or not in PATH"
    echo "👉 Run install_conda.sh first"
    exit 1
fi

# Initialize conda in shell
source "$(conda info --base)/etc/profile.d/conda.sh"

# ─────────────────────────────────────────────
# 2. Check environment.yml
# ─────────────────────────────────────────────
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ $ENV_FILE not found in project root"
    exit 1
fi

# ─────────────────────────────────────────────
# 3. Remove old environment (safe reset)
# ─────────────────────────────────────────────
if conda env list | grep -q "$ENV_NAME"; then
    echo "⚠️ Existing environment found: $ENV_NAME"
    echo "🧹 Removing old environment..."
    conda env remove -n "$ENV_NAME" -y
fi

# ─────────────────────────────────────────────
# 4. Create environment from YAML
# ─────────────────────────────────────────────
echo "📦 Creating Conda environment from $ENV_FILE..."
conda env create -f "$ENV_FILE"

# ─────────────────────────────────────────────
# 5. Activate environment
# ─────────────────────────────────────────────
echo "🔧 Activating environment..."
conda activate "$ENV_NAME"

# ─────────────────────────────────────────────
# 6. Verify Python
# ─────────────────────────────────────────────
PYTHON_VERSION=$(python --version 2>&1)
echo "🐍 Python installed: $PYTHON_VERSION"

# ─────────────────────────────────────────────
# 7. Install extra pip dependencies (if needed)
# ─────────────────────────────────────────────
echo "📥 Installing extra runtime dependencies..."

pip install --upgrade pip

pip install \
    fastapi \
    uvicorn \
    requests \
    tqdm

# ─────────────────────────────────────────────
# 8. Final message
# ─────────────────────────────────────────────
echo ""
echo "✅ Environment setup complete!"
echo "================================"
echo "👉 Activate with:"
echo "   conda activate $ENV_NAME"
echo ""
echo "👉 Next step (IMPORTANT):"
echo "   run Ollama: ollama serve"
echo "   pull models: ollama pull mistral:7b-instruct-q8_0"
echo "                ollama pull nomic-embed-text"
echo ""