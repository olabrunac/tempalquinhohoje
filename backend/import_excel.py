import sys
import re
from datetime import datetime
import pandas as pd
from app.db import SessionLocal, init_db
from app.models import PalquinhoDay, PalquinhoEvent

MONTH_MAP = {
    'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
    'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12
}


def import_visual_sheet(filepath_or_url: str):
    init_db()
    db = SessionLocal()

    try:
        source = filepath_or_url
        if source.startswith('http'):
            match = re.search(r'/d/([a-zA-Z0-9-_]+)', source)
            if match:
                sheet_id = match.group(1)
                gid_match = re.search(r'gid=([0-9]+)', source)
                gid = gid_match.group(1) if gid_match else '0'
                source = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
            df = pd.read_csv(source, header=None)
        elif source.endswith('.csv'):
            df = pd.read_csv(source, header=None)
        else:
            df = pd.read_excel(source, header=None)

        print(f"Lendo planilha visual ({len(df)} linhas)...")

        current_year = None
        current_month = None
        current_date = None
        events_by_date = {}

        for _, row in df.iterrows():
            row_values = [str(val).strip() for val in row.values if pd.notna(val) and str(val).strip() != 'nan']
            if not row_values:
                continue

            col_a = str(row.values[0]).strip().lower() if len(row.values) > 0 and pd.notna(row.values[0]) else ''
            m_match = re.search(r'(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)[\.\s]*([0-9]{2})', col_a)
            if m_match:
                month_name, year_short = m_match.groups()
                current_month = MONTH_MAP.get(month_name)
                current_year = 2000 + int(year_short)
                continue

            day_val = None
            for val in row.values:
                if pd.notna(val):
                    val_str = str(val).strip()
                    if val_str.isdigit() and 1 <= int(val_str) <= 31:
                        day_val = int(val_str)
                        break

            if day_val and current_month and current_year:
                try:
                    current_date = datetime(current_year, current_month, day_val).date()
                    if current_date not in events_by_date:
                        events_by_date[current_date] = []
                    continue
                except ValueError:
                    pass

            if current_date:
                for val in row.values:
                    if pd.notna(val):
                        text_val = str(val).strip()
                        if text_val and text_val != str(current_date.day) and text_val.lower() != 'nan':
                            if text_val not in events_by_date[current_date]:
                                events_by_date[current_date].append(text_val)

        print(f"Encontrados eventos para {len(events_by_date)} datas.")

        for d, texts in events_by_date.items():
            full_note = "\n".join(texts)
            is_palquinho = any('palquinho' in t.lower() for t in texts)

            # Se não for palquinho, marca com prefixo [EVENTO] para ficar laranja (Tem rolê)
            row = db.query(PalquinhoDay).filter_by(day=d).first()
            if row is None:
                row = PalquinhoDay(day=d)
                db.add(row)
            row.has_palquinho = is_palquinho

            # Cada texto da planilha vira um evento (nota própria, sem link).
            db.query(PalquinhoEvent).filter(PalquinhoEvent.day == d).delete()
            for i, t in enumerate(texts):
                db.add(PalquinhoEvent(day=d, position=i + 1, note=t))

            print(f"[{d}] Salvo: Palquinho={is_palquinho} | Eventos: {len(texts)}")

        db.commit()
        print("Importação da planilha visual concluída com sucesso!")
    except Exception as e:
        db.rollback()
        print(f"Erro na importação: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python import_excel.py <link_google_sheets_ou_arquivo.xlsx>")
    else:
        import_visual_sheet(sys.argv[1])
