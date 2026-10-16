"""Testa o endpoint do Story (imagem 1080x1920) e o cron protegido."""

import os
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

DB = Path(tempfile.gettempdir()) / "tph_story_test.db"
if DB.exists():
    DB.unlink()

os.environ["ADMIN_PASSWORD"] = "senha-correta-123"
os.environ["DATABASE_URL"] = f"sqlite:///{DB}"
os.environ["ENVIRONMENT"] = "dev"
os.environ["CRON_SECRET"] = "segredo-cron"

sys.path.insert(0, str(Path(__file__).resolve().parent))

from io import BytesIO

from PIL import Image

from app.db import init_db
from app.localtime import today_local
from app.main import app

init_db()

from fastapi.testclient import TestClient  # noqa: E402

client = TestClient(app)
ADMIN = {"X-Admin-Key": "senha-correta-123"}

hoje = today_local()
D1 = (hoje + timedelta(days=1)).isoformat()

ok = True


def check(nome, cond, extra=""):
    global ok
    ok = ok and bool(cond)
    print("  [%s] %s %s" % ("OK" if cond else "FAIL", nome, extra))


print("1. dia marcado (SIM) com eventos")
r = client.put(
    f"/api/v1/admin/{D1}",
    json={
        "has_palquinho": True,
        "events": [
            {"note": "10:30 jogo A\n14:00 jogo B", "instagram": "https://instagram.com/pedro"},
            {"note": "churrasco", "instagram": "@laje"},
        ],
    },
    headers=ADMIN,
)
check("PUT -> 200", r.status_code == 200, f"(status {r.status_code})")

print("2. GET story .jpg devolve JPEG 1080x1920")
r = client.get(f"/api/v1/story/{D1}.jpg")
check("GET -> 200", r.status_code == 200, f"(status {r.status_code})")
check("content-type jpeg", r.headers.get("content-type") == "image/jpeg", r.headers.get("content-type"))
img = Image.open(BytesIO(r.content))
check("tamanho 1080x1920", img.size == (1080, 1920), str(img.size))
check("é RGB", img.mode == "RGB", img.mode)
check("<= 8MB", len(r.content) <= 8 * 1024 * 1024, f"({len(r.content)} bytes)")
check("cache-control", "s-maxage" in r.headers.get("cache-control", ""), r.headers.get("cache-control"))

print("3. dia sem marcação também gera imagem (default NÃO)")
D2 = (hoje + timedelta(days=30)).isoformat()
r = client.get(f"/api/v1/story/{D2}.jpg")
check("GET -> 200", r.status_code == 200, f"(status {r.status_code})")
check("é JPEG", r.headers.get("content-type") == "image/jpeg")

print("4. nome de arquivo inválido -> 404")
r = client.get("/api/v1/story/nao-e-data.jpg")
check("404", r.status_code == 404, f"(status {r.status_code})")

print("5. cron sem token -> 401")
r = client.get("/api/cron/story")
check("401", r.status_code == 401, f"(status {r.status_code})")

print("6. cron com token errado -> 401")
r = client.get("/api/cron/story", headers={"Authorization": "Bearer errado"})
check("401", r.status_code == 401, f"(status {r.status_code})")

print("7. cron com token certo, sem credenciais IG -> pula (sem publicar)")
r = client.get("/api/cron/story", headers={"Authorization": "Bearer segredo-cron"})
check("200", r.status_code == 200, f"(status {r.status_code})")
check("published=False", r.json().get("published") is False, str(r.json()))

print("\n" + ("TUDO OK" if ok else "HOUVE FALHA"))
sys.exit(0 if ok else 1)
