from pathlib import Path
import base64
import hashlib
import hmac
import json
import time
import urllib.parse
import urllib.request

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from .db import get_db, init_db
from .api import palquinho, visits
from .models import PalquinhoDay
from .localtime import today_local
from .settings import settings

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


def post_tweet(text_msg: str) -> dict:
    if not all([settings.twitter_api_key, settings.twitter_api_secret, settings.twitter_access_token, settings.twitter_access_secret]):
        return {"ok": False, "error": "Twitter credentials not configured", "preview": text_msg}

    url = "https://api.twitter.com/2/tweets"
    method = "POST"

    params = {
        "oauth_consumer_key": settings.twitter_api_key,
        "oauth_token": settings.twitter_access_token,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_nonce": str(int(time.time() * 1000)),
        "oauth_version": "1.0",
    }

    all_params = {**params}
    sorted_params = sorted(all_params.items())
    parameter_string = urllib.parse.urlencode(sorted_params, safe="")

    base_string = f"{method}&{urllib.parse.quote(url, safe='')}&{urllib.parse.quote(parameter_string, safe='')}"
    signing_key = f"{urllib.parse.quote(settings.twitter_api_secret, safe='')}&{urllib.parse.quote(settings.twitter_access_secret, safe='')}"

    hashed = hmac.new(signing_key.encode("utf-8"), base_string.encode("utf-8"), hashlib.sha1)
    signature = base64.b64encode(hashed.digest()).decode("utf-8")

    params["oauth_signature"] = signature

    auth_header = "OAuth " + ", ".join(f'{urllib.parse.quote(k)}="{urllib.parse.quote(v)}"' for k, v in sorted(params.items()))

    req_data = json.dumps({"text": text_msg}).encode("utf-8")
    req = urllib.request.Request(url, data=req_data, headers={
        "Authorization": auth_header,
        "Content-Type": "application/json"
    }, method="POST")

    try:
        with urllib.request.urlopen(req) as response:
            res_body = json.loads(response.read().decode("utf-8"))
            return {"ok": True, "response": res_body}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/cron/tweet-daily")
def tweet_daily(db: Session = Depends(get_db)) -> dict:
    """Cron diário (6am BRT / 9am UTC): posta no Twitter se hoje tem palquinho ou não."""
    today = today_local()
    row = db.query(PalquinhoDay).filter(PalquinhoDay.day == today).first()

    if row and row.has_palquinho:
        msg = "SIM! Hoje tem palquinho! 🎉"
        if row.note:
            msg += f" {row.note}"
        if row.instagram:
            msg += f" \nAnúncio: {row.instagram}"
    else:
        msg = "NÃO. Hoje não tem palquinho ❌"
        if row and row.note:
            msg += f" ({row.note})"
        if row and row.instagram:
            msg += f" \nAnúncio: {row.instagram}"

    result = post_tweet(msg)
    return {"date": str(today), "message": msg, "twitter": result}
