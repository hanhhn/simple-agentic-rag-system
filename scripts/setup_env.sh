#!/bin/bash
# Script to create .env file from .env.example for Linux/Mac

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_EXAMPLE="$ROOT_DIR/env.example"
ENV_FILE="$ROOT_DIR/.env"

if [ ! -f "$ENV_EXAMPLE" ]; then
    echo "❌ .env.example file not found at $ENV_EXAMPLE"
    exit 1
fi

if [ -f "$ENV_FILE" ]; then
    echo "⚠️  .env file already exists at $ENV_FILE"
    read -p "Do you want to overwrite it? (y/N): " OVERWRITE
    if [ "$OVERWRITE" != "y" ] && [ "$OVERWRITE" != "Y" ]; then
        echo "❌ Cancelled. .env file was not changed."
        exit 0
    fi
fi

cp "$ENV_EXAMPLE" "$ENV_FILE"
if [ $? -eq 0 ]; then
    echo "✅ Created .env file at $ENV_FILE"
    echo "📝 Please review and edit the values in .env file if needed."
    exit 0
else
    echo "❌ Error creating .env file"
    exit 1
fi
