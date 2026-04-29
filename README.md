docoracle/
├── ai/
│   ├── __init__.py
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── base_parser.py       # ParsedDocument dataclass + BaseParser ABC
│   │   ├── pdf_parser.py        # PyMuPDF, page-by-page extraction
│   │   ├── docx_parser.py       # python-docx, heading sections + tables
│   │   ├── pptx_parser.py       # python-pptx, slides + speaker notes
│   │   ├── md_parser.py         # pure Python, strips markdown syntax
│   │   └── router.py            # parse_document(path) — auto-detects type
│   ├── chunker/
│   │   ├── __init__.py
│   │   └── chunker.py           # Chunker(chunk_size=512, overlap=64), Chunk dataclass
│   ├── embedding/
│   │   ├── __init__.py
│   │   └── embedder.py          # Embedder — calls Ollama /api/embeddings, returns EmbeddedChunk
│   ├── vectorstore/
│   │   ├── __init__.py
│   │   ├── faiss_store.py       # FAISSStore — IndexFlatIP, cosine similarity
│   │   └── metadata_store.py    # MetadataStore — SQLite, chunk text + metadata
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── dense_retriever.py   # DenseRetriever — FAISS cosine search
│   │   ├── bm25_retriever.py    # BM25Retriever — pure Python keyword search
│   │   ├── hybrid_retriever.py  # HybridRetriever — RRF score fusion
│   │   └── reranker.py          # Reranker — embedding cosine reranking
│   └── generation/
│       ├── __init__.py
│       ├── llm_client.py        # LLMClient — Ollama /api/chat, blocking + streaming
│       └── prompt_builder.py    # build_prompt(query, chunk_ids, store) → messages list
│
├── knowledge_graph/
│   ├── __init__.py
│   ├── entity_extractor.py      # EntityExtractor — capitalized phrases, technical terms, quoted terms
│   ├── relation_extractor.py    # RelationExtractor — rule-based (subject, relation, object) triples
│   ├── graph_builder.py         # GraphBuilder — NetworkX DiGraph from entities + triples
│   ├── graph_store.py           # GraphStore — save/load graph JSON per doc
│   ├── graph_retriever.py       # GraphRetriever — context for query, subgraph, path finding
│   ├── graph_exporter.py        # GraphExporter — frontend JSON, GEXF, CSV
│   └── tests/
│       └── test_knowledge_graph.py
│
├── backend/
│   ├── main.py                  # FastAPI app, router registration
│   ├── config.py                # env vars, settings (pydantic BaseSettings)
│   ├── logging.py               # structured logging setup
│   ├── auth/
│   │   ├── router.py            # POST /auth/register, /auth/login, /auth/logout
│   │   ├── jwt_handler.py       # create/verify JWT tokens (python-jose)
│   │   ├── middleware.py        # protect routes, extract current user
│   │   └── models.py            # User pydantic request/response models
│   ├── api/
│   │   ├── documents.py         # POST /documents/upload, GET /documents, DELETE /documents/{id}
│   │   ├── chat.py              # POST /chat/query — SSE streaming response
│   │   ├── graph.py             # GET /graph/{doc_id} — returns KG JSON for frontend
│   │   └── health.py            # GET /health — model status check
│   ├── services/
│   │   ├── ingest_service.py    # orchestrates ai/ pipeline on upload
│   │   ├── query_service.py     # orchestrates retrieval + generation
│   │   └── kg_service.py        # triggers KG build, serves graph data
│   └── db/
│       ├── database.py          # SQLAlchemy engine, session, Base
│       └── models.py            # User, Document DB table models
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Landing.jsx      # home / marketing page
│   │   │   ├── Login.jsx        # login form
│   │   │   ├── Register.jsx     # register form
│   │   │   └── App.jsx          # main app layout (protected route)
│   │   ├── components/
│   │   │   ├── DocumentSidebar.jsx   # upload + list documents
│   │   │   ├── ChatPanel.jsx         # chat input + streaming message history
│   │   │   ├── CitationCard.jsx      # source highlight on answer
│   │   │   └── GraphViewer.jsx       # react-force-graph knowledge graph viz
│   │   ├── api/
│   │   │   └── client.js        # all fetch/axios calls in one place
│   │   ├── context/
│   │   │   └── AuthContext.jsx  # global auth state (token, user)
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
│
├── data/
│   ├── app.db                   # SQLite — users, documents (SQLAlchemy)
│   ├── docs.db                  # SQLite — chunks + metadata (MetadataStore)
│   ├── faiss_index/             # FAISS vector index files
│   ├── graphs/                  # per-doc knowledge graph JSON
│   └── uploads/                 # raw uploaded files
│
├── tests/
│   ├── test_ingestion.py        # 21 tests ✅
│   ├── test_chunker.py          # 8 tests ✅
│   ├── test_embedding.py        # 7 tests ✅
│   └── test_ai_full.py          # 22 tests ✅
│
├── paper.pdf
├── run.py
├── requirements.txt
└── README.md