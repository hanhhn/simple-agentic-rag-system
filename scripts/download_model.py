#!/usr/bin/env python3
"""
Download Granite embedding model to local cache.

This script downloads the Granite embedding model from Hugging Face and caches it locally.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.logging import get_logger
from src.core.config import get_config


logger = get_logger(__name__)


def download_granite_model():
    """Download Granite embedding model to local cache."""
    print("\n" + "="*70)
    print("Downloading Granite Embedding Model")
    print("="*70 + "\n")

    config = get_config()
    model_name = config.embedding.model_name  # Get from config: ibm-granite/granite-embedding-small-english-r2
    cache_dir = config.storage.model_cache_path

    print(f"Model: {model_name}")
    print(f"Cache directory: {cache_dir}")
    print(f"\nStarting download...\n")

    try:
        from sentence_transformers import SentenceTransformer

        # Download model
        print("Downloading model from Hugging Face...")
        model = SentenceTransformer(
            model_name,
            cache_folder=str(cache_dir)
        )

        # Get model info
        dimension = model.get_sentence_embedding_dimension()
        max_seq_length = model.max_seq_length if hasattr(model, 'max_seq_length') else 'unknown'

        print("\n" + "="*70)
        print("✓ Model downloaded successfully!")
        print("="*70 + "\n")
        print(f"Model name: {model_name}")
        print(f"Dimension: {dimension}")
        print(f"Max sequence length: {max_seq_length}")
        print(f"Cache location: {cache_dir}")
        print("\nModel is ready to use!\n")

        # Verify model location
        model_path = cache_dir / f"models--{model_name.replace('/', '--')}"
        if model_path.exists():
            print(f"Model files stored at: {model_path}")
            print(f"Total size: {_get_dir_size(model_path):.2f} MB\n")

        return model

    except Exception as e:
        print("\n" + "="*70)
        print("✗ Failed to download model")
        print("="*70 + "\n")
        print(f"Error: {e}")
        print(f"Error type: {type(e).__name__}\n")

        logger.error("Failed to download Granite model", error=str(e), exc_info=True)
        sys.exit(1)


def _get_dir_size(directory: Path) -> float:
    """Calculate directory size in MB."""
    total_size = 0
    for item in directory.rglob("*"):
        if item.is_file():
            total_size += item.stat().st_size
    return total_size / (1024 * 1024)  # Convert to MB


def verify_model():
    """Verify that model is downloaded and accessible."""
    print("\n" + "="*70)
    print("Verifying Granite Embedding Model")
    print("="*70 + "\n")

    try:
        from src.embedding.models.granite_embedding import GraniteEmbeddingModel

        # Initialize model (will load from cache if exists)
        print("Loading Granite model...")
        model = GraniteEmbeddingModel(lazy_load=False)

        # Test encoding
        print("\nTesting encoding...")
        test_text = "Hello, this is a test text"
        embedding = model.encode_single(test_text)

        print(f"✓ Model loaded successfully")
        print(f"✓ Encoding test passed")
        print(f"  - Test text: {test_text}")
        print(f"  - Embedding dimension: {len(embedding)}")
        print(f"  - First 5 values: {embedding[:5]}\n")

        return True

    except Exception as e:
        print(f"\n✗ Verification failed: {e}")
        logger.error("Model verification failed", error=str(e), exc_info=True)
        return False


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Download and verify Granite embedding model"
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download model (default: just verify)"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify model after download"
    )

    args = parser.parse_args()

    # If no arguments, do both
    if not args.download and not args.verify:
        args.download = True
        args.verify = True

    # Download if requested
    if args.download:
        download_granite_model()

    # Verify if requested
    if args.verify:
        if verify_model():
            print("="*70)
            print("✓ All checks passed! Model is ready.")
            print("="*70 + "\n")
        else:
            print("="*70)
            print("✗ Verification failed. Please check logs.")
            print("="*70 + "\n")
            sys.exit(1)


if __name__ == "__main__":
    main()
