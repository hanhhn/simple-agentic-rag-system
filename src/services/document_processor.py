"""
Document processing service.
"""
import time
from pathlib import Path
from typing import List, Dict, Optional

from src.core.logging import get_logger
from src.core.exceptions import DocumentProcessingError
from src.core.config import get_config
from src.parsers.base import get_parser_factory
from src.utils.text_chunker import Chunk, chunk_text

# Import parsers to ensure they are registered
import src.parsers  # noqa: F401


logger = get_logger(__name__)


class DocumentProcessor:
    """
    Service for processing documents.
    
    This class handles document parsing, text extraction,
    chunking, and preparation for embedding.
    
    Example:
        >>> processor = DocumentProcessor()
        >>> chunks = processor.process_document("document.txt", "my_collection")
    """
    
    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        chunker_type: str = "sentence"
    ) -> None:
        """
        Initialize document processor.
        
        Args:
            chunk_size: Chunk size in characters
            chunk_overlap: Chunk overlap in characters
            chunker_type: Type of chunker to use
        """
        config = get_config()
        
        self.chunk_size = chunk_size or config.document.chunk_size
        self.chunk_overlap = chunk_overlap or config.document.chunk_overlap
        self.chunker_type = chunker_type
        
        self.parser_factory = get_parser_factory()
        
        logger.info(
            "Document processor initialized",
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            chunker_type=chunker_type
        )
    
    def parse_document(self, filepath: Path | str) -> str:
        """
        Parse a document and extract its text.
        
        Args:
            filepath: Path to the document file
            
        Returns:
            Extracted text content
            
        Raises:
            DocumentProcessingError: If parsing fails
            
        Example:
            >>> processor = DocumentProcessor()
            >>> text = processor.parse_document("document.pdf")
        """
        start_time = time.time()
        filepath_obj = Path(filepath)
        
        try:
            file_size = filepath_obj.stat().st_size if filepath_obj.exists() else 0
            file_ext = filepath_obj.suffix.lower()
            
            logger.info(
                "Starting document parsing",
                filepath=str(filepath),
                file_size_bytes=file_size,
                file_size_mb=f"{file_size / (1024 * 1024):.2f}",
                file_extension=file_ext
            )
            
            # Get appropriate parser
            parser_start = time.time()
            parser = self.parser_factory.get_parser(filepath)
            parser_get_elapsed = time.time() - parser_start
            logger.info("Parser selected", parser_type=type(parser).__name__, elapsed=f"{parser_get_elapsed:.6f}s")
            
            # Parse document
            parse_start = time.time()
            text = parser.parse(filepath)
            parse_elapsed = time.time() - parse_start
            
            if not text:
                elapsed = time.time() - start_time
                logger.warning(
                    "Document contains no text content",
                    filepath=str(filepath),
                    elapsed_time=f"{elapsed:.4f}s"
                )
                raise DocumentProcessingError(
                    "Document contains no text content",
                    details={"filepath": str(filepath)}
                )
            
            total_elapsed = time.time() - start_time
            
            logger.info(
                "Document parsed successfully",
                filepath=str(filepath),
                text_length=len(text),
                parse_time=f"{parse_elapsed:.4f}s",
                total_time=f"{total_elapsed:.4f}s",
                chars_per_second=f"{len(text) / parse_elapsed:.0f}" if parse_elapsed > 0 else "0"
            )
            
            return text
            
        except DocumentProcessingError:
            elapsed = time.time() - start_time
            logger.error(
                "Document parsing failed (DocumentProcessingError)",
                filepath=str(filepath),
                elapsed_time=f"{elapsed:.4f}s"
            )
            raise
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(
                "Failed to parse document",
                filepath=str(filepath),
                error=str(e),
                error_type=type(e).__name__,
                elapsed_time=f"{elapsed:.4f}s"
            )
            raise DocumentProcessingError(
                f"Failed to parse document: {str(e)}",
                details={
                    "filepath": str(filepath),
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "elapsed_time": f"{elapsed:.4f}s"
                }
            )
    
    def chunk_document(
        self,
        text: str,
        metadata: Optional[Dict] = None
    ) -> List[Chunk]:
        """
        Chunk document text into manageable pieces.
        
        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to chunks
            
        Returns:
            List of text chunks
            
        Example:
            >>> processor = DocumentProcessor()
            >>> chunks = processor.chunk_document(document_text)
        """
        start_time = time.time()
        
        try:
            logger.info(
                "Starting document chunking",
                text_length=len(text),
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                chunker_type=self.chunker_type
            )
            
            # Chunk text
            chunk_start = time.time()
            chunks = chunk_text(
                text,
                chunker_type=self.chunker_type,
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
            chunk_elapsed = time.time() - chunk_start
            
            # Add metadata to chunks
            metadata_start = time.time()
            if metadata:
                for chunk in chunks:
                    chunk.metadata.update(metadata)
            metadata_elapsed = time.time() - metadata_start
            
            total_elapsed = time.time() - start_time
            
            avg_chunk_size = sum(len(c.text) for c in chunks) // len(chunks) if chunks else 0
            min_chunk_size = min((len(c.text) for c in chunks), default=0)
            max_chunk_size = max((len(c.text) for c in chunks), default=0)
            
            logger.info(
                "Document chunked successfully",
                chunk_count=len(chunks),
                avg_chunk_size=avg_chunk_size,
                min_chunk_size=min_chunk_size,
                max_chunk_size=max_chunk_size,
                chunk_time=f"{chunk_elapsed:.4f}s",
                metadata_time=f"{metadata_elapsed:.6f}s",
                total_time=f"{total_elapsed:.4f}s",
                chunks_per_second=f"{len(chunks) / chunk_elapsed:.2f}" if chunk_elapsed > 0 else "0"
            )
            
            return chunks
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(
                "Failed to chunk document",
                error=str(e),
                error_type=type(e).__name__,
                text_length=len(text),
                elapsed_time=f"{elapsed:.4f}s"
            )
            raise DocumentProcessingError(
                f"Failed to chunk document: {str(e)}",
                details={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "elapsed_time": f"{elapsed:.4f}s"
                }
            )
    
    def process_document(
        self,
        filepath: Path | str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, any]:
        """
        Process a document end-to-end (parse and chunk).
        
        Args:
            filepath: Path to the document file
            metadata: Optional metadata to attach
            
        Returns:
            Dictionary with processing results
            
        Example:
            >>> processor = DocumentProcessor()
            >>> result = processor.process_document("document.pdf")
            >>> print(result["chunks"])  # List of chunks
        """
        start_time = time.time()
        
        try:
            logger.info(
                "Starting end-to-end document processing",
                filepath=str(filepath),
                has_metadata=metadata is not None
            )
            
            # Parse document
            parse_start = time.time()
            text = self.parse_document(filepath)
            parse_elapsed = time.time() - parse_start
            
            # Chunk document
            chunk_start = time.time()
            chunks = self.chunk_document(text, metadata)
            chunk_elapsed = time.time() - chunk_start
            
            # Prepare result
            result = {
                "filepath": str(filepath),
                "text": text,
                "chunks": chunks,
                "chunk_count": len(chunks),
                "total_length": len(text),
                "metadata": metadata or {}
            }
            
            total_elapsed = time.time() - start_time
            
            logger.info(
                "Document processed successfully",
                filepath=str(filepath),
                chunk_count=len(chunks),
                text_length=len(text),
                parse_time=f"{parse_elapsed:.4f}s",
                chunk_time=f"{chunk_elapsed:.4f}s",
                total_time=f"{total_elapsed:.4f}s",
                processing_rate=f"{len(text) / total_elapsed:.0f} chars/s" if total_elapsed > 0 else "0"
            )
            
            return result
            
        except DocumentProcessingError:
            elapsed = time.time() - start_time
            logger.error(
                "Document processing failed (DocumentProcessingError)",
                filepath=str(filepath),
                elapsed_time=f"{elapsed:.4f}s"
            )
            raise
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(
                "Failed to process document",
                filepath=str(filepath),
                error=str(e),
                error_type=type(e).__name__,
                elapsed_time=f"{elapsed:.4f}s"
            )
            raise DocumentProcessingError(
                f"Failed to process document: {str(e)}",
                details={
                    "filepath": str(filepath),
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "elapsed_time": f"{elapsed:.4f}s"
                }
            )
    
    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported document formats.
        
        Returns:
            List of file extensions
        """
        return self.parser_factory.get_supported_extensions()
