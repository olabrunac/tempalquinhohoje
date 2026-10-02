"""Testa as proteções novas: rate limit do admin, rate limit de sugestão,
limites de tamanho e headers de segurança."""

import os
import tempfile

os.environ["ADMIN_PASSWORD"] = "senha-correta-123"
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.gettempdir()}/tph_test.db"
os.environ["ENVIRONMENT"] = "dev"

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient

from app.main import app
from app.db import init_db

init_db()  # cria o schema no sqlite de teste

client = TestClient(app)
SENHA = "senha-correta-123"
IP = "1.2.3.4"

ok = True


def check(nome, cond, extra=""):
    global ok
    ok = ok and bool(cond)
    print("  [%s] %s %s" % ("OK" if cond else "FAIL", nome, extra))


print("1. admin: senha errada e senha certa")
r = client.put("/api/v1/admin/2026-01-01", json={"has_palquinho": True},
               headers={"X-Admin-Key": "errada", "x-forwarded-for": IP})
check("senha errada -> 401", r.status_code == 401, f"(status {r.status_code})")
r = client.put("/api/v1/admin/2026-01-01", json={"has_palquinho": True},
               headers={"X-Admin-Key": SENHA, "x-forwarded-for": IP})
check("senha certa -> 200", r.status_code == 200, f"(status {r.status_code})")
r = client.put("/api/v1/admin/2026-01-01", json={"has_palquinho": True},
               headers={"x-forwarded-for": IP})
check("sem header -> 401", r.status_code == 401, f"(status {r.status_code})")

print("2. rate limit do admin (20 req/5min por IP)")
ip2 = "9.9.9.9"
statuses = []
for i in range(25):
    r = client.get("/api/v1/admin/dashboard",
                   headers={"X-Admin-Key": "errada", "x-forwarded-for": ip2})
    statuses.append(r.status_code)
check("primeiras 20 -> 401", all(s == 401 for s in statuses[:20]))
check("21+ -> 429", all(s == 429 for s in statuses[20:]),
      f"(statuses 21-25: {statuses[20:]})")
r = client.get("/api/v1/admin/dashboard",
               headers={"X-Admin-Key": "errada", "x-forwarded-for": ip2})
check("429 tem Retry-After", "Retry-After" in r.headers, f"({r.headers.get('Retry-After')}s)")
check("IP diferente nao e afetado",
      client.get("/api/v1/admin/dashboard",
                 headers={"X-Admin-Key": "errada", "x-forwarded-for": "8.8.8.8"}).status_code == 401)
check("login certo nao e penalizado apos limite de outro IP",
      client.get("/api/v1/admin/dashboard",
                 headers={"X-Admin-Key": SENHA, "x-forwarded-for": "7.7.7.7"}).status_code == 200)

print("3. rate limit de sugestao (5/hora por IP)")
ip3 = "5.5.5.5"
codes = []
for i in range(8):
    r = client.post("/api/v1/suggestions",
                    json={"day": "2026-02-02", "organizer": f"ana {i}"},
                    headers={"x-forwarded-for": ip3})
    codes.append(r.status_code)
check("primeiras 5 -> 201", all(c == 201 for c in codes[:5]), f"({codes[:5]})")
check("6+ -> 429", all(c == 429 for c in codes[5:]), f"({codes[5:]})")

print("4. limites de tamanho")
r = client.post("/api/v1/suggestions",
                json={"day": "2026-02-03", "organizer": "x" * 5000},
                headers={"x-forwarded-for": "4.4.4.4"})
check("organizer gigante -> 422", r.status_code == 422, f"(status {r.status_code})")
r = client.post("/api/v1/suggestions",
                json={"day": "2026-02-03", "organizer": ""},
                headers={"x-forwarded-for": "4.4.4.4"})
check("organizer vazio -> 422", r.status_code == 422, f"(status {r.status_code})")
r = client.put("/api/v1/admin/2026-01-02",
               json={"has_palquoting": True},
               headers={"X-Admin-Key": SENHA, "x-forwarded-for": "3.3.3.3"})
check("payload invalido -> 422", r.status_code == 422, f"(status {r.status_code})")

print("5. rotas publicas continuam funcionando")
check("GET /today -> 200", client.get("/api/v1/today").status_code == 200)
check("GET /home -> 200", client.get("/api/v1/home").status_code == 200)
check("GET /days -> 200", client.get("/api/v1/days").status_code == 200)
check("GET /health -> 200", client.get("/api/v1/health").status_code == 200)
check("admin sem senha -> 401",
      client.get("/api/v1/admin/dashboard", headers={"x-forwarded-for": "6.6.6.6"}).status_code == 401)

print("6. headers de seguranca")
r = client.get("/api/v1/today")
for h, v in [("x-content-type-options", "nosniff"),
             ("x-frame-options", "DENY"),
             ("referrer-policy", "no-referrer"),
             ("content-security-policy", "frame-ancestors 'none'")]:
    check(f"{h}", r.headers.get(h) == v, f"(valor: {r.headers.get(h)})")
check("permissions-policy presente", "permissions-policy" in {k.lower() for k in r.headers})

print("7. docs ligado em dev (como esperado)")
check("/docs -> 200 em dev", client.get("/docs").status_code == 200)

print()
print("RESULTADO:", "TODOS OS TESTES PASSARAM" if ok else "HOUVE FALHAS")
sys.exit(0 if ok else 1)