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
    today = None
    for d in db.query(models.PalquinhoDay).filter(models.PalquinhoDay.day >= __import__("datetime").date.today()).all():
        today = d
        break
    if today is None:
        return schemas.TodayOut(day=__import__("datetime").date.today())
    return schemas.TodayOut(day=today.day, has_palquinho=today.has_palquinho, note=today.note)


@router.get("/days", response_model=list[schemas.DayOut])
def list_days(db: Session = Depends(get_db)):
    """Todos os dias já marcados pelo admin."""
    return db.query(models.PalquinhoDay).order_by(models.PalquinhoDay.day).all()


@router.get("/votes/{day}", response_model=list[schemas.VoteOut])
def list_votes(day: str, db: Session = Depends(get_db)):
    """Votos dos amigos para um dia (ordenação por data do voto)."""
    from datetime import date
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
    from datetime import date
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
    from datetime import date
    row = db.query(models.PalquinhoDay).filter_by(day=date.fromisoformat(day)).first()
    if row:
        db.delete(row)
        db.commit()
