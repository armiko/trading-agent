#!/bin/bash

echo "🤖 AI Trading Agent - Setup Script"
echo "==================================="
echo ""

# Check Python version
echo "[1/6] Checking Python version..."
python3 --version || { echo "Error: Python 3 not found"; exit 1; }

# Install dependencies
echo "[2/6] Installing Python dependencies..."
pip install -r requirements.txt || { echo "Error: Failed to install dependencies"; exit 1; }

# Check Ollama
echo "[3/6] Checking Ollama installation..."
if command -v ollama &> /dev/null; then
    echo "✓ Ollama found"
    ollama list
else
    echo "⚠ Ollama not found. Please install from https://ollama.com/download"
fi

# Initialize database
echo "[4/6] Initializing database..."
mkdir -p db
python3 -c "from core.database import init_database; init_database()" || { echo "Error: Failed to init database"; exit 1; }

# Check MT5 connection
echo "[5/6] Checking MT5 connection..."
python3 trade.py status

# Done
echo "[6/6] Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Make sure Ollama is running: ollama serve"
echo "  2. Pull a model: ollama pull qwen3:8b"
echo "  3. Start trading: python3 trade.py start"
echo ""
