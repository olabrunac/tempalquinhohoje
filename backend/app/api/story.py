"""Endpoint público que gera o Story (JPEG) do dia — é a imagem que a Meta baixa
pra publicar no Instagram (cron em /api/cron/story)."""

from __future__ import annotations

import time
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from .. import models
from ..db import get_db
from ..story import insta_handle, render_story_jpeg

router = APIRouter()

WEEKDAYS_SHORT = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"]

# Cache em memória: o mesmo dia costuma ser pedido 2x (a Meta busca, e às vezes
# revalida). Evita redesenhar o Pillow à toa entre as chamadas do mesmo container.
_CACHE_TTL = 120.0
_cache: dict[str, tuple[float, bytes]] = {}


def _state_of(row: models.PalquinhoDay | None) -> str:
    if row is None:
        return "no"
    if row.has_palquinho:
        return "yes"
    return "other" if row.is_other_event else "no"


def _build_week(db: Session, center: date, center_state: str) -> list[dict]:
    sunday = center - timedelta(days=(center.weekday() + 1) % 7)  # Python: seg=0
    states = {r.day: _state_of(r) for r in db.query(models.PalquinhoDay).all()}
    out = []
    for i in range(7):
        dd = sunday + timedelta(days=i)
        viewing = dd == center
        out.append(
            {
                "num": dd.day,
                "dow": WEEKDAYS_SHORT[(dd.weekday() + 1) % 7],
                "state": center_state if viewing else states.get(dd, "no"),
                "viewing": viewing,
            }
        )
    return out


def _render(db: Session, day: date) -> bytes:
    row = db.query(models.PalquinhoDay).filter_by(day=day).first()
    state = _state_of(row)
    events = (
        db.query(models.PalquinhoEvent)
        .filter(models.PalquinhoEvent.day == day)
        .order_by(models.PalquinhoEvent.position, models.PalquinhoEvent.id)
        .all()
    )
    notes = [e.note for e in events if e.note and e.note.strip()]
    handles: list[str] = []
    for e in events:
        h = insta_handle(e.instagram)
        if h and h not in handles:
            handles.append(h)
    return render_story_jpeg(day, state, notes, handles, _build_week(db, day, state))


@router.get(
    "/story/{filename}",
    responses={200: {"content": {"image/jpeg": {}}}},
    response_class=Response,
)
def get_story(filename: str, db: Session = Depends(get_db)) -> Response:
    """Story do dia em JPEG (1080x1920). Público: a Meta precisa buscar por URL."""
    day_str = filename[:-4] if filename.endswith(".jpg") else filename
    try:
        day = date.fromisoformat(day_str)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="dia inválido")

    cached = _cache.get(day_str)
    if cached and time.time() - cached[0] < _CACHE_TTL:
        jpeg = cached[1]
    else:
        jpeg = _render(db, day)
        _cache[day_str] = (time.time(), jpeg)

    return Response(
        content=jpeg,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "public, s-maxage=300, stale-while-revalidate=600",
            "Content-Disposition": "inline",
        },
    )
