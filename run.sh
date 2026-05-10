#!/bin/bash

set -e

echo "======================================"
echo "      DocOracle Full Startup"
echo "======================================"

# -------------------------------
# 1. Start application
# -------------------------------
echo "Ensuring Conda environment is active..."

# Try to find conda and activate docoracle
if command -v conda &> /dev/null; then
    eval "$(conda shell.bash hook)"
    conda activate docoracle || echo "Warning: docoracle env not found"
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