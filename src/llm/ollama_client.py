"""
Ollama LLM client implementation.
"""
import asyncio
from typing import AsyncIterator, Dict, Iterator, Optional

import httpx

from src.core.logging import get_logger
from src.core.exceptions import LLMConnectionError, LLMGenerationError, LLMModelNotFoundError
from src.core.config import get_config
from src.llm.base import LLMClient


logger = get_logger(__name__)


class OllamaClient(LLMClient):
    """
    Ollama LLM client.
    
    This client interacts with Ollama's HTTP API to generate text
    from local LLM models.
    
    Example:
        >>> client = OllamaClient(model="llama2")
        >>> response = client.generate("Hello, how are you?")
        >>> print(response)
    """
    
    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: int | None = None
    ) -> None:
        """
        Initialize Ollama client.
        
        Args:
            model: Model name (uses config default if None)
            base_url: Ollama server URL (uses config default if None)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            timeout: Request timeout in seconds
        """
        config = get_config()
        
        super().__init__(
            model_name=model or config.ollama.model,
            temperature=temperature or config.ollama.temperature,
            max_tokens=max_tokens or config.ollama.max_tokens
        )
        
        self.base_url = base_url or config.ollama.url.rstrip('/')
        self.timeout = timeout or config.ollama.timeout
        
        # Create HTTP client
        self._client = httpx.Client(timeout=self.timeout)
        self._async_client = httpx.AsyncClient(timeout=self.timeout)
        
        logger.info(
            "Ollama client initialized",
            model=self.model_name,
            base_url=self.base_url
        )
    
    def generate(self, prompt: str, **kwargs: Dict) -> str:
        """
        Generate a response from Ollama.
        
        Args:
            prompt: Input prompt
            **kwargs: Additional parameters (e.g., stream, options)
            
        Returns:
            Generated text response
            
        Raises:
            LLMConnectionError: If connection fails
            LLMGenerationError: If generation fails
            
        Example:
            >>> client = OllamaClient()
            >>> response = client.generate("Hello!")
            >>> print(response)
        """
        try:
            logger.info(
                "Generating response from Ollama",
                model=self.model_name,
                prompt_length=len(prompt)
            )
            
            # Prepare request payload
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                }
            }
            
            # Merge additional options
            if "options" in kwargs:
                payload["options"].update(kwargs["options"])
            
            # Make request
            response = self._client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            generated_text = data.get("response", "")
            
            logger.info(
                "Successfully generated response",
                model=self.model_name,
                response_length=len(generated_text)
            )
            
            return generated_text
            
        except httpx.ConnectError as e:
            logger.error("Failed to connect to Ollama", error=str(e))
            raise LLMConnectionError(
                f"Failed to connect to Ollama server: {str(e)}",
                details={"url": self.base_url, "error": str(e)}
            )
        except httpx.HTTPStatusError as e:
            logger.error("Ollama returned HTTP error", status=e.response.status_code, error=str(e))
            raise LLMGenerationError(
                f"Ollama returned error: {e.response.status_code}",
                details={"status": e.response.status_code, "error": str(e)}
            )
        except Exception as e:
            logger.error("Failed to generate response", error=str(e))
            raise LLMGenerationError(
                f"Failed to generate response: {str(e)}",
                details={"error": str(e)}
            )
    
    def generate_stream(self, prompt: str, **kwargs: Dict) -> Iterator[str]:
        """
        Generate a streaming response from Ollama.
        
        Args:
            prompt: Input prompt
            **kwargs: Additional parameters
            
        Yields:
            Chunks of generated text
            
        Example:
            >>> client = OllamaClient()
            >>> for chunk in client.generate_stream("Hello!"):
            ...     print(chunk, end='')
        """
        try:
            logger.info(
                "Generating streaming response from Ollama",
                model=self.model_name,
                prompt_length=len(prompt)
            )
            
            # Prepare request payload
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                }
            }
            
            # Merge additional options
            if "options" in kwargs:
                payload["options"].update(kwargs["options"])
            
            # Make request
            response = self._client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )
            response.raise_for_status()
            
            # Stream response
            for line in response.iter_lines():
                if line:
                    try:
                        data = line.decode('utf-8')
                        json_data = self._parse_json_line(data)
                        
                        if json_data and "response" in json_data:
                            yield json_data["response"]
                            
                    except Exception as e:
                        logger.warning("Failed to parse stream chunk", error=str(e))
                        continue
            
            logger.info(
                "Successfully generated streaming response",
                model=self.model_name
            )
            
        except httpx.ConnectError as e:
            logger.error("Failed to connect to Ollama", error=str(e))
            raise LLMConnectionError(
                f"Failed to connect to Ollama server: {str(e)}",
                details={"url": self.base_url, "error": str(e)}
            )
        except Exception as e:
            logger.error("Failed to generate streaming response", error=str(e))
            raise LLMGenerationError(
                f"Failed to generate streaming response: {str(e)}",
                details={"error": str(e)}
            )
    
    async def generate_async(self, prompt: str, **kwargs: Dict) -> str:
        """
        Asynchronously generate a response from Ollama.
        
        Args:
            prompt: Input prompt
            **kwargs: Additional parameters
            
        Returns:
            Generated text response
        """
        try:
            logger.info(
                "Generating async response from Ollama",
                model=self.model_name,
                prompt_length=len(prompt)
            )
            
            # Prepare request payload
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                }
            }
            
            # Merge additional options
            if "options" in kwargs:
                payload["options"].update(kwargs["options"])
            
            # Make async request
            response = await self._async_client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            generated_text = data.get("response", "")
            
            logger.info(
                "Successfully generated async response",
                model=self.model_name,
                response_length=len(generated_text)
            )
            
            return generated_text
            
        except httpx.ConnectError as e:
            logger.error("Failed to connect to Ollama", error=str(e))
            raise LLMConnectionError(
                f"Failed to connect to Ollama server: {str(e)}",
                details={"url": self.base_url, "error": str(e)}
            )
        except Exception as e:
            logger.error("Failed to generate async response", error=str(e))
            raise LLMGenerationError(
                f"Failed to generate async response: {str(e)}",
                details={"error": str(e)}
            )
    
    def list_models(self) -> list[str]:
        """
        List available models on Ollama server.
        
        Returns:
            List of model names
            
        Example:
            >>> client = OllamaClient()
            >>> models = client.list_models()
            >>> print(models)  # ["llama2", "mistral", ...]
        """
        try:
            response = self._client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            
            data = response.json()
            models = [model["name"] for model in data.get("models", [])]
            
            logger.info("Retrieved available models", count=len(models))
            
            return models
            
        except Exception as e:
            logger.error("Failed to list models", error=str(e))
            raise LLMConnectionError(
                f"Failed to retrieve models: {str(e)}",
                details={"error": str(e)}
            )
    
    def check_model_exists(self, model_name: str | None = None) -> bool:
        """
        Check if a model exists on Ollama server.
        
        Args:
            model_name: Model name to check (uses current model if None)
            
        Returns:
            True if model exists, False otherwise
            
        Example:
            >>> client = OllamaClient()
            >>> if client.check_model_exists("llama2"):
            ...     print("Model is available")
        """
        model = model_name or self.model_name
        models = self.list_models()
        return any(model == m or m.startswith(model) for m in models)
    
    def pull_model(self, model_name: str) -> None:
        """
        Pull a model from Ollama library.
        
        Args:
            model_name: Model name to pull
            
        Raises:
            LLMConnectionError: If pull fails
            
        Example:
            >>> client = OllamaClient()
            >>> client.pull_model("llama2")
        """
        try:
            logger.info("Pulling model from Ollama", model=model_name)
            
            response = self._client.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name}
            )
            response.raise_for_status()
            
            logger.info("Model pulled successfully", model=model_name)
            
        except Exception as e:
            logger.error("Failed to pull model", model=model_name, error=str(e))
            raise LLMConnectionError(
                f"Failed to pull model: {str(e)}",
                details={"model": model_name, "error": str(e)}
            )
    
    def _parse_json_line(self, line: str) -> Optional[Dict]:
        """
        Parse a JSON line from streaming response.
        
        Args:
            line: JSON line to parse
            
        Returns:
            Parsed JSON data or None
        """
        import json
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            return None
    
    def close(self) -> None:
        """
        Close the HTTP client.
        
        Example:
            >>> client = OllamaClient()
            >>> client.close()
        """
        self._client.close()
        self._async_client.aclose()
        logger.info("Ollama client closed")
    
    async def aclose(self) -> None:
        """
        Asynchronously close the HTTP client.
        """
        await self._async_client.aclose()
        self._client.close()
        logger.info("Ollama async client closed")
