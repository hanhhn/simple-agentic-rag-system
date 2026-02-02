"""
Granite embedding model implementation.

Granite is a state-of-the-art embedding model developed by IBM.
It supports:
- Dense retrieval (traditional vector similarity)
- 8192 token context length (same as BGE-M3)
- 384-dimensional embeddings (smaller and faster than BGE-M3)
- 47M parameters (much smaller than BGE-M3)
- English language optimized
- 19-44% faster than leading competitors

Model: ibm-granite/granite-embedding-small-english-r2
Dimension: 384
Max Length: 8192

Reference: https://huggingface.co/ibm-granite/granite-embedding-small-english-r2
"""
import os
from typing import List

# Disable PyTorch threading before importing torch to prevent segmentation faults on ARM64 Docker
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OMP_PLACES'] = '1'
os.environ['OMP_PROC_BIND'] = 'TRUE'
os.environ['OMP_WAIT_POLICY'] = 'ACTIVE'

from src.core.logging import get_logger
from src.core.exceptions import EmbeddingGenerationError
from src.embedding.base import EmbeddingModel
from src.embedding.model_loader import ModelLoader


logger = get_logger(__name__)


class GraniteEmbeddingModel(EmbeddingModel):
    """
    Granite embedding model implementation.

    This class wraps the ibm-granite/granite-embedding-small-english-r2 model,
    providing a clean interface for generating high-quality English embeddings
    with long context support.

    Key Features:
    - 384-dimensional embeddings (smaller and faster than BGE-M3's 1024)
    - 8192 token context length (same as BGE-M3)
    - 47M parameters (much smaller than BGE-M3)
    - Optimized for English text
    - 19-44% faster than leading competitors
    - Apache 2.0 license (enterprise-friendly)

    Model: ibm-granite/granite-embedding-small-english-r2
    Dimension: 384
    Max Length: 8192

    Example:
        >>> model = GraniteEmbeddingModel()
        >>> embedding = model.encode_single("Hello world")
        >>> print(len(embedding))  # 384
    """

    DEFAULT_MODEL = "ibm-granite/granite-embedding-small-english-r2"
    DIMENSION = 384
    MAX_LENGTH = 8192

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        cache_dir: str | None = None,
        lazy_load: bool = True,
        max_length: int = MAX_LENGTH
    ) -> None:
        """
        Initialize Granite embedding model.

        Args:
            model_name: Model name or path (default: ibm-granite/granite-embedding-small-english-r2)
            cache_dir: Directory to cache models
            lazy_load: If True, load model on first use (safer for multiprocessing)
            max_length: Maximum sequence length (default: 8192)
        """
        super().__init__(
            model_name=model_name,
            dimension=self.DIMENSION,
            max_length=max_length
        )

        self.loader = ModelLoader(cache_dir=cache_dir)
        self._model_name = model_name
        self._max_length = max_length

        if lazy_load:
            # Lazy loading - safer for multiprocessing (Celery workers)
            self.model = None
            logger.info(
                "Granite model initialized (lazy loading)",
                model=model_name,
                dimension=self.DIMENSION,
                max_length=max_length
            )
        else:
            # Eager loading
            self.model = self.loader.load_model(model_name)
            logger.info(
                "Granite model initialized",
                model=model_name,
                dimension=self.DIMENSION,
                max_length=max_length
            )

    @property
    def _loaded_model(self):
        """Lazy load of model when first accessed."""
        logger.info("Accessing _loaded_model property", model=self._model_name, has_model=self.model is not None)

        if self.model is None:
            logger.info("Loading Granite model on first access", model=self._model_name)
            try:
                self.model = self.loader.load_model(self._model_name)
                logger.info("Granite model loaded successfully", model=self._model_name)
            except Exception:
                logger.error(
                    "Failed to load Granite model in _loaded_model property",
                    model=self._model_name,
                    exc_info=True
                )
                raise

        logger.info("Returning Granite model from _loaded_model property", model=self._model_name)
        return self.model

    def encode(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Encode multiple texts into embeddings using Granite.

        Granite supports long context (up to 8192 tokens), making it ideal
        for processing longer documents and passages.

        Args:
            texts: List of text strings to encode
            batch_size: Batch size for encoding (default: 32)

        Returns:
            List of 384-dimensional embedding vectors

        Raises:
            EmbeddingGenerationError: If encoding fails

        Example:
            >>> model = GraniteEmbeddingModel()
            >>> embeddings = model.encode(["text1", "text2"], batch_size=16)
            >>> print(len(embeddings))  # 2
            >>> print(len(embeddings[0]))  # 384
        """
        if not texts:
            return []

        logger.info(
            "Starting Granite encode operation",
            count=len(texts),
            batch_size=batch_size
        )

        try:
            logger.info(
                "Encoding texts with Granite",
                count=len(texts),
                batch_size=batch_size,
                max_length=self._max_length
            )

            # Encode texts using lazy-loaded model
            model = self._loaded_model
            logger.info("Granite model loaded, starting encoding", count=len(texts), batch_size=batch_size)

            try:
                # Granite encoding with long context support
                logger.info("Calling model.encode()", text_count=len(texts), batch_size=batch_size)

                # Disable progress bar to prevent stderr pollution in Docker
                logger.info("Starting actual encoding computation...")
                embeddings = model.encode(
                    texts,
                    batch_size=batch_size,
                    show_progress_bar=False,  # Disabled to prevent logging issues
                    convert_to_numpy=True,
                    normalize_embeddings=True
                )

                logger.info("Model.encode() call completed", embeddings_count=len(embeddings) if embeddings is not None else 0)
                logger.info("Granite encoding completed, converting to list", embedding_count=len(embeddings) if embeddings is not None else 0)

                # Convert to list format
                result = [embedding.tolist() for embedding in embeddings]

                logger.info(
                    "Successfully encoded texts with Granite",
                    count=len(texts),
                    dimension=self.DIMENSION
                )

                return result

            except Exception as encode_error:
                logger.error(
                    "Granite model.encode() failed",
                    error=str(encode_error),
                    error_type=type(encode_error).__name__,
                    text_count=len(texts),
                    batch_size=batch_size,
                    exc_info=True
                )
                raise EmbeddingGenerationError(
                    f"Failed to generate Granite embeddings: {str(encode_error)}",
                    details={
                        "error": str(encode_error),
                        "error_type": type(encode_error).__name__,
                        "text_count": len(texts)
                    }
                )
        except Exception as e:
            logger.error("Failed to encode texts with Granite", error=str(e), count=len(texts))
            raise EmbeddingGenerationError(
                f"Failed to generate Granite embeddings: {str(e)}",
                details={"error": str(e), "text_count": len(texts)}
            )

    def encode_single(self, text: str) -> List[float]:
        """
        Encode a single text into a Granite embedding.

        Args:
            text: Text string to encode

        Returns:
            384-dimensional embedding vector

        Raises:
            EmbeddingGenerationError: If encoding fails

        Example:
            >>> model = GraniteEmbeddingModel()
            >>> embedding = model.encode_single("Hello world")
            >>> print(len(embedding))  # 384
        """
        try:
            # Use batch encoding for single text (more efficient)
            embeddings = self.encode([text])
            return embeddings[0] if embeddings else []

        except Exception as e:
            logger.error("Failed to encode text with Granite", text=text[:100], error=str(e))
            raise EmbeddingGenerationError(
                f"Failed to generate Granite embedding: {str(e)}",
                details={"error": str(e), "text_preview": text[:100]}
            )

    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Compute cosine similarity between two Granite embeddings.

        Args:
            embedding1: First embedding vector (384 dimensions)
            embedding2: Second embedding vector (384 dimensions)

        Returns:
            Cosine similarity score (0.0 to 1.0)

        Example:
            >>> model = GraniteEmbeddingModel()
            >>> emb1 = model.encode_single("Hello")
            >>> emb2 = model.encode_single("Hi")
            >>> similarity = model.compute_similarity(emb1, emb2)
            >>> print(similarity)  # e.g., 0.88
        """
        import numpy as np

        # Convert to numpy arrays
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        # Compute cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        # Avoid division by zero
        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)

        # Ensure result is in [0, 1] range
        return float(max(0.0, min(1.0, similarity)))

    def get_dimension(self) -> int:
        """
        Get the dimension of Granite embeddings.

        Returns:
            384 (Granite embedding dimension)
        """
        return self.DIMENSION

    def get_max_length(self) -> int:
        """
        Get the maximum sequence length for Granite.

        Returns:
            Maximum sequence length (default: 8192)
        """
        return self._max_length
