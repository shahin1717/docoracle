#!/bin/bash

set -e

echo "🚀 DocOracle Universal Setup"
echo "============================="

OS="$(uname -s)"
ARCH="$(uname -m)"

echo "🔍 Detected OS: $OS ($ARCH)"

# ── 1. Conda Check & Install ────────────────────────────────────────────────
if ! command -v conda &> /dev/null; then
    echo "⚠️  Conda not found. Installing Miniconda..."
    if [[ "$OS" == "Linux" ]]; then
        if [[ "$ARCH" == "aarch64" || "$ARCH" == "arm64" ]]; then
            curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-aarch64.sh
            bash Miniconda3-latest-Linux-aarch64.sh -b -p "$HOME/miniconda3"
            rm Miniconda3-latest-Linux-aarch64.sh
        else
            curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
            bash Miniconda3-latest-Linux-x86_64.sh -b -p "$HOME/miniconda3"
            rm Miniconda3-latest-Linux-x86_64.sh
        fi
        eval "$($HOME/miniconda3/bin/conda shell.bash hook)"
        
    elif [[ "$OS" == "Darwin" ]]; then
        if [[ "$ARCH" == "arm64" ]]; then
            curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh
            bash Miniconda3-latest-MacOSX-arm64.sh -b -p "$HOME/miniconda3"
            rm Miniconda3-latest-MacOSX-arm64.sh
        else
            curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh
            bash Miniconda3-latest-MacOSX-x86_64.sh -b -p "$HOME/miniconda3"
            rm Miniconda3-latest-MacOSX-x86_64.sh
        fi
        eval "$($HOME/miniconda3/bin/conda shell.bash hook)"
        
    elif [[ "$OS" == MINGW* || "$OS" == MSYS* || "$OS" == CYGWIN* ]]; then
        echo "⚠️  Windows detected. Downloading Miniconda installer..."
        curl -o miniconda.exe https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe
        echo "⚙️  Installing silently... (This may take a minute)"
        start /wait "" miniconda.exe /InstallationType=JustMe /RegisterPython=0 /S /D=%UserProfile%\\Miniconda3
        rm miniconda.exe
        export PATH="$USERPROFILE/Miniconda3/Scripts:$USERPROFILE/Miniconda3:$PATH"
        eval "$($USERPROFILE/Miniconda3/Scripts/conda.exe shell.bash hook)"
    else
        echo "❌ Unsupported OS for automated Conda install: $OS"
        exit 1
    fi
    echo "✅ Conda installed successfully!"
else
    echo "✅ Conda is already installed."
    # Initialize in this script context if not already
    eval "$(conda shell.bash hook 2>/dev/null || true)"
fi

# ── 2. Environment Setup ────────────────────────────────────────────────────
echo ""
echo "📦 Setting up Python Environment"

# Loop until a valid, non-existing environment name is provided
while true; do
    read -p "Enter a name for the new Conda environment (default: docoracle): " ENV_NAME
    ENV_NAME=${ENV_NAME:-docoracle}
    
    # Check if env exists
    if conda env list | awk '{print $1}' | grep -q "^${ENV_NAME}$"; then
        echo "❌ Environment '$ENV_NAME' already exists! Please choose another name."
    else
        echo "✅ Name '$ENV_NAME' is available."
        break
    fi
done

echo "⚙️  Creating environment '$ENV_NAME' from environment.yml..."
# Create a temporary environment.yml with the selected name
sed "s/name:.*/name: $ENV_NAME/" environment.yml > temp_env.yml
conda env create -f temp_env.yml
rm temp_env.yml

echo "🔧 Activating environment '$ENV_NAME'..."
conda activate "$ENV_NAME"

# Install extras
pip install --upgrade pip
pip install fastapi uvicorn requests tqdm

# ── 3. Ollama Install ───────────────────────────────────────────────────────
echo ""
echo "🦙 Checking Ollama Installation..."
if ! command -v ollama &> /dev/null; then
    echo "⚠️  Ollama not found. Installing..."
    if [[ "$OS" == "Linux" ]]; then
        curl -fsSL https://ollama.com/install.sh | sh
    elif [[ "$OS" == "Darwin" ]]; then
        if ! command -v brew &> /dev/null; then
            echo "❌ Homebrew not found. Please install brew or download Ollama manually from ollama.com"
        else
            brew install ollama
        fi
    elif [[ "$OS" == MINGW* || "$OS" == MSYS* || "$OS" == CYGWIN* ]]; then
        echo "⚠️  Downloading Ollama for Windows..."
        curl -o OllamaSetup.exe https://ollama.com/download/OllamaSetup.exe
        echo "⚙️  Installing Ollama..."
        ./OllamaSetup.exe /S
        rm OllamaSetup.exe
        export PATH="$LOCALAPPDATA/Programs/Ollama:$PATH"
    fi
    echo "✅ Ollama installed!"
else
    echo "✅ Ollama is already installed."
fi

# Start Ollama service if needed
echo "🚀 Ensuring Ollama is running..."
if [[ "$OS" == "Linux" || "$OS" == "Darwin" ]]; then
    if ! pgrep -f "ollama serve" > /dev/null; then
        nohup ollama serve > ollama.log 2>&1 &
        sleep 3
    fi
elif [[ "$OS" == MINGW* || "$OS" == MSYS* ]]; then
    # On Windows, ollama app runs in background
    if ! tasklist | grep -q "ollama app.exe"; then
        start "" "ollama app.exe"
        sleep 5
    fi
fi

# Wait for Ollama API to be responsive
echo "⏳ Waiting for Ollama API..."
for i in {1..10}; do
    if curl -s http://localhost:11434/api/tags > /dev/null; then
        echo "✅ Ollama API is ready!"
        break
    fi
    sleep 2
    if [ "$i" -eq 10 ]; then
        echo "⚠️  Ollama API did not respond in time. Continuing anyway..."
    fi
done

# ── 4. Model Setup ──────────────────────────────────────────────────────────
echo ""
echo "🧠 Hardware Analysis & Model Download"
if [ -f "ai/model_manager.py" ]; then
    python ai/model_manager.py
else
    echo "❌ ai/model_manager.py not found!"
fi

echo ""
echo "============================="
echo "🎉 Setup Complete!"
echo "To start the application, run:"
echo "  bash run.sh"
echo "============================="
