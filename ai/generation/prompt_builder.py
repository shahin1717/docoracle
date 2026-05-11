from ai.vectorstore.metadata_store import MetadataStore


def build_prompt(query: str, chunk_ids: list[str], metadata_store: MetadataStore, chat_history: list[dict] = None) -> list[dict]:
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
        "You are a helpful expert assistant. Use the provided context as your primary source.\n\n"
        "STYLE & STRUCTURE RULES:\n"
        "1. Use Markdown headers (e.g., ### Step 1) for a clear structure.\n"
        "2. Use emojis (👉, ✅, 💡) to highlight key steps.\n"
        "3. Use separators (---) between major sections.\n\n"
        "STRICT MATHEMATICAL RULES:\n"
        "1. ALWAYS use LaTeX. NEVER use plain text math.\n"
        "2. DELIMITERS: Use $...$ for inline and $$...$$ for blocks.\n"
        "3. MATRICES: Use \\begin{pmatrix} ... \\end{pmatrix}.\n"
        "4. ROW SEPARATION: You MUST use exactly two backslashes (\\\\) to end a row. Repeat: Use \\\\ between every row. A single \\ will fail.\n"
        "5. BLOCK MATH: Put all matrices on a new line with $$ above and below.\n\n"
        "TEMPLATE EXAMPLE:\n"
        "### Step 1 — The Matrix\n"
        "👉 The matrix $A$ is:\n\n"
        "$$A = \\begin{pmatrix} 1 & 2 \\\\ 3 & 4 \\end{pmatrix}$$\n\n"
        "\n\n"
        "Add little space between lines to make it readable."
        "Your goal is a beautiful, professional study guide. Cite [1], [2] etc."
    )

    user_message = f"Context:\n{context}\n\nQuestion: {query}"

    messages = [
        {"role": "system", "content": system_prompt},
    ]

    if chat_history:
        # Include the last 6 messages to keep context without exceeding context window
        for msg in chat_history[-6:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
    
    messages.append({"role": "user", "content": user_message})

    return messages