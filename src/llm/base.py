"""
Base LLM interface.
"""
from abc import ABC, abstractmethod
from typing import Dict, Iterator, Optional


class LLMClient(ABC):
    """
    Abstract base class for LLM clients.
    
    All LLM client implementations should inherit from this class
    and implement the required methods.
    
    Attributes:
        model_name: Name of the LLM model
        temperature: Sampling temperature (0.0 to 2.0)
        max_tokens: Maximum tokens in response
    """
    
    def __init__(
        self,
        model_name: str,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> None:
        """
        Initialize LLM client.
        
        Args:
            model_name: Name of the model
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
        """
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs: Dict) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: Input prompt for the LLM
            **kwargs: Additional generation parameters
            
        Returns:
            Generated text response
            
        Example:
            >>> client = LLMClient()
            >>> response = client.generate("Hello, how are you?")
            >>> print(response)
        """
        pass
    
    @abstractmethod
    def generate_stream(self, prompt: str, **kwargs: Dict) -> Iterator[str]:
        """
        Generate a streaming response from the LLM.
        
        Args:
            prompt: Input prompt for the LLM
            **kwargs: Additional generation parameters
            
        Yields:
            Chunks of generated text
            
        Example:
            >>> client = LLMClient()
            >>> for chunk in client.generate_stream("Hello"):
            ...     print(chunk, end='')
        """
        pass
    
    @abstractmethod
    async def generate_async(self, prompt: str, **kwargs: Dict) -> str:
        """
        Asynchronously generate a response from the LLM.
        
        Args:
            prompt: Input prompt for the LLM
            **kwargs: Additional generation parameters
            
        Returns:
            Generated text response
        """
        pass
    
    def set_temperature(self, temperature: float) -> None:
        """
        Set the sampling temperature.
        
        Args:
            temperature: Temperature value (0.0 to 2.0)
            
        Example:
            >>> client = LLMClient()
            >>> client.set_temperature(0.5)
        """
        if not 0.0 <= temperature <= 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")
        self.temperature = temperature
    
    def set_max_tokens(self, max_tokens: int) -> None:
        """
        Set the maximum tokens for responses.
        
        Args:
            max_tokens: Maximum token count
            
        Example:
            >>> client = LLMClient()
            >>> client.set_max_tokens(4000)
        """
        if max_tokens < 1:
            raise ValueError("max_tokens must be positive")
        self.max_tokens = max_tokens
    
    def get_model_name(self) -> str:
        """
        Get the current model name.
        
        Returns:
            Model name string
        """
        return self.model_name
