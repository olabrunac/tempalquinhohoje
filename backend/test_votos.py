"""Testa a resposta anônima de "você vai?": 1 por navegador, trocável,
contador "12/20 vão" e limpeza quando o admin desmarca o dia."""

import os
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

DB = Path(tempfile.gettempdir()) / "tph_votos_test.db"
if DB.exists():
    DB.unlink()

os.environ["ADMIN_PASSWORD"] = "senha-correta-123"
os.environ["DATABASE_URL"] = f"sqlite:///{DB}"
os.environ["ENVIRONMENT"] = "dev"

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import text

from app.db import SessionLocal, init_db
from app.localtime import today_local
from app.main import app

init_db()

from fastapi.testclient import TestClient

client = TestClient(app)
ADMIN = {"X-Admin-Key": "senha-correta-123"}

HOJE = today_local()
D1 = (HOJE + timedelta(days=2)).isoformat()
D2 = (HOJE + timedelta(days=3)).isoformat()
PASSADO = (HOJE - timedelta(days=1)).isoformat()

# tokens no formato que o navegador gera (UUID sem hífen serve)
V1 = "a" * 32
V2 = "b" * 32
V3 = "c" * 32

ok = True


def check(nome, cond, extra=""):
    global ok
    ok = ok and bool(cond)
    print("  [%s] %s %s" % ("OK" if cond else "FAIL", nome, extra))


def marcar(day, sim=True, other=False):
    return client.put(
        f"/api/v1/admin/{day}",
        json={"has_palquinho": sim, "is_other_event": other, "events": []},
        headers=ADMIN,
    )


def votar(day, voter, going):
    return client.put(f"/api/v1/vote/{day}", json={"voter": voter, "going": going})


def dia_publico(day):
    r = client.get("/api/v1/days")
    return next((d for d in r.json() if d["day"] == day), None)


print("1. dia sem marcação não aceita resposta")
r = votar(D1, V1, True)
check("dia não marcado -> 409", r.status_code == 409, f"(status {r.status_code})")

print("2. marcar os dias de teste")
check("D1 SIM -> 200", marcar(D1).status_code == 200)
check("D2 NÃO -> 200", marcar(D2, sim=False).status_code == 200)

print("3. primeira resposta (vou) conta 1/1")
r = votar(D1, V1, True)
check("PUT -> 200", r.status_code == 200, f"(status {r.status_code})")
body = r.json()
check("going_count 1", body.get("going_count") == 1, f"(veio {body.get('going_count')})")
check("total_count 1", body.get("total_count") == 1, f"(veio {body.get('total_count')})")
check("resposta devolvida", body.get("going") is True)

print("4. responder de novo não duplica (idempotente)")
r = votar(D1, V1, True)
check("continua 1/1", (r.json()["going_count"], r.json()["total_count"]) == (1, 1))

print("5. segundo navegador diz que não -> 1/2")
r = votar(D1, V2, False)
check("1/2 vão", (r.json()["going_count"], r.json()["total_count"]) == (1, 2),
      f"(veio {r.json()['going_count']}/{r.json()['total_count']})")

print("6. trocar de resposta não soma voto novo")
r = votar(D1, V2, True)
check("2/2 vão", (r.json()["going_count"], r.json()["total_count"]) == (2, 2))
r = votar(D1, V2, False)
check("volta pra 1/2 (não 1/3)", (r.json()["going_count"], r.json()["total_count"]) == (1, 2))

print("7. terceiro navegador entra no denominador")
r = votar(D1, V3, False)
check("1/3 vão", (r.json()["going_count"], r.json()["total_count"]) == (1, 3))

print("8. contadores aparecem em /days")
d = dia_publico(D1)
check("D1 em /days", d is not None)
check("1/3 no /days", d and (d["going_count"], d["total_count"]) == (1, 3),
      f"(veio {d and (d['going_count'], d['total_count'])})")

print("9. contadores aparecem em /today (dia de hoje)")
marcar(HOJE.isoformat())
r = votar(HOJE.isoformat(), V1, True)
check("PUT hoje -> 200", r.status_code == 200)
t = client.get("/api/v1/today").json()
check("1/1 no /today", (t["going_count"], t["total_count"]) == (1, 1),
      f"(veio {t['going_count']}/{t['total_count']})")

print("10. dia NÃO (vermelho) e dia de outro rolê não aceitam resposta")
r = votar(D2, V1, True)
check("dia NÃO -> 409", r.status_code == 409, f"(status {r.status_code})")
D3 = (HOJE + timedelta(days=4)).isoformat()
marcar(D3, sim=False, other=True)
r = votar(D3, V1, True)
check("dia de outro rolê -> 409", r.status_code == 409, f"(status {r.status_code})")

print("11. dia passado não aceita resposta")
marcar(PASSADO)
r = votar(PASSADO, V1, True)
check("dia passado -> 409", r.status_code == 409, f"(status {r.status_code})")

print("12. validação de entrada")
check("data inválida -> 422", votar("2026-13-45", V1, True).status_code == 422)
check("data não-iso -> 422", votar("ontem", V1, True).status_code == 422)
check("voter curto -> 422", votar(D1, "abc", True).status_code == 422)
check("voter com espaço -> 422", votar(D1, "abc def ghi", True).status_code == 422)
check("payload sem going -> 422",
      client.put(f"/api/v1/vote/{D1}", json={"voter": V1}).status_code == 422)

print("13. desmarcar o dia apaga as respostas")
r = client.delete(f"/api/v1/admin/{D1}", headers=ADMIN)
check("DELETE -> 204", r.status_code == 204, f"(status {r.status_code})")
with SessionLocal() as db:
    total = db.execute(
        text("SELECT COUNT(*) FROM palquinho_vote WHERE day = :d"), {"d": D1}
    ).scalar()
check("nenhuma resposta no banco", total == 0, f"(linhas: {total})")

print("14. remarcar o dia começa do zero")
marcar(D1)
d = dia_publico(D1)
check("0/0 depois de remarcar", d and (d["going_count"], d["total_count"]) == (0, 0),
      f"(veio {d and (d['going_count'], d['total_count'])})")

print("15. rate limit por IP (por último: esgota o bucket deste teste)")
status_final = None
for _ in range(150):
    r = votar(D1, V1, True)
    status_final = r.status_code
    if status_final == 429:
        break
check("bloqueia depois de muitas respostas", status_final == 429, f"(status {status_final})")

print()
print("RESULTADO:", "TODOS OS TESTES PASSARAM" if ok else "TEM FALHA")
sys.exit(0 if ok else 1)
