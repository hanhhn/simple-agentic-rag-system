#!/bin/bash
# Start Celery worker for background task processing

set -e

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Change to project root
cd "$PROJECT_ROOT"

# Try to activate conda environment first, then venv
if command -v conda &> /dev/null; then
    if conda env list | grep -q "simple-rag-system"; then
        echo "Activating conda environment: simple-rag-system"
        source "$(conda info --base)/etc/profile.d/conda.sh"
        conda activate simple-rag-system
    fi
fi

# Activate virtual environment if conda not available or not activated
if [ -z "$CONDA_DEFAULT_ENV" ]; then
    if [ -d "venv" ]; then
        source venv/bin/activate
    elif [ -d ".venv" ]; then
        source .venv/bin/activate
    fi
fi

# Set environment variables if not set
export CELERY_BROKER_URL="${CELERY_BROKER_URL:-redis://localhost:6379/0}"
export CELERY_RESULT_BACKEND="${CELERY_RESULT_BACKEND:-redis://localhost:6379/0}"

# Start Celery worker
echo "Starting Celery worker..."
echo "Broker: $CELERY_BROKER_URL"
echo "Backend: $CELERY_RESULT_BACKEND"

celery -A src.tasks.celery_app worker \
    --loglevel=info \
    --queues=documents,embeddings \
    --concurrency=4 \
    --max-tasks-per-child=1000 \
    --time-limit=3600 \
    --soft-time-limit=3000
