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
    - `POST /admin/suggestions/{id}/confirm` `{ has_palquinho, is_other_event?, events[] }` → marca o dia e **acrescenta** o evento do pedido (nota = organizador) aos que o dia já tem, nunca substitui a lista (substituir apagava os eventos já marcados — bug corrigido). Estourou os 5 do dia → **409** com `detail`; sugestão já resolvida → **409** (evita duplicar o evento). Resolve a sugestão (action=confirm). No painel a sugestão pendente tem 3 botões: `confirmar SIM` (verde), `NÃO (outro rolê)` (laranja) e `descartar`.
    - `DELETE /admin/suggestions/{id}` → **pendente**: descarta (action=dismiss, vai pro arquivo); **já arquivada (solved)**: apaga de vez do banco — é assim que o admin limpa o arquivo e mantém só o importante.
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
- **Sugestões arquivam**: confirmada ou descartada vai pro **arquivo** (`status=solved`, com `action confirm/dismiss` + `solved_at`) — o admin confere o histórico antes de soltar o link. No arquivo tem botão **apagar** que remove a sugestão de vez (DELETE em item solved), pra deixar só o importante.
- **Nada de votação**: sugestão serve pra *informar* o admin (data + organizador), não pra votar SIM/NÃO.
- **Calendário do admin**: verde = SIM marcado, contorno vermelho = NÃO marcado (com nota/link), neutro = sem marcação.
- **Feedback visual**: confete arco-íris atrás do SIM quando tem palquinho; favicon ✅/❌ conforme o dia.

## Frontend (comportamento)
- **Tela inicial**: SIM/NÃO gigante, data acima, faixa da semana atual no rodapé (dias verdes/vermelhos; hover mostra as notas do dia, clique abre o Instagram), lista de eventos com nota clicável quando tem link. No canto superior direito fica uma **engrenagem** que abre um **menu flutuante no meio da tela** com: "quer divulgar um evento? manda aqui", "calendário de eventos", Instagram e, no fim, a nota "O tempalquinhohoje é uma iniciativa autônoma de estudantes sem relação com organizadores e instituições da universidade!". O atalho `ç` continua levando pro admin.
- **Sugestão**: modal com **mini calendário** (navegável, dias passados bloqueados, dia escolhido em verde) + organizador + Instagram opcional.
- **Admin**: login com senha, calendário mensal, painel do dia (SIM/NÃO/remover), **editor de eventos** (cada um com nota + link, botão `+` até 5, `✕` apaga), **prévia ao vivo** do dia abaixo do calendário, sugestões com abas **pendentes / arquivo**, botão **compartilhar (imagem)**.
- **Compartilhar (imagem)** — no admin, botão de ícone no painel do dia (`ShareModal.tsx` + `ShareCard.tsx`, lib `html-to-image`). Gera três PNGs, cada um com botão próprio: **semana** (feed 1080×1080), **dia feed** (1080×1080) e **dia stories** (1080×1920). O cartão do dia usa o visual da tela principal (SIM verde / NÃO vermelho / outro rolê laranja, confete, nota + `@` dos organizadores, listinha da semana com anel no dia); o cartão da semana é uma lista vertical dos 7 dias (quadrado colorido + nota de cada dia; **dia vermelho mostra só o quadrado, sem nota**) com o título "Calendário da semana: X a Y de <mês>". Usa o **rascunho** atual (o que está na tela) do dia selecionado; os outros dias da semana vêm do estado salvo. Cartões desenhados em 360px (feed/semana) e 300px (stories) e exportados via `pixelRatio` 3/3/3.6 → 1080. O `@` sai do link do Instagram (`instaHandle`).
- **Mini calendário no modal e calendário do admin**: semana começa no domingo.

## Posts do Instagram (template padrão)
- **`instagram/post-exact.html` é o formato padrão** pra qualquer post informativo no Instagram que eu pedir — reusar essa base e só trocar o texto, nunca inventar layout novo.
- **Formato**: cartão 360×360 exportado com Chrome headless `--force-device-scale-factor=3 --window-size=360,360` → PNG **1080×1080**.
- **Visual**: fundo `#000`, confete de **90 peças** gerado com `seed=7` (LCG `9301/49297/233280`), paleta `['#ef4444','#f97316','#facc15','#16a34a','#3b82f6','#6366f1','#8b5cf6','#ec4899']`, `filter: saturate(.78) brightness(.82)`, `border-radius: 2px`.
- **Estrutura**: `.sc-content` = texto do anúncio (`.sc-note`, `white-space: pre-line`, `\n` entre parágrafos; branco `#fff`, font `.82rem/700`, line-height 1.45); `.sc-bottom` = **legenda de 3 dias** (verde `sim` / laranja `outro evento` / vermelho `não`, quadrados 36px) + `.sc-footer` `tempalquinhohoje.com ·` **ícone SVG Instagram** `tempalquinhohoje` (sem `@`; ícone = mesmo do `MainScreen.tsx`, `viewBox 0 0 24 24`, só o ícone, não o `@`). Rodapé `#e2e8f0`, legendas `#fff`.
- **Tom do texto**: jovem/casual — **não usar ponto final de frase** (terminar com `!` ou sem pontuação), abertura tipo `INFORMAÇÕES:` em caixa alta. Exemplo de texto-base (post de anúncio): "INFORMAÇÕES:\nAlém de palquinhos, também divulgamos OUTROS EVENTOS que rolam pela UFSCar!\nFique de olho no calendário para ficar por dentro de tudo\nTem ou sabe de algum evento para divulgar? Manda uma sugestão pelo site ou pelo Instagram!\nQuer anunciar um evento sem ligação com a UFSCar? Também entre em contato para conversarmos\nLembre-se: pensou se tem palquinho, pensou tempalquinhohoje.com 😺👍".
- **Contraste AAA garantido por sombras fortes** (camadas opacas apertadas coladas no glifo, depois as largas): `.sc-note`/`.sc-leg-cap`/`.sc-footer` → `0 0 2px #000, 0 0 5px #000, 0 0 11px #000, 0 0 24px rgba(0,0,0,1), 0 0 52px rgba(0,0,0,.98), 0 0 100px rgba(0,0,0,.92)` (nota) / sem a última camada (legenda/rodapé). Pior caso medido ≥7:1 sobre qualquer confete.
- **Validar sempre** (3 checagens obrigatórias após regenerar o PNG):
  1. **Sem overflow**: injetar script no HTML (cópia temp, não no original) que imprime `MEASURE card=<clientHeight>/<scrollHeight> foot=<clientWidth>/<scrollWidth>` — card precisa dar `360/360` e rodapé `320/320`. Se estourar (texto novo mais longo), apertar: font `.86`→`.82rem`, line-height `1.5`→`1.45`, gap `12`→`10px`, margem rodapé `12`→`8px`.
  2. **Contraste**: `python instagram/check_contrast.py instagram/post-exact.png` (e passar a caixa do emoji como 2º arg `x,y,w,h` em px do PNG se o emoji estiver no texto — medir com `<span id="emo">` + `getBoundingClientRect()*3`; senão o rosto amarelo gera falso positivo de 1,3:1). Meta: mínimo ≥4,5:1 (AA), média ≥7:1 (AAA) — com as sombras atuais o mínimo fica ~8-10:1.
  3. **Confete**: script acima reporta % de pixels coloridos (meta ~11%) e o tamanho do PNG (1080×1080).
- **Gerar PNG**: `Start-Process chrome -ArgumentList "--headless=new","--disable-gpu","--no-sandbox","--force-device-scale-factor=3","--window-size=360,360","--hide-scrollbars","--virtual-time-budget=4000","--run-all-compositor-stages-before-draw","--screenshot=<png>",<url>` — o `--virtual-time-budget=4000` + `--run-all-compositor-stages-before-draw` são obrigatórios, senão o confete não renderiza e o PNG sai sem ele.
- **Emoji 😺👍**: renders no PNG normalmente (fonte do sistema); fica no fim da última linha do `.sc-note`.
- **Pasta**: manter só o `.html`, o `.png` atual e o `check_contrast.py` em `instagram/` — apagar versões antigas (`post-*_v*.png` etc.) conforme pedir novas.

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