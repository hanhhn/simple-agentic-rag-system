"""
LLM service for generating responses.
"""
import time
from typing import List, Dict, Optional

from src.core.logging import get_logger
from src.core.exceptions import LLMError
from src.core.config import get_config
from src.llm.base import LLMClient
from src.llm.ollama_client import OllamaClient
from src.llm.prompt_builder import PromptBuilder


logger = get_logger(__name__)


class LLMService:
    """
    Service for LLM text generation.
    
    This class provides a high-level interface for generating
    text with LLMs, including prompt building,
    streaming support, and response handling.
    
    Example:
        >>> service = LLMService()
        >>> response = service.generate("Hello, how are you?")
        >>> print(response)
    """
    
    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> None:
        """
        Initialize LLM service.
        
        Args:
            model: Model name (uses config default if None)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
        """
        config = get_config()
        
        # Initialize client
        self.client = OllamaClient(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Initialize prompt builder
        self.prompt_builder = PromptBuilder()
        
        logger.info(
            "LLM service initialized",
            model=self.client.get_model_name(),
            temperature=self.client.temperature,
            max_tokens=self.client.max_tokens
        )
    
    def generate(
        self,
        prompt: str,
        use_template: bool = False,
        **kwargs: Dict
    ) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: Input prompt
            use_template: Whether to use RAG template
            **kwargs: Additional parameters
            
        Returns:
            Generated response
            
        Example:
            >>> service = LLMService()
            >>> response = service.generate("Hello!")
        """
        start_time = time.time()
        
        try:
            model_name = self.client.get_model_name()
            
            logger.info(
                "Starting LLM generation",
                model=model_name,
                prompt_length=len(prompt),
                use_template=use_template,
                kwargs=kwargs
            )
            
            # Generate response
            generate_start = time.time()
            response = self.client.generate(prompt, **kwargs)
            generate_elapsed = time.time() - generate_start
            
            total_elapsed = time.time() - start_time
            
            logger.info(
                "Response generated successfully",
                model=model_name,
                prompt_length=len(prompt),
                response_length=len(response),
                generate_time=f"{generate_elapsed:.4f}s",
                total_time=f"{total_elapsed:.4f}s",
                tokens_per_second=f"{len(response.split()) / generate_elapsed:.2f}" if generate_elapsed > 0 else "0"
            )
            
            return response
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(
                "Failed to generate response",
                model=self.client.get_model_name(),
                error=str(e),
                error_type=type(e).__name__,
                prompt_length=len(prompt),
                elapsed_time=f"{elapsed:.4f}s"
            )
            raise LLMError(
                f"Failed to generate LLM response: {str(e)}",
                details={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "elapsed_time": f"{elapsed:.4f}s"
                }
            )
    
    def generate_rag(
        self,
        question: str,
        contexts: List[str],
        **kwargs: Dict
    ) -> str:
        """
        Generate a RAG response with context.
        
        Args:
            question: User's question
            contexts: List of context strings from retrieved documents
            **kwargs: Additional parameters
            
        Returns:
            Generated response using RAG prompt
            
        Example:
            >>> service = LLMService()
            >>> response = service.generate_rag(
            ...     question="What is RAG?",
            ...     contexts=["RAG stands for Retrieval-Augmented Generation"]
            ... )
        """
        start_time = time.time()
        
        try:
            total_context_length = sum(len(ctx) for ctx in contexts)
            
            logger.info(
                "Starting RAG generation",
                question=question[:100],
                question_length=len(question),
                context_count=len(contexts),
                total_context_length=total_context_length
            )
            
            # Build RAG prompt
            prompt_start = time.time()
            prompt = self.prompt_builder.build_rag_prompt(question, contexts)
            prompt_elapsed = time.time() - prompt_start
            
            logger.info(
                "RAG prompt built",
                prompt_length=len(prompt),
                build_time=f"{prompt_elapsed:.6f}s"
            )
            
            # Generate response
            response = self.generate(prompt, **kwargs)
            
            total_elapsed = time.time() - start_time
            
            logger.info(
                "RAG response generated successfully",
                question=question[:100],
                context_count=len(contexts),
                total_context_length=total_context_length,
                response_length=len(response),
                prompt_build_time=f"{prompt_elapsed:.6f}s",
                total_time=f"{total_elapsed:.4f}s"
            )
            
            return response
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(
                "Failed to generate RAG response",
                question=question[:100],
                context_count=len(contexts),
                error=str(e),
                error_type=type(e).__name__,
                elapsed_time=f"{elapsed:.4f}s"
            )
            raise LLMError(
                f"Failed to generate RAG response: {str(e)}",
                details={
                    "question": question[:100],
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "elapsed_time": f"{elapsed:.4f}s"
                }
            )
    
    def generate_stream(
        self,
        prompt: str,
        use_template: bool = False,
        **kwargs: Dict
    ) -> List[str]:
        """
        Generate a streaming response from the LLM.
        
        Args:
            prompt: Input prompt
            use_template: Whether to use RAG template
            **kwargs: Additional parameters
            
        Returns:
            List of text chunks
            
        Example:
            >>> service = LLMService()
            >>> chunks = service.generate_stream("Hello!")
            >>> for chunk in chunks:
            ...     print(chunk, end='')
        """
        start_time = time.time()
        
        try:
            model_name = self.client.get_model_name()
            
            logger.info(
                "Starting streaming generation",
                model=model_name,
                prompt_length=len(prompt),
                use_template=use_template
            )
            
            # Generate streaming response
            stream_start = time.time()
            chunks = list(self.client.generate_stream(prompt, **kwargs))
            stream_elapsed = time.time() - stream_start
            
            total_length = sum(len(c) for c in chunks)
            total_elapsed = time.time() - start_time
            
            logger.info(
                "Streaming response generated successfully",
                model=model_name,
                chunk_count=len(chunks),
                total_length=total_length,
                stream_time=f"{stream_elapsed:.4f}s",
                total_time=f"{total_elapsed:.4f}s",
                avg_chunk_size=f"{total_length / len(chunks):.1f}" if chunks else "0",
                tokens_per_second=f"{total_length / stream_elapsed:.2f}" if stream_elapsed > 0 else "0"
            )
            
            return chunks
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(
                "Failed to generate streaming response",
                model=self.client.get_model_name(),
                error=str(e),
                error_type=type(e).__name__,
                prompt_length=len(prompt),
                elapsed_time=f"{elapsed:.4f}s"
            )
            raise LLMError(
                f"Failed to generate streaming response: {str(e)}",
                details={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "elapsed_time": f"{elapsed:.4f}s"
                }
            )
    
    def generate_rag_stream(
        self,
        question: str,
        contexts: List[str],
        **kwargs: Dict
    ) -> List[str]:
        """
        Generate a streaming RAG response with context.
        
        Args:
            question: User's question
            contexts: List of context strings from retrieved documents
            **kwargs: Additional parameters
            
        Returns:
            List of text chunks
            
        Example:
            >>> service = LLMService()
            >>> chunks = service.generate_rag_stream(
            ...     question="What is RAG?",
            ...     contexts=["RAG is..."]
            ... )
        """
        try:
            # Build RAG prompt
            prompt = self.prompt_builder.build_rag_prompt(question, contexts)
            
            # Generate streaming response
            chunks = self.generate_stream(prompt, **kwargs)
            
            logger.info(
                "RAG streaming response generated",
                question=question[:100],
                context_count=len(contexts),
                chunk_count=len(chunks)
            )
            
            return chunks
            
        except Exception as e:
            logger.error("Failed to generate RAG streaming response", error=str(e))
            raise LLMError(
                f"Failed to generate RAG streaming response: {str(e)}",
                details={"question": question[:100], "error": str(e)}
            )
    
    def summarize(self, text: str, max_length: int = 200) -> str:
        """
        Summarize a text.
        
        Args:
            text: Text to summarize
            max_length: Maximum length of summary in words
            
        Returns:
            Generated summary
            
        Example:
            >>> service = LLMService()
            >>> summary = service.summarize(long_document)
        """
        try:
            # Build summarization prompt
            prompt = self.prompt_builder.build_summarization_prompt(text, max_length)
            
            # Generate summary
            summary = self.generate(prompt)
            
            logger.info(
                "Summary generated",
                original_length=len(text),
                summary_length=len(summary),
                max_length=max_length
            )
            
            return summary
            
        except Exception as e:
            logger.error("Failed to generate summary", error=str(e))
            raise LLMError(
                f"Failed to generate summary: {str(e)}",
                details={"error": str(e)}
            )
    
    def list_models(self) -> List[str]:
        """
        List available LLM models.
        
        Returns:
            List of model names
        """
        try:
            return self.client.list_models()
        except Exception as e:
            logger.error("Failed to list models", error=str(e))
            raise LLMError(
                f"Failed to list LLM models: {str(e)}",
                details={"error": str(e)}
            )
    
    def set_model(self, model: str) -> None:
        """
        Change the LLM model.
        
        Args:
            model: Name of the new model
        """
        try:
            # Create new client with different model
            self.client = OllamaClient(model=model)
            
            logger.info("LLM model changed", model=model)
            
        except Exception as e:
            logger.error("Failed to change model", model=model, error=str(e))
            raise LLMError(
                f"Failed to change model to '{model}': {str(e)}",
                details={"model": model, "error": str(e)}
            )
    
    def get_model_name(self) -> str:
        """
        Get the current model name.
        
        Returns:
            Model name
        """
        return self.client.get_model_name()
    
    def close(self) -> None:
        """Close LLM client."""
        self.client.close()
        logger.info("LLM service closed")
