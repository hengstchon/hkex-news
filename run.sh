#!/bin/bash
# HKEX Monitor Runner Script
# This script sets up the environment and runs the monitor

set -e

echo "HKEX New Listings Monitor"
echo "========================"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ Error: uv is not installed"
    echo "Please install uv: https://github.com/astral-sh/uv"
    exit 1
fi

echo "✓ uv found"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv
fi

# Install dependencies
echo "Installing dependencies..."
uv pip install -r requirements.txt

# Check config file exists
if [ ! -f "config.json" ]; then
    echo "❌ Error: config.json not found"
    echo "Please create config.json with your Telegram credentials"
    exit 1
fi

# Run the monitor
echo "Starting monitor..."
uv run python hkex_monitor.py
