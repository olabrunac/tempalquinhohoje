"""Testa os eventos por dia: lista com ordem, limite de 3 e migração da nota antiga."""

import os
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

DB = Path(tempfile.gettempdir()) / "tph_eventos_test.db"
if DB.exists():
    DB.unlink()

os.environ["ADMIN_PASSWORD"] = "senha-correta-123"
os.environ["DATABASE_URL"] = f"sqlite:///{DB}"
os.environ["ENVIRONMENT"] = "dev"

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import create_engine, text

from app.db import Base, SessionLocal, init_db, migrate_day_notes_to_events
from app.main import app
from app.models import PalquinhoDay

init_db()

from fastapi.testclient import TestClient

client = TestClient(app)
SENHA = "senha-correta-123"
ADMIN = {"X-Admin-Key": SENHA}
HOJE = date.today()
D1 = (HOJE + timedelta(days=1)).isoformat()
D2 = (HOJE + timedelta(days=2)).isoformat()

ok = True


def check(nome, cond, extra=""):
    global ok
    ok = ok and bool(cond)
    print("  [%s] %s %s" % ("OK" if cond else "FAIL", nome, extra))


def ev(nota, link=None):
    return {"note": nota, "instagram": link}


print("1. salvar dia com 2 eventos, cada um com seu link")
r = client.put(f"/api/v1/admin/{D1}",
               json={"has_palquinho": True,
                     "events": [ev("14:00 - Churrasco", "https://instagram.com/p/aaa"),
                                ev("19:00 - Palquinho", "https://instagram.com/p/bbb")]},
               headers=ADMIN)
check("PUT -> 200", r.status_code == 200, f"(status {r.status_code})")
body = r.json()
check("2 eventos salvos", len(body["events"]) == 2, f"(veio {len(body.get('events', []))})")
check("ordem preservada",
      [e["note"] for e in body["events"]] == ["14:00 - Churrasco", "19:00 - Palquinho"])
check("links separados",
      [e["instagram"] for e in body["events"]] == ["https://instagram.com/p/aaa",
                                                   "https://instagram.com/p/bbb"])
check("positions 1 e 2", [e["position"] for e in body["events"]] == [1, 2])

print("2. leitura pública devolve os eventos do dia")
r = client.get("/api/v1/days")
dia = next((d for d in r.json() if d["day"] == D1), None)
check("dia aparece em /days", dia is not None)
check("2 eventos em /days", dia and len(dia["events"]) == 2)
check("cada evento com seu link",
      dia and [e["instagram"] for e in dia["events"]] ==
      ["https://instagram.com/p/aaa", "https://instagram.com/p/bbb"])
r = client.get("/api/v1/home")
check("dia em /home com eventos",
      next((d for d in r.json()["days"] if d["day"] == D1), {}).get("events") is not None)
check("campo note sumiu da API", "note" not in r.json()["days"][0])

print("3. editar o dia substitui a lista (apagar evento some do banco)")
r = client.put(f"/api/v1/admin/{D1}",
               json={"has_palquinho": True,
                     "events": [ev("19:00 - Palquinho Principal", "https://instagram.com/p/bbb")]},
               headers=ADMIN)
check("PUT -> 200", r.status_code == 200)
check("so 1 evento depois do edit", len(r.json()["events"]) == 1)
check("nota editada", r.json()["events"][0]["note"] == "19:00 - Palquinho Principal")
with SessionLocal() as db:
    total = db.execute(text("SELECT COUNT(*) FROM palquinho_event WHERE day = :d"),
                       {"d": D1}).scalar()
check("1 linha na tabela (nao duplicou)", total == 1, f"(linhas: {total})")

print("4. limite de 3 eventos por dia")
r = client.put(f"/api/v1/admin/{D1}",
               json={"has_palquinho": True,
                     "events": [ev("a"), ev("b"), ev("c"), ev("d")]},
               headers=ADMIN)
check("4 eventos -> 422", r.status_code == 422, f"(status {r.status_code})")
r = client.put(f"/api/v1/admin/{D2}",
               json={"has_palquinho": True, "events": [ev("a"), ev("b"), ev("c")]},
               headers=ADMIN)
check("3 eventos -> 200", r.status_code == 200, f"(status {r.status_code})")
r = client.put(f"/api/v1/admin/{D2}",
               json={"has_palquinho": True, "events": [ev("a"), ev("b"), ev("c"), ev("d")]},
               headers=ADMIN)
check("4 eventos -> 422", r.status_code == 422, f"(status {r.status_code})")

print("5. evento sem link e evento com nota vazia")
r = client.put(f"/api/v1/admin/{D1}",
               json={"has_palquinho": True,
                     "events": [ev("so uma nota"), ev("   "), ev("com link", "  https://ig.com/x  ")]},
               headers=ADMIN)
check("nota vazia e ignorada", len(r.json()["events"]) == 2,
      f"(veio {len(r.json()['events'])})")
check("link sem espaco em volta", r.json()["events"][1]["instagram"] == "https://ig.com/x")
check("evento sem link fica null", r.json()["events"][0]["instagram"] is None)
r = client.put(f"/api/v1/admin/{D1}", json={"has_palquinho": True, "events": [ev("")]}, headers=ADMIN)
check("nota vazia -> 422", r.status_code == 422, f"(status {r.status_code})")

print("6. dia sem evento (so SIM/NÃO)")
r = client.put(f"/api/v1/admin/{D1}", json={"has_palquinho": False, "events": []}, headers=ADMIN)
check("PUT sem eventos -> 200", r.status_code == 200, f"(status {r.status_code})")
check("events vazio", r.json()["events"] == [])

print("7. remover o dia apaga os eventos junto")
client.put(f"/api/v1/admin/{D1}",
           json={"has_palquinho": True, "events": [ev("x"), ev("y")]}, headers=ADMIN)
r = client.delete(f"/api/v1/admin/{D1}", headers=ADMIN)
check("DELETE -> 204", r.status_code == 204, f"(status {r.status_code})")
with SessionLocal() as db:
    restantes = db.execute(text("SELECT COUNT(*) FROM palquinho_event WHERE day = :d"),
                           {"d": D1}).scalar()
check("eventos do dia apagados", restantes == 0, f"(sobraram {restantes})")

print("8. admin continua exigindo senha")
r = client.put(f"/api/v1/admin/{D1}", json={"has_palquinho": True, "events": []})
check("sem senha -> 401", r.status_code == 401, f"(status {r.status_code})")

print("9. migracao da nota antiga vira eventos (sem link)")
legado = (HOJE + timedelta(days=10)).isoformat()
with SessionLocal() as db:
    # No SQLite de teste a tabela nasce do model novo (sem note). No Postgres de
    # prod a coluna antiga continua lá, então recriamos aqui pra simular o banco real.
    db.execute(text("ALTER TABLE palquinho_day ADD COLUMN note TEXT"))
    db.execute(text("ALTER TABLE palquinho_day ADD COLUMN instagram VARCHAR(300)"))
    db.add(PalquinhoDay(day=date.fromisoformat(legado), has_palquinho=True))
    db.commit()
    db.execute(text(
        "UPDATE palquinho_day SET note = :n WHERE day = :d"
    ), {"n": "[EVENTO] 14:00 - churrasco\n19:00 - palquinho", "d": legado})
    db.commit()

convertidos = migrate_day_notes_to_events()
check("dia legado listado na conversao", legado in convertidos, f"(veio {convertidos})")
check("migracao nao repetida na 2a chamada", legado not in migrate_day_notes_to_events())
with SessionLocal() as db:
    rows = db.execute(
        text("SELECT position, note, instagram FROM palquinho_event WHERE day = :d ORDER BY position"),
        {"d": legado}).fetchall()
check("2 eventos migrados", len(rows) == 2, f"(veio {len(rows)})")
check("marcador [EVENTO] removido",
      [r[1] for r in rows] == ["14:00 - churrasco", "19:00 - palquinho"],
      f"(veio {[r[1] for r in rows]})")
check("migrado sem link", all(r[2] is None for r in rows))
check("positions 1 e 2", [r[0] for r in rows] == [1, 2])

print()
print("RESULTADO:", "TODOS OS TESTES PASSARAM" if ok else "HOUVE FALHAS")
sys.exit(0 if ok else 1)