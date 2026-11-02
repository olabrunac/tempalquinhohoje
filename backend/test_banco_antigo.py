"""Reproduz o incidente real do preview (02/11/2026).

O banco do preview tinha um `palquinho_vote` de um protótipo antigo, com outro
formato (`name`, `vote`). Como `create_all` não altera tabela existente, a query
de contagem estourava `UndefinedColumn` e derrubava /days e /home com 500 — a home
ficava com a semana vazia, sem mensagem de erro (o frontend engole o erro do /days).

Duas defesas cobertas aqui:
  1. a tabela nova se chama `palquinho_presence` (não colide com a antiga);
  2. o contador falha em silêncio — nunca derruba a página.

Cenário: RUN_MIGRATIONS=false (deploy antes da migração) + tabela legada presente.
"""

import os
import sys
import tempfile
from pathlib import Path

DB = Path(tempfile.gettempdir()) / "tph_banco_antigo_test.db"
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

# Schema "legado": o banco como estava antes do deploy da feature.
Base.metadata.create_all(bind=engine)
with engine.begin() as conn:
    conn.execute(text("DROP TABLE palquinho_presence"))
    conn.execute(
        text(
            "CREATE TABLE palquinho_vote ("
            " id INTEGER PRIMARY KEY,"
            " day DATE NOT NULL,"
            " name VARCHAR(80),"
            " vote INTEGER,"
            " created_at DATETIME)"
        )
    )
    conn.execute(
        text(
            "INSERT INTO palquinho_vote (day, name, vote) "
            "VALUES (:d, 'fulano', 1)"
        ),
        {"d": today_local().isoformat()},
    )

HOJE = today_local()
FUTURO = HOJE.fromordinal(HOJE.toordinal() + 3)
with SessionLocal() as db:
    db.add_all(
        [
            PalquinhoDay(day=HOJE, has_palquinho=True, is_other_event=False),
            PalquinhoDay(day=FUTURO, has_palquinho=True, is_other_event=False),
        ]
    )
    db.commit()

from fastapi.testclient import TestClient

ok = True


def check(nome, cond, extra=""):
    global ok
    ok = ok and bool(cond)
    print("  [%s] %s %s" % ("OK" if cond else "FAIL", nome, extra))


def tem_tabela(nome: str) -> bool:
    return inspect(engine).has_table(nome)


def colunas(nome: str) -> list[str]:
    return sorted(c["name"] for c in inspect(engine).get_columns(nome))


with TestClient(app) as client:  # init_db desligado (RUN_MIGRATIONS=false)
    print("1. cenário do incidente: palquinho_vote legado, sem palquinho_presence")
    check("tabela legada existe", tem_tabela("palquinho_vote"))
    check("colunas legadas intactas", colunas("palquinho_vote") == ["created_at", "day", "id", "name", "vote"])
    check("tabela nova ainda não existe", not tem_tabela("palquinho_presence"))

    print("2. os endpoints NÃO podem cair por causa da tabela legada")
    r = client.get("/api/v1/days")
    check("/days -> 200", r.status_code == 200, f"(status {r.status_code})")
    check("lista os 2 dias", r.status_code == 200 and len(r.json()) == 2)
    check("/home -> 200", client.get("/api/v1/home").status_code == 200)
    check("/today -> 200", client.get("/api/v1/today").status_code == 200)

    print("3. contador degrada pra zero em vez de estourar")
    t = client.get("/api/v1/home").json()["today"]
    check(
        "hoje com 0/0",
        (t["going_count"], t["total_count"]) == (0, 0),
        f"(veio {t['going_count']}/{t['total_count']})",
    )
    check("hoje continua SIM", t["has_palquinho"] is True)

    print("4. votar cria a tabela nova e funciona")
    voter = "y" * 32
    r = client.put(f"/api/v1/vote/{HOJE.isoformat()}", json={"voter": voter, "going": True})
    check("PUT /vote -> 200", r.status_code == 200, f"(status {r.status_code})")
    check("palquinho_presence criada", tem_tabela("palquinho_presence"))
    if r.status_code == 200:
        check(
            "retorno 1/1",
            (r.json()["going_count"], r.json()["total_count"]) == (1, 1),
            f"(veio {r.json()['going_count']}/{r.json()['total_count']})",
        )

    print("5. a tabela legada fica intacta (nada é apagado)")
    with SessionLocal() as db:
        n = db.execute(text("SELECT COUNT(*) FROM palquinho_vote")).scalar()
    check("voto legado preservado", n == 1, f"(linhas: {n})")
    check("colunas legadas seguem iguais", colunas("palquinho_vote") == ["created_at", "day", "id", "name", "vote"])

    print("6. desmarcar o dia limpa só a tabela nova")
    admin = {"X-Admin-Key": "senha-correta-123"}
    r = client.delete(f"/api/v1/admin/{HOJE.isoformat()}", headers=admin)
    check("DELETE -> 204", r.status_code == 204, f"(status {r.status_code})")
    with SessionLocal() as db:
        n_novo = db.execute(text("SELECT COUNT(*) FROM palquinho_presence")).scalar()
        n_antigo = db.execute(text("SELECT COUNT(*) FROM palquinho_vote")).scalar()
    check("palquinho_presence zerada", n_novo == 0, f"(linhas: {n_novo})")
    check("palquinho_vote legado intocado", n_antigo == 1, f"(linhas: {n_antigo})")

print()
print("RESULTADO:", "TODOS OS TESTES PASSARAM" if ok else "TEM FALHA")
sys.exit(0 if ok else 1)
