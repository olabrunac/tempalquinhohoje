# temPalquinhoHoje — Diretrizes para Agente

## O que é
Site simples e divertido: "**tem palquinho hoje?**" — uma página com **SIM gigante (verde)** ou **NÃO gigante (vermelho)** respondendo se HOJE tem palquinho (a festa do grupo). **O default é NÃO**: só muda quando o admin marca o dia. Quem souber de um palquinho manda uma sugestão (data + organizador + Instagram opcional); o **admin confirma** ou **descarta** no painel.

## Fluxo Operacional
- **PowerShell 5.1**: NUNCA use `&&`. Use `; if ($?) { cmd2 }`.
- **Confiar no disco, não no transcript**: o histórico pode vir contaminado com outra conversa (logger). Sempre ler o arquivo real antes de assumir.
- **Segredos**: `.env` em `backend/` (`DATABASE_URL` + `ADMIN_PASSWORD`). **Nunca faça commit** — repo é **PÚBLICO**. `backend/.env` está no `.gitignore`; usar `.env.example` como base.
- **Workflow**: Issue → Branch → PR para feature/correção. Deploy automático no `git push origin main` via **Vercel** (projeto `logger-s/tempalquinhohoje`, domínio `tempalquinhohoje.vercel.app`).

## Arquitetura
- **Monorepo**: `backend/` (FastAPI + SQLAlchemy), `frontend/` (Vite React + TS), `api/index.py` (adaptador serverless que importa o app FastAPI).
- **Deploy Vercel**: `vercel.json` na raiz — build do frontend (`cd frontend && npm ci && npm run build`, output `frontend/dist`) + função Python `api/index.py`; `requirements.txt` na raiz para as deps da função. Env vars em Produção: `DATABASE_URL` (Neon) e `ADMIN_PASSWORD`.
- **Banco**: SQLite (`backend/tempalquinhohoje.db`) em dev; **PostgreSQL (Neon)** em produção. `create_all` no boot (`backend/app/db.py init_db`) + `_ensure_column()` para migrações leves de coluna nova.
- **Tabelas** (`backend/app/models.py`):
  - `palquinho_day` — `day` (Date, PK), `has_palquinho` (bool), `note` (texto opcional), `instagram` (link do anúncio, opcional), `updated_at`.
  - `palquinho_suggestion` — `id`, `day`, `organizer`, `instagram`, `status` (`pending`/`solved`), `action` (`confirm`/`dismiss`, quando resolvida), `solved_at`, `created_at`.
  - `day_log` — auditoria: quem marcou/desmarcou o dia.
  - `visit` — uma linha por visita à tela inicial (`day`, `created_at`); **visitas do admin não contam**.
- **Endpoints** (`backend/app/api/palquinho.py` + `visits.py`, prefixo `/api/v1`):
  - `GET /today` → `{ day, has_palquinho: bool|null, note, instagram }` (null = não marcado → front mostra NÃO).
  - `GET /days` → todos os dias já marcados.
  - `POST /visits` → conta visita (não conta se vier com `X-Admin-Key` de admin).
  - `POST /suggestions` `{ day, organizer, instagram? }` → sugestão anônima de amigo (público).
  - Admin (header `X-Admin-Key` = `ADMIN_PASSWORD`):
    - `GET /admin/suggestions` → pendentes (default); `?status=solved` lista o arquivo (histórico, com `action` e `solved_at`).
    - `POST /admin/suggestions/{id}/confirm` `{ has_palquinho, note?, instagram? }` → marca o dia e resolve a sugestão (action=confirm).
    - `DELETE /admin/suggestions/{id}` → descarta a sugestão (action=dismiss).
    - `PUT /admin/{day}` `{ has_palquinho, note?, instagram? }` → marca SIM **ou NÃO** (upsert).
    - `DELETE /admin/{day}` → desmarca o dia.
    - `GET /admin/visits` → `{ today, total, days[31] }` de visitas (não-admin) dos últimos 30 dias.
    - `GET /admin/dashboard` → uma requisição só: `{ days, pending, archive, visits }` — o painel admin usa esse (1 cold start, não 4 requisições em paralelo).
- **Settings** (`backend/app/settings.py`): `DATABASE_URL`, `ADMIN_PASSWORD`, `RUN_MIGRATIONS` (bool, default `true`) via pydantic-settings (env da Vercel em prod).
- **Main** (`backend/app/main.py`): FastAPI + CORS + `@app.on_event("startup")` → `init_db()`; inclui routers `palquinho` e `visits`. Também tem `GET /api/v1/health` (com ping no banco) e `GET /api/cron/warmup` (SELECT 1 — pensado pra pinger externo).
- **Cold start otimizado** (`backend/app/db.py`): `init_db()` no prod faz só um **precheck barato** (query única em `information_schema`) e pula o DDL se o schema já estiver certo. No dev (SQLite) e se houver coluna nova, roda `create_all` + `_ensure_column`. Pra desligar o init_db de vez no cold start, setar `RUN_MIGRATIONS=false` nos env da Vercel — nesse caso o schema é responsabilidade do admin (rodar com `true` quando mudar de schema).

## Importante (comportamento)
- **Default do dia = NÃO**: na tela principal, `has_palquinho` null vira NÃO vermelho.
- **"Hoje" é horário de Brasília**: o backend usa `today_local()` (`backend/app/localtime.py`, UTC-3 fixo) pra marcar dia, visita e sugestão — `date.today()` da Vercel seria UTC e erraria o dia depois das 21h.
- **Admin marca SIM ou NÃO**: o admin pode marcar explicitamente **NÃO** (com nota + link do Instagram) pra anunciar outro grande evento no dia — vetor `has_palquinho=false`. Fora isso, não-marcado já é NÃO automaticamente.
- **Visitas**: contam só quem abre a tela inicial sem ser admin (front pula quando há a chave de admin no localStorage **e** o backend ignora requisições com `X-Admin-Key`).
- **Sugestões arquivam**: confirmada ou descartada vai pro **arquivo** (`status=solved`, com `action confirm/dismiss` + `solved_at`) — o admin confere o histórico antes de soltar o link.
- **Nada de votação**: sugestão serve pra *informar* o admin (data + organizador), não pra votar SIM/NÃO.
- **Calendário do admin**: verde = SIM marcado, contorno vermelho = NÃO marcado (com nota/link), neutro = sem marcação.
- **Feedback visual**: confete arco-íris atrás do SIM quando tem palquinho; favicon ✅/❌ conforme o dia.

## Frontend (comportamento)
- **Tela inicial**: SIM/NÃO gigante, data acima, faixa da semana atual no rodapé (dias verdes/vermelhos; hover mostra a nota, clique abre o Instagram), nota + botão "ver anúncio no instagram ↗" (SIM ou NÃO anunciado), botão "sabe de algum palquinho?" + link "admin" no canto superior direito.
- **Sugestão**: modal com **mini calendário** (navegável, dias passados bloqueados, dia escolhido em verde) + organizador + Instagram opcional.
- **Admin**: login com senha, calendário mensal, painel do dia (SIM/NÃO/remover), sugestões com abas **pendentes / arquivo**, e painel de **visitas** colapsável abaixo do calendário.
- **Mini calendário no modal e calendário do admin**: semana começa no domingo.

## Pendências / Backlog
- **Opcional**: print no README (falta uma screenshot do resultado).
- **Opcional**: domínio customizado no Vercel.

## Convenções
- **Campo do domínio**: `has_palquinho` (bool) — mesmo no frontend.
- **Status de sugestão**: `pending` / `solved`; **action**: `confirm` / `dismiss` — mesmo no frontend.
- **Sem framework CSS pesado** — app pequeno, CSS puro já basta.
- **Tema escuro no site inteiro** (main + admin + modal); na tela principal só o SIM/NÃO é colorido (verde/vermelho) sobre fundo preto.
- **Rápido e simples**: prioridade é destravar. Não hiperpensar.