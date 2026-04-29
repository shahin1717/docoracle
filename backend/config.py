"""
backend/config.py

Central settings loaded from environment variables / .env file.
Import `settings` anywhere in the app — don't re-read os.getenv directly.

Usage:
    from backend.config import settings
    print(settings.ollama_base_url)
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"   # docoracle/.env


class Settings(BaseSettings):
    # --- Database ---
    db_user:     str = "shahin_docoracle"
    db_password: str = "docoracle123"
    db_host:     str = "localhost"
    db_port:     int = 5432
    db_name:     str = "shahin_docoracle"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    # --- JWT ---
    secret_key:                    str = "dev_secret_change_in_production"
    algorithm:                     str = "HS256"
    access_token_expire_minutes:   int = 60

    # --- Ollama ---
    ollama_base_url: str = "http://localhost:11434"
    llm_model:       str = "mistral:7b-instruct-q4_0"
    embed_model:     str = "nomic-embed-text"

    # --- Upload limits ---
    max_upload_mb: int = 50

    # --- App ---
    debug: bool = False

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()