import re
from itertools import combinations


# Verb patterns that indicate a relationship between two entities
RELATION_PATTERNS = [
    # "X uses Y", "X uses Y to..."
    (r'\b(uses?|utilizing|utilized)\b', "USES"),
    # "X is a Y", "X is an Y"
    (r'\bis\s+a(?:n)?\b', "IS_A"),
    # "X is part of Y"
    (r'\bis\s+part\s+of\b', "PART_OF"),
    # "X contains Y", "X includes Y"
    (r'\b(contains?|includes?|consisting of)\b', "CONTAINS"),
    # "X extends Y", "X inherits from Y"
    (r'\b(extends?|inherits?\s+from|subclass\s+of)\b', "EXTENDS"),
    # "X depends on Y", "X requires Y"
    (r'\b(depends?\s+on|requires?|needs?)\b', "DEPENDS_ON"),
    # "X produces Y", "X generates Y", "X outputs Y"
    (r'\b(produces?|generates?|outputs?|creates?)\b', "PRODUCES"),
    # "X improves Y", "X enhances Y"
    (r'\b(improves?|enhances?|optimizes?|boosts?)\b', "IMPROVES"),
    # "X replaces Y", "X supersedes Y"
    (r'\b(replaces?|supersedes?)\b', "REPLACES"),
    # "X is based on Y", "X is built on Y"
    (r'\bis\s+(based|built)\s+on\b', "BASED_ON"),
    # "X consists of Y"
    (r'\bconsists?\s+of\b', "CONSISTS_OF"),
    # "X enables Y", "X allows Y"
    (r'\b(enables?|allows?|permits?)\b', "ENABLES"),
]

# Compile once
COMPILED_PATTERNS = [
    (re.compile(pat, re.IGNORECASE), label)
    for pat, label in RELATION_PATTERNS
]


class RelationExtractor:
    """
    Extracts (subject, relation, object) triples from text.

    Strategy:
    1. For each sentence, find all entities present
    2. Try each relation pattern on the sentence
    3. If a pattern matches between two entities, record the triple

    This is rule-based — no ML needed.
    For better quality later, swap _extract_from_sentence with
    an LLM prompt call using the local Ollama model.
    """

    def __init__(self, window_size: int = 150):
        # Max character distance between subject and object in a sentence
        self.window_size = window_size

    def extract(self, text: str, entities: list[dict]) -> list[dict]:
        """
        Extract relation triples from text given a list of entities.
        Returns list of {subject, relation, object, sentence}
        """
        if len(entities) < 2:
            return []

        sentences = self._split_sentences(text)
        triples = []

        for sentence in sentences:
            found = self._entities_in_sentence(sentence, entities)
            if len(found) < 2:
                continue
            new_triples = self._extract_from_sentence(sentence, found)
            triples.extend(new_triples)

        return self._deduplicate(triples)

    def extract_from_chunks(
        self, chunks: list[dict], entities: list[dict]
    ) -> list[dict]:
        """Extract triples across all chunks."""
        all_triples = []
        entity_texts = [e["text"] for e in entities]

        for chunk in chunks:
            # Only process chunks that contain at least 2 known entities
            present = [e for e in entities if e["text"].lower() in chunk["text"].lower()]
            if len(present) < 2:
                continue
            triples = self.extract(chunk["text"], present)
            for t in triples:
                t["chunk_id"] = chunk["chunk_id"]
            all_triples.extend(triples)

        return self._deduplicate(all_triples)

    def _extract_from_sentence(self, sentence: str, entities: list[dict]) -> list[dict]:
        """Try all relation patterns against a sentence containing 2+ entities."""
        triples = []

        for pattern, label in COMPILED_PATTERNS:
            match = pattern.search(sentence)
            if not match:
                continue

            verb_pos = match.start()

            # Find entities before and after the verb
            before = [
                e for e in entities
                if self._find_pos(sentence, e["text"]) < verb_pos
            ]
            after = [
                e for e in entities
                if self._find_pos(sentence, e["text"]) > verb_pos
            ]

            for subj in before:
                for obj in after:
                    if subj["text"].lower() == obj["text"].lower():
                        continue
                    triples.append({
                        "subject": subj["text"],
                        "relation": label,
                        "object": obj["text"],
                        "sentence": sentence.strip(),
                    })

        return triples

    def _entities_in_sentence(self, sentence: str, entities: list[dict]) -> list[dict]:
        """Return entities whose text appears in the sentence."""
        s_lower = sentence.lower()
        return [e for e in entities if e["text"].lower() in s_lower]

    def _find_pos(self, sentence: str, entity_text: str) -> int:
        """Find character position of entity in sentence (case-insensitive)."""
        idx = sentence.lower().find(entity_text.lower())
        return idx if idx != -1 else len(sentence)

    def _split_sentences(self, text: str) -> list[str]:
        raw = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in raw if len(s.strip()) > 10]

    def _deduplicate(self, triples: list[dict]) -> list[dict]:
        """Remove duplicate (subject, relation, object) triples."""
        seen = set()
        result = []
        for t in triples:
            key = (t["subject"].lower(), t["relation"], t["object"].lower())
            if key not in seen:
                seen.add(key)
                result.append(t)
        return result