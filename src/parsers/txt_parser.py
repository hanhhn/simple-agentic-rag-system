"""
Plain text document parser.
"""
from pathlib import Path
from typing import List

from src.core.logging import get_logger
from src.core.exceptions import DocumentParseError
from src.parsers.base import Parser


logger = get_logger(__name__)


class TxtParser(Parser):
    """
    Parser for plain text files.
    
    This parser handles .txt files, reading their content directly.
    It preserves the original text formatting and structure.
    
    Supported extensions: .txt, .text
    
    Example:
        >>> parser = TxtParser()
        >>> text = parser.parse("document.txt")
        >>> print(text)
    """
    
    supported_extensions = ["txt", "text"]
    
    def parse(self, filepath: Path | str) -> str:
        """
        Parse a plain text file and extract its content.
        
        Args:
            filepath: Path to the text file
            
        Returns:
            Text content of the file
            
        Raises:
            DocumentParseError: If file cannot be read or parsed
            
        Example:
            >>> parser = TxtParser()
            >>> text = parser.parse("document.txt")
        """
        path = Path(filepath)
        
        # Validate file
        self.validate_file(path)
        
        logger.info("Parsing text file", filepath=str(path))
        
        try:
            # Read file with explicit encoding handling
            # Try UTF-8 first, then fall back to latin-1 if needed
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                logger.warning("UTF-8 decoding failed, trying latin-1", filepath=str(path))
                content = path.read_text(encoding="latin-1")
            
            # Validate content
            if not content:
                logger.warning("Empty text file", filepath=str(path))
                return ""
            
            logger.info(
                "Successfully parsed text file",
                filepath=str(path),
                char_count=len(content),
                line_count=len(content.splitlines())
            )
            
            return content
            
        except Exception as e:
            logger.error("Failed to parse text file", filepath=str(path), error=str(e))
            raise DocumentParseError(
                f"Failed to parse text file: {str(e)}",
                details={"filepath": str(filepath), "error": str(e)}
            )
