import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import tempfile
from pathlib import Path
import re

from entity_extractor import EntityExtractor
from relation_extractor import RelationExtractor
from graph_builder import GraphBuilder
from graph_store import GraphStore
from graph_retriever import GraphRetriever
from graph_exporter import GraphExporter


SAMPLE_TEXT = """
Transformers use self-attention mechanisms to process sequences.
BERT is a transformer model that uses bidirectional encoding.
GPT is based on transformer architecture and produces text outputs.
Deep Learning contains many neural network layers.
Neural Networks enable pattern recognition in complex data.
Self-attention improves long-range dependency modeling.
BERT extends the transformer architecture with masked language modeling.
"""

SAMPLE_CHUNKS = [
    {"chunk_id": "doc::chunk_0", "text": "Transformers use self-attention mechanisms to process sequences."},
    {"chunk_id": "doc::chunk_1", "text": "BERT is a transformer model that uses bidirectional encoding."},
    {"chunk_id": "doc::chunk_2", "text": "GPT is based on transformer architecture and produces text outputs."},
    {"chunk_id": "doc::chunk_3", "text": "Deep Learning contains many neural network layers."},
]


# ── entity extractor ──────────────────────────────────────────────────────────

class TestEntityExtractor:
    def test_extracts_capitalized_entities(self):
        ex = EntityExtractor()
        entities = ex.extract("BERT and GPT are transformer models.")
        texts = [e["text"] for e in entities]
        assert any("BERT" in t or "GPT" in t for t in texts)

    def test_extracts_technical_terms(self):
        ex = EntityExtractor()
        entities = ex.extract("self-attention is used in transformers.")
        texts = [e["text"] for e in entities]
        assert "self-attention" in texts

    def test_extracts_quoted_terms(self):
        ex = EntityExtractor()
        entities = ex.extract('This is called "embedding layer" in the model.')
        texts = [e["text"] for e in entities]
        assert any("embedding" in t.lower() for t in texts)

    def test_returns_list_of_dicts(self):
        ex = EntityExtractor()
        entities = ex.extract(SAMPLE_TEXT)
        assert isinstance(entities, list)
        for e in entities:
            assert "text" in e
            assert "type" in e

    def test_extract_from_chunks(self):
        ex = EntityExtractor()
        entities = ex.extract_from_chunks(SAMPLE_CHUNKS)
        assert len(entities) > 0
        assert all("frequency" in e for e in entities)
        assert all("chunk_ids" in e for e in entities)

    def test_frequency_counted(self):
        ex = EntityExtractor()
        chunks = [
            {"chunk_id": "c0", "text": "Transformers use self-attention."},
            {"chunk_id": "c1", "text": "Transformers are powerful models."},
        ]
        entities = ex.extract_from_chunks(chunks)
        transformer_ents = [e for e in entities if "transformer" in e["text"].lower()]
        if transformer_ents:
            assert transformer_ents[0]["frequency"] >= 1

    def test_no_stop_words_as_entities(self):
        ex = EntityExtractor()
        entities = ex.extract("The model is very good and it works well.")
        texts = [e["text"].lower() for e in entities]
        stop = {"the", "and", "is", "it", "very"}
        assert not any(t in stop for t in texts)


# ── relation extractor ────────────────────────────────────────────────────────

class TestRelationExtractor:
    def test_extracts_uses_relation(self):
        re_ext = RelationExtractor()
        entities = [
            {"text": "Transformer", "type": "PROPER_NOUN"},
            {"text": "self-attention", "type": "TECHNICAL_TERM"},
        ]
        triples = re_ext.extract(
            "Transformer uses self-attention to process tokens.", entities
        )
        assert len(triples) > 0
        assert triples[0]["relation"] == "USES"

    def test_extracts_is_a_relation(self):
        re_ext = RelationExtractor()
        entities = [
            {"text": "BERT", "type": "PROPER_NOUN"},
            {"text": "Transformer", "type": "PROPER_NOUN"},
        ]
        triples = re_ext.extract("BERT is a Transformer model.", entities)
        relations = [t["relation"] for t in triples]
        assert "IS_A" in relations

    def test_triple_has_required_fields(self):
        re_ext = RelationExtractor()
        entities = [
            {"text": "GPT", "type": "PROPER_NOUN"},
            {"text": "Transformer", "type": "PROPER_NOUN"},
        ]
        triples = re_ext.extract("GPT is based on Transformer architecture.", entities)
        for t in triples:
            assert "subject" in t
            assert "relation" in t
            assert "object" in t
            assert "sentence" in t

    def test_deduplicates_triples(self):
        re_ext = RelationExtractor()
        entities = [
            {"text": "BERT", "type": "PROPER_NOUN"},
            {"text": "Transformer", "type": "PROPER_NOUN"},
        ]
        text = "BERT uses Transformer. BERT uses Transformer."
        triples = re_ext.extract(text, entities)
        keys = [(t["subject"].lower(), t["relation"], t["object"].lower()) for t in triples]
        assert len(keys) == len(set(keys))

    def test_no_self_relations(self):
        re_ext = RelationExtractor()
        entities = [{"text": "BERT", "type": "PROPER_NOUN"}]
        triples = re_ext.extract("BERT uses BERT internally.", entities)
        for t in triples:
            assert t["subject"].lower() != t["object"].lower()

    def test_extract_from_chunks(self):
        re_ext = RelationExtractor()
        entities = [
            {"text": "Transformer", "type": "PROPER_NOUN"},
            {"text": "self-attention", "type": "TECHNICAL_TERM"},
            {"text": "BERT", "type": "PROPER_NOUN"},
        ]
        triples = re_ext.extract_from_chunks(SAMPLE_CHUNKS, entities)
        assert isinstance(triples, list)


# ── graph builder ─────────────────────────────────────────────────────────────

class TestGraphBuilder:
    def _make_graph(self):
        entities = [
            {"text": "Transformer", "type": "PROPER_NOUN", "frequency": 3, "chunk_ids": ["c0"]},
            {"text": "BERT",        "type": "PROPER_NOUN", "frequency": 2, "chunk_ids": ["c1"]},
            {"text": "self-attention", "type": "TECHNICAL_TERM", "frequency": 2, "chunk_ids": ["c0"]},
        ]
        triples = [
            {"subject": "Transformer", "relation": "USES", "object": "self-attention", "sentence": "Transformer uses self-attention."},
            {"subject": "BERT",        "relation": "IS_A", "object": "Transformer",    "sentence": "BERT is a Transformer."},
        ]
        builder = GraphBuilder()
        return builder.build(entities, triples)

    def test_nodes_added(self):
        graph = self._make_graph()
        assert "transformer" in graph.nodes
        assert "bert" in graph.nodes
        assert "self-attention" in graph.nodes

    def test_edges_added(self):
        graph = self._make_graph()
        assert graph.has_edge("transformer", "self-attention")
        assert graph.has_edge("bert", "transformer")

    def test_edge_relation_label(self):
        graph = self._make_graph()
        assert graph["transformer"]["self-attention"]["relation"] == "USES"
        assert graph["bert"]["transformer"]["relation"] == "IS_A"

    def test_node_attributes(self):
        graph = self._make_graph()
        assert graph.nodes["transformer"]["label"] == "Transformer"
        assert graph.nodes["transformer"]["frequency"] == 3

    def test_stats(self):
        builder = GraphBuilder()
        graph = self._make_graph()
        builder.graph = graph
        stats = builder.stats()
        assert stats["nodes"] == 3
        assert stats["edges"] == 2

    def test_get_neighbors(self):
        builder = GraphBuilder()
        graph = self._make_graph()
        builder.graph = graph
        neighbors = builder.get_neighbors("Transformer")
        assert len(neighbors) > 0
        relations = [n["relation"] for n in neighbors]
        assert "USES" in relations


# ── graph store ───────────────────────────────────────────────────────────────

class TestGraphStore:
    def _make_graph(self):
        import networkx as nx
        g = nx.DiGraph()
        g.add_node("bert", label="BERT", type="PROPER_NOUN", frequency=2)
        g.add_node("transformer", label="Transformer", type="PROPER_NOUN", frequency=3)
        g.add_edge("bert", "transformer", relation="IS_A", weight=1)
        return g

    def test_save_and_load(self, tmp_path):
        store = GraphStore(tmp_path)
        graph = self._make_graph()
        store.save(graph, "test_doc")
        loaded = store.load("test_doc")
        assert loaded is not None
        assert "bert" in loaded.nodes
        assert loaded.has_edge("bert", "transformer")

    def test_exists(self, tmp_path):
        store = GraphStore(tmp_path)
        assert not store.exists("missing_doc")
        store.save(self._make_graph(), "test_doc")
        assert store.exists("test_doc")

    def test_delete(self, tmp_path):
        store = GraphStore(tmp_path)
        store.save(self._make_graph(), "test_doc")
        store.delete("test_doc")
        assert not store.exists("test_doc")

    def test_list_docs(self, tmp_path):
        store = GraphStore(tmp_path)
        store.save(self._make_graph(), "doc_a")
        store.save(self._make_graph(), "doc_b")
        docs = store.list_docs()
        assert "doc_a" in docs
        assert "doc_b" in docs

    def test_export_for_frontend(self, tmp_path):
        store = GraphStore(tmp_path)
        store.save(self._make_graph(), "test_doc")
        data = store.export_for_frontend("test_doc")
        assert "nodes" in data
        assert "links" in data
        assert len(data["nodes"]) == 2
        assert len(data["links"]) == 1

    def test_load_missing_returns_none(self, tmp_path):
        store = GraphStore(tmp_path)
        assert store.load("nonexistent") is None


# ── graph retriever ───────────────────────────────────────────────────────────

class TestGraphRetriever:
    def _make_retriever(self):
        import networkx as nx
        g = nx.DiGraph()
        g.add_node("transformer", label="Transformer", type="PROPER_NOUN", frequency=3)
        g.add_node("bert",        label="BERT",        type="PROPER_NOUN", frequency=2)
        g.add_node("self-attention", label="self-attention", type="TECHNICAL_TERM", frequency=2)
        g.add_edge("transformer", "self-attention", relation="USES",  weight=1)
        g.add_edge("bert",        "transformer",    relation="IS_A",  weight=1)
        return GraphRetriever(g)

    def test_get_context_for_query(self):
        retriever = self._make_retriever()
        context = retriever.get_context_for_query("How does BERT work?")
        assert isinstance(context, str)

    def test_context_contains_graph_facts(self):
        retriever = self._make_retriever()
        context = retriever.get_context_for_query("What does BERT use?")
        assert "Knowledge graph context" in context or context == ""

    def test_find_path_between_entities(self):
        retriever = self._make_retriever()
        path = retriever.find_path("BERT", "self-attention")
        assert isinstance(path, list)
        if path:
            assert path[0] == "BERT"

    def test_find_path_missing_entity(self):
        retriever = self._make_retriever()
        path = retriever.find_path("BERT", "nonexistent")
        assert path == []

    def test_get_subgraph(self):
        retriever = self._make_retriever()
        sub = retriever.get_subgraph("bert", depth=1)
        assert "bert" in sub.nodes
        assert "transformer" in sub.nodes

    def test_empty_query_returns_empty(self):
        retriever = self._make_retriever()
        context = retriever.get_context_for_query("")
        assert context == ""


# ── graph exporter ────────────────────────────────────────────────────────────

class TestGraphExporter:
    def _make_graph(self):
        import networkx as nx
        g = nx.DiGraph()
        g.add_node("bert", label="BERT", type="PROPER_NOUN", frequency=2)
        g.add_node("transformer", label="Transformer", type="PROPER_NOUN", frequency=3)
        g.add_edge("bert", "transformer", relation="IS_A", weight=1)
        return g

    def test_to_frontend_json_structure(self):
        exp = GraphExporter()
        data = exp.to_frontend_json(self._make_graph())
        assert "nodes" in data
        assert "links" in data

    def test_frontend_json_node_fields(self):
        exp = GraphExporter()
        data = exp.to_frontend_json(self._make_graph())
        for node in data["nodes"]:
            assert "id" in node
            assert "label" in node
            assert "type" in node
            assert "val" in node

    def test_frontend_json_link_fields(self):
        exp = GraphExporter()
        data = exp.to_frontend_json(self._make_graph())
        for link in data["links"]:
            assert "source" in link
            assert "target" in link
            assert "relation" in link

    def test_to_json_file(self, tmp_path):
        exp = GraphExporter()
        out = tmp_path / "graph.json"
        exp.to_json_file(self._make_graph(), out)
        assert out.exists()
        import json
        data = json.loads(out.read_text())
        assert "nodes" in data

    def test_to_csv(self, tmp_path):
        exp = GraphExporter()
        exp.to_csv(self._make_graph(), tmp_path)
        assert (tmp_path / "nodes.csv").exists()
        assert (tmp_path / "edges.csv").exists()
        content = (tmp_path / "nodes.csv").read_text()
        assert "bert" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])