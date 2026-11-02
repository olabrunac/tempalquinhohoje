"""Prova que o site não cai quando o deploy chega antes da migração.

Simula o pior caso: RUN_MIGRATIONS=false (init_db desligado) e a tabela
`palquinho_presence` ainda não existe, como se a Vercel tivesse subido o código novo
num banco com o schema antigo. A home TEM que continuar respondendo 200 (contador
zerado) e o primeiro voto tem que criar a tabela sozinho — nada de 500 em produção.
"""

import os
import sys
import tempfile
from pathlib import Path

DB = Path(tempfile.gettempdir()) / "tph_sem_migracao_test.db"
if DB.exists():
    DB.unlink()

os.environ["ADMIN_PASSWORD"] = "senha-correta-123"
os.environ["DATABASE_URL"] = f"sqlite:///{DB}"
os.environ["ENVIRONMENT"] = "dev"
os.environ["RUN_MIGRATIONS"] = "false"

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import inspect, text

from app.db import Base, SessionLocal, engine
from app.localtime import today_local
from app.main import app
from app.models import PalquinhoDay

# Schema "antigo": tudo menos a tabela de votos.
Base.metadata.create_all(bind=engine)
with engine.begin() as conn:
    conn.execute(text("DROP TABLE palquinho_presence"))

HOJE = today_local()
with SessionLocal() as db:
    db.add(PalquinhoDay(day=HOJE, has_palquinho=True, is_other_event=False))
    db.commit()

from fastapi.testclient import TestClient

ok = True


def check(nome, cond, extra=""):
    global ok
    ok = ok and bool(cond)
    print("  [%s] %s %s" % ("OK" if cond else "FAIL", nome, extra))


def tem_tabela() -> bool:
    return inspect(engine).has_table("palquinho_presence")


with TestClient(app) as client:  # roda o startup (init_db desligado)
    print("1. schema antigo (sem palquinho_presence) com RUN_MIGRATIONS=false")
    check("tabela de votos ausente", not tem_tabela())
    check("startup não criou nada (init_db desligado)", not tem_tabela())

    print("2. a home não pode cair por causa do contador")
    r = client.get("/api/v1/home")
    check("/home -> 200", r.status_code == 200, f"(status {r.status_code})")
    if r.status_code == 200:
        t = r.json()["today"]
        check("hoje continua SIM", t["has_palquinho"] is True)
        check(
            "contador zerado, sem erro",
            (t["going_count"], t["total_count"]) == (0, 0),
            f"(veio {t['going_count']}/{t['total_count']})",
        )
    check("/today -> 200", client.get("/api/v1/today").status_code == 200)
    check("/days -> 200", client.get("/api/v1/days").status_code == 200)

    print("3. o primeiro voto cria a tabela sozinho")
    voter = "z" * 32
    r = client.put(f"/api/v1/vote/{HOJE.isoformat()}", json={"voter": voter, "going": True})
    check("PUT /vote -> 200", r.status_code == 200, f"(status {r.status_code})")
    if r.status_code == 200:
        check(
            "retorno 1/1",
            (r.json()["going_count"], r.json()["total_count"]) == (1, 1),
            f"(veio {r.json()['going_count']}/{r.json()['total_count']})",
        )
    check("tabela criada sob demanda", tem_tabela())

    print("4. contadores passam a vir do banco")
    t = client.get("/api/v1/home").json()["today"]
    check(
        "1/1 no /home",
        (t["going_count"], t["total_count"]) == (1, 1),
        f"(veio {t['going_count']}/{t['total_count']})",
    )

    print("5. desmarcar o dia continua limpando os votos")
    admin = {"X-Admin-Key": "senha-correta-123"}
    r = client.delete(f"/api/v1/admin/{HOJE.isoformat()}", headers=admin)
    check("DELETE -> 204", r.status_code == 204, f"(status {r.status_code})")
    with SessionLocal() as db:
        n = db.execute(text("SELECT COUNT(*) FROM palquinho_presence")).scalar()
    check("nenhum voto sobrando", n == 0, f"(linhas: {n})")

print()
print("RESULTADO:", "TODOS OS TESTES PASSARAM" if ok else "TEM FALHA")
sys.exit(0 if ok else 1)
