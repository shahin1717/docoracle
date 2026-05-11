# backend/api/users.py
import logging

import requests
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from pydantic import BaseModel
from fastapi.responses import StreamingResponse
import json
from typing import Generator

from backend.auth.middleware import get_current_user
from backend.auth.models import UserOut, UserUpdateRequest
from backend.config import settings
from backend.db.database import get_db
from backend.db.models import User
from ai.model_manager import LLM_MODELS, get_hardware_info, recommend_models

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
    catalog = [{"id": m[0], "vram": m[1], "ram": m[2], "desc": m[3]} for m in LLM_MODELS]

    hw = get_hardware_info()
    rec = recommend_models(hw)

    return {
        "models":  all_models,
        "current": active,
        "default": settings.llm_model,
        "catalog": catalog,
        "recommended": rec.llm_model,
    }


class PullModelRequest(BaseModel):
    model: str


@router.post("/models/pull")
def pull_model_endpoint(
    body: PullModelRequest,
    current_user: User = Depends(get_current_user),
):
    """Proxy Ollama's /api/pull to stream progress."""
    def _stream() -> Generator[str, None, None]:
        try:
            with requests.post(
                f"{settings.ollama_base_url}/api/pull",
                json={"name": body.model, "stream": True},
                stream=True,
                timeout=600,
            ) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if line:
                        yield f"data: {line.decode('utf-8')}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(_stream(), media_type="text/event-stream")


@router.delete("/models/{model_name:path}")
def delete_model_endpoint(
    model_name: str,
    current_user: User = Depends(get_current_user),
):
    """Delete a model from Ollama."""
    try:
        resp = requests.delete(
            f"{settings.ollama_base_url}/api/delete",
            json={"name": model_name},
            timeout=10,
        )
        resp.raise_for_status()
        return {"status": "ok", "deleted": model_name}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete model: {str(e)}",
        )


import bcrypt

from backend.db.models import User, Document, ChatSession
import os

# ── PATCH /users/me ───────────────────────────────────────────────────────────
@router.patch("/me", response_model=UserOut)
def update_user_profile(
    body: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserOut:
    """
    Update user profile details: username, email, password, or preferred model.
    """
    # 1. Handle Username Update
    if body.username and body.username != current_user.username:
        # Check if username is already taken
        existing = db.query(User).filter(User.username == body.username).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken.",
            )
        current_user.username = body.username

    # 2. Handle Email Update
    if body.email and body.email != current_user.email:
        # Check if email is already registered
        existing = db.query(User).filter(User.email == body.email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered.",
            )
        current_user.email = body.email

    # 3. Handle Password Update
    if body.password:
        hashed = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
        current_user.password_hash = hashed

    # 4. Handle Preferred Model Update
    if body.preferred_model is not None:
        # Pass None to reset to server default
        if body.preferred_model != current_user.preferred_model:
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
                        detail=f"Model '{body.preferred_model}' is not available in Ollama.",
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

    log.info("users: profile updated for %s", current_user.username)
    return UserOut.model_validate(current_user)


# ── DELETE /users/me ──────────────────────────────────────────────────────────
@router.delete("/me")
def delete_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete the current user's account and all their data.
    """
    # Physically delete document files
    for doc in current_user.documents:
        if os.path.exists(doc.file_path):
            try:
                os.remove(doc.file_path)
            except Exception as e:
                log.error("Failed to delete file %s: %s", doc.file_path, e)

    db.delete(current_user)
    db.commit()
    log.warning("users: account deleted for %s", current_user.username)
    return {"status": "ok", "message": "Account deleted successfully"}


# ── DELETE /users/history ─────────────────────────────────────────────────────
@router.delete("/history")
def clear_user_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete all chat sessions and documents for the current user.
    """
    # Physically delete document files
    for doc in current_user.documents:
        if os.path.exists(doc.file_path):
            try:
                os.remove(doc.file_path)
            except Exception as e:
                log.error("Failed to delete file %s: %s", doc.file_path, e)

    # Delete records
    db.query(Document).filter(Document.user_id == current_user.id).delete()
    db.query(ChatSession).filter(ChatSession.user_id == current_user.id).delete()
    db.commit()

    log.info("users: history cleared for %s", current_user.username)
    return {"status": "ok", "message": "History cleared successfully"}