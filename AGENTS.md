# temPalquinhoHoje — Diretrizes para Agente

## O que é
Site simples e divertido: "**tem palquinho hoje?**" — uma página com **SIM gigante (verde)** ou **NÃO gigante (vermelho)** respondendo se HOJE tem palquinho (a festa do grupo). **O default é NÃO**: só muda quando o admin marca o dia. Quem souber de um palquinho manda uma sugestão (data + organizador + Instagram opcional); o **admin confirma** ou **descarta** no painel.

## Fluxo Operacional
- **PowerShell 5.1**: NUNCA use `&&`. Use `; if ($?) { cmd2 }`.
- **Confiar no disco, não no transcript**: o histórico pode vir contaminado com outra conversa (logger). Sempre ler o arquivo real antes de assumir.
- **Segredos**: `.env` em `backend/` (`DATABASE_URL` + `ADMIN_PASSWORD`). **Nunca faça commit** — repo é **PÚBLICO**. `backend/.env` está no `.gitignore`; usar `.env.example` como base.
- **Workflow**: Issue → Branch → PR para feature/correção. Deploy automático no `git push origin main` via **Vercel** (projeto `logger-s/tempalquinhohoje`).
- **Domínio**: principal é **`tempalquinhohoje.com`** (apex canônico, `www` redireciona). `palquinho.com` é alias e faz 308 pro principal — nunca apontar `og:url`/`canonical` pra ele. `tempalquinhohoje.vercel.app` segue no ar por links antigos mas não é canônico.

## Arquitetura
- **Monorepo**: `backend/` (FastAPI + SQLAlchemy), `frontend/` (Vite React + TS), `api/index.py` (adaptador serverless que importa o app FastAPI).
- **Deploy Vercel**: `vercel.json` na raiz — build do frontend (`cd frontend && npm ci && npm run build`, output `frontend/dist`) + função Python `api/index.py`; `requirements.txt` na raiz para as deps da função. Env vars em Produção: `DATABASE_URL` (Neon) e `ADMIN_PASSWORD`.
- **Banco**: SQLite (`backend/tempalquinhohoje.db`) em dev; **PostgreSQL (Neon)** em produção. `create_all` no boot (`backend/app/db.py init_db`) + `_ensure_column()` para migrações leves de coluna nova.
- **Tabelas** (`backend/app/models.py`):
  - `palquinho_day` — `day` (Date, PK), `has_palquinho` (bool), `is_other_event` (bool, default `false`), `updated_at`. **Não tem mais `note`/`instagram`**: quem carrega isso agora é `palquinho_event`.
    - `is_other_event` é o que define a cor: `has_palquin=false` + `is_other_event=true` = **laranja** ("tem rolê"); `false` = **vermelho** (NÃO, só a nota do dia). O backend força `false` quando `has_palquin=true` — dia verde ignora.
  - `palquinho_event` — `id`, `day`, `position` (ordem de exibição), `note` (texto do evento, pode ter `\n`), `instagram` (link **daquele** evento, opcional). Limite de **5 eventos por dia** (`MAX_EVENTS_PER_DAY`).
  - `palquinho_suggestion` — `id`, `day`, `organizer`, `instagram`, `status` (`pending`/`solved`), `action` (`confirm`/`dismiss`, quando resolvida), `solved_at`, `created_at`.
  - `day_log` — auditoria: quem marcou/desmarcou o dia.
  - ~~`visit`~~ — **removida**: métricas de visita agora são do Vercel Analytics (sem custo no Neon).
- **Endpoints** (tudo em `backend/app/api/palquinho.py`, prefixo `/api/v1`):
  - `GET /today` → `{ day, has_palquinho: bool|null, is_other_event: bool, events[] }` (null = não marcado → front mostra NÃO). Cada evento é `{ id, position, note, instagram }`.
  - `GET /home` → `{ today, days[] }` — SIM/NÃO de hoje + todos os dias marcados, em 1 requisição.
  - `GET /days` → todos os dias já marcados, cada um com sua lista de eventos.
  - `POST /suggestions` `{ day, organizer, instagram? }` → sugestão anônima de amigo (público).
  - Admin (header `X-Admin-Key` = `ADMIN_PASSWORD`):
    - `GET /admin/suggestions` → pendentes (default); `?status=solved` lista o arquivo (histórico, com `action` e `solved_at`).
    - `POST /admin/suggestions/{id}/confirm` `{ has_palquinho, events[] }` → marca o dia (criando um evento a partir do pedido: nota = organizador) e resolve a sugestão (action=confirm).
    - `DELETE /admin/suggestions/{id}` → descarta a sugestão (action=dismiss).
    - `PUT /admin/{day}` `{ has_palquinho, is_other_event?, events[] }` → marca SIM **ou NÃO** (upsert). `is_other_event=true` deixa o dia laranja. A lista enviada **substitui** os eventos do dia (apagar na UI = sumir do banco).
    - `DELETE /admin/{day}` → desmarca o dia (os eventos do dia vão junto).
    - `GET /admin/dashboard` → uma requisição só: `{ days, pending, archive }` — o painel admin usa esse (1 cold start, não 3 requisições).
- **Settings** (`backend/app/settings.py`): `DATABASE_URL`, `ADMIN_PASSWORD`, `ENVIRONMENT` (`dev`/`prod` — em prod desliga `/docs`), `RUN_MIGRATIONS` (bool, default `true`) via pydantic-settings (env da Vercel em prod).
- **Main** (`backend/app/main.py`): FastAPI + CORS + `@app.on_event("startup")` → `init_db()`; inclui só o router `palquinho`. Também tem `GET /api/v1/health` (com ping no banco). O `/api/cron/warmup` está **comentado** — manter o compute do Neon sempre ligado consome os 100 CU-h/mês do Free; o scale-to-zero do Neon já resolve (custo de ~0,3-0,5s na 1ª visita após 5 min parado).
- **Cold start otimizado** (`backend/app/db.py`): `init_db()` no prod faz só um **precheck barato** (query única em `information_schema`) e pula o DDL se o schema já estiver certo. No dev (SQLite) e se houver coluna nova, roda `create_all` + `_ensure_column`. Pra desligar o init_db de vez no cold start, setar `RUN_MIGRATIONS=false` nos env da Vercel — nesse caso o schema é responsabilidade do admin (rodar com `true` quando mudar de schema).

## Importante (comportamento)
- **Default do dia = NÃO**: na tela principal, `has_palquinho` null vira NÃO vermelho.
- **"Hoje" é horário de Brasília**: o backend usa `today_local()` (`backend/app/localtime.py`, UTC-3 fixo) pra marcar dia e sugestão — `date.today()` da Vercel seria UTC e erraria o dia depois das 21h.
- **Três botões no admin**: `marcar SIM` (verde), `marcar NÃO` (vermelho — só pra deixar a nota do dia) e `NÃO (outro rolê)` (laranja — o dia é de outro evento). Nota não é sinônimo de evento: dá pra ter dia vermelho com anotação.
- **Cor vem de `is_other_event`, não da lista de eventos**: a presença de evento não deixa o dia laranja sozinha — o admin escolhe no botão.
- **Evento é entidade própria** (`palquinho_event`), não linha de texto: cada um tem nota e link próprios, com ordem. Salvar o dia **substitui** a lista inteira. Limite de 5/dia no schema (fecha a brecha) e no `+` da UI (evita o erro).
- **Nota pode ter quebra de linha**: o admin usa `<textarea>`; a quebra de linha (`\n`) é preservada no banco e na exibição (`white-space: pre-line`). Serve pra juntar horários no mesmo bloco (ex.: "10:30 jogo A\n14:00 jogo B"). No tooltip da semana do rodapé, `\n` vira ` · `.
- **Nota com link é clicável** e ganha indicativo visual (sublinhado + `↗`) pra não parecer texto morto. Nota sem link é texto normal.
- **Migração da nota antiga** (`db.py migrate_day_notes_to_events`): dia que tinha `note` multilinha vira 1 evento por linha, **sem link** (a Columns `note`/`instagram` sobraram vazias no banco e não são mais lidas). Idempotente: só mexe em dia que tem nota e ainda não tem evento. Conferir o que ficou sem link com `python backend/listar_eventos.py`.
- **Visitas**: vêm do **Vercel Analytics** (grátis, `@vercel/analytics`), não do banco. Ver no dashboard da Vercel, não no painel admin.
- **Sugestões arquivam**: confirmada ou descartada vai pro **arquivo** (`status=solved`, com `action confirm/dismiss` + `solved_at`) — o admin confere o histórico antes de soltar o link.
- **Nada de votação**: sugestão serve pra *informar* o admin (data + organizador), não pra votar SIM/NÃO.
- **Calendário do admin**: verde = SIM marcado, contorno vermelho = NÃO marcado (com nota/link), neutro = sem marcação.
- **Feedback visual**: confete arco-íris atrás do SIM quando tem palquinho; favicon ✅/❌ conforme o dia.

## Frontend (comportamento)
- **Tela inicial**: SIM/NÃO gigante, data acima, faixa da semana atual no rodapé (dias verdes/vermelhos; hover mostra as notas do dia, clique abre o Instagram), lista de eventos com nota clicável quando tem link, botão "sabe de algum palquinho?" + link "admin" no canto superior direito.
- **Sugestão**: modal com **mini calendário** (navegável, dias passados bloqueados, dia escolhido em verde) + organizador + Instagram opcional.
- **Admin**: login com senha, calendário mensal, painel do dia (SIM/NÃO/remover), **editor de eventos** (cada um com nota + link, botão `+` até 3, `✕` apaga), **prévia ao vivo** do dia abaixo do calendário, sugestões com abas **pendentes / arquivo**.
- **Mini calendário no modal e calendário do admin**: semana começa no domingo.

## Pendências / Backlog
- **Opcional**: print no README (falta uma screenshot do resultado).
- **Opcional**: domínio customizado no Vercel.

## Convenções
- **Segurança (não quebrar)**: `POST /suggestions` é público e tem rate limit por IP (5/hora). Rotas `/admin/*` usam `require_admin` com rate limit por IP (20 req/5min) + `secrets.compare_digest`. Senha do admin **nunca** vai pro `localStorage` — fica só na memória do React (`AdminScreen.tsx`), então recarregar a página exige logar de novo (intencional). Em `ENVIRONMENT=prod`, `/docs` e `/openapi.json` ficam desligados. Headers de segurança (`X-Frame-Options: DENY`, `nosniff`, `frame-ancestors 'none'`) são adicionados pelo middleware em `main.py`.
- **Rate limit é em memória** (`backend/app/ratelimit.py`): protege contra ataque pequeno/bot, mas morre no cold start e não é compartilhado entre instâncias serverless. Se precisar de garantia real, o próximo passo é persistir tentativas no Postgres (tabela `login_attempt`) ou limitador na borda (Vercel WAF / Cloudflare).
- **Limites de tamanho** nos payloads (`schemas.py`): `organizer` 80, `instagram` 300, `note` 2000 — casa com as colunas do model e corta abuso antes do banco.
- **Limite de eventos** (`schemas.py`): `events` com `max_length=MAX_EVENTS_PER_DAY` (5) — um `PUT` com 6+ eventos volta 422. O mesmo número vive no frontend (`MAX_EVENTS` em `AdminScreen.tsx`) pro `+` sumir antes do erro.
- **Testes de segurança**: `python backend/test_seguranca.py` roda uma bateria (rate limit, auth, limites, headers) com SQLite temporário. Não precisa instalar nada a mais.
- **Testes de eventos**: `python backend/test_eventos.py` cobre a lista por dia (ordem, links separados, substituir a lista, limite de 3, apagar junto com o dia) e a migração da nota antiga.
- **Versão (`frontend/src/version.ts`)**: **sobe +0.1 a cada deploy em `main` que tenha mudança visível** (`1.0 -> 1.1 -> 1.2`). Bump é parte do deploy — se mudou algo que o usuário vê (tela, texto, CSS, imagem de preview, `index.html`), sobe a versão junto. Deploy só de backend (endpoint, regra de negócio, bug que o usuário não vê) **não** mexe na versão. Só vira `2.0` (ou `X.0`) em mudança grande/quebradora. Exibida discretamente no canto superior esquerdo da tela principal.
- **Campo do domínio**: `has_palquinho` (bool) — mesmo no frontend.
- **Status de sugestão**: `pending` / `solved`; **action**: `confirm` / `dismiss` — mesmo no frontend.
- **Sem framework CSS pesado** — app pequeno, CSS puro já basta.
- **Tema escuro no site inteiro** (main + admin + modal); na tela principal só o SIM/NÃO é colorido (verde/vermelho) sobre fundo preto.
- **Rápido e simples**: prioridade é destravar. Não hiperpensar.