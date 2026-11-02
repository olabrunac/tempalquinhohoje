import os
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from .db import engine, get_db, init_db
from .api import palquinho
from .localtime import today_local
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


@app.get("/api/v1/debug")
def debug(db: Session = Depends(get_db)) -> dict:
    """Diagnóstico de ambiente — SÓ existe em preview/development.

    Serve pra responder "o preview está vendo o mesmo banco?" sem precisar abrir
    o dashboard: mostra host/nome do banco (nunca usuário/senha), quais tabelas
    existem e quantas linhas tem em cada uma. Em produção responde 404, então não
    vira superfície pública.
    """
    if IS_PROD or os.getenv("VERCEL_ENV") == "production":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    # Cada passo isolado: se uma tabela não existir, devolve o erro só daquele item
    # em vez de um 500 seco (que é justamente o que queremos diagnosticar).
    def conta(sql: str):
        try:
            return db.execute(text(sql)).scalar()
        except Exception as exc:  # noqa: BLE001 — é diagnóstico, queremos a mensagem
            db.rollback()
            return f"ERRO: {type(exc).__name__}: {str(exc)[:200]}"

    try:
        tabelas = sorted(inspect(engine).get_table_names())
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        tabelas = f"ERRO: {type(exc).__name__}: {str(exc)[:200]}"

    return {
        "vercel_env": os.getenv("VERCEL_ENV", "local"),
        "environment": os.getenv("ENVIRONMENT", "dev"),
        "run_migrations": os.getenv("RUN_MIGRATIONS"),
        "hoje_local": today_local().isoformat(),
        "banco": {
            "driver": engine.url.get_backend_name(),
            "host": engine.url.host,          # sem usuário nem senha
            "nome": engine.url.database,
        },
        "tabelas": tabelas,
        "linhas": {
            "palquinho_day": conta("SELECT COUNT(*) FROM palquinho_day"),
            "palquinho_event": conta("SELECT COUNT(*) FROM palquinho_event"),
            "palquinho_suggestion": conta("SELECT COUNT(*) FROM palquinho_suggestion"),
            "palquinho_vote": conta("SELECT COUNT(*) FROM palquinho_vote"),
        },
        "dias": {
            "primeiro": conta("SELECT MIN(day) FROM palquinho_day"),
            "ultimo": conta("SELECT MAX(day) FROM palquinho_day"),
        },
    }


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
