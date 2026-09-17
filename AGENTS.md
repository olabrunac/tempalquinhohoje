# temPalquinhoHoje — Diretrizes para Agente

## O que é
Site simples e divertido: "**tem palquinho hoje?**" — uma página com **SIM gigante (verde)** ou **NÃO gigante (vermelho)** respondendo se HOJE tem palquinho (a festa do grupo). Os amigos votam com o palpite; o **admin confirma** marcando o dia.

## Fluxo Operacional
- **PowerShell 5.1**: NUNCA use `&&`. Use `; if ($?) { cmd2 }`.
- **Confiar no disco, não no transcript**: o histórico pode vir contaminado com outra conversa (logger). Sempre ler o arquivo real antes de assumir.
- **Segredos**: `.env` em `backend/` (`DATABASE_URL` do Neon + `ADMIN_PASSWORD`). **Nunca faça commit** — repo é **PÚBLICO**. `backend/.env` está no `.gitignore`; usar `.env.example` como base.
- **Workflow**: Issue → Branch → PR para feature/correção. Deploy automático no `git push origin main` via **Vercel** (projeto `olabrunac/tempalquinhohoje`).

## Arquitetura (esqueleto atual — backend FastAPI + SQLite/Neon)
- **Monorepo**: `backend/` (FastAPI + SQLAlchemy) e `frontend/` (Vite React + TS — scaffold inicial).
- **Banco**: SQLite (`backend/tempalquinhohoje.db`) em dev; **PostgreSQL (Neon)** em produção. `create_all` no boot (`backend/app/db.py init_db`).
- **Tabelas** (`backend/app/models.py`):
  - `palquinho_day` — `day` (Date, PK), `has_palquinho` (bool), `note` (texto opcional), `updated_at`.
  - `palquinho_vote` — `id`, `day`, `name` (quem votou), `vote` (bool), `created_at`. Único voto por (day, name).
  - `day_log` — auditoria: quem marcou/desmarcou o dia.
- **Endpoints** (`backend/app/api/palquinho.py`, prefixo `/api/v1`):
  - `GET /today` → `{ day, has_palquinho: bool|null, note }` (null = não marcado ainda) — **a tela principal**.
  - `GET /days` → todos os dias já marcados.
  - `GET /votes/{day}` → votos de um dia.
  - `POST /vote` `{ day, name, vote }` → voto do amigo (upsert por day+name).
  - Admin (header `X-Admin-Key` = `ADMIN_PASSWORD`):
    - `PUT /admin/{day}` `{ has_palquinho, note }` → marca o dia.
    - `DELETE /admin/{day}` → desmarca o dia.
- **Settings** (`backend/app/settings.py`): `DATABASE_URL`, `ADMIN_PASSWORD` via pydantic-settings (`.env`).
- **Main** (`backend/app/main.py`): FastAPI + CORS + `@app.on_event("startup")` → `init_db()`.

## Pendências / Backlog
1. **Frontend da tela principal** — SIM gigante verde / NÃO gigante vermelho para hoje (calls `GET /today`); se `has_palquinho` for `null`, mostrar "não marcado ainda" + botão pro amigo votar (modal com nome + SIM/NÃO).
2. **Frontend admin** — rota `/admin`: pede senha (vira `X-Admin-Key`), mostra calendário do mês, clique num dia → marcar SIM/NÃO (com nota opcional).
3. **Opcional**: lista dos próximos dias já marcados.
4. **README** com print do resultado — repo público.
5. **Deploy Vercel** pendente (criar serviço, conectar Neon). Deploy atual: só o scaffold backend.

## Convenções
- **Campo do domínio**: `has_palquinho` (bool) — mesmo no frontend.
- **Sem framework CSS pesado** — app pequeno, Tailwind suficiente.
- **Rápido e simples**: prioridade é destravar. Não hiperpensar.
