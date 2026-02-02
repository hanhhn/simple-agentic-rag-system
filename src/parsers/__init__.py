"""
Document parsers for the RAG system.
"""
from src.parsers.base import get_parser_factory
from src.parsers.pdf_parser import PdfParser
from src.parsers.txt_parser import TxtParser
from src.parsers.docx_parser import DocxParser
from src.parsers.md_parser import MdParser

# Register all parsers with the factory
_parser_factory = get_parser_factory()
_parser_factory.register_parser(PdfParser)
_parser_factory.register_parser(TxtParser)
_parser_factory.register_parser(DocxParser)
_parser_factory.register_parser(MdParser)

__all__ = [
    "PdfParser",
    "TxtParser",
    "DocxParser",
    "MdParser",
    "get_parser_factory",
]
