"""
Embedding cache for improving performance.
"""
import hashlib
import json
import time
from pathlib import Path
from typing import List, Optional
from collections import OrderedDict

from src.core.logging import get_logger
from src.core.exceptions import EmbeddingCacheError


logger = get_logger(__name__)


class EmbeddingCache:
    """
    Cache for storing embeddings to avoid recomputation.
    
    This cache stores text-to-embeddings mappings, allowing the system
    to reuse previously computed embeddings for identical text inputs.
    Uses LRU (Least Recently Used) eviction strategy when cache size limit is reached.
    
    Attributes:
        cache_dir: Directory to store cache files
        cache_file: Path to the cache file
        cache: In-memory cache dictionary (OrderedDict for LRU)
        enabled: Whether caching is enabled
        max_size: Maximum number of cache entries
        auto_save_interval: Number of operations before auto-save
        
    Example:
        >>> cache = EmbeddingCache(cache_dir="./data/cache", max_size=5000)
        >>> embedding = cache.get("Hello world")
        >>> if embedding is None:
        ...     # Compute embedding
        ...     cache.set("Hello world", [0.1, 0.2, 0.3])
    """
    
    def __init__(self, cache_dir: Path | str, enabled: bool = True, max_size: int = 10000, 
                 auto_save_interval: int = 100) -> None:
        """
        Initialize the embedding cache.
        
        Args:
            cache_dir: Directory to store cache files
            enabled: Whether to enable caching
            max_size: Maximum number of entries in cache (LRU eviction when exceeded)
            auto_save_interval: Auto-save after N set operations (0 to disable)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.cache_file = self.cache_dir / "embeddings_cache.json"
        self.enabled = enabled
        self.max_size = max_size
        self.auto_save_interval = auto_save_interval
        # Use OrderedDict for LRU cache
        self.cache: OrderedDict = OrderedDict()
        self._operation_count = 0
        self._cache_hits = 0
        self._cache_misses = 0
        self._total_get_time = 0.0
        self._total_set_time = 0.0
        
        logger.info(
            "EmbeddingCache initialized",
            cache_dir=str(self.cache_dir),
            cache_file=str(self.cache_file),
            enabled=enabled,
            max_size=max_size,
            auto_save_interval=auto_save_interval
        )
        
        # Load existing cache if enabled
        if self.enabled and self.cache_file.exists():
            self._load()
    
    def _get_cache_key(self, text: str) -> str:
        """
        Generate a cache key for the given text.
        
        Args:
            text: Text to generate key for
            
        Returns:
            SHA-256 hash of the text as cache key
        """
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    def get(self, text: str) -> Optional[List[float]]:
        """
        Get embedding from cache if it exists.
        
        Args:
            text: Text to look up in cache
            
        Returns:
            Cached embedding vector or None if not found
        """
        start_time = time.time()
        
        if not self.enabled:
            self._cache_misses += 1
            logger.info("Cache is disabled, skipping cache lookup")
            return None
        
        key = self._get_cache_key(text)
        value = self.cache.get(key)
        
        # Track hits and misses
        elapsed = time.time() - start_time
        self._total_get_time += elapsed
        
        if value is not None and key in self.cache:
            self._cache_hits += 1
            # Move to end for LRU (most recently used)
            self.cache.move_to_end(key)
            logger.info(
                "Cache hit",
                cache_hit_rate=f"{self.get_cache_hit_rate():.2%}",
                retrieval_time=f"{elapsed:.6f}s",
                entries=len(self.cache)
            )
        else:
            self._cache_misses += 1
            logger.info(
                "Cache miss",
                cache_hit_rate=f"{self.get_cache_hit_rate():.2%}",
                lookup_time=f"{elapsed:.6f}s",
                entries=len(self.cache)
            )
        
        return value
    
    def set(self, text: str, embedding: List[float]) -> None:
        """
        Store an embedding in the cache.
        
        Args:
            text: Text that was embedded
            embedding: Embedding vector to cache
            
        Example:
            >>> cache.set("Hello world", [0.1, 0.2, 0.3])
        """
        start_time = time.time()
        
        if not self.enabled:
            logger.info("Cache is disabled, skipping cache set")
            return
        
        key = self._get_cache_key(text)
        
        # Update existing key or add new one
        if key in self.cache:
            self.cache.move_to_end(key)
            logger.info("Updated existing cache entry", entries=len(self.cache))
        else:
            self.cache[key] = embedding
            logger.info("Added new cache entry", entries=len(self.cache))
        
        # Evict oldest entries if cache is too large
        evicted = 0
        while len(self.cache) > self.max_size:
            self.cache.popitem(last=False)
            evicted += 1
        
        if evicted > 0:
            logger.info(
                "LRU eviction performed",
                evicted_entries=evicted,
                current_entries=len(self.cache),
                max_size=self.max_size
            )
        
        elapsed = time.time() - start_time
        self._total_set_time += elapsed
        
        # Auto-save if enabled
        self._increment_operation_count()
    
    def get_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Get multiple embeddings from cache.
        
        Args:
            texts: List of texts to look up
            
        Returns:
            List of cached embeddings (None for cache misses)
        """
        return [self.get(text) for text in texts]
    
    def set_batch(self, texts: List[str], embeddings: List[List[float]]) -> None:
        """
        Store multiple embeddings in cache.
        
        Args:
            texts: List of texts that were embedded
            embeddings: List of embedding vectors to cache
            
        Example:
            >>> cache.set_batch(["text1", "text2"], [[0.1], [0.2]])
        """
        if not self.enabled:
            return
        
        if len(texts) != len(embeddings):
            logger.warning(
                "Batch size mismatch in cache set",
                texts_count=len(texts),
                embeddings_count=len(embeddings)
            )
            return
        
        for text, embedding in zip(texts, embeddings):
            self.set(text, embedding)
    
    def clear(self) -> None:
        """
        Clear all cached embeddings.
        
        Example:
            >>> cache.clear()
        """
        count = len(self.cache)
        self.cache.clear()
        self._operation_count = 0
        self._cache_hits = 0
        self._cache_misses = 0
        self._total_get_time = 0.0
        self._total_set_time = 0.0
        logger.info(
            "Embedding cache cleared",
            cleared_entries=count,
            cache_hit_rate_before_clear=f"{self.get_cache_hit_rate():.2%}"
        )
    
    def save(self) -> None:
        """
        Save cache to disk.
        
        Example:
            >>> cache.save()
        """
        if not self.enabled:
            return
        
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f)
            logger.info("Embedding cache saved", cache_file=str(self.cache_file))
        except Exception as e:
            raise EmbeddingCacheError(
                f"Failed to save cache: {str(e)}",
                details={"cache_file": str(self.cache_file), "error": str(e)}
            )
    
    def _load(self) -> None:
        """
        Load cache from disk.
        
        Raises:
            EmbeddingCacheError: If cache file cannot be loaded
        """
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                self.cache = json.load(f)
            logger.info(
                "Embedding cache loaded",
                cache_file=str(self.cache_file),
                entries=len(self.cache)
            )
        except json.JSONDecodeError as e:
            logger.warning(
                "Cache file is corrupted, starting with empty cache",
                cache_file=str(self.cache_file),
                error=str(e)
            )
            self.cache = {}
        except Exception as e:
            raise EmbeddingCacheError(
                f"Failed to load cache: {str(e)}",
                details={"cache_file": str(self.cache_file), "error": str(e)}
            )
    
    def _increment_operation_count(self) -> None:
        """Increment operation counter and auto-save if needed."""
        self._operation_count += 1
        
        if self.auto_save_interval > 0 and self._operation_count >= self.auto_save_interval:
            self.save()
            self._operation_count = 0
    
    def get_cache_hit_rate(self) -> float:
        """
        Calculate cache hit rate.
        
        Returns:
            Cache hit rate as percentage (0.0 to 1.0)
        """
        total = self._cache_hits + self._cache_misses
        if total == 0:
            return 0.0
        return self._cache_hits / total
    
    def get_stats(self) -> dict:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        total_ops = self._cache_hits + self._cache_misses
        avg_get_time = self._total_get_time / self._cache_hits if self._cache_hits > 0 else 0.0
        avg_set_time = self._total_set_time / self._operation_count if self._operation_count > 0 else 0.0
        
        return {
            "enabled": self.enabled,
            "entries": len(self.cache),
            "max_size": self.max_size,
            "cache_file": str(self.cache_file),
            "cache_size_bytes": self.cache_file.stat().st_size if self.cache_file.exists() else 0,
            "operation_count": self._operation_count,
            "auto_save_interval": self.auto_save_interval,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_rate": f"{self.get_cache_hit_rate() * 100:.2f}%",
            "total_operations": total_ops,
            "avg_get_time": f"{avg_get_time:.6f}s",
            "avg_set_time": f"{avg_set_time:.6f}s"
        }
