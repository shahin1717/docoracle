# backend/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.logging import setup_logging
from backend.db.database import init_db

# ── routers ───────────────────────────────────────────────────────────────────
from backend.auth.router import router as auth_router
from backend.api.documents import router as documents_router
from backend.api.chat import router as chat_router
from backend.api.graph import router as graph_router
from backend.api.health import router as health_router


# ── lifespan (startup / shutdown) ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    setup_logging(debug=settings.debug)
    init_db()                          # creates tables if they don't exist
    yield
    # shutdown  (nothing to clean up yet)


# ── app ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",       # Swagger UI
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,   # ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── routes ────────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(graph_router)
app.include_router(health_router)


# ── root ──────────────────────────────────────────────────────────────────────
@app.get("/", tags=["root"])
def root():
    return {"app": settings.app_name, "status": "running", "docs": "/docs"}