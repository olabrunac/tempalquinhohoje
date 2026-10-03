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
    _ensure_column("palquinho_suggestion", "action", "VARCHAR(10)")
    _ensure_column("palquinho_suggestion", "solved_at", "TIMESTAMP")
    migrate_day_notes_to_events()
    _schema_checked = True


_EXPECTED = {
    "palquinho_day": {"day", "has_palquinho", "updated_at"},
    "palquinho_event": {"id", "day", "position", "note", "instagram"},
    "palquinho_suggestion": {
        "id", "day", "organizer", "instagram", "status", "action", "solved_at", "created_at",
    },
    "day_log": {"id", "day", "action", "has_palquinho", "created_at"},
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
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {ddl_type}"))
    except Exception:
        try:
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"))
        except Exception:
            pass


_EVENTO_PREFIX = "[EVENTO]"


def _split_legacy_note(note: str) -> tuple[list[str], bool]:
    """Nota antiga = uma linha por evento. Tira o marcador [EVENTO] das linhas.

    Devolve (linhas, é_outro_evento) — o prefixo marcava dia de "outro evento"
    (laranja no site) e hoje o admin escolhe isso na hora de salvar.
    """
    lines: list[str] = []
    is_outro_evento = False
    for raw in note.splitlines():
        line = raw.strip()
        if line.startswith(_EVENTO_PREFIX):
            is_outro_evento = True
            line = line[len(_EVENTO_PREFIX):].strip()
        if line:
            lines.append(line)
    return lines, is_outro_evento


def migrate_day_notes_to_events() -> list[str]:
    """Converte a nota multilinha dos dias já marcados em um evento por linha.

    Idempotente: só mexe em dia que tem nota e ainda não tem nenhum evento, então
    rodar em todo cold start não duplica nada. O link antigo NÃO é copiado — o admin
    prefere revisar evento por evento depois (a sugestão guarda o instagram dele).

    Devolve a lista de dias convertidos, pra conferir no log.
    """
    from sqlalchemy import text

    try:
        with engine.begin() as conn:
            rows = conn.execute(
                text(
                    "SELECT d.day, d.note FROM palquinho_day d "
                    "WHERE d.note IS NOT NULL AND TRIM(d.note) <> '' "
                    "AND NOT EXISTS (SELECT 1 FROM palquinho_event e WHERE e.day = d.day) "
                    "ORDER BY d.day"
                )
            ).fetchall()
            converted: list[str] = []
            for day, note in rows:
                lines, _is_outro = _split_legacy_note(note)
                for i, line in enumerate(lines):
                    conn.execute(
                        text(
                            "INSERT INTO palquinho_event (day, position, note, instagram) "
                            "VALUES (:day, :position, :note, NULL)"
                        ),
                        {"day": day, "position": i + 1, "note": line},
                    )
                if lines:
                    converted.append(str(day))
    except Exception:
        return []
    if converted:
        print(f"[migrate] {len(converted)} dia(s) convertido(s) para eventos: {', '.join(converted)}")
    return converted
