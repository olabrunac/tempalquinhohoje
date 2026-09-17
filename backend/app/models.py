from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class PalquinhoDay(Base):
    """Dia marcado como tendo (ou não) palquinho pelo admin."""
    __tablename__ = "palquinho_day"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    has_palquinho: Mapped[bool]
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PalquinhoVote(Base):
    """Voto dos amigos: chute se tem palquinho em um dia."""
    __tablename__ = "palquinho_vote"
    __table_args__ = (
        UniqueConstraint("day", "name", name="uq_palquinho_vote_day_name"),
        Index("ix_palquinho_vote_day", "day"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(Date)
    name: Mapped[str] = mapped_column(String(40))
    vote: Mapped[bool]  # True = SIM, False = NÃO
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DayLog(Base):
    """Log mínimo de quem marcou o quê (auditoria simples)."""
    __tablename__ = "day_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    action: Mapped[str] = mapped_column(String(10))  # set / unset
    has_palquinho: Mapped[bool | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
