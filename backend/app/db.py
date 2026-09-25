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


_schema_checked = False


def init_db() -> None:
    global _schema_checked
    """Cria/migra o schema se precisar. No cold start do prod faz só um precheck barato."""
    from . import models  # noqa: F401  (registra as tabelas no metadata)

    if not settings.run_migrations:
        return

    if _schema_checked:
        return

    if engine.dialect.name == "postgresql" and _schema_ok():
        _schema_checked = True
        return

    Base.metadata.create_all(bind=engine)
    _ensure_column("palquinho_suggestion", "instagram", "VARCHAR(300)")
    _ensure_column("palquinho_day", "instagram", "VARCHAR(300)")
    _ensure_column("palquinho_day", "status", "VARCHAR(10) DEFAULT 'yes'")
    _ensure_column("palquinho_suggestion", "action", "VARCHAR(10)")
    _ensure_column("palquinho_suggestion", "solved_at", "TIMESTAMP")
    _schema_checked = True


_EXPECTED = {
    "palquinho_day": {"day", "has_palquinho", "status", "note", "instagram", "updated_at"},
    "palquinho_suggestion": {
        "id", "day", "organizer", "instagram", "status", "action", "solved_at", "created_at",
    },
    "day_log": {"id", "day", "action", "has_palquinho", "created_at"},
    "visit": {"id", "day", "created_at"},
}


def _schema_ok() -> bool:
    """Precheck barato: se tabelas/colunas esperadas já existem, pula o DDL."""
    from sqlalchemy import text

    names = ", ".join(f"'{t}'" for t in _EXPECTED)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT table_name, column_name FROM information_schema.columns "
                f"WHERE table_schema = 'public' AND table_name IN ({names})"
            )
        )
    have: dict[str, set[str]] = {}
    for table, column in rows:
        have.setdefault(table, set()).add(column)
    return all(cols <= have.get(table, set()) for table, cols in _EXPECTED.items())


def _ensure_column(table: str, column: str, ddl_type: str) -> None:
    """Migração leve: adiciona a coluna se ainda não existir."""
    from sqlalchemy import text

    try:
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"))
    except Exception:
        pass  # coluna já existe
