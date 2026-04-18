import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import numpy as np
from unittest.mock import patch, MagicMock

from ai.chunker.chunker import Chunk
from ai.embedding import Embedder, EmbeddedChunk


def fake_vector(dim=768):
    return list(np.random.rand(dim).astype(np.float32))

def make_chunk(text="hello world", index=0):
    return Chunk(
        chunk_id=f"doc.pdf::chunk_{index}",
        text=text,
        token_count=len(text.split()),
        source_path="doc.pdf",
        page_num=1,
        chunk_index=index,
        metadata={"file_type": "pdf", "title": "Test"},
    )

def mock_post(url, json=None, timeout=None):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"embedding": fake_vector()}
    resp.raise_for_status = MagicMock()
    return resp


class TestEmbedder:
    def test_embed_text_returns_numpy_array(self):
        with patch("requests.post", side_effect=mock_post):
            vec = Embedder().embed_text("test sentence")
        assert isinstance(vec, np.ndarray)
        assert vec.shape == (768,)
        assert vec.dtype == np.float32

    def test_embed_chunks_returns_embedded_chunks(self):
        chunks = [make_chunk("sentence one", 0), make_chunk("sentence two", 1)]
        with patch("requests.post", side_effect=mock_post):
            results = Embedder().embed_chunks(chunks)
        assert len(results) == 2
        assert all(isinstance(r, EmbeddedChunk) for r in results)

    def test_chunk_ids_preserved(self):
        chunks = [make_chunk("text", i) for i in range(3)]
        with patch("requests.post", side_effect=mock_post):
            results = Embedder().embed_chunks(chunks)
        ids = [r.chunk_id for r in results]
        assert ids == [c.chunk_id for c in chunks]

    def test_vector_dimension_correct(self):
        with patch("requests.post", side_effect=mock_post):
            results = Embedder().embed_chunks([make_chunk()])
        assert results[0].vector.shape == (768,)

    def test_batching_calls_post_once_per_chunk(self):
        chunks = [make_chunk(f"chunk {i}", i) for i in range(5)]
        with patch("requests.post", side_effect=mock_post) as mock:
            Embedder().embed_chunks(chunks, batch_size=2)
        assert mock.call_count == 5  # one call per chunk

    def test_is_available_false_when_ollama_down(self):
        import requests as req
        with patch("requests.get", side_effect=req.exceptions.ConnectionError):
            assert Embedder().is_available() is False

    def test_original_chunk_accessible(self):
        chunk = make_chunk("some text", 0)
        with patch("requests.post", side_effect=mock_post):
            result = Embedder().embed_chunks([chunk])[0]
        assert result.chunk.text == "some text"
        assert result.chunk.source_path == "doc.pdf"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
