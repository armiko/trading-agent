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

# Check 9Router
    echo "[3/6] Checking 9Router installation..."
    if command -v 9router &> /dev/null; then
        echo "✓ 9Router found"
    else
        echo "⚠ 9Router not found. Install: npm install -g 9router"
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
echo "  1. Make sure 9Router is running: 9router"
echo "  2. Start trading: python3 trade.py start"
echo ""
