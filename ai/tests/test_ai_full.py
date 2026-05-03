import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import tempfile
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock


# ── helpers ───────────────────────────────────────────────────────────────────

def make_md(content):
    tmp = tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False, encoding="utf-8")
    tmp.write(content)
    tmp.close()
    return Path(tmp.name)

def fake_vector(dim=768):
    v = np.random.rand(dim).astype(np.float32)
    return v / np.linalg.norm(v)

def mock_post(url=None, json=None, timeout=None, stream=False):
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"embedding": fake_vector().tolist()}
    return resp

def make_chunk_dict(i=0, text="hello world this is a test sentence"):
    return {
        "chunk_id": f"doc.pdf::chunk_{i}",
        "source_path": "doc.pdf",
        "title": "Test Doc",
        "file_type": "pdf",
        "page_num": 1,
        "chunk_index": i,
        "text": text,
        "token_count": len(text.split()),
        "metadata": {},
    }

LONG_MD = """
# Machine Learning

Machine learning is a subset of artificial intelligence. It allows systems to learn from data.
Supervised learning uses labeled data to train models. Unsupervised learning finds hidden patterns.
Reinforcement learning trains agents using rewards and penalties. Each approach solves different problems.

## Deep Learning

Deep learning uses neural networks with many layers. Convolutional networks excel at image tasks.
Recurrent networks handle sequences and time series. Transformers now dominate natural language processing.
BERT and GPT are both transformer-based architectures. They differ in their pretraining objectives.

## Applications

Recommendation systems use collaborative filtering techniques. Computer vision powers autonomous vehicles.
Natural language processing enables intelligent chatbots. Healthcare applies ML to medical imaging analysis.
"""


# ── vectorstore ───────────────────────────────────────────────────────────────

class TestFAISSStore:
    def test_add_and_search(self):
        from ai.vectorstore import FAISSStore
        store = FAISSStore(dim=8)
        vecs = np.random.rand(5, 8).astype(np.float32)
        ids = [f"chunk_{i}" for i in range(5)]
        store.add(ids, vecs)
        results = store.search(vecs[0], top_k=3)
        assert len(results) == 3
        assert results[0][0] == "chunk_0"

    def test_size(self):
        from ai.vectorstore import FAISSStore
        store = FAISSStore(dim=8)
        vecs = np.random.rand(4, 8).astype(np.float32)
        store.add([f"c_{i}" for i in range(4)], vecs)
        assert store.size == 4

    def test_save_and_load(self, tmp_path):
        from ai.vectorstore import FAISSStore
        store = FAISSStore(dim=8)
        vecs = np.random.rand(3, 8).astype(np.float32)
        store.add(["a", "b", "c"], vecs)
        store.save(tmp_path / "idx")
        store2 = FAISSStore(dim=8)
        store2.load(tmp_path / "idx")
        assert store2.size == 3
        results = store2.search(vecs[0], top_k=1)
        assert results[0][0] == "a"

    def test_returns_scores(self):
        from ai.vectorstore import FAISSStore
        store = FAISSStore(dim=8)
        vecs = np.random.rand(3, 8).astype(np.float32)
        store.add(["x", "y", "z"], vecs)
        results = store.search(vecs[0], top_k=3)
        assert all(isinstance(score, float) for _, score in results)


class TestMetadataStore:
    def test_insert_and_get(self, tmp_path):
        from ai.vectorstore import MetadataStore
        store = MetadataStore(tmp_path / "test.db")
        store.insert_chunks([make_chunk_dict(0)])
        result = store.get_chunk("doc.pdf::chunk_0")
        assert result is not None
        assert result["text"] == "hello world this is a test sentence"
        store.close()

    def test_get_chunks_ordered(self, tmp_path):
        from ai.vectorstore import MetadataStore
        store = MetadataStore(tmp_path / "test.db")
        chunks = [make_chunk_dict(i, f"text number {i}") for i in range(3)]
        store.insert_chunks(chunks)
        ids = ["doc.pdf::chunk_2", "doc.pdf::chunk_0"]
        results = store.get_chunks(ids)
        assert results[0]["chunk_id"] == "doc.pdf::chunk_2"
        assert results[1]["chunk_id"] == "doc.pdf::chunk_0"
        store.close()

    def test_get_by_source(self, tmp_path):
        from ai.vectorstore import MetadataStore
        store = MetadataStore(tmp_path / "test.db")
        store.insert_chunks([make_chunk_dict(i) for i in range(3)])
        results = store.get_by_source("doc.pdf")
        assert len(results) == 3
        store.close()

    def test_delete_source(self, tmp_path):
        from ai.vectorstore import MetadataStore
        store = MetadataStore(tmp_path / "test.db")
        store.insert_chunks([make_chunk_dict(0)])
        store.delete_source("doc.pdf")
        assert store.get_chunk("doc.pdf::chunk_0") is None
        store.close()

    def test_missing_chunk_returns_none(self, tmp_path):
        from ai.vectorstore import MetadataStore
        store = MetadataStore(tmp_path / "test.db")
        assert store.get_chunk("nonexistent") is None
        store.close()


# ── retrieval ─────────────────────────────────────────────────────────────────

class TestBM25Retriever:
    def test_basic_retrieval(self):
        from ai.retrieval import BM25Retriever
        bm25 = BM25Retriever()
        chunks = [
            {"chunk_id": "c0", "text": "machine learning neural networks deep learning"},
            {"chunk_id": "c1", "text": "cooking recipes pasta tomato sauce"},
            {"chunk_id": "c2", "text": "neural networks transformers attention mechanism"},
        ]
        bm25.index(chunks)
        results = bm25.retrieve("neural networks", top_k=2)
        ids = [r[0] for r in results]
        assert "c0" in ids or "c2" in ids

    def test_no_match_returns_empty(self):
        from ai.retrieval import BM25Retriever
        bm25 = BM25Retriever()
        bm25.index([{"chunk_id": "c0", "text": "cats and dogs"}])
        results = bm25.retrieve("quantum physics")
        assert results == []

    def test_scores_sorted_descending(self):
        from ai.retrieval import BM25Retriever
        bm25 = BM25Retriever()
        chunks = [{"chunk_id": f"c{i}", "text": f"word{i} common common"} for i in range(5)]
        bm25.index(chunks)
        results = bm25.retrieve("common word0", top_k=5)
        scores = [s for _, s in results]
        assert scores == sorted(scores, reverse=True)

    def test_top_k_respected(self):
        from ai.retrieval import BM25Retriever
        bm25 = BM25Retriever()
        chunks = [{"chunk_id": f"c{i}", "text": f"machine learning test {i}"} for i in range(10)]
        bm25.index(chunks)
        results = bm25.retrieve("machine learning", top_k=3)
        assert len(results) <= 3


class TestHybridRetriever:
    def test_combines_results(self):
        from ai.retrieval import BM25Retriever, HybridRetriever
        from ai.vectorstore import FAISSStore
        from ai.embedding import Embedder

        store = FAISSStore(dim=4)
        vecs = np.array([
            [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]
        ], dtype=np.float32)
        store.add(["c0", "c1", "c2"], vecs)

        embedder = MagicMock()
        embedder.embed_text.return_value = np.array([1, 0, 0, 0], dtype=np.float32)

        from ai.retrieval import DenseRetriever
        dense = DenseRetriever(store, embedder)

        bm25 = BM25Retriever()
        bm25.index([
            {"chunk_id": "c0", "text": "neural network transformer"},
            {"chunk_id": "c1", "text": "cooking recipe pasta"},
            {"chunk_id": "c2", "text": "deep learning model"},
        ])

        hybrid = HybridRetriever(dense, bm25)
        results = hybrid.retrieve("neural network", top_k=3)
        assert len(results) > 0
        ids = [r[0] for r in results]
        assert "c0" in ids

    def test_rrf_scores_are_positive(self):
        from ai.retrieval import BM25Retriever, HybridRetriever, DenseRetriever
        from ai.vectorstore import FAISSStore

        store = FAISSStore(dim=4)
        vecs = np.random.rand(3, 4).astype(np.float32)
        store.add(["c0", "c1", "c2"], vecs)

        embedder = MagicMock()
        embedder.embed_text.return_value = vecs[0]

        dense = DenseRetriever(store, embedder)
        bm25 = BM25Retriever()
        bm25.index([{"chunk_id": f"c{i}", "text": f"text {i} word"} for i in range(3)])

        hybrid = HybridRetriever(dense, bm25)
        results = hybrid.retrieve("text word", top_k=3)
        assert all(score > 0 for _, score in results)


# ── generation ────────────────────────────────────────────────────────────────

class TestPromptBuilder:
    def test_builds_two_messages(self, tmp_path):
        from ai.generation import build_prompt
        from ai.vectorstore import MetadataStore
        store = MetadataStore(tmp_path / "test.db")
        store.insert_chunks([make_chunk_dict(0, "Transformers use self-attention mechanisms.")])
        messages = build_prompt("What is a transformer?", ["doc.pdf::chunk_0"], store)
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        store.close()

    def test_context_included_in_user_message(self, tmp_path):
        from ai.generation import build_prompt
        from ai.vectorstore import MetadataStore
        store = MetadataStore(tmp_path / "test.db")
        store.insert_chunks([make_chunk_dict(0, "BERT is a transformer model.")])
        messages = build_prompt("What is BERT?", ["doc.pdf::chunk_0"], store)
        assert "BERT is a transformer model." in messages[1]["content"]
        store.close()

    def test_query_included_in_user_message(self, tmp_path):
        from ai.generation import build_prompt
        from ai.vectorstore import MetadataStore
        store = MetadataStore(tmp_path / "test.db")
        store.insert_chunks([make_chunk_dict(0)])
        messages = build_prompt("What is attention?", ["doc.pdf::chunk_0"], store)
        assert "What is attention?" in messages[1]["content"]
        store.close()

    def test_system_prompt_contains_citation_instruction(self, tmp_path):
        from ai.generation import build_prompt
        from ai.vectorstore import MetadataStore
        store = MetadataStore(tmp_path / "test.db")
        store.insert_chunks([make_chunk_dict(0)])
        messages = build_prompt("query", ["doc.pdf::chunk_0"], store)
        assert "cite" in messages[0]["content"].lower()
        store.close()


class TestLLMClient:
    def test_generate_returns_string(self):
        from ai.generation import LLMClient
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"message": {"content": "Paris is the capital."}}
        with patch("requests.post", return_value=mock_resp):
            result = LLMClient().generate([{"role": "user", "content": "test"}])
        assert isinstance(result, str)
        assert "Paris" in result

    def test_stream_yields_tokens(self):
        from ai.generation import LLMClient
        import json
        lines = [
            json.dumps({"message": {"content": "Hello"}, "done": False}).encode(),
            json.dumps({"message": {"content": " world"}, "done": True}).encode(),
        ]
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.iter_lines.return_value = lines
        with patch("requests.post", return_value=mock_resp):
            tokens = list(LLMClient().stream([{"role": "user", "content": "hi"}]))
        assert tokens == ["Hello", " world"]

    def test_is_available_false_when_down(self):
        from ai.generation import LLMClient
        import requests as req
        with patch("requests.get", side_effect=req.exceptions.ConnectionError):
            assert LLMClient().is_available() is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
