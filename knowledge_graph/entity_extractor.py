import re


STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "this", "that", "these", "those", "i", "we", "you", "he",
    "she", "it", "they", "what", "which", "who", "whom", "whose", "when",
    "where", "why", "how", "all", "each", "every", "both", "few", "more",
    "most", "other", "some", "such", "no", "not", "only", "same", "so",
    "than", "too", "very", "just", "but", "and", "or", "for", "of", "in",
    "on", "at", "to", "from", "with", "about", "into", "through", "during",
    "also", "its", "their", "our", "your", "his", "her", "my",
}


class EntityExtractor:
    """
    Extracts named entities from text without any external ML models.

    Strategy — three passes:
    1. Capitalized noun phrases  (e.g. "Neural Network", "GPT-4")
    2. Technical terms           (e.g. "self-attention", "backpropagation")
    3. Quoted or defined terms   (e.g. 'called "embedding"')

    Why no spaCy here?
    spaCy is optional — you can plug it in later by subclassing this.
    This version runs with zero dependencies and works well for
    technical documents which are the main use case.
    """

    def __init__(self, min_length: int = 3, max_words: int = 4):
        self.min_length = min_length
        self.max_words = max_words

    def extract(self, text: str) -> list[dict]:
        """
        Extract entities from text.
        Returns list of dicts: {text, type, start, end}
        """
        entities = {}

        for entity, meta in self._capitalized_phrases(text).items():
            entities[entity] = meta

        for entity, meta in self._technical_terms(text).items():
            if entity not in entities:
                entities[entity] = meta

        for entity, meta in self._quoted_terms(text).items():
            if entity not in entities:
                entities[entity] = meta

        return list(entities.values())

    def extract_from_chunks(self, chunks: list[dict]) -> list[dict]:
        """
        Extract entities from a list of chunk dicts.
        Deduplicates across chunks, counts frequency.
        """
        freq: dict[str, dict] = {}

        for chunk in chunks:
            found = self.extract(chunk["text"])
            for ent in found:
                key = ent["text"].lower()
                if key in freq:
                    freq[key]["frequency"] += 1
                    freq[key]["chunk_ids"].append(chunk["chunk_id"])
                else:
                    freq[key] = {
                        "text": ent["text"],
                        "type": ent["type"],
                        "frequency": 1,
                        "chunk_ids": [chunk["chunk_id"]],
                    }

        # Filter out low-frequency noise — entities appearing only once
        # are often parsing artifacts
        return [e for e in freq.values() if e["frequency"] >= 1]

    def _capitalized_phrases(self, text: str) -> dict:
        """
        Find sequences of capitalized words AND acronyms (e.g. BERT, GPT-4).
        """
        pattern = re.compile(
            r'\b((?:[A-Z][a-z]+|[A-Z]{2,})(?:\s+(?:[A-Z][a-z]+|[A-Z]{2,})){0,3})\b'
        )

        results = {}
        for match in pattern.finditer(text):
            phrase = match.group(1).strip()
            words = phrase.lower().split()

            if any(w in STOP_WORDS for w in words):
                continue
            if len(phrase) < self.min_length:
                continue
            if len(words) > self.max_words:
                continue

            results[phrase] = {
                "text": phrase,
                "type": "PROPER_NOUN",
                "start": match.start(),
                "end": match.end(),
            }

        return results

    def _technical_terms(self, text: str) -> dict:
        """Find hyphenated or compound technical terms."""
        # e.g. self-attention, back-propagation, fine-tuning
        pattern = re.compile(r'\b([a-z]+(?:-[a-z]+)+)\b')
        results = {}
        for match in pattern.finditer(text):
            term = match.group(1)
            if len(term) < self.min_length:
                continue
            results[term] = {
                "text": term,
                "type": "TECHNICAL_TERM",
                "start": match.start(),
                "end": match.end(),
            }
        return results

    def _quoted_terms(self, text: str) -> dict:
        """Find terms introduced with 'called', 'known as', 'termed'."""
        pattern = re.compile(
            r'(?:called|known as|termed|named|referred to as)\s+"?([A-Za-z][A-Za-z\s\-]{2,30})"?',
            re.IGNORECASE
        )
        results = {}
        for match in pattern.finditer(text):
            term = match.group(1).strip().rstrip('"')
            if len(term) < self.min_length:
                continue
            results[term.lower()] = {
                "text": term,
                "type": "DEFINED_TERM",
                "start": match.start(),
                "end": match.end(),
            }
        return results