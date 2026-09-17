# tempalquinhohoje

> **tem palquinho hoje?** — SIM gigante ou NÃO gigante.

Site que responde, num grão, se hoje tem palquinho (a festa do grupo). Os amigos votam
com o palpite; o admin confirma marcando o dia no calendário.

## Stack
- **Backend**: FastAPI + SQLAlchemy (Python 3.12) — pasta `backend/`
- **Frontend**: Vite + React + TypeScript — pasta `frontend/`
- **Banco**: SQLite (local) / Neon Postgres (produção)
- **Deploy**: Vercel (Services) + Neon

## Rodar local
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # preencha DATABASE_URL + ADMIN_PASSWORD
uvicorn app.main:app --reload --port 8000
```

## Endpoints principais
| Método | Rota | O que faz |
|---|---|---|
| GET | `/api/v1/today` | Tem palquinho hoje? (null = não marcado) |
| GET | `/api/v1/days` | Dias já marcados |
| GET | `/api/v1/votes/{day}` | Votos de um dia |
| POST | `/api/v1/vote` | Voto do amigo (SIM/NÃO) |
| PUT | `/api/v1/admin/{day}` | Admin marca o dia (header `X-Admin-Key`) |
| DELETE | `/api/v1/admin/{day}` | Admin desmarca o dia |
| GET | `/api/v1/health` | Healthcheck |
