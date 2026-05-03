"""
backend/api/health.py

GET /health — checks if the API is up and if Ollama is reachable.
No auth required — used for monitoring / startup checks.
"""

import requests
import os
from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL       = os.getenv("LLM_MODEL",       "mistral:7b-instruct-q4_0")
EMBED_MODEL      = os.getenv("EMBED_MODEL",      "nomic-embed-text")


def _check_ollama() -> dict:
    """Return status of Ollama and whether required models are loaded."""
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        resp.raise_for_status()
        loaded = [m["name"] for m in resp.json().get("models", [])]
        return {
            "reachable": True,
            "llm_loaded":   LLM_MODEL   in loaded,
            "embed_loaded": EMBED_MODEL in loaded,
            "loaded_models": loaded,
        }
    except Exception as e:
        return {
            "reachable": False,
            "llm_loaded": False,
            "embed_loaded": False,
            "error": str(e),
        }


@router.get("")
def health():
    ollama = _check_ollama()
    ready  = ollama["reachable"] and ollama["llm_loaded"] and ollama["embed_loaded"]
    return {
        "status": "ready" if ready else "degraded",
        "ollama": ollama,
    }