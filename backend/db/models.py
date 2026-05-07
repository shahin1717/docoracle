# backend/db/models.py
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, DateTime, ForeignKey, Boolean, Text
)
from sqlalchemy.orm import relationship

from backend.db.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


# ── User ──────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id           = Column(String, primary_key=True, default=_uuid)
    username     = Column(String(64),  unique=True, nullable=False, index=True)
    email        = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active    = Column(Boolean, default=True, nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False)

    # one user → many documents
    documents = relationship("Document", back_populates="owner",
                             cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username}>"


# ── Document ──────────────────────────────────────────────────────────────────
class Document(Base):
    __tablename__ = "documents"

    id           = Column(String, primary_key=True, default=_uuid)
    user_id      = Column(String, ForeignKey("users.id", ondelete="CASCADE"),
                          nullable=False, index=True)

    filename     = Column(String(255), nullable=False)   # original file name
    file_type    = Column(String(16),  nullable=False)   # pdf / docx / pptx / md
    file_path    = Column(String(512), nullable=False)   # absolute path on disk
    file_size    = Column(Integer,     nullable=False)   # bytes

    # ingestion state
    status       = Column(String(32), default="pending", nullable=False)
    # pending → processing → ready | failed
    error_msg    = Column(Text, nullable=True)

    # counts populated after ingestion
    chunk_count  = Column(Integer, default=0, nullable=False)
    page_count   = Column(Integer, default=0, nullable=False)

    # knowledge graph built?
    kg_ready     = Column(Boolean, default=False, nullable=False)

    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at   = Column(DateTime, default=datetime.utcnow,
                          onupdate=datetime.utcnow, nullable=False)

    # relationship back to owner
    owner = relationship("User", back_populates="documents")

    def __repr__(self) -> str:
        return f"<Document id={self.id} filename={self.filename} status={self.status}>"