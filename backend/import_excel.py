import sys
import re
from datetime import datetime
import pandas as pd
from app.db import SessionLocal, init_db
from app.models import PalquinhoDay


def get_sheets_csv_url(url: str) -> str:
    match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
    if not match:
        return url
    sheet_id = match.group(1)
    gid_match = re.search(r'gid=([0-9]+)', url)
    gid = gid_match.group(1) if gid_match else '0'
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


def import_events(source: str):
    init_db()
    db = SessionLocal()

    try:
        url_or_path = get_sheets_csv_url(source)
        print(f"Lendo dados de: {url_or_path}...")

        if url_or_path.startswith('http'):
            df = pd.read_csv(url_or_path)
        elif url_or_path.endswith('.csv'):
            df = pd.read_csv(url_or_path)
        else:
            df = pd.read_excel(url_or_path)

        print(f"Lendo {len(df)} linhas com sucesso...")

        events_by_date = {}

        for _, row in df.iterrows():
            raw_date = row.get('Data') or row.get('data') or row.get('DATE') or row.get('date')
            if pd.isna(raw_date):
                continue

            if isinstance(raw_date, datetime):
                d_str = raw_date.strftime('%Y-%m-%d')
            else:
                try:
                    d_str = pd.to_datetime(raw_date).strftime('%Y-%m-%d')
                except Exception:
                    continue

            evento = str(row.get('Evento') or row.get('evento') or row.get('Descricao') or row.get('descrição') or '').strip()
            tipo = str(row.get('Tipo') or row.get('tipo') or 'palquinho').strip().lower()
            insta = row.get('Instagram') or row.get('instagram') or None
            if pd.isna(insta):
                insta = None
            else:
                insta = str(insta).strip()

            is_palquinho = 'palquinho' in tipo or 'sim' in tipo
            is_other = not is_palquinho

            if d_str not in events_by_date:
                events_by_date[d_str] = {
                    'has_palquinho': is_palquinho,
                    'notes': [],
                    'instagram': insta
                }

            note_line = evento
            if is_other and not note_line.startswith('[EVENTO]'):
                note_line = f"[EVENTO] {note_line}"

            events_by_date[d_str]['notes'].append(note_line)
            if not events_by_date[d_str]['instagram'] and insta:
                events_by_date[d_str]['instagram'] = insta
            if is_palquinho:
                events_by_date[d_str]['has_palquinho'] = True

        for d_str, data in events_by_date.items():
            d = datetime.strptime(d_str, '%Y-%m-%d').date()
            full_note = "\n".join(data['notes'])

            row = db.query(PalquinhoDay).filter_by(day=d).first()
            if row is None:
                row = PalquinhoDay(day=d)
                db.add(row)

            row.has_palquinho = data['has_palquinho']
            row.note = full_note
            row.instagram = data['instagram']
            print(f"[{d_str}] Salvo: Palquinho={data['has_palquinho']} | Eventos: {len(data['notes'])}")

        db.commit()
        print("Importação concluída com sucesso!")
    except Exception as e:
        db.rollback()
        print(f"Erro na importação: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python import_excel.py <link_google_sheets_ou_arquivo.xlsx>")
    else:
        import_events(sys.argv[1])
