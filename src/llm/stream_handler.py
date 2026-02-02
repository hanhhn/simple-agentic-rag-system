"""
Stream response handler for LLM outputs.
"""
import asyncio
from typing import AsyncIterator, Callable, Iterator, Optional

from src.core.logging import get_logger


logger = get_logger(__name__)


class StreamHandler:
    """
    Handler for streaming LLM responses.
    
    This class provides utilities for handling streaming responses,
    including buffering, callbacks, and async iteration.
    
    Example:
        >>> handler = StreamHandler()
        >>> async for chunk in handler.handle_stream(stream_function):
        ...     print(chunk, end='')
    """
    
    def __init__(self, buffer_size: int = 100) -> None:
        """
        Initialize stream handler.
        
        Args:
            buffer_size: Size of buffer for text processing
        """
        self.buffer_size = buffer_size
        self.buffer = ""
    
    def handle_stream(
        self,
        stream_generator: Iterator[str],
        callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        Handle a streaming response synchronously.
        
        Args:
            stream_generator: Generator yielding text chunks
            callback: Optional callback function for each chunk
            
        Returns:
            Complete generated text
            
        Example:
            >>> handler = StreamHandler()
            >>> def on_chunk(chunk):
            ...     print(f"Chunk: {chunk}")
            >>> full_text = handler.handle_stream(stream, on_chunk)
        """
        full_text = ""
        
        for chunk in stream_generator:
            # Add to buffer
            self.buffer += chunk
            
            # Process buffer if it's large enough
            if len(self.buffer) >= self.buffer_size:
                processed = self._process_buffer(self.buffer)
                full_text += processed
                
                # Call callback if provided
                if callback:
                    callback(processed)
                
                self.buffer = ""
        
        # Process remaining buffer
        if self.buffer:
            processed = self._process_buffer(self.buffer)
            full_text += processed
            if callback:
                callback(processed)
            self.buffer = ""
        
        return full_text
    
    async def handle_stream_async(
        self,
        stream_generator: AsyncIterator[str],
        callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        Handle a streaming response asynchronously.
        
        Args:
            stream_generator: Async generator yielding text chunks
            callback: Optional callback function for each chunk
            
        Returns:
            Complete generated text
        """
        full_text = ""
        
        async for chunk in stream_generator:
            # Add to buffer
            self.buffer += chunk
            
            # Process buffer if it's large enough
            if len(self.buffer) >= self.buffer_size:
                processed = self._process_buffer(self.buffer)
                full_text += processed
                
                # Call callback if provided
                if callback:
                    callback(processed)
                
                self.buffer = ""
        
        # Process remaining buffer
        if self.buffer:
            processed = self._process_buffer(self.buffer)
            full_text += processed
            if callback:
                callback(processed)
            self.buffer = ""
        
        return full_text
    
    def _process_buffer(self, buffer: str) -> str:
        """
        Process text buffer.
        
        This method can be overridden to implement custom
        processing logic (e.g., markdown formatting,
        token counting, etc.)
        
        Args:
            buffer: Text buffer to process
            
        Returns:
            Processed text
        """
        return buffer
    
    def stream_to_generator(
        self,
        iterator: Iterator[str],
        delay: float = 0.01
    ) -> Iterator[str]:
        """
        Convert an iterator to a streaming generator with delay.
        
        Args:
            iterator: Iterator yielding text
            delay: Delay between yields in seconds
            
        Yields:
            Text chunks with delay
        """
        for item in iterator:
            if delay > 0:
                import time
                time.sleep(delay)
            yield item
    
    async def stream_to_async_generator(
        self,
        async_iterator: AsyncIterator[str],
        delay: float = 0.01
    ) -> AsyncIterator[str]:
        """
        Convert an async iterator to an async streaming generator.
        
        Args:
            async_iterator: Async iterator yielding text
            delay: Delay between yields in seconds
            
        Yields:
            Text chunks with delay
        """
        async for item in async_iterator:
            if delay > 0:
                await asyncio.sleep(delay)
            yield item
    
    def get_full_text(self) -> str:
        """
        Get the accumulated full text from buffer.
        
        Returns:
            Full accumulated text
        """
        return self.buffer
    
    def clear(self) -> None:
        """Clear the buffer."""
        self.buffer = ""
        logger.info("Stream handler buffer cleared")


class StreamingCallback:
    """
    Callback manager for streaming responses.
    
    This class manages multiple callbacks that can be triggered
    during streaming response generation.
    
    Example:
        >>> callbacks = StreamingCallback()
        >>> @callbacks.on_chunk
        ... def handle_chunk(chunk):
        ...     print(chunk)
        >>> handler.handle_stream(stream, callbacks.on_chunk)
    """
    
    def __init__(self) -> None:
        """Initialize streaming callbacks."""
        self._chunk_callbacks: list[Callable[[str], None]] = []
        self._start_callbacks: list[Callable[[], None]] = []
        self._end_callbacks: list[Callable[[str], None]] = []
        self._error_callbacks: list[Callable[[Exception], None]] = []
    
    def on_chunk(self, callback: Callable[[str], None]) -> Callable[[str], None]:
        """
        Decorator to register a chunk callback.
        
        Args:
            callback: Function to call for each chunk
            
        Returns:
            The callback function
            
        Example:
            >>> @callbacks.on_chunk
            ... def handle_chunk(chunk):
            ...     print(chunk)
        """
        self._chunk_callbacks.append(callback)
        return callback
    
    def on_start(self, callback: Callable[[], None]) -> Callable[[], None]:
        """
        Decorator to register a start callback.
        
        Args:
            callback: Function to call when streaming starts
            
        Returns:
            The callback function
        """
        self._start_callbacks.append(callback)
        return callback
    
    def on_end(self, callback: Callable[[str], None]) -> Callable[[str], None]:
        """
        Decorator to register an end callback.
        
        Args:
            callback: Function to call when streaming ends
            
        Returns:
            The callback function
        """
        self._end_callbacks.append(callback)
        return callback
    
    def on_error(self, callback: Callable[[Exception], None]) -> Callable[[Exception], None]:
        """
        Decorator to register an error callback.
        
        Args:
            callback: Function to call on error
            
        Returns:
            The callback function
        """
        self._error_callbacks.append(callback)
        return callback
    
    def trigger_chunk(self, chunk: str) -> None:
        """
        Trigger all chunk callbacks.
        
        Args:
            chunk: Text chunk to pass to callbacks
        """
        for callback in self._chunk_callbacks:
            try:
                callback(chunk)
            except Exception as e:
                logger.error("Chunk callback failed", error=str(e))
    
    def trigger_start(self) -> None:
        """Trigger all start callbacks."""
        for callback in self._start_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error("Start callback failed", error=str(e))
    
    def trigger_end(self, full_text: str) -> None:
        """
        Trigger all end callbacks.
        
        Args:
            full_text: Complete generated text
        """
        for callback in self._end_callbacks:
            try:
                callback(full_text)
            except Exception as e:
                logger.error("End callback failed", error=str(e))
    
    def trigger_error(self, error: Exception) -> None:
        """
        Trigger all error callbacks.
        
        Args:
            error: Exception that occurred
        """
        for callback in self._error_callbacks:
            try:
                callback(error)
            except Exception as e:
                logger.error("Error callback failed", error=str(e))
