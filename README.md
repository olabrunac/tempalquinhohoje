# temPalquinhoHoje

> **tem palquinho hoje?** — SIM gigante ou NÃO gigante.

Site que responde, num grão, se hoje tem palquinho (a festa do grupo). **O default é NÃO** —
só muda quando o admin marca o dia. Quem souber de um palquinho manda uma sugestão
(data + organizador + link do anúncio no Instagram) e o **admin confirma** ou **descarta** no painel.

🔗 **No ar:** https://tempalquinhohoje.vercel.app

## Funcionalidades

- **SIM verde gigante / NÃO vermelho gigante** sobre fundo preto, com a data em cima.
- **Confete arco-íris** caindo atrás do SIM quando tem palquinho.
- **Favicon dinâmico**: ✅ verde quando tem, ❌ vermelho quando não tem.
- **Faixa da semana atual** no rodapé: cada dia verde (SIM) ou vermelho (NÃO); passar o mouse
  mostra a nota, e clicar abre o Instagram do anúncio (alinha certinho no celular e no PC).
- **Nota + link do Instagram do anúncio**: tanto pra dias SIM quanto pra dias NÃO que tenham
  outro evento grande pra anunciar.
- **Sugestão anônima** com mini calendário clicável (data + organizador + link opcional).
- **Admin** (`/admin`):
  - calendário mensal pra marcar **SIM** ou **NÃO** (com nota e link) e desmarcar;
  - sugestões com abas **pendentes / arquivo** (histórico com confirmada ✓ / descartada ✗);
  - **contador de visitas** (abaixo do calendário, colapsável) — **visitas do admin não contam**.
- Tema escuro em todo o site.

## Stack

- **Backend**: FastAPI + SQLAlchemy (Python 3.12) — pasta `backend/`, adaptador serverless em `api/`
- **Frontend**: Vite + React + TypeScript — pasta `frontend/`
- **Banco**: SQLite (local) / Neon Postgres (produção)
- **Deploy**: Vercel (projeto `logger-s/tempalquinhohoje`, domínio `tempalquinhohoje.vercel.app`)
  — auto-deploy no `git push origin main`

## Estrutura

```
backend/app/        FastAPI app (models, schemas, api, db, settings)
frontend/src/       React app (MainScreen, AdminScreen, SuggestionModal, api client)
api/index.py        Adaptador serverless que importa o FastAPI app
vercel.json         Build do frontend + config de rotas SPA/API
```

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

> **Segredos**: `backend/.env` nunca vai pro git (`.gitignore`). Em produção as variáveis
> `DATABASE_URL` (Neon) e `ADMIN_PASSWORD` ficam no painel da Vercel.

## Endpoints principais

Todas as rotas usam o prefixo `/api/v1` (rota rápida: `PUT /admin/{day}`, etc.).

| Método | Rota | O que faz |
|---|---|---|
| GET | `/today` | Tem palquinho hoje? (`has_palquinho: null` = não marcado → site mostra NÃO) |
| GET | `/days` | Dias já marcados (com note/instagram) |
| POST | `/visits` | Conta uma visita à tela inicial (admin não conta) |
| POST | `/suggestions` | Amigo manda sugestão `{ day, organizer, instagram? }` |
| GET | `/admin/suggestions` | Pendentes (header `X-Admin-Key`); use `?status=solved` pro arquivo |
| POST | `/admin/suggestions/{id}/confirm` | Confirma a sugestão e marca o dia |
| DELETE | `/admin/suggestions/{id}` | Descarta a sugestão |
| PUT | `/admin/{day}` | Marca SIM/NÃO `{ has_palquinho, note?, instagram? }` |
| DELETE | `/admin/{day}` | Desmarca o dia |
| GET | `/admin/visits` | Resumo de visitas (hoje, total, últimos 30 dias) |
| GET | `/health` | Healthcheck |

## Fluxo

1. O amigo abre o site e vê o status de hoje: **SIM gigante verde** ou **NÃO gigante vermelho**
   (default NÃO, não-marcado).
2. No rodapé, a semana atual mostra de relance quais dias têm palquinho (verde) e quais não
   (vermelho). Dia verde ou NÃO-anunciado: hover mostra a nota, clique abre o Instagram.
3. Botão do canto — *"sabe de algum palquinho?"* — abre um modal com **mini calendário**:
   data + organizador (anônimo) + link do anúncio no Instagram (opcional).
4. No `/admin`, o admin:
   - vê as **sugestões pendentes**, confirma (marca o dia, aproveitando o Instagram da sugestão)
     ou descarta — tudo vai pro **arquivo** pra conferência do histórico;
   - marca dias direto no calendário como **SIM** (tem palquinho) ou **NÃO** (ex.: outro grande
     evento no dia, com nota e link pra anunciar);
   - acompanha as **visitas** por dia (abaixo do calendário).
5. Confirmando = a tela principal atualiza na hora.