#!/usr/bin/env python3
"""
Script to create .env file from .env.example for local development.
"""
import shutil
from pathlib import Path

def setup_env():
    """Copy .env.example to .env if it doesn't exist."""
    root_dir = Path(__file__).parent.parent
    env_example = root_dir / "env.example"
    env_file = root_dir / ".env"
    
    if not env_example.exists():
        print(f"❌ env.example file not found at {env_example}")
        return False
    
    if env_file.exists():
        print(f"⚠️  .env file already exists at {env_file}")
        response = input("Do you want to overwrite it? (y/N): ").strip().lower()
        if response != 'y':
            print("❌ Cancelled. .env file was not changed.")
            return False
    
    try:
        shutil.copy(env_example, env_file)
        print(f"✅ Created .env file at {env_file}")
        print("📝 Please review and edit the values in .env file if needed.")
        return True
    except Exception as e:
        print(f"❌ Error creating .env file: {e}")
        return False

if __name__ == "__main__":
    setup_env()
