"""
Base parser interface for document parsers.

This module defines the abstract base class that all document parsers
must implement, ensuring a consistent interface for different file formats.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional


class Parser(ABC):
    """
    Abstract base class for document parsers.
    
    All document parsers should inherit from this class and implement
    the parse method. This ensures a consistent interface across all
    supported file formats.
    
    Attributes:
        supported_extensions: List of file extensions this parser supports
    """
    
    supported_extensions: List[str] = []
    
    @abstractmethod
    def parse(self, filepath: Path | str) -> str:
        """
        Parse a document file and extract text content.
        
        Args:
            filepath: Path to the document file
            
        Returns:
            Extracted text content as a string
            
        Raises:
            DocumentParseError: If parsing fails
            
        Example:
            >>> parser = TxtParser()
            >>> text = parser.parse("document.txt")
            >>> print(text)
        """
        pass
    
    def supports(self, filepath: Path | str) -> bool:
        """
        Check if this parser supports the given file.
        
        Args:
            filepath: Path to the file to check
            
        Returns:
            True if the parser supports this file type, False otherwise
            
        Example:
            >>> parser = TxtParser()
            >>> if parser.supports("document.txt"):
            ...     text = parser.parse("document.txt")
        """
        path = Path(filepath)
        ext = path.suffix.lstrip('.').lower()
        return ext in [e.lstrip('.').lower() for e in self.supported_extensions]
    
    def validate_file(self, filepath: Path | str) -> None:
        """
        Validate that the file exists and is readable.
        
        Args:
            filepath: Path to the file to validate
            
        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If file is not readable
            
        Example:
            >>> parser = TxtParser()
            >>> parser.validate_file("document.txt")
        """
        path = Path(filepath)
        
        if not path.exists():
            from src.core.exceptions import FileNotFoundError as CoreFileNotFoundError
            raise CoreFileNotFoundError(
                f"File not found: {filepath}",
                details={"filepath": str(filepath)}
            )
        
        if not path.is_file():
            from src.core.exceptions import FileStorageError
            raise FileStorageError(
                f"Path is not a file: {filepath}",
                details={"filepath": str(filepath)}
            )
        
        if not path.is_file() or not path.exists():
            from src.core.exceptions import FileStorageError
            raise FileStorageError(
                f"Cannot read file: {filepath}",
                details={"filepath": str(filepath)}
            )


class TextExtractor(ABC):
    """
    Abstract base class for text extractors.
    
    This is an alternative interface for parsers that may need to extract
    structured information from documents, not just raw text.
    """
    
    @abstractmethod
    def extract_text(self, filepath: Path | str) -> str:
        """
        Extract raw text from a document.
        
        Args:
            filepath: Path to the document file
            
        Returns:
            Extracted text content
        """
        pass
    
    @abstractmethod
    def extract_metadata(self, filepath: Path | str) -> dict:
        """
        Extract metadata from a document.
        
        Args:
            filepath: Path to the document file
            
        Returns:
            Dictionary of metadata (e.g., title, author, creation date)
        """
        pass


class ParserFactory:
    """
    Factory class for creating appropriate parsers for different file types.
    
    This factory manages the mapping between file extensions and parser
    implementations, making it easy to add new parsers.
    
    Attributes:
        _parsers: Dictionary mapping file extensions to parser classes
        
    Example:
        >>> factory = ParserFactory()
        >>> factory.register_parser(TxtParser)
        >>> parser = factory.get_parser("document.txt")
        >>> text = parser.parse("document.txt")
    """
    
    def __init__(self) -> None:
        """Initialize the parser factory."""
        self._parsers: dict[str, type[Parser]] = {}
    
    def register_parser(self, parser_class: type[Parser]) -> None:
        """
        Register a parser class for its supported file extensions.
        
        Args:
            parser_class: Parser class to register
            
        Example:
            >>> factory = ParserFactory()
            >>> factory.register_parser(TxtParser)
        """
        for ext in parser_class.supported_extensions:
            ext_clean = ext.lstrip('.').lower()
            self._parsers[ext_clean] = parser_class
    
    def get_parser(self, filepath: Path | str) -> Parser:
        """
        Get the appropriate parser for a given file.
        
        Args:
            filepath: Path to the file
            
        Returns:
            Parser instance for this file type
            
        Raises:
            UnsupportedParserError: If no parser is available for this file type
            
        Example:
            >>> factory = ParserFactory()
            >>> parser = factory.get_parser("document.pdf")
        """
        path = Path(filepath)
        ext = path.suffix.lstrip('.').lower()
        
        if ext not in self._parsers:
            from src.core.exceptions import UnsupportedParserError
            raise UnsupportedParserError(
                f"No parser available for file extension: .{ext}",
                details={"extension": ext, "supported": list(self._parsers.keys())}
            )
        
        parser_class = self._parsers[ext]
        return parser_class()
    
    def get_supported_extensions(self) -> List[str]:
        """
        Get list of all supported file extensions.
        
        Returns:
            List of supported file extensions
            
        Example:
            >>> factory = ParserFactory()
            >>> extensions = factory.get_supported_extensions()
            >>> print(extensions)  # ["txt", "pdf", "docx", "md"]
        """
        return list(self._parsers.keys())


# Global parser factory instance
_parser_factory = ParserFactory()


def get_parser_factory() -> ParserFactory:
    """
    Get the global parser factory instance.
    
    Returns:
        Global ParserFactory instance
        
    Example:
        >>> factory = get_parser_factory()
        >>> parser = factory.get_parser("document.txt")
    """
    return _parser_factory


def parse_document(filepath: Path | str) -> str:
    """
    Convenience function to parse a document using the appropriate parser.
    
    Args:
        filepath: Path to the document file
        
    Returns:
        Extracted text content
        
    Raises:
        UnsupportedParserError: If no parser is available
        DocumentParseError: If parsing fails
        
    Example:
        >>> text = parse_document("document.pdf")
        >>> print(text)
    """
    factory = get_parser_factory()
    parser = factory.get_parser(filepath)
    return parser.parse(filepath)
