# backend/api/health.py
import logging

import requests
from fastapi import APIRouter

from backend.config import settings

router = APIRouter(prefix="/health", tags=["health"])
log = logging.getLogger(__name__)


@router.get("")
def health_check() -> dict:
    """
    GET /health

    Returns:
        - api:    always "ok"
        - ollama: "ok" | "unavailable"
        - llm:    model name + loaded status
        - embed:  embed model name + loaded status
    """
    ollama_ok   = False
    llm_loaded  = False
    embed_loaded = False

    try:
        # ── check Ollama is running ───────────────────────────────────────────
        resp = requests.get(
            f"{settings.ollama_base_url}/api/tags",
            timeout=3,
        )
        if resp.status_code == 200:
            ollama_ok = True
            loaded_models = {m["name"] for m in resp.json().get("models", [])}
            llm_loaded   = settings.llm_model   in loaded_models
            embed_loaded = settings.embed_model in loaded_models

    except Exception:
        log.warning("health: Ollama unreachable at %s", settings.ollama_base_url)

    return {
        "api":    "ok",
        "ollama": "ok" if ollama_ok else "unavailable",
        "llm": {
            "model":  settings.llm_model,
            "loaded": llm_loaded,
        },
        "embed": {
            "model":  settings.embed_model,
            "loaded": embed_loaded,
        },
    }