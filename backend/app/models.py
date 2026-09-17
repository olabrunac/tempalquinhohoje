from datetime import date, datetime

from sqlalchemy import Date, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class PalquinhoDay(Base):
    """Dia marcado como tendo (ou não) palquinho pelo admin."""
    __tablename__ = "palquinho_day"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    has_palquinho: Mapped[bool]
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PalquinhoSuggestion(Base):
    """Sugestão anônima de amigo: 'tal dia tem palquinho' com quem organiza e link do anúncio."""
    __tablename__ = "palquinho_suggestion"

    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    organizer: Mapped[str] = mapped_column(String(80))
    instagram: Mapped[str | None] = mapped_column(String(300), nullable=True)
    status: Mapped[str] = mapped_column(String(10), default="pending")  # pending / solved
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DayLog(Base):
    """Log mínimo de quem marcou o quê (auditoria simples)."""
    __tablename__ = "day_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    action: Mapped[str] = mapped_column(String(10))  # set / unset
    has_palquinho: Mapped[bool | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
