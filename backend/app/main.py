from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from .db import get_db, init_db
from .api import palquinho, visits

app = FastAPI(title="temPalquinhoHoje", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(palquinho.router, prefix="/api/v1", tags=["palquinho"])
app.include_router(visits.router, prefix="/api/v1", tags=["visits"])


@app.on_event("startup")
def _startup() -> None:
    """Cria tabelas se necessário. Cold start Neon: schema estável, uma execução rápida."""
    init_db()


@app.get("/api/v1/health")
def health(db: Session = Depends(get_db)) -> dict:
    """Health com ping no banco — mantém a conexão do Neon aquecida em pingers externos."""
    db.execute(text("SELECT 1"))
    return {"status": "ok", "db": "ok"}


@app.get("/api/cron/warmup")
def warmup(db: Session = Depends(get_db)) -> dict:
    """Warm up: consulta leve pra esquentar a função e segurar conexão do Neon aberta.

    Na Vercel Hobby o cron só roda 1x/dia, então use um pinger externo
    (ex.: UptimeRobot, 5 em 5 min) apontando pra cá. Em planos Pro dá pra
    adicionar via vercel.json: "crons": [{ "path": "/api/cron/warmup", "schedule": "*/5 * * * *" }].
    """
    db.execute(text("SELECT 1"))
    return {"ok": True}
