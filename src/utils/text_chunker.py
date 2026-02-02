"""
Text chunking strategies for splitting text into manageable pieces.

This module provides various text chunking strategies to split text into
chunks suitable for embedding and retrieval. Different strategies are
provided for different types of content and use cases.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator, List
import re


@dataclass
class Chunk:
    """
    Represents a text chunk with metadata.
    
    Attributes:
        text: The chunk text content
        start_index: Starting character index in the original text
        end_index: Ending character index in the original text
        metadata: Additional metadata about the chunk
    """
    text: str
    start_index: int
    end_index: int
    metadata: dict = None
    
    def __post_init__(self) -> None:
        """Initialize metadata if not provided."""
        if self.metadata is None:
            self.metadata = {}


class BaseChunker(ABC):
    """
    Abstract base class for text chunkers.
    
    All chunker implementations should inherit from this class and
    implement the chunk method.
    """
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200) -> None:
        """
        Initialize the chunker.
        
        Args:
            chunk_size: Maximum size of each chunk in characters
            chunk_overlap: Number of characters to overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
    
    @abstractmethod
    def chunk(self, text: str) -> List[Chunk]:
        """
        Split text into chunks.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of Chunk objects
        """
        pass


class CharacterChunker(BaseChunker):
    """
    Simple character-based chunker.
    
    Splits text into chunks based on character count. This is the simplest
    chunking strategy and works well for most general use cases.
    
    Example:
        >>> chunker = CharacterChunker(chunk_size=100, chunk_overlap=20)
        >>> chunks = chunker.chunk("This is a long text that needs to be chunked...")
    """
    
    def chunk(self, text: str) -> List[Chunk]:
        """
        Split text into character-based chunks.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of Chunk objects
        """
        if not text:
            return []
        
        chunks = []
        start = 0
        
        while start < len(text):
            # Determine end of this chunk
            end = start + self.chunk_size
            
            # Adjust for overlap if not the first chunk
            if start > 0:
                start = start - self.chunk_overlap
            
            # Ensure we don't go beyond text length
            if end > len(text):
                end = len(text)
            
            # Extract chunk
            chunk_text = text[start:end].strip()
            
            if chunk_text:  # Only add non-empty chunks
                chunk = Chunk(
                    text=chunk_text,
                    start_index=start,
                    end_index=end,
                    metadata={"chunk_type": "character", "chunk_size": len(chunk_text)}
                )
                chunks.append(chunk)
            
            # Move to next chunk
            start = end
        
        return chunks


class WordChunker(BaseChunker):
    """
    Word-based chunker.
    
    Splits text into chunks based on word count, ensuring chunks don't
    split words in the middle. This is better for maintaining readability.
    
    Example:
        >>> chunker = WordChunker(chunk_size=100, chunk_overlap=20)
        >>> chunks = chunker.chunk("This is a long text that needs to be chunked...")
    """
    
    def chunk(self, text: str) -> List[Chunk]:
        """
        Split text into word-based chunks.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of Chunk objects
        """
        if not text:
            return []
        
        words = text.split()
        chunks = []
        start_word = 0
        
        while start_word < len(words):
            # Calculate word count for this chunk
            end_word = min(start_word + self.chunk_size, len(words))
            
            # Adjust for overlap
            if start_word > 0:
                overlap_words = min(self.chunk_overlap, start_word)
                start_word = start_word - overlap_words
            
            # Extract chunk
            chunk_words = words[start_word:end_word]
            chunk_text = " ".join(chunk_words)
            
            # Find actual character indices
            chunk_start = text.find(chunk_words[0]) if chunk_words else 0
            chunk_end = text.rfind(chunk_words[-1]) + len(chunk_words[-1]) if chunk_words else len(text)
            
            chunk = Chunk(
                text=chunk_text,
                start_index=chunk_start,
                end_index=chunk_end,
                metadata={
                    "chunk_type": "word",
                    "word_count": len(chunk_words),
                    "start_word": start_word,
                    "end_word": end_word
                }
            )
            chunks.append(chunk)
            
            # Move to next chunk
            start_word = end_word
        
        return chunks


class SentenceChunker(BaseChunker):
    """
    Sentence-based chunker.
    
    Splits text into chunks based on sentence boundaries, ensuring chunks
    don't split sentences in the middle. This provides better semantic
    coherence for retrieval.
    
    Example:
        >>> chunker = SentenceChunker(chunk_size=1000, chunk_overlap=200)
        >>> chunks = chunker.chunk("This is sentence one. This is sentence two...")
    """
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200) -> None:
        """
        Initialize the sentence chunker.
        
        Args:
            chunk_size: Maximum size of each chunk in characters
            chunk_overlap: Number of characters to overlap between chunks
        """
        super().__init__(chunk_size, chunk_overlap)
        # Pattern to match sentence endings
        self.sentence_pattern = re.compile(
            r'(?<=[.!?])\s+(?=[A-Z])|'  # Sentence ending followed by space and uppercase
            r'(?<=[.!?])\s*$'             # Sentence ending at end of text
        )
    
    def split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.
        
        Args:
            text: Text to split
            
        Returns:
            List of sentences
        """
        sentences = self.sentence_pattern.split(text)
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences
    
    def chunk(self, text: str) -> List[Chunk]:
        """
        Split text into sentence-based chunks.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of Chunk objects
        """
        if not text:
            return []
        
        sentences = self.split_sentences(text)
        chunks = []
        current_chunk = ""
        current_start = 0
        
        for i, sentence in enumerate(sentences):
            # Check if adding this sentence exceeds chunk size
            if current_chunk and len(current_chunk) + len(sentence) > self.chunk_size:
                # Save current chunk
                if current_chunk:
                    current_chunk = current_chunk.strip()
                    chunk = Chunk(
                        text=current_chunk,
                        start_index=current_start,
                        end_index=current_start + len(current_chunk),
                        metadata={
                            "chunk_type": "sentence",
                            "sentence_count": current_chunk.count('.') + current_chunk.count('!') + current_chunk.count('?'),
                            "chunk_size": len(current_chunk)
                        }
                    )
                    chunks.append(chunk)
                
                # Start new chunk with overlap
                # Find last sentence to overlap with
                overlap_sentences = self._get_overlap_sentences(current_chunk, self.chunk_overlap)
                current_chunk = overlap_sentences + " " + sentence
                current_start = text.rfind(overlap_sentences) if overlap_sentences else current_start
            else:
                # Add sentence to current chunk
                if not current_chunk:
                    current_start = text.find(sentence)
                current_chunk = current_chunk + " " + sentence if current_chunk else sentence
        
        # Add final chunk if not empty
        if current_chunk.strip():
            current_chunk = current_chunk.strip()
            chunk = Chunk(
                text=current_chunk,
                start_index=current_start,
                end_index=current_start + len(current_chunk),
                metadata={
                    "chunk_type": "sentence",
                    "sentence_count": current_chunk.count('.') + current_chunk.count('!') + current_chunk.count('?'),
                    "chunk_size": len(current_chunk)
                }
            )
            chunks.append(chunk)
        
        return chunks
    
    def _get_overlap_sentences(self, text: str, overlap_size: int) -> str:
        """
        Get the last portion of text for overlap.
        
        Args:
            text: Text to extract overlap from
            overlap_size: Size of overlap in characters
            
        Returns:
            Text to overlap with next chunk
        """
        if not text:
            return ""
        
        if len(text) <= overlap_size:
            return text
        
        # Get overlap portion
        overlap_text = text[-overlap_size:]
        
        # Find last sentence boundary
        last_period = overlap_text.rfind('.')
        last_exclamation = overlap_text.rfind('!')
        last_question = overlap_text.rfind('?')
        
        last_boundary = max(last_period, last_exclamation, last_question)
        
        if last_boundary > 0:
            # Return from last complete sentence
            return overlap_text[last_boundary + 1:].strip()
        
        return overlap_text.strip()


class ParagraphChunker(BaseChunker):
    """
    Paragraph-based chunker.
    
    Splits text into chunks based on paragraph boundaries (double newlines).
    This is useful for documents where paragraphs are semantically meaningful.
    
    Example:
        >>> chunker = ParagraphChunker(chunk_size=1000, chunk_overlap=200)
        >>> chunks = chunker.chunk("Para 1\n\nPara 2\n\nPara 3...")
    """
    
    def chunk(self, text: str) -> List[Chunk]:
        """
        Split text into paragraph-based chunks.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of Chunk objects
        """
        if not text:
            return []
        
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        chunks = []
        current_chunk = ""
        current_start = 0
        
        for para in paragraphs:
            # Check if adding this paragraph exceeds chunk size
            if current_chunk and len(current_chunk) + len(para) > self.chunk_size:
                # Save current chunk
                if current_chunk:
                    current_chunk = current_chunk.strip()
                    chunk = Chunk(
                        text=current_chunk,
                        start_index=current_start,
                        end_index=current_start + len(current_chunk),
                        metadata={
                            "chunk_type": "paragraph",
                            "paragraph_count": current_chunk.count('\n\n') + 1,
                            "chunk_size": len(current_chunk)
                        }
                    )
                    chunks.append(chunk)
                
                # Start new chunk with overlap
                overlap_para = self._get_overlap_paragraph(current_chunk, self.chunk_overlap)
                current_chunk = overlap_para + "\n\n" + para
                current_start = text.rfind(overlap_para) if overlap_para else current_start
            else:
                # Add paragraph to current chunk
                if not current_chunk:
                    current_start = text.find(para)
                current_chunk = current_chunk + "\n\n" + para if current_chunk else para
        
        # Add final chunk if not empty
        if current_chunk.strip():
            current_chunk = current_chunk.strip()
            chunk = Chunk(
                text=current_chunk,
                start_index=current_start,
                end_index=current_start + len(current_chunk),
                metadata={
                    "chunk_type": "paragraph",
                    "paragraph_count": current_chunk.count('\n\n') + 1,
                    "chunk_size": len(current_chunk)
                }
            )
            chunks.append(chunk)
        
        return chunks
    
    def _get_overlap_paragraph(self, text: str, overlap_size: int) -> str:
        """
        Get the last paragraph for overlap.
        
        Args:
            text: Text to extract overlap from
            overlap_size: Size of overlap in characters
            
        Returns:
            Text to overlap with next chunk
        """
        if not text:
            return ""
        
        if len(text) <= overlap_size:
            return text
        
        # Get overlap portion
        overlap_text = text[-overlap_size:]
        
        # Find last paragraph boundary
        last_boundary = overlap_text.rfind('\n\n')
        
        if last_boundary > 0:
            return overlap_text[last_boundary + 2:].strip()
        
        return overlap_text.strip()


class RecursiveCharacterChunker(BaseChunker):
    """
    Recursive character-based chunker with multiple separators.
    
    This chunker tries multiple separators in order to find the best place
    to split text. It's more sophisticated than simple character chunking
    and often produces better semantic chunks.
    
    Example:
        >>> chunker = RecursiveCharacterChunker(chunk_size=1000, chunk_overlap=200)
        >>> chunks = chunker.chunk("This is a long text that needs to be chunked...")
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: List[str] = None
    ) -> None:
        """
        Initialize the recursive character chunker.
        
        Args:
            chunk_size: Maximum size of each chunk in characters
            chunk_overlap: Number of characters to overlap between chunks
            separators: List of separators to try, in order of preference
        """
        super().__init__(chunk_size, chunk_overlap)
        self.separators = separators or ['\n\n', '\n', '. ', ' ', '']
    
    def chunk(self, text: str) -> List[Chunk]:
        """
        Split text using recursive character chunking.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of Chunk objects
        """
        if not text:
            return []
        
        chunks = []
        
        def _chunk_text(text: str, start_idx: int, separator_idx: int = 0) -> None:
            """Recursive function to split text."""
            if len(text) <= self.chunk_size:
                chunks.append(Chunk(
                    text=text.strip(),
                    start_index=start_idx,
                    end_index=start_idx + len(text.strip()),
                    metadata={"chunk_type": "recursive", "chunk_size": len(text.strip())}
                ))
                return
            
            # Try to split with current separator
            if separator_idx < len(self.separators):
                separator = self.separators[separator_idx]
                
                if separator:
                    parts = text.split(separator)
                else:
                    parts = [text]
                
                # If separator splits into more than 2 parts
                if len(parts) > 1:
                    current = ""
                    for part in parts:
                        if len(current) + len(part) + len(separator) <= self.chunk_size:
                            current = current + part + separator if current else part
                        else:
                            if current.strip():
                                chunks.append(Chunk(
                                    text=current.strip(),
                                    start_index=start_idx,
                                    end_index=start_idx + len(current.strip()),
                                    metadata={"chunk_type": "recursive", "chunk_size": len(current.strip())}
                                ))
                                start_idx += len(current)
                            current = part
                    
                    if current.strip():
                        _chunk_text(current, start_idx, separator_idx + 1)
                else:
                    # Try next separator
                    _chunk_text(text, start_idx, separator_idx + 1)
            else:
                # No more separators, force split at chunk_size
                while len(text) > self.chunk_size:
                    chunk_text = text[:self.chunk_size].strip()
                    chunks.append(Chunk(
                        text=chunk_text,
                        start_index=start_idx,
                        end_index=start_idx + len(chunk_text),
                        metadata={"chunk_type": "recursive", "chunk_size": len(chunk_text)}
                    ))
                    start_idx += len(chunk_text)
                    text = text[self.chunk_size:].strip()
                
                if text:
                    chunks.append(Chunk(
                        text=text.strip(),
                        start_index=start_idx,
                        end_index=start_idx + len(text.strip()),
                        metadata={"chunk_type": "recursive", "chunk_size": len(text.strip())}
                    ))
        
        _chunk_text(text, 0)
        
        # Add overlap to chunks
        if self.chunk_overlap > 0:
            for i in range(1, len(chunks)):
                overlap_text = chunks[i-1].text[-self.chunk_overlap:]
                chunks[i].text = overlap_text + " " + chunks[i].text
                chunks[i].start_index -= len(overlap_text)
        
        return chunks


def chunk_text(
    text: str,
    chunker_type: str = "sentence",
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> List[Chunk]:
    """
    Convenience function to chunk text using a specified strategy.
    
    Args:
        text: Text to chunk
        chunker_type: Type of chunker to use ("character", "word", "sentence", "paragraph", "recursive")
        chunk_size: Maximum size of each chunk
        chunk_overlap: Number of characters to overlap between chunks
        
    Returns:
        List of Chunk objects
        
    Example:
        >>> chunks = chunk_text("Long text...", chunker_type="sentence", chunk_size=500)
    """
    chunkers = {
        "character": CharacterChunker,
        "word": WordChunker,
        "sentence": SentenceChunker,
        "paragraph": ParagraphChunker,
        "recursive": RecursiveCharacterChunker,
    }
    
    chunker_class = chunkers.get(chunker_type.lower())
    if not chunker_class:
        raise ValueError(f"Unknown chunker type: {chunker_type}")
    
    chunker = chunker_class(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return chunker.chunk(text)
