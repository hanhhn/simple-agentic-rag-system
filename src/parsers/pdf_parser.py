"""
PDF document parser.
"""
from pathlib import Path
from typing import List

import PyPDF2

from src.core.logging import get_logger
from src.core.exceptions import DocumentParseError
from src.parsers.base import Parser


logger = get_logger(__name__)


class PdfParser(Parser):
    """
    Parser for PDF files.
    
    This parser handles .pdf files, extracting text content from each page.
    It attempts to preserve reading order and structure as much as possible.
    
    Supported extensions: .pdf
    
    Example:
        >>> parser = PdfParser()
        >>> text = parser.parse("document.pdf")
        >>> print(text)
    """
    
    supported_extensions = ["pdf"]
    
    def __init__(self, preserve_layout: bool = False) -> None:
        """
        Initialize PDF parser.
        
        Args:
            preserve_layout: Whether to attempt to preserve original layout
                          This may affect text quality but better preserves structure
        """
        self.preserve_layout = preserve_layout
    
    def parse(self, filepath: Path | str) -> str:
        """
        Parse a PDF file and extract its text content.
        
        Args:
            filepath: Path to PDF file
            
        Returns:
            Extracted text content from all pages
            
        Raises:
            DocumentParseError: If file cannot be read or parsed
            
        Example:
            >>> parser = PdfParser()
            >>> text = parser.parse("document.pdf")
        """
        path = Path(filepath)
        
        # Validate file
        self.validate_file(path)
        
        logger.info("Parsing PDF file", filepath=str(path))
        
        try:
            # Open PDF file
            with open(path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                # Get number of pages
                num_pages = len(reader.pages)
                logger.info("PDF file opened", filepath=str(path), page_count=num_pages)
                
                # Extract text from each page
                pages_text = []
                for page_num, page in enumerate(reader.pages, start=1):
                    try:
                        page_text = page.extract_text()
                        
                        if page_text:
                            pages_text.append(page_text)
                            logger.info(
                                "Extracted text from page",
                                filepath=str(path),
                                page=page_num,
                                char_count=len(page_text)
                            )
                        else:
                            logger.warning(
                                "No text extracted from page (possibly image-only)",
                                filepath=str(path),
                                page=page_num
                            )
                            
                    except Exception as e:
                        logger.error(
                            "Failed to extract text from page",
                            filepath=str(path),
                            page=page_num,
                            error=str(e)
                        )
                        # Continue to next page
                
                # Combine pages with separator
                if pages_text:
                    full_text = "\n\n".join(pages_text)
                    
                    # Clean up the text
                    full_text = self._clean_text(full_text)
                    
                    logger.info(
                        "Successfully parsed PDF file",
                        filepath=str(path),
                        total_pages=len(pages_text),
                        total_chars=len(full_text)
                    )
                    
                    return full_text
                else:
                    logger.warning("No text extracted from PDF (possibly image-only)", filepath=str(path))
                    return ""
                    
        except PyPDF2.PdfReadError as e:
            logger.error("Failed to read PDF (invalid or encrypted)", filepath=str(path), error=str(e))
            raise DocumentParseError(
                f"Failed to read PDF file: {str(e)}. The file may be encrypted or corrupted.",
                details={"filepath": str(filepath), "error": str(e)}
            )
        except Exception as e:
            logger.error("Failed to parse PDF file", filepath=str(path), error=str(e))
            raise DocumentParseError(
                f"Failed to parse PDF file: {str(e)}",
                details={"filepath": str(filepath), "error": str(e)}
            )
    
    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize extracted text.
        
        PDF extraction often produces artifacts like excessive whitespace,
        broken words, etc. This method cleans those up.
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text
        """
        import re
        
        # Remove excessive whitespace within lines
        text = re.sub(r' +', ' ', text)
        
        # Remove excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Fix hyphenated words at line breaks
        text = re.sub(r'-\n(\S)', r'\1', text)
        
        # Fix spaces before punctuation
        text = re.sub(r'\s+([,.!?;:])', r'\1', text)
        
        # Normalize quotes
        text = text.replace('"', '"')
        text = text.replace('"', '"')
        text = text.replace(''', "'")
        text = text.replace(''', "'")
        
        return text.strip()
    
    def get_page_count(self, filepath: Path | str) -> int:
        """
        Get the number of pages in a PDF file.
        
        Args:
            filepath: Path to PDF file
            
        Returns:
            Number of pages
            
        Raises:
            DocumentParseError: If file cannot be read
        """
        path = Path(filepath)
        
        try:
            with open(path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                return len(reader.pages)
        except Exception as e:
            logger.error("Failed to get page count", filepath=str(path), error=str(e))
            raise DocumentParseError(
                f"Failed to read PDF file: {str(e)}",
                details={"filepath": str(filepath), "error": str(e)}
            )
    
    def extract_page(self, filepath: Path | str, page_num: int) -> str:
        """
        Extract text from a specific page of a PDF.
        
        Args:
            filepath: Path to PDF file
            page_num: Page number (1-indexed)
            
        Returns:
            Text from the specified page
            
        Raises:
            DocumentParseError: If page cannot be extracted
        """
        path = Path(filepath)
        
        try:
            with open(path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                if page_num < 1 or page_num > len(reader.pages):
                    raise ValueError(f"Page number {page_num} is out of range (1-{len(reader.pages)})")
                
                page = reader.pages[page_num - 1]
                text = page.extract_text()
                
                return self._clean_text(text)
                
        except Exception as e:
            logger.error("Failed to extract page", filepath=str(path), page=page_num, error=str(e))
            raise DocumentParseError(
                f"Failed to extract page {page_num}: {str(e)}",
                details={"filepath": str(filepath), "page": page_num, "error": str(e)}
            )
