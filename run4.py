import sys
from pathlib import Path
import numpy as np

from ai.model_manager import select_model_interactive
from ai.ingestion import parse_document
from ai.chunker import Chunker
from ai.embedding import Embedder
from ai.vectorstore import FAISSStore, MetadataStore
from ai.retrieval import HybridRetriever, DenseRetriever, BM25Retriever
from ai.generation import LLMClient, build_prompt


def run(pdf_paths: list[str], prompt: str):

    # ── model selection ───────────────────────────────────────
    rec      = select_model_interactive()
    embedder = Embedder(
        model=rec.embed_model,
        ollama_url="http://localhost:11434/api/embeddings"
    )
    store      = FAISSStore()
    meta_store = MetadataStore("data/docs.db")
    all_chunks = []

    for pdf_path in pdf_paths:
        print(f"\n📄 {pdf_path}")
        doc    = parse_document(pdf_path)
        chunks = Chunker(chunk_size=1024, overlap=128).chunk_document(doc)
        print(f"   {doc.page_count} pages → {len(chunks)} chunks")

        embedded = embedder.embed_chunks(chunks)
        vectors  = np.stack([e.vector for e in embedded])
        store.add([e.chunk_id for e in embedded], vectors)

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

    dense  = DenseRetriever(store, embedder)
    bm25   = BM25Retriever()
    bm25.index([{"chunk_id": c.chunk_id, "text": c.text} for c in all_chunks])
    hybrid = HybridRetriever(dense, bm25)
    results   = hybrid.retrieve(prompt, top_k=15)
    chunk_ids = [r[0] for r in results]

    messages = build_prompt(prompt, chunk_ids, meta_store)
    client   = LLMClient(
        model=rec.llm_model,
        ollama_url="http://localhost:11434/api/chat"
    )

    print("=" * 55)
    for token in client.stream(messages):
        print(token, end="", flush=True)
    print("\n" + "=" * 55)

    print("\n📚 Sources:")
    for i, chunk in enumerate(meta_store.get_chunks(chunk_ids), 1):
        print(f"  [{i}] {chunk['title']} — page {chunk['page_num'] or 'N/A'}")

    meta_store.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python run.py <pdf1> <pdf2> ... <prompt>")
        sys.exit(1)
    *paths, query = sys.argv[1:]
    run(paths, query)