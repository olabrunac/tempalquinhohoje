"""Cron da Vercel: publica o Story do dia no Instagram.

A Vercel chama esse endpoint 1x/dia (ver vercel.json) e envia sozinha o header
"Authorization: Bearer $CRON_SECRET" quando a env CRON_SECRET existe.
Sem credenciais do Instagram, ele não faz nada (só responde que pulou) — assim
o dev/preview não quebra.
"""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Header, HTTPException, status

from ..instagram import InstagramError, publish_story
from ..localtime import today_local
from ..settings import settings

router = APIRouter()


@router.get("/cron/story")
def cron_story(authorization: str | None = Header(default=None)) -> dict:
    # Protege o endpoint: sem CRON_SECRET (dev) fica aberto; em prod é obrigatório.
    if settings.CRON_SECRET:
        expected = f"Bearer {settings.CRON_SECRET}"
        given = authorization or ""
        if not secrets.compare_digest(given.encode(), expected.encode()):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="não autorizado")

    if not (settings.IG_USER_ID and settings.IG_ACCESS_TOKEN):
        return {"published": False, "reason": "IG_USER_ID/IG_ACCESS_TOKEN não configurados"}

    day = today_local()
    image_url = f"{settings.STORY_BASE_URL.rstrip('/')}/api/v1/story/{day.isoformat()}.jpg"
    try:
        result = publish_story(image_url)
    except InstagramError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    return {"published": True, "day": day.isoformat(), "image_url": image_url, "result": result}
