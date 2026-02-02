"""
Singleton Model Manager for efficient model loading and caching.

This module provides a singleton pattern to ensure that embedding models
are loaded only once and reused across the application, significantly
reducing memory usage and startup time.
"""
import time
from pathlib import Path
from typing import Optional, Dict
from threading import Lock

from src.core.logging import get_logger
from src.core.exceptions import EmbeddingModelNotFoundError
from src.core.config import get_config


logger = get_logger(__name__)


class ModelManager:
    """
    Singleton manager for Granite embedding model.

    This class ensures that Granite is loaded only once and reused
    across the application. It provides thread-safe model loading and
    caching.

    Attributes:
        instance: The singleton instance of ModelManager
        cache_dir: Directory to cache downloaded models

    Example:
        >>> manager = ModelManager.get_instance()
        >>> model = manager.get_model("ibm-granite/granite-embedding-small-english-r2")
    """
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls, *args, **kwargs):
        """Implement singleton pattern with thread safety."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(
        self,
        cache_dir: Optional[Path | str] = None
    ) -> None:
        """
        Initialize model manager.
        
        Args:
            cache_dir: Directory to cache models
        """
        # Avoid re-initialization
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        config = get_config()
        
        self.cache_dir = Path(cache_dir or config.storage.model_cache_path)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Dictionary to store loaded models
        # Key: model_name, Value: (model, reference_count)
        self._models: Dict[str, tuple[object, int]] = {}
        self._model_lock = Lock()
        
        # Import ModelLoader here to avoid circular imports
        from src.embedding.model_loader import ModelLoader
        self._loader = ModelLoader(cache_dir=self.cache_dir)
        
        self._initialized = True
        logger.info(
            "ModelManager initialized",
            cache_dir=str(self.cache_dir),
            thread_safe=True
        )
    
    @classmethod
    def get_instance(
        cls,
        cache_dir: Optional[Path | str] = None,
        device: Optional[str] = None
    ) -> 'ModelManager':
        """
        Get the singleton instance of ModelManager.
        
        Args:
            cache_dir: Directory to cache models (ignored after first call)
            device: Default device for model loading (ignored after first call)
            
        Returns:
            The singleton ModelManager instance
            
        Example:
            >>> manager = ModelManager.get_instance()
        """
        if cls._instance is None:
            cls._instance = cls(cache_dir=cache_dir, device=device)
        return cls._instance
    
    def get_model(self, model_name: str) -> object:
        """
        Get or load Granite model with reference counting.

        This method implements lazy loading with reference counting.
        Models are loaded on first request and kept in memory until
        explicitly released.

        Args:
            model_name: Name of the model to get/load (will always use Granite)

        Returns:
            The loaded Granite sentence-transformers model

        Raises:
            EmbeddingModelNotFoundError: If model cannot be loaded

        Example:
            >>> manager = ModelManager.get_instance()
            >>> model = manager.get_model("ibm-granite/granite-embedding-small-english-r2")
        """
        start_time = time.time()
        
        with self._model_lock:
            # Check if model is already loaded
            if model_name in self._models:
                model, ref_count = self._models[model_name]
                new_ref_count = ref_count + 1
                self._models[model_name] = (model, new_ref_count)
                elapsed = time.time() - start_time
                logger.info(
                    "Granite model retrieved from cache",
                    model=model_name,
                    ref_count=new_ref_count,
                    total_cached=len(self._models),
                    retrieval_time=f"{elapsed:.6f}s"
                )
                return model

            # Load the model
            logger.info(
                "Loading Granite model through ModelManager",
                model=model_name,
                current_cache_size=len(self._models)
            )

            load_start = time.time()
            try:
                model = self._loader.load_model(model_name)
                load_elapsed = time.time() - load_start

                self._models[model_name] = (model, 1)

                total_elapsed = time.time() - start_time
                logger.info(
                    "Granite model loaded and cached",
                    model=model_name,
                    ref_count=1,
                    total_cached=len(self._models),
                    load_time=f"{load_elapsed:.4f}s",
                    total_time=f"{total_elapsed:.4f}s"
                )
                return model
            except EmbeddingModelNotFoundError:
                elapsed = time.time() - start_time
                logger.error(
                    "Granite model not found",
                    model=model_name,
                    elapsed_time=f"{elapsed:.4f}s"
                )
                raise
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(
                    "Failed to load Granite model",
                    model=model_name,
                    error=str(e),
                    error_type=type(e).__name__,
                    elapsed_time=f"{elapsed:.4f}s"
                )
                raise EmbeddingModelNotFoundError(
                    f"Failed to load Granite model '{model_name}': {str(e)}",
                    details={
                        "model_name": model_name,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "elapsed_time": f"{elapsed:.4f}s"
                    }
                )
    
    def release_model(self, model_name: str) -> None:
        """
        Release a model reference.
        
        When reference count reaches zero, the model can be unloaded.
        However, by default, models are kept in memory for performance.
        Call unload_model() to force unload.
        
        Args:
            model_name: Name of the model to release
            
        Example:
            >>> manager = ModelManager.get_instance()
            >>> manager.release_model("sentence-transformers/all-MiniLM-L6-v2")
        """
        with self._model_lock:
            if model_name in self._models:
                model, ref_count = self._models[model_name]
                new_ref_count = max(0, ref_count - 1)
                
                if new_ref_count == 0:
                    logger.info("Model reference count reached 0", model=model_name)
                else:
                    logger.info(
                        "Model reference decremented",
                        model=model_name,
                        ref_count=new_ref_count
                    )
                
                self._models[model_name] = (model, new_ref_count)
    
    def unload_model(self, model_name: str) -> None:
        """
        Forcefully unload a model from memory.
        
        This will unload the model even if it has active references.
        Be careful as this may cause issues if the model is still in use.
        
        Args:
            model_name: Name of the model to unload
            
        Example:
            >>> manager = ModelManager.get_instance()
            >>> manager.unload_model("sentence-transformers/all-MiniLM-L6-v2")
        """
        with self._model_lock:
            if model_name in self._models:
                del self._models[model_name]
                logger.info("Model unloaded from memory", model=model_name)
    
    def unload_all(self) -> None:
        """
        Unload all models from memory.
        
        Example:
            >>> manager = ModelManager.get_instance()
            >>> manager.unload_all()
        """
        with self._model_lock:
            count = len(self._models)
            self._models.clear()
            logger.info("All models unloaded from memory", count=count)
    
    def get_model_dimension(self, model_name: str) -> int:
        """
        Get the embedding dimension for a model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Embedding dimension
            
        Raises:
            EmbeddingModelNotFoundError: If model cannot be loaded
            
        Example:
            >>> manager = ModelManager.get_instance()
            >>> dim = manager.get_model_dimension("sentence-transformers/all-MiniLM-L6-v2")
            >>> print(dim)  # 384
        """
        model = self.get_model(model_name)
        return model.get_sentence_embedding_dimension()
    
    def get_stats(self) -> dict:
        """
        Get statistics about loaded models.
        
        Returns:
            Dictionary with model manager statistics
            
        Example:
            >>> manager = ModelManager.get_instance()
            >>> stats = manager.get_stats()
            >>> print(stats)
        """
        with self._model_lock:
            model_info = []
            total_refs = 0
            
            for model_name, (model, ref_count) in self._models.items():
                try:
                    dimension = model.get_sentence_embedding_dimension()
                except Exception:
                    dimension = -1
                
                model_info.append({
                    "name": model_name,
                    "dimension": dimension,
                    "reference_count": ref_count
                })
                total_refs += ref_count
            
            return {
                "total_models": len(self._models),
                "total_references": total_refs,
                "models": model_info
            }
    
    def preload_models(self, model_names: list[str]) -> None:
        """
        Preload multiple models into memory.
        
        Useful for warming up the application with commonly used models.
        
        Args:
            model_names: List of model names to preload
            
        Example:
        >>> manager = ModelManager.get_instance()
        >>> manager.preload_models(["ibm-granite/granite-embedding-small-english-r2"])
        """
        start_time = time.time()
        logger.info(
            "Starting model preloading",
            count=len(model_names),
            models=model_names
        )
        
        loaded_count = 0
        failed_count = 0
        
        for idx, model_name in enumerate(model_names, 1):
            model_start = time.time()
            try:
                self.get_model(model_name)
                loaded_count += 1
                elapsed = time.time() - model_start
                logger.info(
                    "Model preloaded",
                    model=model_name,
                    progress=f"{idx}/{len(model_names)}",
                    elapsed_time=f"{elapsed:.4f}s"
                )
            except Exception as e:
                failed_count += 1
                elapsed = time.time() - model_start
                logger.error(
                    "Failed to preload model",
                    model=model_name,
                    progress=f"{idx}/{len(model_names)}",
                    error=str(e),
                    error_type=type(e).__name__,
                    elapsed_time=f"{elapsed:.4f}s"
                )
        
        total_elapsed = time.time() - start_time
        logger.info(
            "Preloading completed",
            total_models=len(model_names),
            loaded=loaded_count,
            failed=failed_count,
            cached_models=len(self._models),
            total_time=f"{total_elapsed:.4f}s",
            avg_time_per_model=f"{total_elapsed / len(model_names):.4f}s" if model_names else "0s"
        )
