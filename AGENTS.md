# tempalquinhohoje — Diretrizes para Agente

## 🎯 O que é
Site simples e divertido: "**tem palquinho hoje?**" — uma página com **SIM gigante (verde)** ou **NÃO gigante (vermelho)** respondendo se HOJE tem palquinho (a festa do grupo). Amigos votam com o palpite; o **admin confirma** marcando o dia no calendário.

## 🚀 Fluxo Operacional
- **PowerShell 5.1**: **NUNCA** use `&&`. Use `; if ($?) { cmd2 }`.
- **Segredos**: `.env` em `backend/` (variáveis reais: `DATABASE_URL` do **Neon** + `ADMIN_PASSWORD`). **Nunca faça commit** — repo é **PÚBLICO**; `backend/.env` e `.env` na raiz estão no `.gitignore`. Copie `.env.example` → `.env`.
- **Workflow**: Issue → Branch → PR para feature/correção. Commit direto na main só para o que for deploy rápido.
- **Deploy**: **Vercel** (Services: `frontend/` Vite estático + `backend/` ASGI `entrypoint: main:app`; rewrites `/api/*` → backend e `/(.*)` → SPA) + **Neon Postgres**. Deploy automático ao `git push origin main` (Projekt congelado — `main` = produção).

## 🏗️ Arquitetura (esqueleto atual — backend só)
- **Monorepo**: `backend/` (FastAPI + SQLAlchemy) e `frontend/` (Vite React + TS — scaffold inicial).
- **Banco**: **SQLite** (`backend/tempalquinhohoje.db`, dev local) / **PostgreSQL (Neon)** em produção — primeiro boot roda `init_db` que cria as tabelas (SQLAlchemy `Base.metadata.create_all` em `backend/app/db.py`).
- **Tabelas** (`backend/app/models.py`):
  - `palquinho_day` — `day` (Date, PK), `has_palquinho` (bool), `note` (texto opcional), `updated_at`.
  - `palquinho_vote` — `id`, `day`, `name` (quem votou), `vote` (bool), `created_at`. Único voto por (day, name).
  - `day_log` — auditoria: quem marcou/desmarcou dia (`set`/`unset`).
- **Endpoints** (prefixo `/api/v1`, router `backend/app/api/palquinho.py`):
  - `GET /today` → `{ day, has_palquinho: bool|null, note }` (null = não marcado ainda) — **a tela principal**.
  - `GET /days` → todos os dias já marcados.
  - `GET /votes/{day}` → votos de um dia.
  - `POST /vote` `{ day, name, vote }` → voto do amigo (upsert por day+name).
  - Admin (cabeçalho `X-Admin-Key` = `ADMIN_PASSWORD`):
    - `PUT /admin/{day}` `{ has_palquinho, note }` → marca dia.
    - `DELETE /admin/{day}` → desmarca.
- **Config** (`backend/app/settings.py`): `DATABASE_URL`, `ADMIN_PASSWORD` via pydantic-settings (`.env`).
- **Main**: `backend/app/main.py` — FastAPI + CORS (tudo liberado, app pequeno) + `@app.on_event("startup")` roda `init_db()`.

## 📋 Pendências / Backlog
1. **Frontend da tela principal** — SIM gigante verde / NÃO gigante vermelho para hoje (`GET /today`); se `has_palquinho` for `null`, mostrar "não marcado ainda" com botão para o amigo votar (modal com nome + SIM/NÃO).
2. **Frontend admin** — rota `/admin`: pede senha (vira `X-Admin-Key`), mostra calendário do mês, clique num dia → marcar SIM/NÃO (com nota opcional), ver votos do dia e confirmar.
3. **Opcional**: exibir lista dos próximos dias já marcados (ex.: "Sexta tem palquinho 🎉").
4. **README bom** com print/emoji do resultado — repo público reúe gente do grupo.
5. Commit inicial já empurrado; **deploy Vercel** pendente (criar serviço, conectar Neon).

## ⚙️ Convenções
- **Variável do domínio**: `has_palquinho` (bool). Na frontend usar `has_palquinho` camelCase igual.
- Mexer direto **sem `agent` perfeccionismo** — projeto é pequeno, prioridade é destravar o mais rápido possível.
- Confirmar factos lendo o arquivo real; o transcript pode vir contaminado com outra conversa (logger) — **confiar em `Get-Content`/read e no git, não no histórico da conversa**.

## ✅ Implementado
- Repo `olabrunac/tempalquinhohoje` criado (público) + git init + remote `origin` + commit inicial com todo o backend scaffold.
