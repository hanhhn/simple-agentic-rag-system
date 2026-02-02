"""
Embedding models and utilities for the RAG system.

This module provides:
- Abstract base class for embedding models
- Granite embedding model implementation
- Model manager with singleton pattern for efficient caching
- Model loader with advanced optimizations
- Disk-based embedding cache with LRU eviction
- Startup utilities for model prewarming
"""

from .base import EmbeddingModel
from .model_loader import ModelLoader
from .model_manager import ModelManager
from .cache import EmbeddingCache
from .models import GraniteEmbeddingModel
from . import startup

__all__ = [
    "EmbeddingModel",
    "ModelLoader",
    "ModelManager",
    "EmbeddingCache",
    "GraniteEmbeddingModel",
    "startup",
]
