from datetime import date, datetime

from sqlalchemy import Date, DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class PalquinhoDay(Base):
    """Dia marcado como tendo (ou não) palquinho pelo admin.

    A lista de eventos (nota + link de cada um) vive em PalquinhoEvent. As colunas
    note/instagram foram removidas do model; sobraram vazias no banco e não são lidas.

    `is_other_event` é o que decide a cor do dia: com ele ligado, um dia sem palquinho
    aparece laranja ("tem rolê"), em vez do vermelho de "não tem". Precisa ser explícito
    porque o dia pode ter nota sem ser evento — e aí o admin quer o vermelho.
    """
    __tablename__ = "palquinho_day"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    has_palquinho: Mapped[bool]
    is_other_event: Mapped[bool] = mapped_column(default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PalquinhoEvent(Base):
    """Um evento de um dia (churrasco, palquinho, rolê...).

    Substitui a nota multilinha em palquinho_day: cada evento tem sua própria nota
    e seu próprio link do Instagram. `position` define a ordem de exibição.
    """
    __tablename__ = "palquinho_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    position: Mapped[int] = mapped_column(default=1)
    note: Mapped[str] = mapped_column(Text)
    instagram: Mapped[str | None] = mapped_column(String(300), nullable=True)


class PalquinhoVote(Base):
    """Resposta anônima de "você vai?" num dia com palquinho.

    Um registro por navegador (token aleatório no localStorage), unique (day, voter):
    responder de novo TROCA a resposta em vez de somar outro voto. Sem nome e sem IP —
    o número é termômetro, não lista de presença. O "não" fica guardado só pra pessoa
    poder mudar de ideia; o site conta apenas quem vai.

    BANCO ANTIGO TEM ARMADILHA: existia um `palquinho_vote` de um protótipo com outro
    formato (`name`, `vote`). Como `create_all` não altera tabela existente, reaproveitar
    esse nome deixava a query de contagem estourando `UndefinedColumn` e derrubava
    /days e /home com 500. Por isso a tabela agora se chama `palquinho_presence`:
    nome novo, criado do zero, sem colidir com nada que já esteja lá.
    """
    __tablename__ = "palquinho_presence"
    __table_args__ = (UniqueConstraint("day", "voter", name="uq_presence_day_voter"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    voter: Mapped[str] = mapped_column(String(64))
    going: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PalquinhoSuggestion(Base):
    """Sugestão anônima de amigo: 'tal dia tem palquinho' com quem organiza e link do anúncio."""
    __tablename__ = "palquinho_suggestion"

    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    organizer: Mapped[str] = mapped_column(String(80))
    instagram: Mapped[str | None] = mapped_column(String(300), nullable=True)
    status: Mapped[str] = mapped_column(String(10), default="pending")  # pending / solved
    action: Mapped[str | None] = mapped_column(String(10), nullable=True)  # confirm / dismiss
    solved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DayLog(Base):
    """Log mínimo de quem marcou o quê (auditoria simples)."""
    __tablename__ = "day_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    action: Mapped[str] = mapped_column(String(10))  # set / unset
    has_palquinho: Mapped[bool | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
