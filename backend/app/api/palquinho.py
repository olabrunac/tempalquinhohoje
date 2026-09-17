from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db
from ..settings import settings


def require_admin(x_admin_key: str | None = Header(default=None)) -> None:
    if not x_admin_key or x_admin_key != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin não autorizado")


router = APIRouter()


@router.get("/today", response_model=schemas.TodayOut)
def get_today(db: Session = Depends(get_db)):
    """SIM/NÃO de hoje. None se o admin ainda não marcou o dia."""
    today = date.today()
    row = db.query(models.PalquinhoDay).filter(models.PalquinhoDay.day == today).first()
    if row is None:
        return schemas.TodayOut(day=today)
    return schemas.TodayOut(day=today, has_palquinho=row.has_palquinho, note=row.note)


@router.get("/days", response_model=list[schemas.DayOut])
def list_days(db: Session = Depends(get_db)):
    """Todos os dias já marcados pelo admin."""
    return db.query(models.PalquinhoDay).order_by(models.PalquinhoDay.day).all()


@router.get("/votes/{day}", response_model=list[schemas.VoteOut])
def list_votes(day: str, db: Session = Depends(get_db)):
    """Votos dos amigos para um dia (ordenação por data do voto)."""
    return db.query(models.PalquinhoVote).filter(models.PalquinhoVote.day == date.fromisoformat(day)).order_by(models.PalquinhoVote.created_at).all()


@router.post("/vote", response_model=schemas.VoteOut, status_code=status.HTTP_201_CREATED)
def vote(payload: schemas.VoteIn, db: Session = Depends(get_db)):
    """Amigo chuta SIM/NÃO. Um voto por pessoa por dia (upsert)."""
    existing = db.query(models.PalquinhoVote).filter_by(day=payload.day, name=payload.name).first()
    if existing:
        existing.vote = payload.vote
        db.commit()
        db.refresh(existing)
        return existing
    row = models.PalquinhoVote(day=payload.day, name=payload.name, vote=payload.vote)
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
def list_suggestions(db: Session = Depends(get_db)):
    """Sugestões dos amigos: dias com voto que o admin ainda não confirmou."""
    days_with_votes = [
        d for (d,) in db.query(models.PalquinhoVote.day).distinct().all()
    ]
    marked_days = {d.day for d in db.query(models.PalquinhoDay).all()}
    result = []
    for d in days_with_votes:
        if d in marked_days:
            continue
        votes = (
            db.query(models.PalquinhoVote)
            .filter(models.PalquinhoVote.day == d)
            .order_by(models.PalquinhoVote.created_at)
            .all()
        )
        result.append(schemas.SuggestionOut(day=d, votes=votes))
    result.sort(key=lambda s: s.day)
    return result
