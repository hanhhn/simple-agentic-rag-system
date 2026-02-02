"""
Markdown document parser.
"""
import re
from pathlib import Path
from typing import List

import markdown
from markdown.extensions.tables import TableExtension
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.codehilite import CodeHiliteExtension

from src.core.logging import get_logger
from src.core.exceptions import DocumentParseError
from src.parsers.base import Parser


logger = get_logger(__name__)


class MdParser(Parser):
    """
    Parser for Markdown files.
    
    This parser handles .md and .markdown files, converting them to plain text
    while preserving the structure and content. It can optionally convert markdown
    to HTML and extract clean text.
    
    Supported extensions: .md, .markdown
    
    Example:
        >>> parser = MdParser()
        >>> text = parser.parse("README.md")
        >>> print(text)
    """
    
    supported_extensions = ["md", "markdown"]
    
    def __init__(self, convert_to_plain: bool = True) -> None:
        """
        Initialize the Markdown parser.
        
        Args:
            convert_to_plain: Whether to convert markdown to plain text (default: True)
                            If False, returns raw markdown content
        """
        self.convert_to_plain = convert_to_plain
        
        # Set up markdown extensions
        self.extensions = [
            TableExtension(),
            FencedCodeExtension(),
            CodeHiliteExtension(linenums=False, guess_lang=False),
            "markdown.extensions.meta",
            "markdown.extensions.nl2br",
            "markdown.extensions.sane_lists",
        ]
    
    def parse(self, filepath: Path | str) -> str:
        """
        Parse a Markdown file and extract its content.
        
        Args:
            filepath: Path to the markdown file
            
        Returns:
            Text content (plain text or markdown depending on initialization)
            
        Raises:
            DocumentParseError: If file cannot be read or parsed
            
        Example:
            >>> parser = MdParser()
            >>> text = parser.parse("README.md")
        """
        path = Path(filepath)
        
        # Validate file
        self.validate_file(path)
        
        logger.info("Parsing markdown file", filepath=str(path))
        
        try:
            # Read file
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                logger.warning("UTF-8 decoding failed, trying latin-1", filepath=str(path))
                content = path.read_text(encoding="latin-1")
            
            if not content:
                logger.warning("Empty markdown file", filepath=str(path))
                return ""
            
            if self.convert_to_plain:
                # Convert markdown to HTML then extract text
                html = markdown.markdown(content, extensions=self.extensions)
                text = self._html_to_plain_text(html)
            else:
                # Return raw markdown
                text = content
            
            logger.info(
                "Successfully parsed markdown file",
                filepath=str(path),
                char_count=len(text),
                converted=self.convert_to_plain
            )
            
            return text
            
        except Exception as e:
            logger.error("Failed to parse markdown file", filepath=str(path), error=str(e))
            raise DocumentParseError(
                f"Failed to parse markdown file: {str(e)}",
                details={"filepath": str(filepath), "error": str(e)}
            )
    
    def _html_to_plain_text(self, html: str) -> str:
        """
        Convert HTML to plain text.
        
        This method extracts text content from HTML, removing tags and
        normalizing whitespace.
        
        Args:
            html: HTML string to convert
            
        Returns:
            Plain text representation
        """
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', html)
        
        # Replace HTML entities
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&apos;', "'")
        text = text.replace('&nbsp;', ' ')
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def extract_metadata(self, filepath: Path | str) -> dict:
        """
        Extract metadata from Markdown frontmatter.
        
        This method extracts YAML frontmatter from markdown files,
        which is commonly used for metadata like title, author, etc.
        
        Args:
            filepath: Path to the markdown file
            
        Returns:
            Dictionary of metadata
        """
        path = Path(filepath)
        
        try:
            content = path.read_text(encoding="utf-8")
            
            # Check for YAML frontmatter
            if content.startswith("---"):
                end = content.find("\n---", 3)
                if end > 0:
                    # Extract frontmatter
                    frontmatter = content[3:end].strip()
                    
                    # Simple parsing (for full YAML parsing, install PyYAML)
                    metadata = self._parse_simple_frontmatter(frontmatter)
                    return metadata
            
            return {}
            
        except Exception as e:
            logger.warning("Failed to extract metadata from markdown", filepath=str(path), error=str(e))
            return {}
    
    def _parse_simple_frontmatter(self, frontmatter: str) -> dict:
        """
        Simple frontmatter parser (handles key: value format).
        
        For complex YAML, you would use the PyYAML library.
        
        Args:
            frontmatter: Frontmatter content string
            
        Returns:
            Dictionary of metadata
        """
        metadata = {}
        
        for line in frontmatter.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                metadata[key.strip()] = value.strip()
        
        return metadata
