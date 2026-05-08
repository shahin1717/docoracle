from ai.vectorstore.metadata_store import MetadataStore


def build_prompt(query: str, chunk_ids: list[str], metadata_store: MetadataStore) -> list[dict]:
    """
    Assembles the message list to send to Ollama.
    Returns OpenAI-style messages: [system, user].
    """
    chunks = metadata_store.get_chunks(chunk_ids)

    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk.get("title") or chunk["source_path"]
        page = f", page {chunk['page_num']}" if chunk["page_num"] else ""
        context_parts.append(f"[{i}] (source: {source}{page})\n{chunk['text']}")

    context = "\n\n".join(context_parts)

    system_prompt = (
        "You are a helpful expert assistant. "
        "Use the provided context as your primary source. "
        "You are given context extracted from a document. "
        "Answer the question thoroughly and in detail using the context. "
        "You may use your own knowledge to explain or clarify concepts from the context. "
        "But not to hallucinate new facts. "
        "Always cite [1], [2] etc. when directly referencing a chunk. "
        "Give clear, complete answers."

    )

    user_message = f"Context:\n{context}\n\nQuestion: {query}"

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_message},
    ]