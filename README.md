# tempalquinhohoje

> **tem palquinho hoje?** — SIM gigante ou NÃO gigante.

Site que responde, num grão, se hoje tem palquinho (a festa do grupo). **O default é NÃO** —
só muda quando o admin marca o dia. Quem souber de algum palquinho manda uma sugestão
com a data e o organizador; o admin confirma no painel.

## Stack
- **Backend**: FastAPI + SQLAlchemy (Python 3.12) — pasta `backend/`, adaptador serverless em `api/`
- **Frontend**: Vite + React + TypeScript — pasta `frontend/`
- **Banco**: SQLite (local) / Neon Postgres (produção)
- **Deploy**: Vercel (projeto `tempalquinhohoje`) + Neon — auto-deploy no `git push origin main`

## Rodar local
```bash
# backend (porta 8000)
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # preencha DATABASE_URL + ADMIN_PASSWORD
uvicorn app.main:app --reload --port 8000

# frontend (em outro terminal, porta 5173)
cd frontend
npm install
npm run dev
```

Abra `http://localhost:5173` (o Vite faz proxy de `/api` pro backend na 8000).
Admin: `http://localhost:5173/admin` (senha = `ADMIN_PASSWORD`).

## Endpoints principais
| Método | Rota | O que faz |
|---|---|---|
| GET | `/api/v1/today` | Tem palquinho hoje? (null = não marcado → site mostra NÃO) |
| GET | `/api/v1/days` | Dias já marcados |
| POST | `/api/v1/suggestions` | Amigo manda sugestão anônima `{ day, organizer, instagram? }` |
| GET | `/api/v1/admin/suggestions` | Sugestões pendentes (header `X-Admin-Key`) |
| POST | `/api/v1/admin/suggestions/{id}/confirm` | Confirma a sugestão e marca o dia |
| DELETE | `/api/v1/admin/suggestions/{id}` | Descarta a sugestão sem marcar |
| PUT | `/api/v1/admin/{day}` | Admin marca o dia (header `X-Admin-Key`) |
| DELETE | `/api/v1/admin/{day}` | Admin desmarca o dia |
| GET | `/api/v1/health` | Healthcheck |

## Fluxo
1. O amigo abre o site e vê o status de hoje: **SIM gigante verde** ou **NÃO gigante vermelho** (default NÃO).
2. Botão discreto no canto — *"sabe de algum palquinho?"* — manda data + organizador (anonimamente, com link do anúncio no Instagram opcional) como sugestão.
3. No `/admin`, o admin vê as sugestões pendentes, confirma (marca o dia) ou descarta, e também marca dias direto no calendário (com nota opcional).
4. Confirmou = tela principal atualiza.