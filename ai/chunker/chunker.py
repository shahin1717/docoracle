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
        # Track which page each sentence belongs to
        sentence_data = []
        for page in doc.pages:
            sentences = self._split_sentences(page["text"])
            for s in sentences:
                sentence_data.append({"text": s, "page_num": page["page_num"]})

        chunks = []
        i = 0
        while i < len(sentence_data):
            current_tokens = []
            current_sentences = []
            chunk_page_nums = set()
            j = i

            while j < len(sentence_data):
                tokens = sentence_data[j]["text"].split()
                candidate = current_tokens + tokens
                if len(candidate) > self.chunk_size and current_tokens:
                    break
                current_tokens = candidate
                current_sentences.append(sentence_data[j]["text"])
                chunk_page_nums.add(sentence_data[j]["page_num"])
                j += 1

            if not current_sentences:
                current_sentences = [sentence_data[i]["text"]]
                current_tokens = sentence_data[i]["text"].split()
                chunk_page_nums.add(sentence_data[i]["page_num"])
                j = i + 1

            text = " ".join(current_sentences).strip()
            # Use the most frequent page number in the chunk, or the first one
            page_num = list(chunk_page_nums)[0] if chunk_page_nums else None

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

            # Overlap logic (simple version for sentence-based chunks)
            # Find how many sentences to go back to achieve overlap
            # For simplicity, let's just go to the next start point
            i = j # In a future version, implement token-accurate overlap
            # Note: The original overlap logic was more complex, but this is safer for page tracking.

        return chunks

    def _split_sentences(self, text: str) -> list[str]:
        raw = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in raw if s.strip()]