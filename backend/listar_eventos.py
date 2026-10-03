"""Lista os eventos de cada dia marcado, destacando os que ainda estao sem link.

Roda em cima do DATABASE_URL configurado (em prod, o mesmo do .env da Vercel).
Depois da migracao, os dias que vieram da nota antiga aparecem sem link — sao
esses que vale conferir e preencher.

Uso:
    cd backend
    python listar_eventos.py            # so os dias que precisam de atencao
    python listar_eventos.py --todos    # todos os dias marcados
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# settings.py le o .env da pasta; sem isso o script nao acha o DATABASE_URL.
from app.settings import settings  # noqa: E402

from sqlalchemy import text  # noqa: E402

from app.db import engine  # noqa: E402
from app.localtime import today_local  # noqa: E402

QUERY = """
SELECT d.day, d.has_palquinho, e.position, e.note, e.instagram
FROM palquinho_day d
LEFT JOIN palquinho_event e ON e.day = d.day
ORDER BY d.day, e.position, e.id
"""


def main() -> int:
    mostrar_todos = "--todos" in sys.argv

    with engine.connect() as conn:
        rows = conn.execute(text(QUERY)).fetchall()

    if not rows:
        print("Nenhum dia marcado no banco.")
        return 0

    dias: dict = {}
    for day, has_pal, position, note, instagram in rows:
        dias.setdefault(day, {"has_palquinho": has_pal, "eventos": []})
        if note is not None:
            dias[day]["eventos"].append((position, note, instagram))

    hoje = today_local()
    convertidos = [d for d, v in dias.items() if v["eventos"] and not v["has_palquinho"]]

    print(f"Banco: {settings.DATABASE_URL.split('@')[-1]}")
    print(f"Total de dias marcados: {len(dias)}\n")

    for day in sorted(dias):
        info = dias[day]
        eventos = info["eventos"]
        sem_link = [e for e in eventos if not e[2]]

        if not mostrar_todos and not sem_link:
            continue

        marca = "HOJE" if str(day) == str(hoje) else ""
        print(f"{day}  palquinho={'SIM' if info['has_palquinho'] else 'NAO'}  {marca}")
        if not eventos:
            print("  (sem eventos)")
            continue
        for position, note, instagram in eventos:
            link = instagram or "SEM LINK <- conferir"
            print(f"  {position}. {note}")
            print(f"     {link}")
        print()

    print("-" * 60)
    print(f"Dias com evento sem link: {len(convertidos)}")
    for day in sorted(convertidos):
        print(f"  - {day}")
    if not mostrar_todos:
        print("\n(mostrando so os dias com evento sem link; use --todos para ver tudo)")
    return 0


if __name__ == "__main__":
    sys.exit(main())