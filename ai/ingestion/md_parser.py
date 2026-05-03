import re
from pathlib import Path

from .base_parser import BaseParser, ParsedDocument

SUPPORTED_EXTENSIONS = {".md", ".markdown", ".txt"}


class MarkdownParser(BaseParser):
    """
    Parses Markdown and plain text files.

    No external dependencies — pure Python.
    Splits the document into logical sections by heading (## / ###).
    Each heading + its following paragraphs becomes one "page".

    Plain .txt files are treated as one big section with no headings.
    """

    def supports(self, file_path: str | Path) -> bool:
        return Path(file_path).suffix.lower() in SUPPORTED_EXTENSIONS

    def parse(self, file_path: str | Path) -> ParsedDocument:
        path = self._validate_file(file_path)

        if not self.supports(path):
            raise ValueError(f"MarkdownParser does not support: {path.suffix}")

        raw = path.read_text(encoding="utf-8", errors="replace")
        full_text = self._strip_markdown(raw)
        sections = self._split_into_sections(raw)

        metadata = {
            "file_size_bytes": path.stat().st_size,
            "encoding": "utf-8",
            "section_count": len(sections),
            "has_headings": any(s["metadata"].get("heading") for s in sections),
        }

        # Use the first H1 as the title if present
        title = self._extract_title(raw) or path.stem

        return ParsedDocument(
            source_path=str(path),
            file_type="md" if path.suffix.lower() in {".md", ".markdown"} else "txt",
            title=title,
            full_text=full_text,
            pages=sections,
            metadata=metadata,
        )

    def _split_into_sections(self, raw: str) -> list[dict]:
        """
        Split markdown into sections at each heading.
        Each section = heading + all text until the next heading.
        """
        # Match heading lines: # Heading, ## Heading, etc.
        heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

        sections = []
        matches = list(heading_pattern.finditer(raw))

        if not matches:
            # No headings — treat whole doc as one section
            text = self._strip_markdown(raw).strip()
            if text:
                sections.append({
                    "page_num": 1,
                    "text": text,
                    "metadata": {"heading": None, "heading_level": 0, "type": "body"},
                })
            return sections

        # Text before the first heading
        preamble = raw[:matches[0].start()].strip()
        if preamble:
            sections.append({
                "page_num": 1,
                "text": self._strip_markdown(preamble),
                "metadata": {"heading": None, "heading_level": 0, "type": "preamble"},
            })

        for i, match in enumerate(matches):
            level = len(match.group(1))  # number of # characters
            heading = match.group(2).strip()

            # Body text is everything from this heading until the next one
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
            body_raw = raw[start:end].strip()
            body_text = self._strip_markdown(body_raw)

            combined = f"{heading}\n{body_text}".strip()

            sections.append({
                "page_num": len(sections) + 1,
                "text": combined,
                "metadata": {
                    "heading": heading,
                    "heading_level": level,
                    "type": "section",
                },
            })

        return sections

    def _strip_markdown(self, text: str) -> str:
        """
        Remove markdown syntax, leaving clean readable text.
        Handles: headings, bold/italic, links, images, code blocks, blockquotes.
        """
        # Fenced code blocks — keep the code, strip the fences
        text = re.sub(r"```[a-z]*\n(.*?)```", r"\1", text, flags=re.DOTALL)
        text = re.sub(r"`([^`]+)`", r"\1", text)

        # Headings → plain text (strip the # symbols)
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)

        # Bold and italic
        text = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", text)
        text = re.sub(r"_{1,3}(.+?)_{1,3}", r"\1", text)

        # Links: [text](url) → text
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

        # Images: ![alt](url) → alt
        text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)

        # Blockquotes
        text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)

        # Horizontal rules
        text = re.sub(r"^(-{3,}|={3,}|\*{3,})$", "", text, flags=re.MULTILINE)

        # HTML tags (occasionally in markdown)
        text = re.sub(r"<[^>]+>", "", text)

        # Collapse multiple blank lines to one
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    def _extract_title(self, raw: str) -> str:
        """Find the first H1 heading in the document."""
        match = re.search(r"^#\s+(.+)$", raw, re.MULTILINE)
        return match.group(1).strip() if match else ""