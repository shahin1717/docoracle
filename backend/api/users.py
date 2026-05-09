# backend/api/users.py
import logging

import requests
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth.middleware import get_current_user
from backend.auth.models import UserOut, UserUpdateRequest
from backend.config import settings
from backend.db.database import get_db
from backend.db.models import User

router = APIRouter(prefix="/users", tags=["users"])
log = logging.getLogger(__name__)


# ── GET /users/models ─────────────────────────────────────────────────────────
@router.get("/models")
def list_available_models(
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Returns all models currently pulled in Ollama.
    Frontend uses this to populate the model dropdown.

    Response:
        {
            "models": ["mistral:7b-instruct-q4_0", "llama3:8b", ...],
            "current": "mistral:7b-instruct-q4_0",   # user's active model
            "default": "mistral:7b-instruct-q4_0"    # server default
        }
    """
    try:
        resp = requests.get(
            f"{settings.ollama_base_url}/api/tags",
            timeout=3,
        )
        resp.raise_for_status()
        all_models = [m["name"] for m in resp.json().get("models", [])]
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ollama is not reachable. Make sure it is running.",
        )

    active = current_user.preferred_model or settings.llm_model

    return {
        "models":  all_models,
        "current": active,
        "default": settings.llm_model,
    }


# ── PATCH /users/me ───────────────────────────────────────────────────────────
@router.patch("/me", response_model=UserOut)
def update_preferences(
    body: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserOut:
    """
    Save the user's preferred model.
    Pass preferred_model: null to reset to server default.
    """
    if body.preferred_model is not None:
        # validate the model actually exists in Ollama
        try:
            resp = requests.get(
                f"{settings.ollama_base_url}/api/tags",
                timeout=3,
            )
            available = [m["name"] for m in resp.json().get("models", [])]
            if body.preferred_model not in available:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Model '{body.preferred_model}' is not available in Ollama. "
                           f"Run: ollama pull {body.preferred_model}",
                )
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cannot reach Ollama to validate model.",
            )

    current_user.preferred_model = body.preferred_model
    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    log.info(
        "users: %s set preferred_model → %s",
        current_user.username,
        current_user.preferred_model or "default",
    )
    return UserOut.model_validate(current_user)