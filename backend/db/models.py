# backend/db/models.py
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, DateTime, ForeignKey, Boolean, Text, JSON
)
from sqlalchemy.orm import relationship

from backend.db.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


# ── User ──────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id              = Column(String, primary_key=True, default=_uuid)
    username        = Column(String(64),  unique=True, nullable=False, index=True)
    email           = Column(String(255), unique=True, nullable=False, index=True)
    password_hash   = Column(String(255), nullable=False)
    is_active       = Column(Boolean, default=True, nullable=False)
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)

    # user-selected LLM — falls back to settings.llm_model if None
    preferred_model = Column(String(128), nullable=True, default=None)

    # one user → many documents
    documents = relationship("Document", back_populates="owner",
                             cascade="all, delete-orphan")

    # one user -> many chat sessions
    chat_sessions = relationship("ChatSession", back_populates="owner",
                                 cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username}>"


# ── Document ──────────────────────────────────────────────────────────────────
class Document(Base):
    __tablename__ = "documents"

    id           = Column(String, primary_key=True, default=_uuid)
    user_id      = Column(String, ForeignKey("users.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    session_id   = Column(String, ForeignKey("chat_sessions.id", ondelete="CASCADE"),
                          nullable=True, index=True)

    filename     = Column(String(255), nullable=False)
    file_type    = Column(String(16),  nullable=False)
    file_path    = Column(String(512), nullable=False)
    file_size    = Column(Integer,     nullable=False)

    status       = Column(String(32), default="pending", nullable=False)
    error_msg    = Column(Text, nullable=True)

    chunk_count  = Column(Integer, default=0, nullable=False)
    page_count   = Column(Integer, default=0, nullable=False)
    kg_ready     = Column(Boolean, default=False, nullable=False)
    kg_status    = Column(String(32), default="none", nullable=False) # none, processing, ready, error

    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at   = Column(DateTime, default=datetime.utcnow,
                          onupdate=datetime.utcnow, nullable=False)

    owner = relationship("User", back_populates="documents")
    session = relationship("ChatSession", back_populates="documents")

    def __repr__(self) -> str:
        return f"<Document id={self.id} filename={self.filename} status={self.status}>"


# ── ChatSession ───────────────────────────────────────────────────────────────
class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id         = Column(String, primary_key=True, default=_uuid)
    user_id    = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title      = Column(String(255), default="New Chat", nullable=False)
    notes      = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    owner    = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<ChatSession id={self.id} title={self.title}>"


# ── ChatMessage ───────────────────────────────────────────────────────────────
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id         = Column(String, primary_key=True, default=_uuid)
    session_id = Column(String, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role       = Column(String(32), nullable=False)  # "user" or "assistant"
    content    = Column(Text, nullable=False)
    sources    = Column(JSON, nullable=True) # List of source metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    session = relationship("ChatSession", back_populates="messages")

    def __repr__(self) -> str:
        return f"<ChatMessage id={self.id} role={self.role}>"