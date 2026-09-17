from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .settings import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Cria as tabelas se ainda não existirem."""
    from . import models  # noqa: F401  (registra as tabelas no metadata)

    Base.metadata.create_all(bind=engine)
    _ensure_suggestion_instagram()


def _ensure_suggestion_instagram() -> None:
    """Migração leve: garante a coluna `instagram` em `palquinho_suggestion`."""
    from sqlalchemy import text

    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE palquinho_suggestion ADD COLUMN instagram VARCHAR(300)"))
    except Exception:
        pass  # coluna já existe
