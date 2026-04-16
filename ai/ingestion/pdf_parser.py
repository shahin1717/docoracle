from pathlib import Path
import fitz  # PyMuPDF

from .base_parser import BaseParser, ParsedDocument

SUPPORTED_EXTENSIONS = {".pdf"}


class PDFParser(BaseParser):
    """
    Parses PDF files using PyMuPDF (fitz).

    Why PyMuPDF over pdfplumber or PyPDF2?
    - Fastest of the three
    - Handles scanned PDFs with embedded text layers
    - Extracts page-level metadata (rotation, dimensions)
    - get_text("blocks") gives us positional text blocks, useful later
      for table detection and layout-aware chunking
    """

    def supports(self, file_path: str | Path) -> bool:
        return Path(file_path).suffix.lower() in SUPPORTED_EXTENSIONS

    def parse(self, file_path: str | Path) -> ParsedDocument:
        path = self._validate_file(file_path)

        if not self.supports(path):
            raise ValueError(f"PDFParser does not support: {path.suffix}")

        doc = fitz.open(str(path))
        pages = []
        all_text_parts = []

        for page_num, page in enumerate(doc, start=1):
            # get_text("text") gives clean plain text, preserving reading order.
            # Alternative: get_text("blocks") for layout-aware extraction — useful
            # for two-column PDFs or documents with complex layouts.
            text = page.get_text("text").strip()

            if not text:
                # Page may be image-only (scanned). Flag it for future OCR.
                text = f"[Page {page_num}: image-only, no text layer]"

            pages.append({
                "page_num": page_num,
                "text": text,
                "metadata": {
                    "width": page.rect.width,
                    "height": page.rect.height,
                    "rotation": page.rotation,
                }
            })
            all_text_parts.append(text)

        full_text = "\n\n".join(all_text_parts)

        # Extract document-level metadata from PDF properties
        raw_meta = doc.metadata or {}
        metadata = {
            "author": raw_meta.get("author", ""),
            "creation_date": raw_meta.get("creationDate", ""),
            "subject": raw_meta.get("subject", ""),
            "page_count": doc.page_count,
            "file_size_bytes": path.stat().st_size,
        }

        doc.close()

        # Use the PDF's Title metadata if present, fall back to filename
        title = raw_meta.get("title") or path.stem

        return ParsedDocument(
            source_path=str(path),
            file_type="pdf",
            title=title,
            full_text=full_text,
            pages=pages,
            metadata=metadata,
        )