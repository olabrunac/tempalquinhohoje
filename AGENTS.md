# temPalquinhoHoje — Diretrizes para Agente

## O que é
Site simples e divertido: "**tem palquinho hoje?**" — uma página com **SIM gigante (verde)** ou **NÃO gigante (vermelho)** respondendo se HOJE tem palquinho (a festa do grupo). **O default é NÃO**: só muda quando o admin marca o dia. Quem souber de um palquinho manda uma sugestão (data + organizador); o **admin confirma** ou **descarta** no painel.

## Fluxo Operacional
- **PowerShell 5.1**: NUNCA use `&&`. Use `; if ($?) { cmd2 }`.
- **Confiar no disco, não no transcript**: o histórico pode vir contaminado com outra conversa (logger). Sempre ler o arquivo real antes de assumir.
- **Segredos**: `.env` em `backend/` (`DATABASE_URL` + `ADMIN_PASSWORD`). **Nunca faça commit** — repo é **PÚBLICO**. `backend/.env` está no `.gitignore`; usar `.env.example` como base.
- **Workflow**: Issue → Branch → PR para feature/correção. Deploy automático no `git push origin main` via **Vercel** (projeto `logger-s/tempalquinhohoje`, domínio `tempalquinhohoje.vercel.app`).

## Arquitetura
- **Monorepo**: `backend/` (FastAPI + SQLAlchemy), `frontend/` (Vite React + TS), `api/index.py` (adaptador serverless que importa o app FastAPI).
- **Deploy Vercel**: `vercel.json` na raiz — build do frontend (`cd frontend && npm ci && npm run build`, output `frontend/dist`) + função Python `api/index.py`; `requirements.txt` na raiz para as deps da função. Env vars em Produção: `DATABASE_URL` (Neon) e `ADMIN_PASSWORD`.
- **Banco**: SQLite (`backend/tempalquinhohoje.db`) em dev; **PostgreSQL (Neon)** em produção. `create_all` no boot (`backend/app/db.py init_db`).
- **Tabelas** (`backend/app/models.py`):
  - `palquinho_day` — `day` (Date, PK), `has_palquinho` (bool), `note` (texto opcional), `updated_at`.
  - `palquinho_suggestion` — `id`, `day`, `organizer` (quem o amigo acha que organiza), `instagram` (link do anúncio, opcional), `status` (`pending`/`solved`), `created_at`.
  - `day_log` — auditoria: quem marcou/desmarcou o dia.
- **Endpoints** (`backend/app/api/palquinho.py`, prefixo `/api/v1`):
  - `GET /today` → `{ day, has_palquinho: bool|null, note }` (null = não marcado → front mostra NÃO).
  - `GET /days` → todos os dias já marcados.
  - `POST /suggestions` `{ day, organizer, instagram? }` → sugestão anônima de amigo (público).
  - Admin (header `X-Admin-Key` = `ADMIN_PASSWORD`):
    - `GET /admin/suggestions` → sugestões pendentes com o estado atual do dia.
    - `POST /admin/suggestions/{id}/confirm` `{ has_palquinho, note? }` → marca o dia e resolve a sugestão.
    - `DELETE /admin/suggestions/{id}` → descarta a sugestão sem marcar.
    - `PUT /admin/{day}` `{ has_palquinho, note }` → marca o dia.
    - `DELETE /admin/{day}` → desmarca o dia.
- **Settings** (`backend/app/settings.py`): `DATABASE_URL`, `ADMIN_PASSWORD` via pydantic-settings (env da Vercel em prod).
- **Main** (`backend/app/main.py`): FastAPI + CORS + `@app.on_event("startup")` → `init_db()`.

## Importante (comportamento)
- **Default do dia = NÃO**: na tela principal, `has_palquinho` null vira NÃO vermelho. Só o admin muda isso marcando o dia como SIM.
- **Sem "marcar NÃO" no admin**: não existe botão de NÃO — todo dia não marcado como SIM já é NÃO automaticamente. O admin só marca SIM ou remove a marcação.
- **Nada de votação**: sugestão serve pra *informar* o admin (data + organizador), não pra votar SIM/NÃO.
- No calendário do admin, dia sem marcação é neutro na grade (não marcado = NÃO, mas sem destaque na grade).

## Pendências / Backlog
- **Opcional**: lista dos próximos dias já marcados na tela principal.
- **Opcional**: domínio customizado no Vercel.
- **README** com print do resultado — repo público (falta o print).

## Convenções
- **Campo do domínio**: `has_palquinho` (bool) — mesmo no frontend.
- **Status de sugestão**: `pending` / `solved` — mesmo no frontend.
- **Sem framework CSS pesado** — app pequeno, CSS puro já basta.
- **Tema escuro no site inteiro** (main + admin + modal); na tela principal só o SIM/NÃO é colorido (verde/vermelho) sobre fundo preto.
- **Rápido e simples**: prioridade é destravar. Não hiperpensar.