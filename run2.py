import sys
import numpy as np
from pathlib import Path

from ai.ingestion import parse_document
from ai.chunker import Chunker
from ai.embedding import Embedder
from ai.vectorstore import FAISSStore, MetadataStore
from ai.retrieval import HybridRetriever, DenseRetriever, BM25Retriever
from ai.generation import LLMClient, build_prompt

from knowledge_graph import (
    EntityExtractor, RelationExtractor,
    GraphBuilder, GraphStore, GraphRetriever
)


def build_knowledge_graph(chunks: list, doc_id: str):
    """Extract entities + relations, build graph, save it."""
    print("\n[KG] Extracting entities...")
    extractor = EntityExtractor()
    entities  = extractor.extract_from_chunks([
        {"chunk_id": c.chunk_id, "text": c.text} for c in chunks
    ])
    print(f"     {len(entities)} entities found")

    print("[KG] Extracting relations...")
    rel_extractor = RelationExtractor()
    triples = rel_extractor.extract_from_chunks([
        {"chunk_id": c.chunk_id, "text": c.text} for c in chunks
    ], entities)
    print(f"     {len(triples)} triples found")

    print("[KG] Building graph...")
    builder = GraphBuilder()
    graph   = builder.build(entities, triples)
    stats   = builder.stats()
    print(f"     {stats['nodes']} nodes, {stats['edges']} edges")

    print("[KG] Saving graph...")
    GraphStore("data/graphs").save(graph, doc_id)
    print(f"     Saved to data/graphs/{doc_id}.json")

    return graph


def run(pdf_path: str, prompt: str):
    doc_id = Path(pdf_path).stem

    print("\n[1] Parsing document...")
    doc = parse_document(pdf_path)
    print(f"    {doc.title} — {doc.page_count} pages, {doc.word_count} words")

    print("\n[2] Chunking...")
    chunks = Chunker().chunk_document(doc)
    print(f"    {len(chunks)} chunks created")

    print("\n[3] Embedding chunks...")
    embedder = Embedder()
    embedded = embedder.embed_chunks(chunks)

    print("\n[4] Building vector store...")
    store   = FAISSStore()
    vectors = np.stack([e.vector for e in embedded])
    ids     = [e.chunk_id for e in embedded]
    store.add(ids, vectors)

    meta_store = MetadataStore("data/docs.db")
    meta_store.insert_chunks([{
        "chunk_id":    c.chunk_id,
        "source_path": c.source_path,
        "title":       c.metadata["title"],
        "file_type":   c.metadata["file_type"],
        "page_num":    c.page_num,
        "chunk_index": c.chunk_index,
        "text":        c.text,
        "token_count": c.token_count,
        "metadata":    c.metadata,
    } for c in chunks])

    # ── Knowledge Graph ───────────────────────────────────────
    graph = build_knowledge_graph(chunks, doc_id)

    print("\n[5] Retrieving relevant chunks...")
    dense  = DenseRetriever(store, embedder)
    bm25   = BM25Retriever()
    bm25.index([{"chunk_id": c.chunk_id, "text": c.text} for c in chunks])
    hybrid = HybridRetriever(dense, bm25)
    results   = hybrid.retrieve(prompt, top_k=5)
    chunk_ids = [r[0] for r in results]
    print(f"    Top {len(chunk_ids)} chunks retrieved")

    # ── Graph-augmented context ───────────────────────────────
    print("\n[6] Augmenting with knowledge graph...")
    kg_retriever  = GraphRetriever(graph)
    graph_context = kg_retriever.get_context_for_query(prompt)
    if graph_context:
        print(f"    Graph context: {graph_context[:80]}...")
    else:
        print("    No graph context found for this query")

    print("\n[7] Generating answer...\n")

    # Inject graph context into the prompt
    messages = build_prompt(prompt, chunk_ids, meta_store)
    if graph_context:
        messages[1]["content"] = graph_context + "\n\n" + messages[1]["content"]

    client = LLMClient()
    print("=" * 60)
    for token in client.stream(messages):
        print(token, end="", flush=True)
    print("\n" + "=" * 60)

    meta_store.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python run.py <pdf_path> <prompt>")
        print('Example: python run.py paper.pdf "What is the main contribution?"')
        sys.exit(1)

    run(sys.argv[1], sys.argv[2])