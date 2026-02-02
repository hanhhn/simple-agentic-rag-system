"""
Text cleaning utilities for preprocessing text before embedding and chunking.

This module provides various text cleaning functions to normalize and clean text,
improving the quality of embeddings and search results.
"""
import re
from typing import Pattern
import unicodedata


class TextCleaner:
    """
    Text cleaning utility class for normalizing and cleaning text.
    
    This class provides various methods to clean and normalize text before
    processing, including removing whitespace, normalizing characters, and
    handling special characters.
    
    Attributes:
        preserve_case: Whether to preserve original case (default: False)
        preserve_newlines: Whether to preserve newlines (default: False)
        
    Example:
        >>> cleaner = TextCleaner()
        >>> clean_text = cleaner.clean("  Hello   World!  ")
        >>> print(clean_text)  # "hello world!"
    """
    
    def __init__(
        self,
        preserve_case: bool = False,
        preserve_newlines: bool = False,
        remove_urls: bool = True,
        remove_emails: bool = True,
        remove_numbers: bool = False
    ) -> None:
        """
        Initialize the text cleaner.
        
        Args:
            preserve_case: Whether to preserve original case
            preserve_newlines: Whether to preserve newlines
            remove_urls: Whether to remove URLs from text
            remove_emails: Whether to remove email addresses
            remove_numbers: Whether to remove numbers
        """
        self.preserve_case = preserve_case
        self.preserve_newlines = preserve_newlines
        self.remove_urls = remove_urls
        self.remove_emails = remove_emails
        self.remove_numbers = remove_numbers
        
        # Compile regex patterns for efficiency
        self.url_pattern: Pattern[str] = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        self.email_pattern: Pattern[str] = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        )
        self.number_pattern: Pattern[str] = re.compile(r'\b\d+\b')
        self.extra_whitespace_pattern: Pattern[str] = re.compile(r'\s+')
        self.punctuation_pattern: Pattern[str] = re.compile(r'[^\w\s]')
    
    def clean(self, text: str) -> str:
        """
        Clean text using all configured cleaning methods.
        
        This is the main method that applies all cleaning operations in sequence.
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text string
            
        Example:
            >>> cleaner = TextCleaner()
            >>> clean_text = cleaner.clean("  Hello   World!  ")
        """
        if not text:
            return ""
        
        # Normalize Unicode characters
        text = self.normalize_unicode(text)
        
        # Remove URLs if configured
        if self.remove_urls:
            text = self.remove_urls_from_text(text)
        
        # Remove emails if configured
        if self.remove_emails:
            text = self.remove_emails_from_text(text)
        
        # Remove numbers if configured
        if self.remove_numbers:
            text = self.remove_numbers_from_text(text)
        
        # Remove extra whitespace
        text = self.remove_extra_whitespace(text)
        
        # Normalize case
        if not self.preserve_case:
            text = text.lower()
        
        return text.strip()
    
    def normalize_unicode(self, text: str) -> str:
        """
        Normalize Unicode characters to their canonical form.
        
        Args:
            text: Text to normalize
            
        Returns:
            Normalized text
            
        Example:
            >>> cleaner = TextCleaner()
            >>> normalized = cleaner.normalize_unicode("café")
            >>> print(normalized)  # "cafe" (or "café" depending on normalization)
        """
        return unicodedata.normalize("NFKC", text)
    
    def remove_urls_from_text(self, text: str) -> str:
        """
        Remove URLs from text.
        
        Args:
            text: Text to process
            
        Returns:
            Text with URLs removed
            
        Example:
            >>> cleaner = TextCleaner()
            >>> text = cleaner.remove_urls_from_text("Visit http://example.com for more info")
            >>> print(text)  # "Visit  for more info"
        """
        return self.url_pattern.sub(' ', text)
    
    def remove_emails_from_text(self, text: str) -> str:
        """
        Remove email addresses from text.
        
        Args:
            text: Text to process
            
        Returns:
            Text with email addresses removed
        """
        return self.email_pattern.sub(' ', text)
    
    def remove_numbers_from_text(self, text: str) -> str:
        """
        Remove standalone numbers from text.
        
        Args:
            text: Text to process
            
        Returns:
            Text with numbers removed
        """
        return self.number_pattern.sub(' ', text)
    
    def remove_extra_whitespace(self, text: str) -> str:
        """
        Remove extra whitespace from text.
        
        This replaces multiple consecutive whitespace characters with a single space.
        
        Args:
            text: Text to process
            
        Returns:
            Text with normalized whitespace
            
        Example:
            >>> cleaner = TextCleaner()
            >>> text = cleaner.remove_extra_whitespace("Hello    World")
            >>> print(text)  # "Hello World"
        """
        if self.preserve_newlines:
            # Replace multiple spaces/tabs but preserve newlines
            text = re.sub(r'[ \t]+', ' ', text)
        else:
            text = self.extra_whitespace_pattern.sub(' ', text)
        
        return text.strip()
    
    def remove_special_chars(self, text: str, keep_punctuation: bool = True) -> str:
        """
        Remove special characters from text.
        
        Args:
            text: Text to process
            keep_punctuation: Whether to keep common punctuation marks
            
        Returns:
            Text with special characters removed
            
        Example:
            >>> cleaner = TextCleaner()
            >>> text = cleaner.remove_special_chars("Hello, @World!")
            >>> print(text)  # "Hello World" (if keep_punctuation=True)
        """
        if keep_punctuation:
            # Keep common punctuation
            keep_chars = r'.,!?;:'
            pattern = rf'[^\w\s{keep_chars}]'
            return re.sub(pattern, ' ', text)
        else:
            # Remove all non-alphanumeric characters
            return re.sub(r'[^\w\s]', ' ', text)
    
    def remove_html_tags(self, text: str) -> str:
        """
        Remove HTML tags from text.
        
        Args:
            text: Text potentially containing HTML
            
        Returns:
            Text with HTML tags removed
            
        Example:
            >>> cleaner = TextCleaner()
            >>> text = cleaner.remove_html_tags("<p>Hello <b>World</b></p>")
            >>> print(text)  # "Hello World"
        """
        html_pattern = re.compile(r'<[^>]+>')
        return html_pattern.sub(' ', text)
    
    def truncate_text(self, text: str, max_length: int, add_ellipsis: bool = True) -> str:
        """
        Truncate text to a maximum length.
        
        Args:
            text: Text to truncate
            max_length: Maximum length in characters
            add_ellipsis: Whether to add ellipsis (...) when truncating
            
        Returns:
            Truncated text
            
        Example:
            >>> cleaner = TextCleaner()
            >>> text = cleaner.truncate_text("This is a long text", 10)
            >>> print(text)  # "This is..."
        """
        if len(text) <= max_length:
            return text
        
        truncated = text[:max_length].strip()
        if add_ellipsis:
            truncated += "..."
        
        return truncated


def clean_text(
    text: str,
    preserve_case: bool = False,
    preserve_newlines: bool = False,
    remove_urls: bool = True,
    remove_emails: bool = True,
    remove_numbers: bool = False,
    remove_html: bool = True,
    max_length: int | None = None
) -> str:
    """
    Convenience function to clean text with common defaults.
    
    Args:
        text: Text to clean
        preserve_case: Whether to preserve original case
        preserve_newlines: Whether to preserve newlines
        remove_urls: Whether to remove URLs
        remove_emails: Whether to remove emails
        remove_numbers: Whether to remove numbers
        remove_html: Whether to remove HTML tags
        max_length: Optional maximum length to truncate to
        
    Returns:
        Cleaned text string
        
    Example:
        >>> clean_text("  Hello <b>World</b>!  ", remove_html=True)
        >>> # "hello world!"
    """
    if not text:
        return ""
    
    cleaner = TextCleaner(
        preserve_case=preserve_case,
        preserve_newlines=preserve_newlines,
        remove_urls=remove_urls,
        remove_emails=remove_emails,
        remove_numbers=remove_numbers
    )
    
    result = cleaner.clean(text)
    
    if remove_html:
        result = cleaner.remove_html_tags(result)
    
    if max_length:
        result = cleaner.truncate_text(result, max_length)
    
    return result


def normalize_text(text: str) -> str:
    """
    Normalize text for better embedding and search.
    
    This function applies a standard set of normalization operations suitable
    for text that will be embedded and used in semantic search.
    
    Args:
        text: Text to normalize
        
    Returns:
        Normalized text
        
    Example:
        >>> normalized = normalize_text("  HELLO   World!  ")
        >>> print(normalized)  # "hello world!"
    """
    return clean_text(
        text,
        preserve_case=False,
        preserve_newlines=False,
        remove_urls=True,
        remove_emails=True,
        remove_numbers=False,
        remove_html=True
    )
