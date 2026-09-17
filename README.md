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
| GET | `/api/v1/today` | Tem palquinho hoje? (null = não marcado) |
| GET | `/api/v1/days` | Dias já marcados |
| GET | `/api/v1/votes/{day}` | Votos de um dia |
| POST | `/api/v1/vote` | Palpite do amigo (SIM/NÃO) — vira sugestão pro admin |
| GET | `/api/v1/admin/suggestions` | Sugestões dos amigos ainda não confirmadas (header `X-Admin-Key`) |
| PUT | `/api/v1/admin/{day}` | Admin marca o dia (header `X-Admin-Key`) |
| DELETE | `/api/v1/admin/{day}` | Admin desmarca o dia |
| GET | `/api/v1/health` | Healthcheck |

## Fluxo
1. O amigo abre o site e vê o status de hoje (SIM gigante verde / NÃO gigante vermelho).
2. Se o dia ainda não está marcado, ele vota (nome + SIM/NÃO) — vira uma **sugestão**.
3. No `/admin`, o admin vê as sugestões pendentes, confirma (ou marca direto no calendário) e ainda pode adicionar uma nota.
4. Confirmou = tela principal do dia atualiza sozinha.
