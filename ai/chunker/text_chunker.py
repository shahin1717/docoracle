import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import tempfile
from pathlib import Path

from ai.ingestion import parse_document
from ai.chunker import Chunker, Chunk


def make_md(content):
    tmp = tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False, encoding="utf-8")
    tmp.write(content)
    tmp.close()
    return Path(tmp.name)


LONG_TEXT = """
# Introduction to Machine Learning

Machine learning is a subset of artificial intelligence. It allows computers to learn from data.
There are three main types of machine learning. The first is supervised learning.
In supervised learning, models train on labeled data. The second is unsupervised learning.
Unsupervised learning finds patterns in unlabeled data. The third is reinforcement learning.
Reinforcement learning trains agents through rewards and penalties. Each type has different use cases.

## Deep Learning

Deep learning uses neural networks with many layers. These layers learn hierarchical features.
Convolutional networks work well for images. Recurrent networks handle sequential data.
Transformers have become dominant in NLP tasks. They use self-attention mechanisms.
BERT and GPT are well-known transformer models. They are pretrained on large corpora.

## Applications

Machine learning powers many modern applications. Recommendation systems use collaborative filtering.
Natural language processing enables chatbots. Computer vision drives autonomous vehicles.
Healthcare uses ML for medical image analysis. Finance applies it to fraud detection.
"""


class TestChunker:
    def test_returns_chunks(self):
        path = make_md(LONG_TEXT)
        doc = parse_document(path)
        chunks = Chunker().chunk_document(doc)
        assert len(chunks) > 0
        assert all(isinstance(c, Chunk) for c in chunks)
        os.unlink(path)

    def test_chunk_size_respected(self):
        path = make_md(LONG_TEXT)
        doc = parse_document(path)
        chunker = Chunker(chunk_size=100, overlap=10)
        chunks = chunker.chunk_document(doc)
        for c in chunks:
            assert c.token_count <= 150
        os.unlink(path)

    def test_overlap_means_shared_content(self):
        path = make_md(LONG_TEXT)
        doc = parse_document(path)
        chunks = Chunker(chunk_size=80, overlap=20).chunk_document(doc)
        if len(chunks) >= 2:
            words_0 = set(chunks[0].text.split()[-10:])
            words_1 = set(chunks[1].text.split()[:15])
            assert len(words_0 & words_1) > 0
        os.unlink(path)

    def test_chunk_ids_are_unique(self):
        path = make_md(LONG_TEXT)
        doc = parse_document(path)
        chunks = Chunker().chunk_document(doc)
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids))
        os.unlink(path)

    def test_chunk_metadata_populated(self):
        path = make_md(LONG_TEXT)
        doc = parse_document(path)
        chunks = Chunker().chunk_document(doc)
        for c in chunks:
            assert c.source_path != ""
            assert c.metadata["file_type"] == "md"
            assert "title" in c.metadata
        os.unlink(path)

    def test_no_empty_chunks(self):
        path = make_md(LONG_TEXT)
        doc = parse_document(path)
        chunks = Chunker().chunk_document(doc)
        assert all(c.text.strip() != "" for c in chunks)
        os.unlink(path)

    def test_short_doc_gives_one_chunk(self):
        path = make_md("# Hi\n\nThis is a very short document.")
        doc = parse_document(path)
        chunks = Chunker(chunk_size=512).chunk_document(doc)
        assert len(chunks) == 1
        os.unlink(path)

    def test_chunk_index_sequential(self):
        path = make_md(LONG_TEXT)
        doc = parse_document(path)
        chunks = Chunker().chunk_document(doc)
        for i, c in enumerate(chunks):
            assert c.chunk_index == i
        os.unlink(path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])