"""
Embedding service for managing embedding generation.
"""
import time
from typing import List, Optional

from src.core.logging import get_logger
from src.core.exceptions import EmbeddingError
from src.core.config import get_config
from src.embedding.base import EmbeddingModel
from src.embedding.models.granite_embedding import GraniteEmbeddingModel
from src.embedding.cache import EmbeddingCache


logger = get_logger(__name__)


class EmbeddingService:
    """
    Service for generating and managing embeddings.

    This class provides a high-level interface for embedding generation,
    including caching, batch processing, and model management.

    Uses Granite embedding model exclusively for high-quality English embeddings.

    Example:
        >>> service = EmbeddingService()
        >>> embeddings = service.generate_embeddings(["text1", "text2"])
        >>> print(len(embeddings))  # 2
    """
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        use_cache: bool = True
    ) -> None:
        """
        Initialize embedding service.
        
        Args:
            model_name: Model name (uses config default if None)
            use_cache: Whether to use embedding cache
        """
        config = get_config()
        
        self.model_name = model_name or config.embedding.model_name
        self.use_cache = use_cache
        
        # Initialize cache
        self.cache = EmbeddingCache(
            cache_dir=config.storage.cache_path,
            enabled=use_cache
        )
        
        # Lazy load model - don't load until first use
        # This avoids issues with loading models in forked processes
        self._model: Optional[EmbeddingModel] = None
        
        logger.info(
            "Embedding service initialized (lazy loading)",
            model=self.model_name,
            use_cache=use_cache
        )
    
    @property
    def model(self) -> EmbeddingModel:
        """
        Get the embedding model, loading it lazily if needed.
        
        This property ensures the model is only loaded when first accessed,
        which is safer for multiprocessing contexts (e.g., Celery workers).
        
        Returns:
            Initialized embedding model
        """
        if self._model is None:
            self._model = self._load_model(self.model_name)
            logger.info(
                "Model loaded (lazy initialization)",
                model=self.model_name,
                dimension=self._model.get_dimension()
            )
        return self._model
    
    def _load_model(self, model_name: str) -> EmbeddingModel:
        """
        Load the embedding model.

        Uses Granite embedding model exclusively.

        Args:
            model_name: Name of the model (will always use Granite)

        Returns:
            Initialized Granite model
        """
        logger.info("Loading Granite model", model=model_name)
        # Enable lazy loading for multiprocessing safety
        return GraniteEmbeddingModel(model_name=model_name, lazy_load=True)
    
    def generate_embedding(self, text: str, use_cache_override: Optional[bool] = None) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            use_cache_override: Override cache setting for this call
            
        Returns:
            Embedding vector
            
        Example:
            >>> service = EmbeddingService()
            >>> embedding = service.generate_embedding("Hello world")
            >>> print(len(embedding))  # model dimension
        """
        start_time = time.time()
        use_cache = use_cache_override if use_cache_override is not None else self.use_cache
        
        logger.info(
            "Generating single embedding",
            text_length=len(text),
            model=self.model_name,
            use_cache=use_cache
        )
        
        # Check cache
        cache_start = time.time()
        if use_cache:
            cached_embedding = self.cache.get(text)
            cache_elapsed = time.time() - cache_start
            
            if cached_embedding:
                total_elapsed = time.time() - start_time
                logger.info(
                    "Embedding cache hit",
                    text_length=len(text),
                    dimension=len(cached_embedding),
                    cache_lookup_time=f"{cache_elapsed:.6f}s",
                    total_time=f"{total_elapsed:.6f}s"
                )
                return cached_embedding
            
            logger.info(
                "Embedding cache miss",
                text_length=len(text),
                cache_lookup_time=f"{cache_elapsed:.6f}s"
            )
        
        # Generate embedding
        encode_start = time.time()
        try:
            embedding = self.model.encode_single(text)
            encode_elapsed = time.time() - encode_start
            
            # Cache result
            cache_set_start = time.time()
            if use_cache:
                self.cache.set(text, embedding)
            cache_set_elapsed = time.time() - cache_set_start
            
            total_elapsed = time.time() - start_time
            
            logger.info(
                "Embedding generated successfully",
                text_length=len(text),
                dimension=len(embedding),
                model=self.model_name,
                encode_time=f"{encode_elapsed:.4f}s",
                cache_set_time=f"{cache_set_elapsed:.6f}s",
                total_time=f"{total_elapsed:.4f}s",
                cached=use_cache
            )
            
            return embedding
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(
                "Failed to generate embedding",
                text_preview=text[:100],
                text_length=len(text),
                error=str(e),
                error_type=type(e).__name__,
                elapsed_time=f"{elapsed:.4f}s"
            )
            raise EmbeddingError(
                f"Failed to generate embedding: {str(e)}",
                details={
                    "text_preview": text[:100],
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "elapsed_time": f"{elapsed:.4f}s"
                }
            )
    
    def generate_embeddings(
        self,
        texts: List[str],
        batch_size: int = 32,
        use_cache_override: Optional[bool] = None
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing
            use_cache_override: Override cache setting for this call
            
        Returns:
            List of embedding vectors
            
        Example:
            >>> service = EmbeddingService()
            >>> embeddings = service.generate_embeddings(["text1", "text2"])
            >>> print(len(embeddings))  # 2
        """
        start_time = time.time()
        
        if not texts:
            logger.info("No texts provided for batch embedding")
            return []
        
        use_cache = use_cache_override if use_cache_override is not None else self.use_cache
        
        total_chars = sum(len(text) for text in texts)
        avg_length = total_chars / len(texts) if texts else 0
        
        logger.info(
            "Starting batch embedding generation",
            count=len(texts),
            batch_size=batch_size,
            model=self.model_name,
            total_chars=total_chars,
            avg_text_length=f"{avg_length:.1f}",
            use_cache=use_cache
        )
        
        # Check cache for all texts
        if use_cache:
            cache_start = time.time()
            cached_embeddings = self.cache.get_batch(texts)
            cache_elapsed = time.time() - cache_start
            
            # Count cache hits and misses
            cache_hits = sum(1 for emb in cached_embeddings if emb is not None)
            cache_misses = len(texts) - cache_hits
            
            logger.info(
                "Cache lookup completed",
                total=len(texts),
                cache_hits=cache_hits,
                cache_misses=cache_misses,
                cache_hit_rate=f"{(cache_hits / len(texts) * 100):.1f}%",
                cache_lookup_time=f"{cache_elapsed:.4f}s"
            )
            
            # Generate embeddings for cache misses
            texts_to_encode = [
                text for text, cached in zip(texts, cached_embeddings)
                if cached is None
            ]
            
            if texts_to_encode:
                # Generate embeddings for cache misses
                encode_start = time.time()
                new_embeddings = self.model.encode(texts_to_encode, batch_size=batch_size)
                encode_elapsed = time.time() - encode_start
                
                # Cache new embeddings
                cache_set_start = time.time()
                if use_cache:
                    self.cache.set_batch(texts_to_encode, new_embeddings)
                cache_set_elapsed = time.time() - cache_set_start
                
                # Combine cached and new embeddings
                combine_start = time.time()
                embeddings = []
                new_idx = 0
                for cached in cached_embeddings:
                    if cached is not None:
                        embeddings.append(cached)
                    else:
                        embeddings.append(new_embeddings[new_idx])
                        new_idx += 1
                combine_elapsed = time.time() - combine_start
                
                total_elapsed = time.time() - start_time
                
                logger.info(
                    "Embeddings generated with cache",
                    total=len(texts),
                    cached=cache_hits,
                    generated=cache_misses,
                    encode_time=f"{encode_elapsed:.4f}s",
                    cache_set_time=f"{cache_set_elapsed:.4f}s",
                    combine_time=f"{combine_elapsed:.6f}s",
                    total_time=f"{total_elapsed:.4f}s",
                    avg_time_per_text=f"{(total_elapsed / len(texts) * 1000):.2f}ms"
                )
                
                return embeddings
            else:
                # All cached
                total_elapsed = time.time() - start_time
                logger.info(
                    "All embeddings from cache",
                    count=len(texts),
                    cache_lookup_time=f"{cache_elapsed:.4f}s",
                    total_time=f"{total_elapsed:.4f}s"
                )
                return cached_embeddings
        else:
            # No caching, generate all
            try:
                encode_start = time.time()
                embeddings = self.model.encode(texts, batch_size=batch_size)
                encode_elapsed = time.time() - encode_start
                
                total_elapsed = time.time() - start_time
                
                logger.info(
                    "Embeddings generated without cache",
                    count=len(texts),
                    batch_size=batch_size,
                    model=self.model_name,
                    encode_time=f"{encode_elapsed:.4f}s",
                    total_time=f"{total_elapsed:.4f}s",
                    avg_time_per_text=f"{(total_elapsed / len(texts) * 1000):.2f}ms"
                )
                
                return embeddings
                
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(
                    "Failed to generate embeddings",
                    count=len(texts),
                    error=str(e),
                    error_type=type(e).__name__,
                    elapsed_time=f"{elapsed:.4f}s"
                )
                raise EmbeddingError(
                    f"Failed to generate embeddings: {str(e)}",
                    details={
                        "text_count": len(texts),
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "elapsed_time": f"{elapsed:.4f}s"
                    }
                )
    
    def get_dimension(self) -> int:
        """
        Get the dimension of embeddings.
        
        Returns:
            Embedding dimension
        """
        return self.model.get_dimension()
    
    def get_model_name(self) -> str:
        """
        Get the current model name.
        
        Returns:
            Model name
        """
        return self.model_name
    
    def save_cache(self) -> None:
        """
        Save the embedding cache to disk.
        
        Example:
            >>> service = EmbeddingService()
            >>> service.save_cache()
        """
        self.cache.save()
        logger.info("Embedding cache saved")
    
    def clear_cache(self) -> None:
        """
        Clear the embedding cache.
        
        Example:
            >>> service = EmbeddingService()
            >>> service.clear_cache()
        """
        self.cache.clear()
        logger.info("Embedding cache cleared")
    
    def get_cache_stats(self) -> dict:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        return self.cache.get_stats()
    
    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        return self.model.compute_similarity(embedding1, embedding2)
