from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import init_db
from .api import palquinho

app = FastAPI(title="temPalquinhoHoje", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(palquinho.router, prefix="/api/v1", tags=["palquinho"])


@app.on_event("startup")
def _startup() -> None:
    """Cria tabelas se necessário. Cold start Neon: schema estável, uma execução rápida."""
    init_db()


@app.get("/api/v1/health")
def health() -> dict:
    return {"status": "ok"}
