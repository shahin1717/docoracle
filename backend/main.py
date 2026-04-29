"""
backend/main.py

FastAPI application entry point.

Start the server:
    uvicorn backend.main:app --reload --port 8000

API docs available at:
    http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.db.database import init_db
from backend.logging import setup_logging

# --- Routers ---
from backend.auth.router   import router as auth_router
from backend.api.health    import router as health_router
from backend.api.documents import router as documents_router
from backend.api.chat      import router as chat_router
from backend.api.graph     import router as graph_router

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="DocOracle API",
    description="Local, API-free NotebookLM clone — RAG over your own documents.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS — allow the Vite dev server (port 5173) during development
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev
        "http://localhost:3000",   # alternative
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Startup — create DB tables if they don't exist yet
# ---------------------------------------------------------------------------
@app.on_event("startup")
def on_startup():
    setup_logging(debug=settings.debug)
    init_db()

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth_router)
app.include_router(health_router)
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(graph_router)

# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------
@app.get("/", tags=["root"])
def root():
    return {
        "app":     "DocOracle",
        "version": "0.1.0",
        "docs":    "/docs",
    }