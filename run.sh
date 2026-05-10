#!/bin/bash

set -e

echo "======================================"
echo "      DocOracle Full Startup"
echo "======================================"

# -------------------------------
# 1. Conda setup
# -------------------------------
echo ""
echo "🧱 Step 1: Conda setup"
echo "--------------------------------------"

bash ./conda.sh

# reload conda into current shell
source "$HOME/miniconda3/etc/profile.d/conda.sh"

ENV_NAME="docoracle"

conda activate "$ENV_NAME"

echo "✅ Conda environment activated"

# -------------------------------
# 2. Python environment setup
# -------------------------------
echo ""
echo "📦 Step 2: Python project setup"
echo "--------------------------------------"

bash ./setup_env.sh

# -------------------------------
# 3. Ollama setup
# -------------------------------
echo ""
echo "🧠 Step 3: Ollama setup"
echo "--------------------------------------"

bash ./ollama.sh

# -------------------------------
# 4. Start backend
# -------------------------------
echo ""
echo "🚀 Step 4: Starting backend"
echo "--------------------------------------"

cd backend
 uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
cd ..

# -------------------------------
# 5. Start frontend (if exists)
# -------------------------------
if [ -d "frontend" ]; then
    echo ""
    echo "🌐 Step 5: Starting frontend"
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