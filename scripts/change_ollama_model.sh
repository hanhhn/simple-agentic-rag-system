#!/bin/bash
# Script to change the Ollama model used in the RAG system
# Usage: ./scripts/change_ollama_model.sh <model_name>
# Example: ./scripts/change_ollama_model.sh mistral

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <model_name>"
    echo ""
    echo "Change the Ollama model used by the RAG system."
    echo ""
    echo "Available models can be found at: https://ollama.com/library"
    echo ""
    echo "Common models:"
    echo "  - llama2 (default, ~3.8 GB)"
    echo "  - mistral (~4.1 GB)"
    echo "  - llama3 (~4.7 GB)"
    echo "  - phi (~2.3 GB)"
    echo "  - codellama (~3.8 GB)"
    echo ""
    echo "Example:"
    echo "  $0 mistral"
    exit 1
fi

MODEL_NAME="$1"

echo "=========================================="
echo "Changing Ollama model to: $MODEL_NAME"
echo "=========================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found. Please copy env.example to .env first."
    exit 1
fi

# Update OLLAMA_MODEL in .env
if grep -q "^OLLAMA_MODEL=" .env; then
    echo "Updating OLLAMA_MODEL in .env..."
    sed -i.bak "s/^OLLAMA_MODEL=.*/OLLAMA_MODEL=$MODEL_NAME/" .env
    rm .env.bak
else
    echo "Adding OLLAMA_MODEL to .env..."
    echo "OLLAMA_MODEL=$MODEL_NAME" >> .env
fi

# Update OLLAMA_MODEL in docker-compose.yml
if grep -q "OLLAMA_MODEL=llama2" docker-compose.yml; then
    echo "Updating OLLAMA_MODEL in docker-compose.yml..."
    sed -i.bak "s/- OLLAMA_MODEL=.*/- OLLAMA_MODEL=$MODEL_NAME/" docker-compose.yml
    rm docker-compose.yml.bak
elif grep -q "^- OLLAMA_MODEL=" docker-compose.yml; then
    echo "Updating OLLAMA_MODEL in docker-compose.yml..."
    sed -i.bak "s/^- OLLAMA_MODEL=.*/- OLLAMA_MODEL=$MODEL_NAME/" docker-compose.yml
    rm docker-compose.yml.bak
else
    echo "Warning: Could not find OLLAMA_MODEL in docker-compose.yml"
fi

echo ""
echo "✓ Configuration updated!"
echo ""
echo "To apply the changes, restart the Ollama container:"
echo "  docker-compose restart ollama"
echo ""
echo "Or restart all services:"
echo "  docker-compose down"
echo "  docker-compose up -d"
echo ""
echo "=========================================="
