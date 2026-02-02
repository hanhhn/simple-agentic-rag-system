"""
BGE-M3 embedding model implementation.

BGE-M3 is a state-of-the-art multilingual embedding model developed by BAAI.
It supports:
- Dense retrieval (traditional vector similarity)
- Sparse retrieval (lexical matching)
- Multi-vector retrieval (colBERT-style)
- 8192 token context length (much longer than most models)
- 100+ languages

Model: BAAI/bge-m3
Dimension: 1024
Max Length: 8192

Reference: https://huggingface.co/BAAI/bge-m3
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


class BGEM3Model(EmbeddingModel):
    """
    BGE-M3 embedding model implementation.
    
    This class wraps the BAAI/bge-m3 model, providing a clean interface
    for generating high-quality multilingual embeddings with long context support.
    
    Key Features:
    - 1024-dimensional embeddings (higher quality)
    - 8192 token context length (much longer than typical 512)
    - Supports 100+ languages
    - Optimized for both short and long texts
    
    Model: BAAI/bge-m3
    Dimension: 1024
    Max Length: 8192
    
    Example:
        >>> model = BGEM3Model()
        >>> embedding = model.encode_single("Hello world")
        >>> print(len(embedding))  # 1024
    """
    
    DEFAULT_MODEL = "BAAI/bge-m3"
    DIMENSION = 1024
    MAX_LENGTH = 8192
    
    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        cache_dir: str | None = None,
        lazy_load: bool = True,
        max_length: int = MAX_LENGTH
    ) -> None:
        """
        Initialize BGE-M3 model.
        
        Args:
            model_name: Model name or path (default: BAAI/bge-m3)
            cache_dir: Directory to cache models
            lazy_load: If True, load model on first use (safer for multiprocessing)
            max_length: Maximum sequence length (default: 8192, can be reduced for memory)
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
                "BGE-M3 model initialized (lazy loading)",
                model=model_name,
                dimension=self.DIMENSION,
                max_length=max_length
            )
        else:
            # Eager loading
            self.model = self.loader.load_model(model_name)
            logger.info(
                "BGE-M3 model initialized",
                model=model_name,
                dimension=self.DIMENSION,
                max_length=max_length
            )

    @property
    def _loaded_model(self):
        """Lazy load of model when first accessed."""
        logger.info("Accessing _loaded_model property", model=self._model_name, has_model=self.model is not None)

        if self.model is None:
            logger.info("Loading BGE-M3 model on first access", model=self._model_name)
            try:
                self.model = self.loader.load_model(self._model_name)
                logger.info("BGE-M3 model loaded successfully", model=self._model_name)
            except Exception:
                logger.error(
                    "Failed to load BGE-M3 model in _loaded_model property",
                    model=self._model_name,
                    exc_info=True
                )
                raise

        logger.info("Returning BGE-M3 model from _loaded_model property", model=self._model_name)
        return self.model
    
    def encode(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Encode multiple texts into embeddings using BGE-M3.
        
        BGE-M3 supports long context (up to 8192 tokens), making it ideal
        for processing longer documents and passages.
        
        Args:
            texts: List of text strings to encode
            batch_size: Batch size for encoding (default: 32)
            
        Returns:
            List of 1024-dimensional embedding vectors
            
        Raises:
            EmbeddingGenerationError: If encoding fails
            
        Example:
            >>> model = BGEM3Model()
            >>> embeddings = model.encode(["text1", "text2"], batch_size=16)
            >>> print(len(embeddings))  # 2
            >>> print(len(embeddings[0]))  # 1024
        """
        if not texts:
            return []

        logger.info(
            "Starting BGE-M3 encode operation",
            count=len(texts),
            batch_size=batch_size
        )

        try:
            logger.info(
                "Encoding texts with BGE-M3",
                count=len(texts),
                batch_size=batch_size,
                max_length=self._max_length
            )

            # Encode texts using lazy-loaded model
            model = self._loaded_model
            logger.info("BGE-M3 model loaded, starting encoding", count=len(texts), batch_size=batch_size)

            try:
                # BGE-M3 encoding with long context support
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
                logger.info("BGE-M3 encoding completed, converting to list", embedding_count=len(embeddings) if embeddings is not None else 0)

                # Convert to list format
                result = [embedding.tolist() for embedding in embeddings]

                logger.info(
                    "Successfully encoded texts with BGE-M3",
                    count=len(texts),
                    dimension=self.DIMENSION
                )

                return result

            except Exception as encode_error:
                logger.error(
                    "BGE-M3 model.encode() failed",
                    error=str(encode_error),
                    error_type=type(encode_error).__name__,
                    text_count=len(texts),
                    batch_size=batch_size,
                    exc_info=True
                )
                raise EmbeddingGenerationError(
                    f"Failed to generate BGE-M3 embeddings: {str(encode_error)}",
                    details={
                        "error": str(encode_error),
                        "error_type": type(encode_error).__name__,
                        "text_count": len(texts)
                    }
                )
        except Exception as e:
            logger.error("Failed to encode texts with BGE-M3", error=str(e), count=len(texts))
            raise EmbeddingGenerationError(
                f"Failed to generate BGE-M3 embeddings: {str(e)}",
                details={"error": str(e), "text_count": len(texts)}
            )
    
    def encode_single(self, text: str) -> List[float]:
        """
        Encode a single text into a BGE-M3 embedding.
        
        Args:
            text: Text string to encode
            
        Returns:
            1024-dimensional embedding vector
            
        Raises:
            EmbeddingGenerationError: If encoding fails
            
        Example:
            >>> model = BGEM3Model()
            >>> embedding = model.encode_single("Hello world")
            >>> print(len(embedding))  # 1024
        """
        try:
            # Use batch encoding for single text (more efficient)
            embeddings = self.encode([text])
            return embeddings[0] if embeddings else []
            
        except Exception as e:
            logger.error("Failed to encode text with BGE-M3", text=text[:100], error=str(e))
            raise EmbeddingGenerationError(
                f"Failed to generate BGE-M3 embedding: {str(e)}",
                details={"error": str(e), "text_preview": text[:100]}
            )
    
    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Compute cosine similarity between two BGE-M3 embeddings.
        
        Args:
            embedding1: First embedding vector (1024 dimensions)
            embedding2: Second embedding vector (1024 dimensions)
            
        Returns:
            Cosine similarity score (0.0 to 1.0)
            
        Example:
            >>> model = BGEM3Model()
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
        Get the dimension of BGE-M3 embeddings.
        
        Returns:
            1024 (BGE-M3 embedding dimension)
        """
        return self.DIMENSION
    
    def get_max_length(self) -> int:
        """
        Get the maximum sequence length for BGE-M3.
        
        Returns:
            Maximum sequence length (default: 8192)
        """
        return self._max_length
