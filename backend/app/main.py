from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from .db import get_db, init_db
from .api import palquinho
from .settings import IS_PROD

# Em produção, /docs e /openapi.json ficam desligados: publicar a schema ajuda
# quem quiser mapear as rotas (inclusive as de admin) sem precisar tentar senha.
app = FastAPI(
    title="temPalquinhoHoje",
    version="0.1.0",
    docs_url=None if IS_PROD else "/docs",
    redoc_url=None if IS_PROD else "/redoc",
    openapi_url=None if IS_PROD else "/openapi.json",
)

# allow_origins=["*"] + allow_credentials=True é uma combinação que o navegador
# rejeita (e que a spec proíbe). O site é público e não usa cookie de sessão, então
# usamos wildcard sem credenciais — é a configuração correta aqui.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Admin-Key"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Headers básicos de hardening em toda resposta da API."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    # a API só devolve JSON; ninguém deve conseguir embutir num <iframe>
    response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
    return response

app.include_router(palquinho.router, prefix="/api/v1", tags=["palquinho"])


@app.on_event("startup")
def _startup() -> None:
    """Cria tabelas se necessário. Cold start Neon: schema estável, uma execução rápida."""
    init_db()


@app.get("/api/v1/health")
def health(db: Session = Depends(get_db)) -> dict:
    """Health com ping no banco. Também serve como pinger externo do Neon."""
    db.execute(text("SELECT 1"))
    return {"status": "ok", "db": "ok"}


# Warmup desativado por padrão: mantém o compute do Neon sempre ligado e consome
# os 100 CU-hours/mês do plano Free. O scale-to-zero do Neon já resolve — a primeira
# visita após 5 min parado custa ~0,3-0,5s a mais, imperceptível pro usuário.
#
# Se algum dia precisar, descomente o endpoint abaixo e aponte um pinger externo
# (ex.: UptimeRobot) pra cá. Prefira intervalo grande (15-30 min) pra não queimar cota.
#
# @app.get("/api/cron/warmup")
# def warmup(db: Session = Depends(get_db)) -> dict:
#     """Ping leve no banco: esquenta a função e segura a conexão do Neon aberta."""
#     db.execute(text("SELECT 1"))
#     return {"ok": True}
