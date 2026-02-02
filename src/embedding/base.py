"""
Base embedding model interface.
"""
from abc import ABC, abstractmethod
from typing import List


class EmbeddingModel(ABC):
    """
    Abstract base class for embedding models.
    
    All embedding model implementations should inherit from this class
    and implement the required methods.
    
    Attributes:
        model_name: Name or path of the embedding model
        dimension: Dimension of the embedding vectors
        max_length: Maximum input sequence length
    """
    
    def __init__(self, model_name: str, dimension: int, max_length: int = 512) -> None:
        """
        Initialize the embedding model.
        
        Args:
            model_name: Name or path of the model
            dimension: Embedding dimension
            max_length: Maximum input sequence length
        """
        self.model_name = model_name
        self.dimension = dimension
        self.max_length = max_length
    
    @abstractmethod
    def encode(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Encode texts into embedding vectors.
        
        Args:
            texts: List of text strings to encode
            batch_size: Batch size for encoding
            
        Returns:
            List of embedding vectors (each is a list of floats)
            
        Example:
            >>> model = EmbeddingModel()
            >>> embeddings = model.encode(["text1", "text2"])
            >>> print(len(embeddings))  # 2
        """
        pass
    
    @abstractmethod
    def encode_single(self, text: str) -> List[float]:
        """
        Encode a single text into an embedding vector.
        
        Args:
            text: Text string to encode
            
        Returns:
            Embedding vector as a list of floats
            
        Example:
            >>> model = EmbeddingModel()
            >>> embedding = model.encode_single("Hello world")
            >>> print(len(embedding))  # dimension of the model
        """
        pass
    
    def get_dimension(self) -> int:
        """
        Get the dimension of the embedding vectors.
        
        Returns:
            Embedding dimension
        """
        return self.dimension
    
    def get_model_name(self) -> str:
        """
        Get the name/path of the model.
        
        Returns:
            Model name or path
        """
        return self.model_name
