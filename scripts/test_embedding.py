#!/usr/bin/env python3
"""
Test script for Granite embedding model.

This script tests the Granite embedding model functionality.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.logging import get_logger
from src.embedding.models.granite_embedding import GraniteEmbeddingModel
from src.services.embedding_service import EmbeddingService


logger = get_logger(__name__)


def test_basic_encoding():
    """Test basic single text encoding."""
    print("\n" + "="*70)
    print("Test 1: Basic Encoding")
    print("="*70 + "\n")

    try:
        model = GraniteEmbeddingModel(lazy_load=False)

        test_text = "Hello, this is a test sentence for Granite embedding model."
        print(f"Test text: '{test_text}'")

        embedding = model.encode_single(test_text)

        print(f"\n✓ Encoding successful!")
        print(f"  - Embedding dimension: {len(embedding)}")
        print(f"  - First 5 values: {embedding[:5]}")
        print(f"  - Last 5 values: {embedding[-5:]}")
        print(f"  - Min value: {min(embedding):.6f}")
        print(f"  - Max value: {max(embedding):.6f}")

        # Check dimension
        assert len(embedding) == 384, f"Expected 384, got {len(embedding)}"
        print("\n✓ Dimension check passed (384)")

        return True

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        logger.error("Basic encoding test failed", error=str(e), exc_info=True)
        return False


def test_batch_encoding():
    """Test batch text encoding."""
    print("\n" + "="*70)
    print("Test 2: Batch Encoding")
    print("="*70 + "\n")

    try:
        model = GraniteEmbeddingModel(lazy_load=False)

        test_texts = [
            "This is the first test sentence.",
            "This is the second test sentence.",
            "This is the third test sentence.",
            "This is the fourth test sentence.",
            "This is the fifth test sentence."
        ]

        print(f"Testing batch encoding for {len(test_texts)} texts...")

        embeddings = model.encode(test_texts, batch_size=2)

        print(f"\n✓ Batch encoding successful!")
        print(f"  - Number of embeddings: {len(embeddings)}")

        for i, (text, emb) in enumerate(zip(test_texts, embeddings)):
            print(f"  - Text {i+1}: '{text[:50]}...' -> {len(emb)} dims")

        # Check all dimensions
        for i, emb in enumerate(embeddings):
            assert len(emb) == 384, f"Embedding {i} has wrong dimension: {len(emb)}"
        print("\n✓ All dimension checks passed (384)")

        return True

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        logger.error("Batch encoding test failed", error=str(e), exc_info=True)
        return False


def test_similarity_computation():
    """Test similarity computation."""
    print("\n" + "="*70)
    print("Test 3: Similarity Computation")
    print("="*70 + "\n")

    try:
        model = GraniteEmbeddingModel(lazy_load=False)

        # Similar texts
        text1 = "Machine learning is a subset of artificial intelligence."
        text2 = "ML is part of AI."

        print(f"Text 1: '{text1}'")
        print(f"Text 2: '{text2}'")

        emb1 = model.encode_single(text1)
        emb2 = model.encode_single(text2)

        similarity = model.compute_similarity(emb1, emb2)

        print(f"\n✓ Similarity computation successful!")
        print(f"  - Similarity score: {similarity:.4f}")

        # Check range
        assert 0.0 <= similarity <= 1.0, f"Similarity out of range: {similarity}"
        print("\n✓ Similarity range check passed [0.0, 1.0]")

        # Self-similarity should be 1.0
        self_similarity = model.compute_similarity(emb1, emb1)
        print(f"  - Self-similarity: {self_similarity:.4f}")
        assert abs(self_similarity - 1.0) < 0.001, f"Self-similarity not 1.0: {self_similarity}"
        print("✓ Self-similarity check passed (≈1.0)")

        return True

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        logger.error("Similarity test failed", error=str(e), exc_info=True)
        return False


def test_long_context():
    """Test long context handling."""
    print("\n" + "="*70)
    print("Test 4: Long Context Handling")
    print("="*70 + "\n")

    try:
        model = GraniteEmbeddingModel(lazy_load=False)

        # Create a long text (close to 8192 tokens)
        long_text = "This is a test sentence. " * 500  # ~500 words
        print(f"Testing long text...")
        print(f"  - Length: {len(long_text)} characters")
        print(f"  - Word count: {len(long_text.split())} words")

        embedding = model.encode_single(long_text)

        print(f"\n✓ Long context encoding successful!")
        print(f"  - Embedding dimension: {len(embedding)}")
        assert len(embedding) == 384, f"Expected 384, got {len(embedding)}"
        print("\n✓ Long context test passed")

        return True

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        logger.error("Long context test failed", error=str(e), exc_info=True)
        return False


def test_embedding_service():
    """Test EmbeddingService integration."""
    print("\n" + "="*70)
    print("Test 5: EmbeddingService Integration")
    print("="*70 + "\n")

    try:
        service = EmbeddingService()

        print(f"Model name: {service.get_model_name()}")
        print(f"Embedding dimension: {service.get_dimension()}")

        # Test single embedding
        test_text = "Test text for EmbeddingService"
        embedding = service.generate_embedding(test_text)

        print(f"\n✓ Single embedding successful!")
        print(f"  - Embedding dimension: {len(embedding)}")

        # Test batch embedding
        test_texts = ["First text", "Second text", "Third text"]
        embeddings = service.generate_embeddings(test_texts, batch_size=2)

        print(f"\n✓ Batch embedding successful!")
        print(f"  - Number of embeddings: {len(embeddings)}")

        # Check cache stats
        stats = service.get_cache_stats()
        print(f"\n✓ Cache stats: {stats}")

        return True

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        logger.error("EmbeddingService test failed", error=str(e), exc_info=True)
        return False


def test_model_properties():
    """Test model properties."""
    print("\n" + "="*70)
    print("Test 6: Model Properties")
    print("="*70 + "\n")

    try:
        model = GraniteEmbeddingModel(lazy_load=False)

        print("Model Properties:")
        print(f"  - Model name: {model.get_model_name()}")
        print(f"  - Embedding dimension: {model.get_dimension()}")
        print(f"  - Max length: {model.get_max_length()}")
        print(f"  - Class: {model.__class__.__name__}")

        # Check expected values
        assert model.get_dimension() == 384, f"Dimension mismatch: {model.get_dimension()}"
        assert model.get_max_length() == 8192, f"Max length mismatch: {model.get_max_length()}"

        print("\n✓ All property checks passed")
        return True

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        logger.error("Model properties test failed", error=str(e), exc_info=True)
        return False


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("Granite Embedding Model Test Suite")
    print("="*70)

    tests = [
        ("Basic Encoding", test_basic_encoding),
        ("Batch Encoding", test_batch_encoding),
        ("Similarity Computation", test_similarity_computation),
        ("Long Context Handling", test_long_context),
        ("EmbeddingService Integration", test_embedding_service),
        ("Model Properties", test_model_properties),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Unexpected error in {test_name}: {e}")
            logger.error(f"Unexpected error in {test_name}", error=str(e), exc_info=True)
            results.append((test_name, False))

    # Print summary
    print("\n" + "="*70)
    print("Test Summary")
    print("="*70 + "\n")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n" + "="*70)
        print("✓ All tests passed successfully!")
        print("="*70 + "\n")
        return 0
    else:
        print("\n" + "="*70)
        print("✗ Some tests failed. Please check logs.")
        print("="*70 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
