import time
import requests
import numpy as np
from dataclasses import dataclass

from ai.chunker.chunker import Chunk


OLLAMA_URL = "http://localhost:11434/api/embeddings"
DEFAULT_MODEL = "nomic-embed-text"


@dataclass
class EmbeddedChunk:
    """A Chunk that now also carries its vector."""
    chunk: Chunk
    vector: np.ndarray   # shape: (768,) for nomic-embed-text

    @property
    def chunk_id(self):
        return self.chunk.chunk_id


class Embedder:
    """
    Calls Ollama's embedding endpoint to turn text into vectors.

    Why Ollama instead of HuggingFace directly?
    - No GPU memory management code needed — Ollama handles it
    - Same HTTP interface for both embedding and generation
    - Easy to swap models: just change model name

    Ollama must be running: `ollama serve`
    Model must be pulled: `ollama pull nomic-embed-text`
    """

    def __init__(self, model: str = DEFAULT_MODEL, ollama_url: str = OLLAMA_URL):
        self.model = model
        self.url = ollama_url

    def embed_text(self, text: str) -> np.ndarray:
        """Embed a single string. Returns a 1D numpy array."""
        response = requests.post(self.url, json={
            "model": self.model,
            "prompt": text,
        }, timeout=30)
        response.raise_for_status()
        vector = response.json()["embedding"]
        return np.array(vector, dtype=np.float32)

    def embed_chunks(self, chunks: list[Chunk], batch_size: int = 32) -> list[EmbeddedChunk]:
        """
        Embed a list of Chunks in batches.
        Returns EmbeddedChunk objects pairing each Chunk with its vector.
        """
        results = []
        total = len(chunks)

        for i in range(0, total, batch_size):
            batch = chunks[i:i + batch_size]
            print(f"  Embedding {i+1}–{min(i+batch_size, total)} / {total}...")

            for chunk in batch:
                vector = self.embed_text(chunk.text)
                results.append(EmbeddedChunk(chunk=chunk, vector=vector))

        return results

    def is_available(self) -> bool:
        """Check if Ollama is running and the model is loaded."""
        try:
            r = requests.get(self.url.replace("/api/embeddings", "/api/tags"), timeout=5)
            if r.status_code != 200:
                return False
            models = [m["name"] for m in r.json().get("models", [])]
            return any(self.model in m for m in models)
        except requests.exceptions.ConnectionError:
            return False
