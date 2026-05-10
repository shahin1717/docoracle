#!/bin/bash

set -e

echo "======================================"
echo "      Ollama Setup for DocOracle"
echo "======================================"

# -------------------------------
# Check if Ollama exists
# -------------------------------
if command -v ollama &> /dev/null; then
    echo "✅ Ollama already installed"
else
    echo "⬇️ Installing Ollama..."

    OS="$(uname -s)"

    if [[ "$OS" == "Linux" ]]; then
        curl -fsSL https://ollama.com/install.sh | sh
    elif [[ "$OS" == "Darwin" ]]; then
        if ! command -v brew &> /dev/null; then
            echo "❌ Homebrew not found. Install brew first."
            exit 1
        fi
        brew install ollama
    else
        echo "❌ Unsupported OS: $OS"
        exit 1
    fi
fi

echo "🧠 Starting Ollama service..."

# start ollama in background if not running
if pgrep -f "ollama serve" > /dev/null; then
    echo "✅ Ollama already running"
else
    nohup ollama serve > ollama.log 2>&1 &
    sleep 3
fi

# -------------------------------
# Required models for your RAG
# -------------------------------

echo "📦 Pulling required models..."

# LLM for chat
ollama pull mistral:7b-instruct-q8_0

# Embedding model for RAG
ollama pull nomic-embed-text

echo ""
echo "======================================"
echo "✅ Ollama setup complete!"
echo "Models installed:"
echo "  - mistral:7b-instruct-q8_0"
echo "  - nomic-embed-text"
echo "======================================"