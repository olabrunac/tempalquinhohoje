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


@router.get("/today", response_model=schemas.TodayOut)
def get_today(response: Response, db: Session = Depends(get_db)):
    """SIM/NÃO de hoje. None se o admin ainda não marcou o dia."""
    response.headers["Cache-Control"] = "public, s-maxage=5, stale-while-revalidate=3600"
    today = today_local()
    row = db.query(models.PalquinhoDay).filter(models.PalquinhoDay.day == today).first()
    if row is None:
        return schemas.TodayOut(day=today)
    return schemas.TodayOut(day=today, has_palquinho=row.has_palquinho, note=row.note, instagram=row.instagram)


@router.get("/home", response_model=schemas.HomeOut)
def get_home(response: Response, db: Session = Depends(get_db)):
    """Retorna o SIM/NÃO de hoje e todos os dias marcados em 1 única requisição."""
    response.headers["Cache-Control"] = "public, s-maxage=5, stale-while-revalidate=3600"
    today = today_local()
    row = db.query(models.PalquinhoDay).filter(models.PalquinhoDay.day == today).first()
    today_out = (
        schemas.TodayOut(day=today)
        if row is None
        else schemas.TodayOut(day=today, has_palquinho=row.has_palquinho, note=row.note, instagram=row.instagram)
    )
    days_out = db.query(models.PalquinhoDay).order_by(models.PalquinhoDay.day).all()
    return schemas.HomeOut(today=today_out, days=days_out)


@router.get("/days", response_model=list[schemas.DayOut])
def list_days(db: Session = Depends(get_db)):
    """Todos os dias já marcados pelo admin."""
    return db.query(models.PalquinhoDay).order_by(models.PalquinhoDay.day).all()


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
    """Admin marca se tem palquinho num dia (upsert)."""
    d = date.fromisoformat(day)
    row = db.query(models.PalquinhoDay).filter_by(day=d).first()
    if row is None:
        row = models.PalquinhoDay(day=d)
        db.add(row)
    row.has_palquinho = payload.has_palquinho
    row.note = payload.note
    row.instagram = payload.instagram
    db.commit()
    db.refresh(row)
    return row


@router.delete("/admin/{day}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def unset_day(day: str, db: Session = Depends(get_db)):
    """Admin remove a marcação de um dia."""
    row = db.query(models.PalquinhoDay).filter_by(day=date.fromisoformat(day)).first()
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
    return schemas.DashboardOut(
        days=days,
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
    row = db.query(models.PalquinhoDay).filter_by(day=sug.day).first()
    if row is None:
        row = models.PalquinhoDay(day=sug.day)
        db.add(row)
    row.has_palquinho = payload.has_palquinho
    row.note = payload.note
    row.instagram = payload.instagram
    sug.status = "solved"
    sug.action = "confirm"
    sug.solved_at = datetime.now()
    db.commit()
    db.refresh(row)
    return row


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
