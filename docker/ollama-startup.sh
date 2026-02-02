#!/bin/bash
set -e

# Ollama startup script
# This script pulls the configured model on startup

MODEL="${OLLAMA_MODEL:-llama2}"

echo "=========================================="
echo "Starting Ollama service..."
echo "=========================================="
echo "OLLAMA_MODEL: ${MODEL}"
echo "OLLAMA_KEEP_ALIVE: ${OLLAMA_KEEP_ALIVE:-24h}"
echo "=========================================="

# Start Ollama in background
echo "Starting Ollama server..."
/bin/ollama serve &
OLLAMA_PID=$!

# Give Ollama time to start
echo "Waiting for Ollama server to initialize..."
sleep 15

# Wait for Ollama to be ready by trying to list models
echo "Waiting for Ollama to be ready..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
  if ollama list > /dev/null 2>&1; then
    echo "✓ Ollama is ready!"
    break
  fi
  RETRY_COUNT=$((RETRY_COUNT + 1))
  echo "Waiting... ($RETRY_COUNT/$MAX_RETRIES)"
  sleep 3
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
  echo "✗ Ollama server failed to start after ${MAX_RETRIES} retries"
  exit 1
fi

# Pull configured model if it doesn't exist
echo ""
echo "=========================================="
echo "Checking for model: ${MODEL}"
echo "=========================================="

# Check if model exists
if ! ollama list | grep -q "${MODEL}"; then
  echo "Model '${MODEL}' not found locally. Pulling from Ollama library..."
  echo "This may take several minutes depending on your internet connection..."
  if ollama pull "${MODEL}"; then
    echo "✓ Model '${MODEL}' pulled successfully!"
  else
    echo "✗ Failed to pull model '${MODEL}'"
    exit 1
  fi
else
  echo "✓ Model '${MODEL}' already exists locally."
fi

# Show available models
echo ""
echo "=========================================="
echo "Available models:"
echo "=========================================="
ollama list

echo ""
echo "=========================================="
echo "Ollama is fully initialized!"
echo "Model: ${MODEL}"
echo "API: http://localhost:11434"
echo "=========================================="

# Keep container running by waiting on background process
wait $OLLAMA_PID
