from datetime import timedelta

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..api.palquinho import require_admin
from ..db import get_db
from ..localtime import today_local
from ..settings import settings

router = APIRouter()


@router.post("/visits", status_code=status.HTTP_201_CREATED)
def create_visit(x_admin_key: str | None = Header(default=None), db: Session = Depends(get_db)):
    """Conta uma visita à tela inicial. Visitas do próprio admin não entram na conta."""
    if x_admin_key and x_admin_key == settings.ADMIN_PASSWORD:
        return
    db.add(models.Visit(day=today_local()))
    db.commit()


@router.get("/admin/visits", response_model=schemas.VisitsAdminOut, dependencies=[Depends(require_admin)])
def get_visits(db: Session = Depends(get_db)):
    """Visitas (não-admin) dos últimos 30 dias + total."""
    today = today_local()
    start = today - timedelta(days=30)
    rows = (
        db.query(models.Visit.day, func.count(models.Visit.id))
        .filter(models.Visit.day >= start)
        .group_by(models.Visit.day)
        .all()
    )
    counts = {d: c for d, c in rows}
    total = db.query(func.count(models.Visit.id)).scalar() or 0
    days = [
        schemas.VisitDayOut(day=d, count=counts.get(d, 0))
        for d in (start + timedelta(days=i) for i in range(31))
    ]
    return schemas.VisitsAdminOut(total=total, today=counts.get(today, 0), days=days)


@router.get("/admin/dashboard", response_model=schemas.DashboardOut, dependencies=[Depends(require_admin)])
def get_dashboard(db: Session = Depends(get_db)):
    """Tudo que o painel admin precisa em 1 requisição — 1 cold start só."""
    today = today_local()

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

    start = today - timedelta(days=30)
    visit_rows = (
        db.query(models.Visit.day, func.count(models.Visit.id))
        .filter(models.Visit.day >= start)
        .group_by(models.Visit.day)
        .all()
    )
    counts = {d: c for d, c in visit_rows}
    total = db.query(func.count(models.Visit.id)).scalar() or 0

    return schemas.DashboardOut(
        days=days,
        pending=[to_out(s) for s in pending],
        archive=[to_out(s) for s in archive],
        visits=schemas.VisitsAdminOut(
            total=total,
            today=counts.get(today, 0),
            days=[
                schemas.VisitDayOut(day=d, count=counts.get(d, 0))
                for d in (start + timedelta(days=i) for i in range(31))
            ],
        ),
    )