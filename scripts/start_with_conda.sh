#!/bin/bash
# Script to start the application with conda environment

set -e

echo "Checking conda environment..."

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo "❌ Conda is not found in PATH. Please install conda or add it to PATH."
    exit 1
fi

# Check if environment exists
if ! conda env list | grep -q "simple-rag-system"; then
    echo "⚠️  Conda environment 'simple-rag-system' not found."
    echo "Creating environment from environment.yml..."
    conda env create -f environment.yml
    if [ $? -ne 0 ]; then
        echo "❌ Failed to create conda environment."
        exit 1
    fi
fi

# Activate environment
echo "Activating conda environment..."
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate simple-rag-system

if [ $? -ne 0 ]; then
    echo "❌ Failed to activate conda environment."
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating from env.example..."
    if [ -f "env.example" ]; then
        cp env.example .env
        echo "✅ Created .env file. Please review and edit if needed."
    else
        echo "❌ env.example file not found. Please create .env manually."
        exit 1
    fi
fi

# Start the application
echo ""
echo "✅ Conda environment activated: simple-rag-system"
echo "📝 Make sure Qdrant, Ollama, and Redis are running"
echo "🚀 Starting FastAPI server..."
echo ""

uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
