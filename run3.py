import sys
from pathlib import Path

import numpy as np

from ai.ingestion import parse_document
from ai.chunker import Chunker
from ai.embedding import Embedder
from ai.vectorstore import FAISSStore, MetadataStore
from ai.retrieval import HybridRetriever, DenseRetriever, BM25Retriever
from ai.generation import LLMClient, build_prompt


def run(pdf_paths: list[str], prompt: str):

    embedder  = Embedder()
    store     = FAISSStore()
    meta_store = MetadataStore("data/docs.db")
    all_chunks = []

    # ── ingest all documents ──────────────────────────────────
    for pdf_path in pdf_paths:
        print(f"\n📄 Processing: {pdf_path}")

        print("  [1] Parsing...")
        doc = parse_document(pdf_path)
        print(f"      {doc.title} — {doc.page_count} pages, {doc.word_count} words")

        print("  [2] Chunking...")
        chunks = Chunker(chunk_size=1024, overlap=128).chunk_document(doc)
        print(f"      {len(chunks)} chunks created")

        print("  [3] Embedding...")
        embedded = embedder.embed_chunks(chunks)

        vectors = np.stack([e.vector for e in embedded])
        ids     = [e.chunk_id for e in embedded]
        store.add(ids, vectors)

        meta_store.insert_chunks([{
            "chunk_id":    e.chunk_id,
            "source_path": e.chunk.source_path,
            "title":       e.chunk.metadata["title"],
            "file_type":   e.chunk.metadata["file_type"],
            "page_num":    e.chunk.page_num,
            "chunk_index": e.chunk.chunk_index,
            "text":        e.chunk.text,
            "token_count": e.chunk.token_count,
            "metadata":    e.chunk.metadata,
        } for e in embedded])

        all_chunks.extend(chunks)
        print(f"      ✓ done")

    # ── retrieve across all docs ──────────────────────────────
    print(f"\n[Retrieval] Searching across {len(pdf_paths)} documents...")
    dense  = DenseRetriever(store, embedder)
    bm25   = BM25Retriever()
    bm25.index([{"chunk_id": c.chunk_id, "text": c.text} for c in all_chunks])
    hybrid = HybridRetriever(dense, bm25)
    results   = hybrid.retrieve(prompt, top_k=15)
    chunk_ids = [r[0] for r in results]
    print(f"    Top {len(chunk_ids)} chunks retrieved")

    # ── generate ──────────────────────────────────────────────
    print("\n[Answer]\n")
    messages = build_prompt(prompt, chunk_ids, meta_store)
    client   = LLMClient()
    print("=" * 60)
    for token in client.stream(messages):
        print(token, end="", flush=True)
    print("\n" + "=" * 60)

    # ── sources ───────────────────────────────────────────────
    print("\n📚 Sources:\n")
    source_chunks = meta_store.get_chunks(chunk_ids)
    for i, chunk in enumerate(source_chunks, 1):
        print(f"  [{i}] {chunk['title']} — page {chunk['page_num'] or 'N/A'}")
        print(f"       \"{chunk['text'][:100].strip()}...\"")

    meta_store.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python run.py <pdf1> <pdf2> ... <prompt>")
        print('Example: python run.py doc1.pdf doc2.pdf "What is entropy?"')
        sys.exit(1)

    # last argument is the prompt, everything before is files
    *paths, query = sys.argv[1:]
    run(paths, query)