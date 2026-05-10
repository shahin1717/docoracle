#!/bin/bash

set -e

echo "🔧 Detecting OS..."

OS="$(uname -s)"
ARCH="$(uname -m)"

# -------------------------------
# Check if conda already exists
# -------------------------------
if command -v conda &> /dev/null; then
    echo "✅ Conda already installed. Skipping installation."
    conda --version
    exit 0
fi

echo "❌ Conda not found. Installing Miniconda..."

# -------------------------------
# Choose installer
# -------------------------------
if [[ "$OS" == "Linux" ]]; then
    INSTALLER="Miniconda3-latest-Linux-x86_64.sh"
elif [[ "$OS" == "Darwin" ]]; then
    if [[ "$ARCH" == "arm64" ]]; then
        INSTALLER="Miniconda3-latest-MacOSX-arm64.sh"
    else
        INSTALLER="Miniconda3-latest-MacOSX-x86_64.sh"
    fi
else
    echo "❌ Unsupported OS: $OS"
    exit 1
fi

URL="https://repo.anaconda.com/miniconda/$INSTALLER"

# -------------------------------
# Download
# -------------------------------
echo "⬇️ Downloading Miniconda..."
curl -LO "$URL"

# -------------------------------
# Install
# -------------------------------
echo "📦 Installing Miniconda..."

bash "$INSTALLER" -b -p "$HOME/miniconda3"

# -------------------------------
# Init shell support
# -------------------------------
echo "🧠 Initializing conda..."

"$HOME/miniconda3/bin/conda" init bash
"$HOME/miniconda3/bin/conda" init zsh || true

# -------------------------------
# Cleanup
# -------------------------------
echo "🧹 Cleaning up..."
rm "$INSTALLER"

echo "✅ Conda installed successfully!"
echo ""
echo "👉 IMPORTANT:"
echo "Restart terminal OR run:"
echo "  source ~/.bashrc"
echo "  source ~/.zshrc"
echo ""
echo "Verify with:"
echo "  conda --version"