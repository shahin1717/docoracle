# backend/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.logging import setup_logging
from backend.db.database import init_db

from backend.auth.router import router as auth_router
from backend.api.documents import router as documents_router
from backend.api.chat import router as chat_router
from backend.api.graph import router as graph_router
from backend.api.health import router as health_router
from backend.api.users import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(debug=settings.debug)
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(graph_router)
app.include_router(health_router)


@app.get("/", tags=["root"])
def root():
    return {"app": settings.app_name, "status": "running", "docs": "/docs"}