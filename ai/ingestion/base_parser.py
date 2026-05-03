from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ParsedDocument:
    """
    The output of any parser.
    Every parser returns this — the rest of the pipeline only ever sees this type.
    """
    source_path: str          # original file path
    file_type: str            # "pdf", "docx", "pptx", "md"
    title: str                # filename or extracted title
    full_text: str            # complete plain text, all pages/slides joined
    pages: list[dict]         # list of {page_num, text, metadata}
    metadata: dict = field(default_factory=dict)  # author, word count, etc.

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def word_count(self) -> int:
        return len(self.full_text.split())


class BaseParser(ABC):
    """
    All parsers implement this interface.
    The pipeline calls parse() — it doesn't care which parser is underneath.
    """

    @abstractmethod
    def parse(self, file_path: str | Path) -> ParsedDocument:
        """Read a file and return a ParsedDocument. Raise ValueError for unsupported files."""
        ...

    @abstractmethod
    def supports(self, file_path: str | Path) -> bool:
        """Return True if this parser can handle the given file."""
        ...

    def _validate_file(self, file_path: str | Path) -> Path:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if not path.is_file():
            raise ValueError(f"Not a file: {path}")
        return path