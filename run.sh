#!/bin/bash

set -e

echo "======================================"
echo "      DocOracle Full Startup"
echo "======================================"

# -------------------------------
# Cleanup on exit
# -------------------------------
cleanup() {
    echo ""
    echo "🛑 Shutting down DocOracle..."
    if [ -n "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    exit 0
}
trap cleanup SIGINT SIGTERM

# -------------------------------
# 1. Start application
# -------------------------------
echo "Ensuring Conda environment is active..."

# Try to find conda and activate environment
if command -v conda &> /dev/null; then
    eval "$(conda shell.bash hook)"
    
    # Check if we should prompt or default
    read -p "Enter your Conda environment name (default: docoracle): " ENV_NAME
    ENV_NAME=${ENV_NAME:-docoracle}
    
    conda activate "$ENV_NAME" || echo "Warning: $ENV_NAME env not found"
else
    echo "Warning: conda not found in PATH"
fi

# -------------------------------
# 2. Start backend
# -------------------------------
echo ""
echo "🚀 Starting backend"
echo "--------------------------------------"

uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# -------------------------------
# 3. Start frontend (if exists)
# -------------------------------
if [ -d "frontend" ]; then
    echo ""
    echo "🌐 Starting frontend"
    echo "--------------------------------------"

    cd frontend
    npm install
    npm run dev &
    FRONTEND_PID=$!
    cd ..
fi

# -------------------------------
# Summary
# -------------------------------
echo ""
echo "======================================"
echo "🚀 DocOracle is running!"
echo "Backend PID : $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo "======================================"

wait