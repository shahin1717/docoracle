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
        self.window_size = window_size

    def extract(self, text: str, entities: list[dict]) -> list[dict]:
        return self._from_hierarchy(entities)

    def extract_from_chunks(self, chunks: list[dict], entities: list[dict]) -> list[dict]:
        return self._from_hierarchy(entities)

    def _from_hierarchy(self, entities: list[dict]) -> list[dict]:
        """
        Build triples from parent-child relationships in the entity hierarchy.
        ROOT → CONTAINS → MAIN_TOPIC
        MAIN_TOPIC → CONTAINS → SUBTOPIC
        """
        triples = []
        entity_map = {e["text"]: e for e in entities}

        for entity in entities:
            parent_name = entity.get("parent")
            if not parent_name:
                continue
            if parent_name not in entity_map:
                continue

            triples.append({
                "subject":  parent_name,
                "relation": "CONTAINS",
                "object":   entity["text"],
                "sentence": f"{parent_name} contains {entity['text']}",
            })

        return triples
    


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