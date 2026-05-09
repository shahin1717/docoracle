#!/bin/bash

set -e

echo "🔧 Detecting OS..."

OS="$(uname -s)"
ARCH="$(uname -m)"

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

echo "⬇️ Downloading Miniconda..."
curl -LO "$URL"

echo "📦 Installing Miniconda..."

bash "$INSTALLER" -b -p "$HOME/miniconda3"

echo "🧠 Initializing conda..."

# Initialize for bash and zsh
"$HOME/miniconda3/bin/conda" init bash
"$HOME/miniconda3/bin/conda" init zsh || true

echo "🧹 Cleaning up..."
rm "$INSTALLER"

echo "✅ Conda installed successfully!"
echo ""
echo "👉 IMPORTANT: restart your terminal or run:"
echo "source ~/.bashrc"
echo ""
echo "Then verify with:"
echo "conda --version"