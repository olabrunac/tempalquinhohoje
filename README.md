# temPalquinhoHoje

> **tem palquinho hoje?** — SIM gigante ou NÃO gigante.

Site que responde se hoje tem palquinho. **O default é NÃO**: só muda quando o admin
marca o dia. Quem souber de um palquinho manda uma sugestão (data + organizador + link
opcional do Instagram) e o **admin confirma** ou **descarta** no painel.

🔗 **No ar:** https://tempalquinhohoje.com (alias: https://palquinho.com)

## Funcionalidades

- **SIM verde gigante / NÃO vermelho gigante** sobre fundo preto, com a data em cima.
- **"NÃO (outro rolê)" laranja**: dia sem palquinho, mas que tem outro evento grande pra anunciar.
- **Confete arco-íris** caindo atrás do SIM quando tem palquinho (e ao navegar pra um dia SIM).
- **Favicon dinâmico**: ✅ verde quando tem, ❌ vermelho quando não tem.
- **Aviso de "próximo palquinho"**: em dia vermelho ou laranja, uma pílula clicável mostra
  quando é o próximo dia SIM e pula direto pra ele.
- **Enquete "você vai?"**: em dia SIM de hoje em diante, `[Sim]` / `[Não]` + contador
  `12/20 vão`. Uma resposta por navegador (token anônimo no `localStorage`), trocável,
  sem nome/e-mail/IP. O contador público mostra só quem vai.
- **Faixa da semana atual** no rodapé: cada dia verde (SIM), laranja (outro rolê) ou
  vermelho (NÃO); passar o mouse mostra as notas do dia e clicar abre o dia.
- **Até 5 eventos por dia**, cada um com sua nota (aceita quebra de linha) e seu próprio
  link do Instagram. Nota que tem link vira clicável (sublinhada, com ↗) pra não parecer
  texto morto. Vale tanto pra dias SIM quanto pra dias NÃO/laranja.
- **Sugestão anônima** com mini calendário clicável (data + organizador + Instagram opcional).
- **Menu da engrenagem**: divulgar um evento, calendário de eventos, Instagram, e o aviso
  de que o site é uma iniciativa autônoma de estudantes.
- **Calendário público de eventos** em `/eventos`.
- Tema escuro no site inteiro (tela principal, admin e modais).

## Admin (`/admin`)

- Login com senha (fica **só na memória** do React: recarregar a página exige logar de novo).
- Calendário mensal pra marcar **SIM**, **NÃO**, **NÃO (outro rolê)** e desmarcar o dia.
- Editor de eventos: cada um com nota + link, botão `+` até 5, `✕` apaga. A lista salva
  **substitui** a do dia.
- **Prévia ao vivo** do dia abaixo do calendário, antes de salvar.
- Sugestões com abas **pendentes / arquivo** (confirmada ✓ / descartada ✗, cada uma com
  botão apagar; no arquivo o apagar remove de vez).
- **Compartilhar (imagem)**: gera três PNGs prontos pro Instagram — **semana** (feed
  1080×1350), **dia feed** (1080×1350) e **dia stories** (1080×1920), com o mesmo visual
  da tela principal. O cartão da semana tem tipografia adaptativa: cresce quando a semana
  tem pouco evento e encolhe (sem cortar nem quebrar título) quando está cheia.

O atalho `ç` leva pro admin a partir da tela principal.

## Stack

- **Backend**: FastAPI + SQLAlchemy (`backend/app`), SQLite em dev e PostgreSQL (Neon) em produção.
- **Frontend**: Vite + React + TypeScript (`frontend/src`), CSS puro.
- **Deploy**: Vercel (build do frontend + função serverless `api/index.py` que importa o app FastAPI).

```
backend/            app FastAPI (api/palquinho.py tem os endpoints)
api/index.py        adaptador serverless da Vercel
frontend/src/       telas (MainScreen, AdminScreen, EventsScreen, modais, ShareCard)
vercel.json         build + função Python
requirements.txt    deps da função serverless
```

## Rodando local

Backend (porta 8000) — PowerShell 5.1, sem `&&`:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r ..\requirements.txt
Copy-Item ..\.env.example .env   # depois preencha DATABASE_URL e ADMIN_PASSWORD
python -m uvicorn app.main:app --port 8000
```

Frontend (porta 5173, com proxy de `/api` pro backend):

```powershell
cd frontend
npm ci
npm run dev
```

### Variáveis de ambiente (`backend/.env`)

| Variável | O que é |
|---|---|
| `DATABASE_URL` | string de conexão (SQLite em dev, Postgres/Neon em prod) |
| `ADMIN_PASSWORD` | senha do admin, enviada no header `X-Admin-Key` |
| `ENVIRONMENT` | `dev` ou `prod` (em `prod` desliga `/docs` e `/openapi.json`) |
| `RUN_MIGRATIONS` | `true`/`false` — desliga o `init_db` do cold start (default `true`) |

O `.env` **nunca** vai pro repositório (é público); use o `.env.example` como base.

## Deploy

`git push origin main` → a Vercel builda e publica sozinha. As env vars
(`DATABASE_URL`, `ADMIN_PASSWORD`) ficam configuradas no projeto da Vercel, em Produção.

## Testes

Rodam com SQLite temporário, sem instalar nada extra:

```powershell
python backend/test_seguranca.py        # rate limit, auth, limites, headers
python backend/test_eventos.py          # eventos por dia, ordem, links, limite, migração
python backend/test_votos.py            # enquete "você vai?"
python backend/test_votos_sem_migracao.py  # deploy sem RUN_MIGRATIONS não derruba a home
python backend/test_banco_antigo.py     # banco legado com palquinho_vote antigo
```

O `test_votos.py` esgota o rate limit do IP de propósito — rode ele por último.

## Convenções

- Versão em `frontend/src/version.ts` (+0.1 a cada mudança visível no deploy; só vira
  `2.0` em mudança grande/quebradora) e exibida discretamente no canto da tela principal.
- SIM/NÃO é de horário de **Brasília** (`backend/app/localtime.py`); o servidor da Vercel é UTC.
- Rate limit é em memória (protege contra bot pequeno; morre no cold start).
