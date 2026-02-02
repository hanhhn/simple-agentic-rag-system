"""
Embedding model implementations.

This module provides the Granite embedding model - the primary and only
embedding model used in the system. Granite offers superior performance,
long context support (8192 tokens), and enterprise-friendly license.
"""

from .granite_embedding import GraniteEmbeddingModel

__all__ = [
    "GraniteEmbeddingModel",
]
