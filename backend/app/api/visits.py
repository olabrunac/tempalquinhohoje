from datetime import date, timedelta

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..api.palquinho import require_admin
from ..db import get_db
from ..settings import settings

router = APIRouter()


@router.post("/visits", status_code=status.HTTP_201_CREATED)
def create_visit(x_admin_key: str | None = Header(default=None), db: Session = Depends(get_db)):
    """Conta uma visita à tela inicial. Visitas do próprio admin não entram na conta."""
    if x_admin_key and x_admin_key == settings.ADMIN_PASSWORD:
        return
    db.add(models.Visit(day=date.today()))
    db.commit()


@router.get("/admin/visits", response_model=schemas.VisitsAdminOut, dependencies=[Depends(require_admin)])
def get_visits(db: Session = Depends(get_db)):
    """Visitas (não-admin) dos últimos 30 dias + total."""
    today = date.today()
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