import sys
from pathlib import Path

from ai.ingestion import parse_document
from ai.chunker import Chunker
from ai.embedding import Embedder
from ai.vectorstore import FAISSStore, MetadataStore
from ai.retrieval import HybridRetriever, DenseRetriever, BM25Retriever
from ai.generation import LLMClient, build_prompt


def run(pdf_path: str, prompt: str):

    print("\n[1] Parsing document...")
    doc = parse_document(pdf_path)
    print(f"    {doc.title} — {doc.page_count} pages, {doc.word_count} words")

    print("\n[2] Chunking...")
    chunks = Chunker().chunk_document(doc)
    print(f"    {len(chunks)} chunks created")

    print("\n[3] Embedding chunks (Ollama must be running)...")
    embedder = Embedder()
    embedded = embedder.embed_chunks(chunks)

    print("\n[4] Building vector store...")
    store = FAISSStore()
    import numpy as np
    vectors = np.stack([e.vector for e in embedded])
    ids = [e.chunk_id for e in embedded]
    store.add(ids, vectors)

    meta_store = MetadataStore("data/docs.db")
    meta_store.insert_chunks([{
        "chunk_id":   c.chunk_id,
        "source_path": c.source_path,
        "title":      c.metadata["title"],
        "file_type":  c.metadata["file_type"],
        "page_num":   c.page_num,
        "chunk_index": c.chunk_index,
        "text":       c.text,
        "token_count": c.token_count,
        "metadata":   c.metadata,
    } for c in chunks])

    print("\n[5] Retrieving relevant chunks...")
    dense   = DenseRetriever(store, embedder)
    bm25    = BM25Retriever()
    bm25.index([{"chunk_id": c.chunk_id, "text": c.text} for c in chunks])
    hybrid  = HybridRetriever(dense, bm25)
    results = hybrid.retrieve(prompt, top_k=5)
    chunk_ids = [r[0] for r in results]
    print(f"    Top {len(chunk_ids)} chunks retrieved")

    print("\n[6] Generating answer...\n")
    messages = build_prompt(prompt, chunk_ids, meta_store)
    client   = LLMClient()
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