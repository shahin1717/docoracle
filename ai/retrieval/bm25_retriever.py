import math
from collections import Counter


class BM25Retriever:
    """
    Classic keyword search using BM25 scoring.
    Operates on raw text — no vectors needed.
    Complements dense search for exact keyword matches.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self._corpus: list[tuple[str, list[str]]] = []  # (chunk_id, tokens)
        self._avgdl: float = 0
        self._df: dict[str, int] = {}
        self._n: int = 0

    def index(self, chunks: list[dict]):
        """
        Build BM25 index from chunks.
        Each chunk dict needs: chunk_id, text.
        """
        self._corpus = []
        for chunk in chunks:
            tokens = self._tokenize(chunk["text"])
            self._corpus.append((chunk["chunk_id"], tokens))

        self._n = len(self._corpus)
        self._avgdl = sum(len(tokens) for _, tokens in self._corpus) / max(self._n, 1)

        self._df = {}
        for _, tokens in self._corpus:
            for term in set(tokens):
                self._df[term] = self._df.get(term, 0) + 1

    def retrieve(self, query: str, top_k: int = 10) -> list[tuple[str, float]]:
        """Returns list of (chunk_id, score) sorted by score descending."""
        query_tokens = self._tokenize(query)
        scores = []

        for chunk_id, tokens in self._corpus:
            score = self._score(query_tokens, tokens)
            if score > 0:
                scores.append((chunk_id, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def _score(self, query_tokens: list[str], doc_tokens: list[str]) -> float:
        tf = Counter(doc_tokens)
        dl = len(doc_tokens)
        score = 0.0

        for term in query_tokens:
            if term not in tf:
                continue
            df = self._df.get(term, 0)
            idf = math.log((self._n - df + 0.5) / (df + 0.5) + 1)
            tf_val = tf[term]
            numerator = tf_val * (self.k1 + 1)
            denominator = tf_val + self.k1 * (1 - self.b + self.b * dl / self._avgdl)
            score += idf * (numerator / denominator)

        return score

    def _tokenize(self, text: str) -> list[str]:
        return text.lower().split()