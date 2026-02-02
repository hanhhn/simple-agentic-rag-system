"""
Model loader for Granite embedding model.
"""
import time
from pathlib import Path
from typing import Optional
from sentence_transformers import SentenceTransformer

from src.core.logging import get_logger
from src.core.exceptions import EmbeddingModelNotFoundError
from src.core.config import get_config


logger = get_logger(__name__)


class ModelLoader:
    """
    Optimized loader for Granite embedding model.

    This class handles loading and managing Granite model with:
    - In-memory caching for reuse
    - Automatic model download from Hugging Face
    - CPU-optimized loading

    Attributes:
        cache_dir: Directory to cache downloaded models

    Example:
        >>> loader = ModelLoader()
        >>> model = loader.load_model("ibm-granite/granite-embedding-small-english-r2")
    """
    
    def __init__(
        self,
        cache_dir: Optional[Path | str] = None
    ) -> None:
        """
        Initialize model loader.
        
        Args:
            cache_dir: Directory to cache models (uses config default if None)
        """
        config = get_config()
        
        self.cache_dir = Path(cache_dir or config.storage.model_cache_path)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self._loaded_models: dict = {}
        
        logger.info(
            "ModelLoader initialized",
            cache_dir=str(self.cache_dir)
        )
    
    def load_model(self, model_name: str) -> object:
        """
        Load Granite embedding model from Hugging Face or local path.

        Args:
            model_name: Name of the model on Hugging Face or local path

        Returns:
            Loaded sentence-transformers model

        Raises:
            EmbeddingModelNotFoundError: If model cannot be loaded

        Example:
            >>> loader = ModelLoader()
            >>> model = loader.load_model("ibm-granite/granite-embedding-small-english-r2")
        """
        start_time = time.time()
        
        # Check if model is already loaded
        if model_name in self._loaded_models:
            elapsed = time.time() - start_time
            logger.info(
                "Model already loaded in memory",
                model=model_name,
                retrieval_time=f"{elapsed:.4f}s"
            )
            return self._loaded_models[model_name]
        
        logger.info(
            "Loading Granite embedding model",
            model=model_name,
            cache_dir=str(self.cache_dir)
        )

        try:
            # Prepare model arguments
            model_kwargs = {
                "cache_folder": str(self.cache_dir),
                "device": "cpu",  # Always use CPU for simplicity
            }

            # Load model
            logger.info("Starting model download/load", model=model_name)
            load_start = time.time()
            model = SentenceTransformer(model_name, **model_kwargs)
            load_elapsed = time.time() - load_start
            logger.info("Model downloaded/loaded", model=model_name, load_time=f"{load_elapsed:.4f}s")

            # Get model details
            dimension = model.get_sentence_embedding_dimension()
            max_seq_length = model.max_seq_length if hasattr(model, 'max_seq_length') else 'unknown'

            logger.info(
                "Granite model loaded successfully",
                model=model_name,
                dimension=dimension,
                max_seq_length=max_seq_length,
                load_time=f"{load_elapsed:.4f}s"
            )
            
            # Set model to eval mode for inference
            try:
                for param in model.parameters():
                    param.requires_grad = False
                logger.info("Set model to eval mode", model=model_name)
            except Exception as e:
                logger.warning("Could not set requires_grad=False", model=model_name, error=str(e))
            
            # Cache in memory
            self._loaded_models[model_name] = model
            
            total_elapsed = time.time() - start_time
            logger.info(
                "Model caching completed",
                model=model_name,
                cache_size=len(self._loaded_models),
                total_time=f"{total_elapsed:.4f}s"
            )
            
            return model
            
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
                f"Failed to load Granite embedding model '{model_name}': {str(e)}",
                details={
                    "model_name": model_name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "elapsed_time": f"{elapsed:.4f}s"
                }
            )
    
    def unload_model(self, model_name: str) -> None:
        """
        Unload a model from memory cache.
        
        Args:
            model_name: Name of the model to unload
            
        Example:
            >>> loader = ModelLoader()
            >>> loader.unload_model("ibm-granite/granite-embedding-small-english-r2")
        """
        if model_name in self._loaded_models:
            del self._loaded_models[model_name]
            logger.info(
                "Model unloaded from memory",
                model=model_name,
                remaining_models=len(self._loaded_models)
            )
        else:
            logger.warning(
                "Model not found in memory",
                model=model_name,
                cached_models=list(self._loaded_models.keys())
            )
    
    def unload_all(self) -> None:
        """
        Unload all models from memory cache.
        
        Example:
            >>> loader = ModelLoader()
            >>> loader.unload_all()
        """
        count = len(self._loaded_models)
        models_to_unload = list(self._loaded_models.keys())
        self._loaded_models.clear()
        logger.info(
            "All models unloaded from memory",
            unloaded_count=count,
            models=models_to_unload
        )
    
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
            >>> loader = ModelLoader()
            >>> dim = loader.get_model_dimension("ibm-granite/granite-embedding-small-english-r2")
            >>> print(dim)  # 384
        """
        model = self.load_model(model_name)
        return model.get_sentence_embedding_dimension()
    
    def clear_cache(self) -> None:
        """
        Clear the model cache directory.
        
        Warning: This will delete downloaded models, requiring
        them to be downloaded again.
        
        Example:
            >>> loader = ModelLoader()
            >>> loader.clear_cache()
        """
        import shutil
        
        logger.warning("Clearing model cache", cache_dir=str(self.cache_dir))
        
        # Unload all models first
        self.unload_all()
        
        # Clear cache directory
        for item in self.cache_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
                logger.info("Removed model from cache", model=item.name)
    
    def get_cache_size(self) -> int:
        """
        Get the size of the model cache directory in bytes.
        
        Returns:
            Cache directory size in bytes
            
        Example:
            >>> loader = ModelLoader()
            >>> size_mb = loader.get_cache_size() / (1024 * 1024)
            >>> print(f"Cache size: {size_mb:.1f} MB")
        """
        total_size = 0
        
        if self.cache_dir.exists():
            for item in self.cache_dir.rglob("*"):
                if item.is_file():
                    total_size += item.stat().st_size
        
        return total_size
    
    def list_cached_models(self) -> list[str]:
        """
        List all models in the cache directory.
        
        Returns:
            List of model names/directories
            
        Example:
            >>> loader = ModelLoader()
            >>> models = loader.list_cached_models()
            >>> for model in models:
            ...     print(model)
        """
        models = []
        
        if self.cache_dir.exists():
            # Look for model directories
            for item in self.cache_dir.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    models.append(item.name)
        
        return sorted(models)
