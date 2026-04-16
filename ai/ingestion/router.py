from pathlib import Path

from .base_parser import BaseParser, ParsedDocument
from .pdf_parser import PDFParser
from .docx_parser import DOCXParser
from .pptx_parser import PPTXParser
from .md_parser import MarkdownParser


# Registry of all available parsers, in priority order.
# The router tries each parser until one returns supports=True.
_PARSERS: list[BaseParser] = [
    PDFParser(),
    DOCXParser(),
    PPTXParser(),
    MarkdownParser(),
]


def parse_document(file_path: str | Path) -> ParsedDocument:
    """
    Main entry point for the ingestion layer.

    The pipeline always calls this — it never imports individual parsers.
    This keeps the rest of the codebase decoupled from which parser is used.

    Usage:
        doc = parse_document("research_paper.pdf")
        print(doc.full_text[:500])
        print(doc.page_count)

    Raises:
        FileNotFoundError: if the file doesn't exist
        ValueError: if no parser supports the file type
    """
    path = Path(file_path)

    for parser in _PARSERS:
        if parser.supports(path):
            return parser.parse(path)

    supported = [".pdf", ".docx", ".pptx", ".md", ".markdown", ".txt"]
    raise ValueError(
        f"No parser available for '{path.suffix}' files. "
        f"Supported: {', '.join(supported)}"
    )


def get_supported_extensions() -> list[str]:
    """Return all extensions the ingestion layer can handle."""
    extensions = []
    for parser in _PARSERS:
        # Peek at each parser's supported extensions
        for ext in [".pdf", ".docx", ".pptx", ".md", ".markdown", ".txt"]:
            if parser.supports(Path(f"test{ext}")):
                extensions.append(ext)
    return extensions