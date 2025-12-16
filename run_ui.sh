#!/bin/bash
# Quick start script for AI Investment Agent Web UI

set -e

echo "🚀 Starting AI Investment Agent Web UI..."
echo ""

# Check if we're in the project root
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found"
    echo "Please create .env file with required API keys:"
    echo "  - GOOGLE_API_KEY"
    echo "  - TAVILY_API_KEY"
    echo "  - FINNHUB_API_KEY"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if poetry is available
if command -v poetry &> /dev/null; then
    echo "📦 Using Poetry to run Streamlit..."
    poetry run streamlit run ui/app.py
else
    echo "📦 Using direct Python to run Streamlit..."
    python -m streamlit run ui/app.py
fi
