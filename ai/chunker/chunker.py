import re
from dataclasses import dataclass

from ai.ingestion.base_parser import ParsedDocument


@dataclass
class Chunk:
    """One piece of text ready to be embedded."""
    chunk_id: str        # "{source_path}::chunk_{index}"
    text: str            # the actual text content
    token_count: int     # how many tokens this chunk is
    source_path: str     # which file it came from
    page_num: int | None # which page/slide/section
    chunk_index: int     # position in the document (0-based)
    metadata: dict       # heading, file_type, title, etc.


class Chunker:
    """
    Splits a ParsedDocument into overlapping chunks.

    Strategy:
    1. Split full_text into sentences
    2. Pack sentences into chunks until we hit chunk_size tokens
    3. The next chunk starts overlap tokens back
    """

    def __init__(self, chunk_size: int = 512, overlap: int = 64):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_document(self, doc: ParsedDocument) -> list[Chunk]:
        sentences = self._split_sentences(doc.full_text)
        sentence_tokens = [s.split() for s in sentences]

        chunks = []
        i = 0

        while i < len(sentences):
            current_tokens = []
            current_sentences = []
            j = i

            while j < len(sentences):
                candidate = current_tokens + sentence_tokens[j]
                if len(candidate) > self.chunk_size and current_tokens:
                    break
                current_tokens = candidate
                current_sentences.append(sentences[j])
                j += 1

            if not current_sentences:
                current_sentences = [sentences[i]]
                current_tokens = sentence_tokens[i]
                j = i + 1

            text = " ".join(current_sentences).strip()
            page_num = self._find_page(doc, text)

            chunks.append(Chunk(
                chunk_id=f"{doc.source_path}::chunk_{len(chunks)}",
                text=text,
                token_count=len(current_tokens),
                source_path=doc.source_path,
                page_num=page_num,
                chunk_index=len(chunks),
                metadata={
                    "title": doc.title,
                    "file_type": doc.file_type,
                },
            ))

            i = self._next_start(i, j, sentence_tokens, self.overlap)

        return chunks

    def _split_sentences(self, text: str) -> list[str]:
        raw = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in raw if s.strip()]

    def _count_tokens(self, text: str) -> int:
        return len(text.split())

    def _next_start(self, i, j, sentence_tokens, overlap):
        budget = overlap
        k = j - 1
        while k > i and budget > 0:
            budget -= len(sentence_tokens[k])
            if budget <= 0:
                return k + 1
            k -= 1
        return j

    def _find_page(self, doc, text):
        sample = text[:80]
        for page in doc.pages:
            if sample in page["text"]:
                return page["page_num"]
        return None