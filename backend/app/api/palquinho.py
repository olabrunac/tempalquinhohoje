import secrets
from datetime import date, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db
from ..localtime import today_local
from ..ratelimit import client_ip, limiter
from ..settings import settings


def require_admin(request: Request, x_admin_key: str | None = Header(default=None)) -> None:
    """Checa a senha do admin com rate limit por IP.

    A comparação usa secrets.compare_digest pra não vazar o valor por tempo.
    O rate limit conta tentativas (chamadas a /admin/*), então um admin que usa
    o painel de verdade também conta — o limite é folgado o bastante pra isso.
    """
    ip = client_ip(request)
    bucket = f"admin:{ip}"
    allowed, _, retry_after = limiter.check(bucket, 20, 300.0)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas. Tente novamente em alguns minutos.",
            headers={"Retry-After": str(int(retry_after) + 1)},
        )

    expected = settings.ADMIN_PASSWORD
    given = x_admin_key or ""
    # compare_digest exige str ASCII de mesmo encoding; normaliza com segurança
    if not secrets.compare_digest(given.encode("utf-8"), expected.encode("utf-8")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin não autorizado")

    # autenticado: zera o contador pra não penalizar quem entrou certo
    limiter.reset(bucket)


router = APIRouter()


def _events_by_day(db: Session, days: list[models.PalquinhoDay]) -> dict[date, list[models.PalquinhoEvent]]:
    """Carrega os eventos de vários dias em uma query só (evita N+1 nos endpoints)."""
    if not days:
        return {}
    wanted = [d.day for d in days]
    rows = (
        db.query(models.PalquinhoEvent)
        .filter(models.PalquinhoEvent.day.in_(wanted))
        .order_by(models.PalquinhoEvent.day, models.PalquinhoEvent.position, models.PalquinhoEvent.id)
        .all()
    )
    grouped: dict[date, list[models.PalquinhoEvent]] = {}
    for ev in rows:
        grouped.setdefault(ev.day, []).append(ev)
    return grouped


def _day_out(row: models.PalquinhoDay, events: list[models.PalquinhoEvent]) -> schemas.DayOut:
    return schemas.DayOut(
        day=row.day,
        has_palquinho=row.has_palquinho,
        events=[schemas.EventOut.model_validate(e) for e in events],
    )


def _upsert_day(db: Session, d: date, has_palquinho: bool) -> models.PalquinhoDay:
    row = db.query(models.PalquinhoDay).filter_by(day=d).first()
    if row is None:
        row = models.PalquinhoDay(day=d)
        db.add(row)
    row.has_palquinho = has_palquinho
    return row


def _replace_events(db: Session, d: date, incoming: list[schemas.EventIn]) -> list[models.PalquinhoEvent]:
    """Substitui a lista de eventos do dia. A lista inteira vem do admin a cada save,
    então deletar e recriar é mais simples que diff — e some o que foi apagado na UI."""
    db.query(models.PalquinhoEvent).filter(models.PalquinhoEvent.day == d).delete()
    created = [
        models.PalquinhoEvent(
            day=d,
            position=i + 1,
            note=ev.note.strip(),
            instagram=(ev.instagram or "").strip() or None,
        )
        for i, ev in enumerate(incoming)
        if ev.note.strip()
    ]
    for ev in created:
        db.add(ev)
    return created


@router.get("/today", response_model=schemas.TodayOut)
def get_today(response: Response, db: Session = Depends(get_db)):
    """SIM/NÃO de hoje. None se o admin ainda não marcou o dia."""
    response.headers["Cache-Control"] = "public, s-maxage=5, stale-while-revalidate=3600"
    today = today_local()
    row = db.query(models.PalquinhoDay).filter(models.PalquinhoDay.day == today).first()
    if row is None:
        return schemas.TodayOut(day=today)
    events = _events_by_day(db, [row]).get(today, [])
    return schemas.TodayOut(
        day=today,
        has_palquinho=row.has_palquinho,
        events=[schemas.EventOut.model_validate(e) for e in events],
    )


@router.get("/home", response_model=schemas.HomeOut)
def get_home(response: Response, db: Session = Depends(get_db)):
    """Retorna o SIM/NÃO de hoje e todos os dias marcados em 1 única requisição."""
    response.headers["Cache-Control"] = "public, s-maxage=5, stale-while-revalidate=3600"
    today = today_local()
    days = db.query(models.PalquinhoDay).order_by(models.PalquinhoDay.day).all()
    grouped = _events_by_day(db, days)
    row = next((d for d in days if d.day == today), None)
    today_out = (
        schemas.TodayOut(day=today)
        if row is None
        else schemas.TodayOut(
            day=today,
            has_palquinho=row.has_palquinho,
            events=[schemas.EventOut.model_validate(e) for e in grouped.get(today, [])],
        )
    )
    return schemas.HomeOut(today=today_out, days=[_day_out(d, grouped.get(d.day, [])) for d in days])


@router.get("/days", response_model=list[schemas.DayOut])
def list_days(db: Session = Depends(get_db)):
    """Todos os dias já marcados pelo admin, cada um com sua lista de eventos."""
    days = db.query(models.PalquinhoDay).order_by(models.PalquinhoDay.day).all()
    grouped = _events_by_day(db, days)
    return [_day_out(d, grouped.get(d.day, [])) for d in days]


@router.post("/suggestions", response_model=schemas.SuggestionOut, status_code=status.HTTP_201_CREATED)
def create_suggestion(payload: schemas.SuggestionIn, request: Request, db: Session = Depends(get_db)):
    """Amigo manda uma sugestão anônima: 'dia X tem palquinho, organizador Y'.

    Público, então tem rate limit por IP pra evitar spam.
    """
    ip = client_ip(request)
    allowed, _, retry_after = limiter.check(f"suggest:{ip}", 5, 3600.0)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Você já enviou várias sugestões. Tente mais tarde.",
            headers={"Retry-After": str(int(retry_after) + 1)},
        )

    row = models.PalquinhoSuggestion(
        day=payload.day,
        organizer=payload.organizer.strip(),
        instagram=(payload.instagram or "").strip() or None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ---- Admin (cabeçalho X-Admin-Key) ----

@router.put("/admin/{day}", response_model=schemas.DayOut, dependencies=[Depends(require_admin)])
def set_day(day: str, payload: schemas.DaySetIn, db: Session = Depends(get_db)):
    """Admin marca o dia (SIM ou NÃO) e substitui a lista de eventos."""
    d = date.fromisoformat(day)
    row = _upsert_day(db, d, payload.has_palquinho)
    events = _replace_events(db, d, payload.events)
    db.commit()
    db.refresh(row)
    return _day_out(row, events)


@router.delete("/admin/{day}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def unset_day(day: str, db: Session = Depends(get_db)):
    """Admin remove a marcação do dia (os eventos do dia vão junto)."""
    d = date.fromisoformat(day)
    row = db.query(models.PalquinhoDay).filter_by(day=d).first()
    db.query(models.PalquinhoEvent).filter(models.PalquinhoEvent.day == d).delete()
    if row:
        db.delete(row)
    db.commit()


@router.get("/admin/suggestions", response_model=list[schemas.SuggestionOut], dependencies=[Depends(require_admin)])
def list_suggestions(status: str | None = Query(default="pending"), db: Session = Depends(get_db)):
    """Sugestões: 'pending' (padrão), 'solved' (arquivo) — com o estado atual do dia."""
    q = db.query(models.PalquinhoSuggestion)
    if status == "solved":
        q = q.filter(models.PalquinhoSuggestion.status == "solved").order_by(
            models.PalquinhoSuggestion.solved_at.desc()
        )
    else:
        q = q.filter(models.PalquinhoSuggestion.status == "pending").order_by(
            models.PalquinhoSuggestion.day
        )
    marked = {d.day: d.has_palquinho for d in db.query(models.PalquinhoDay).all()}
    return [
        schemas.SuggestionOut(
            id=s.id,
            day=s.day,
            organizer=s.organizer,
            instagram=s.instagram,
            status=s.status,
            action=s.action,
            solved_at=s.solved_at,
            created_at=s.created_at,
            has_palquinho=marked.get(s.day),
        )
        for s in q.all()
    ]


@router.get("/admin/dashboard", response_model=schemas.DashboardOut, dependencies=[Depends(require_admin)])
def get_dashboard(db: Session = Depends(get_db)):
    """Tudo que o painel admin precisa em 1 requisição só — 1 cold start, não 3."""
    days = db.query(models.PalquinhoDay).order_by(models.PalquinhoDay.day).all()
    pending = (
        db.query(models.PalquinhoSuggestion)
        .filter(models.PalquinhoSuggestion.status == "pending")
        .order_by(models.PalquinhoSuggestion.day)
        .all()
    )
    archive = (
        db.query(models.PalquinhoSuggestion)
        .filter(models.PalquinhoSuggestion.status == "solved")
        .order_by(models.PalquinhoSuggestion.solved_at.desc())
        .all()
    )
    marked = {d.day: d.has_palquinho for d in days}
    to_out = lambda s: schemas.SuggestionOut(
        id=s.id,
        day=s.day,
        organizer=s.organizer,
        instagram=s.instagram,
        status=s.status,
        action=s.action,
        solved_at=s.solved_at,
        created_at=s.created_at,
        has_palquinho=marked.get(s.day),
    )
    grouped = _events_by_day(db, days)
    return schemas.DashboardOut(
        days=[_day_out(d, grouped.get(d.day, [])) for d in days],
        pending=[to_out(s) for s in pending],
        archive=[to_out(s) for s in archive],
    )


@router.post(
    "/admin/suggestions/{suggestion_id}/confirm",
    response_model=schemas.DayOut,
    dependencies=[Depends(require_admin)],
)
def confirm_suggestion(suggestion_id: int, payload: schemas.DaySetIn, db: Session = Depends(get_db)):
    """Admin confirma a sugestão: marca o dia e resolve a sugestão."""
    sug = db.get(models.PalquinhoSuggestion, suggestion_id)
    if sug is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sugestão não encontrada")
    row = _upsert_day(db, sug.day, payload.has_palquinho)
    events = _replace_events(db, sug.day, payload.events)
    sug.status = "solved"
    sug.action = "confirm"
    sug.solved_at = datetime.now()
    db.commit()
    db.refresh(row)
    return _day_out(row, events)


@router.delete(
    "/admin/suggestions/{suggestion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def dismiss_suggestion(suggestion_id: int, db: Session = Depends(get_db)):
    """Admin descarta a sugestão sem marcar o dia."""
    sug = db.get(models.PalquinhoSuggestion, suggestion_id)
    if sug is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sugestão não encontrada")
    sug.status = "solved"
    sug.action = "dismiss"
    sug.solved_at = datetime.now()
    db.commit()
