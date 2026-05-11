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
        context_parts.append(f"--- SOURCE [{i}] ---\nDOC: {source}{page}\nTEXT: {chunk['text']}\n")

    context = "\n\n".join(context_parts)

    system_prompt = (
        "You are CitationBot. YOUR ONLY JOB is to answer questions using the provided context and citing it.\n\n"
        "RULES OF ENGAGEMENT:\n"
        "1. EVERY SINGLE SENTENCE that contains a fact MUST end with a source tag like [1].\n"
        "2. If you find a fact in Source 1 and Source 3, you MUST write: 'The fact is true [1, 3].'\n"
        "3. NEVER use your internal knowledge. If the context doesn't have the info, say 'I cannot find this in the documents [n]' (cite the closest source anyway).\n"
        "4. DO NOT write a bibliography at the end. Only use [n] tags.\n\n"
        "PERFECT EXAMPLE:\n"
        "The quicksort algorithm is efficient [1]. It uses a pivot to partition data [2, 4].\n\n"
        "MATHEMATICAL RULES:\n"
        "1. Use $...$ for inline and $$...$$ for blocks.\n"
        "2. Use \\\\ for row ends in matrices.\n\n"
        "IF YOU DO NOT USE [n] TAGS, YOU FAIL. BE AGGRESSIVE WITH CITATIONS."
    )

    full_system_prompt = (
        f"{system_prompt}\n\n"
        "--- RESEARCH CONTEXT START ---\n"
        f"{context}\n"
        "--- RESEARCH CONTEXT END ---\n\n"
        "CRITICAL RULE: USE ONLY THE CONTEXT ABOVE. DO NOT USE YOUR INTERNAL KNOWLEDGE. "
        "IF YOU USE EXTERNAL INFORMATION, YOU ARE FAILING. "
        "EVERY FACT MUST BE CITED WITH [n]."
    )
    
    messages = [
        {"role": "system", "content": full_system_prompt},
    ]

    if chat_history:
        # Include the last 6 messages to keep context without exceeding context window
        for msg in chat_history[-6:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
    
    user_query_with_rules = (
        "You are in STRIKT CITATION MODE. "
        "Answer the following question using ONLY the provided sources. "
        "Use [n] for every claim.\n\n"
        f"QUESTION: {query}"
    )
    messages.append({"role": "user", "content": user_query_with_rules})

    return messages