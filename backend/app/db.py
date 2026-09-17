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
    _ensure_column("palquinho_suggestion", "instagram", "VARCHAR(300)")
    _ensure_column("palquinho_day", "instagram", "VARCHAR(300)")
    _ensure_column("palquinho_suggestion", "action", "VARCHAR(10)")
    _ensure_column("palquinho_suggestion", "solved_at", "TIMESTAMP")


def _ensure_column(table: str, column: str, ddl_type: str) -> None:
    """Migração leve: adiciona a coluna se ainda não existir."""
    from sqlalchemy import text

    try:
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"))
    except Exception:
        pass  # coluna já existe
