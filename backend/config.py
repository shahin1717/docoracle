# backend/config.py
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── App ───────────────────────────────────────────────────────────────────
    app_name: str = "DocOracle"
    debug: bool = False

    # ── Paths ─────────────────────────────────────────────────────────────────
    base_dir: Path = Path(__file__).resolve().parent.parent   # project root
    data_dir: Path = base_dir / "data"
    uploads_dir: Path = data_dir / "uploads"
    faiss_dir: Path = data_dir / "faiss_index"
    graphs_dir: Path = data_dir / "graphs"

    # ── Databases ─────────────────────────────────────────────────────────────
    app_db_url: str = ""          # filled in model_post_init
    docs_db_path: str = ""        # filled in model_post_init

    # ── Auth ──────────────────────────────────────────────────────────────────
    secret_key: str = "CHANGE_ME_IN_PRODUCTION_USE_32_CHAR_SECRET"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24   # 24 hours

    # ── Ollama ────────────────────────────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "mistral:7b-instruct-q4_0"
    embed_model: str = "nomic-embed-text"

    # ── RAG ───────────────────────────────────────────────────────────────────
    chunk_size: int = 512
    chunk_overlap: int = 64
    retrieval_top_k: int = 10       # candidates before reranking
    rerank_top_k: int = 5           # chunks sent to LLM

    # ── CORS ──────────────────────────────────────────────────────────────────
    allowed_origins: list[str] = ["http://localhost:5173"]   # Vite dev server

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    def model_post_init(self, __context) -> None:
        """Ensure all directories exist and set derived paths."""
        for d in (self.data_dir, self.uploads_dir, self.faiss_dir, self.graphs_dir):
            d.mkdir(parents=True, exist_ok=True)

        if not self.app_db_url:
            object.__setattr__(
                self, "app_db_url", f"sqlite:///{self.data_dir / 'app.db'}"
            )
        if not self.docs_db_path:
            object.__setattr__(
                self, "docs_db_path", str(self.data_dir / "docs.db")
            )


# Single shared instance — import this everywhere
settings = Settings()