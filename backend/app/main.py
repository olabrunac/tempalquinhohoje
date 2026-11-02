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
    # VERCEL_ENV é do deployment ("production" | "preview"), não do .env do projeto.
    # Importante: o preview também roda com ENVIRONMENT=prod, então IS_PROD sozinho
    # bloquearia justamente onde precisamos do diagnóstico.
    if IS_PROD and os.getenv("VERCEL_ENV") != "preview":
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

    # Colunas reais de cada tabela: é aqui que "coluna faltando" aparece (o schema
    # do banco pode estar mais velho que o código que está rodando).
    colunas = {}
    for nome in ("palquinho_day", "palquinho_event", "palquinho_suggestion", "palquinho_vote"):
        try:
            colunas[nome] = sorted(c["name"] for c in inspect(engine).get_columns(nome))
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            colunas[nome] = f"ERRO: {type(exc).__name__}: {str(exc)[:200]}"

    # Reproduz o endpoint que está estourando e guarda a mensagem do banco.
    def reproduz(fn):
        try:
            resultado = fn()
            if callable(resultado):
                return {"ok": "funcao_retornada", "tipo": type(resultado).__name__}
            return {"ok": resultado}
        except Exception as exc:  # noqa: BLE001
            import traceback

            db.rollback()
            frames = [f for f in traceback.format_exc().strip().splitlines() if f.strip()]
            return {
                "erro": f"{type(exc).__name__}: {str(exc)[:400]}",
                "ultimo_frame": frames[-2].strip() if len(frames) > 1 else None,
            }

    def _conta_dias() -> int:
        from app import models

        return db.query(models.PalquinhoDay).count()

    def _conta_eventos() -> int:
        from app import models

        return db.query(models.PalquinhoEvent).count()

    def _roda_days():
        return len(palquinho.list_days(db))

    def _roda_home():
        from fastapi import Response

        return palquinho.get_home(Response(), db).model_dump(mode="json")["days"].__len__()

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
        "colunas": colunas,
        "linhas": {
            "palquinho_day": conta("SELECT COUNT(*) FROM palquinho_day"),
            "palquinho_event": conta("SELECT COUNT(*) FROM palquinho_event"),
            "palquinho_suggestion": conta("SELECT COUNT(*) FROM palquinho_suggestion"),
            "palquinho_vote": conta("SELECT COUNT(*) FROM palquinho_vote"),
        },
        "endpoints": {
            "/days": reproduz(_roda_days),
            "/home": reproduz(_roda_home),
            "query_dias": reproduz(_conta_dias),
            "query_eventos": reproduz(_conta_eventos),
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
