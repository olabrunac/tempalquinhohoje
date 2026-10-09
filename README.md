# temPalquinhoHoje

> **tem palquinho hoje?** — SIM gigante ou NÃO gigante.

Site que responde se hoje tem palquinho. **O default é NÃO** —
só muda quando o admin marca o dia. Quem souber de um palquinho manda uma sugestão
(data + organizador + link do anúncio no Instagram) e o **admin confirma** ou **descarta** no painel.

🔗 **No ar:** https://tempalquinhohoje.com (alias: https://palquinho.com)

## Funcionalidades

- **SIM verde gigante / NÃO vermelho gigante** sobre fundo preto, com a data em cima.
- **Confete arco-íris** caindo atrás do SIM quando tem palquinho.
- **Favicon dinâmico**: ✅ verde quando tem, ❌ vermelho quando não tem.
- **Faixa da semana atual** no rodapé: cada dia verde (SIM) ou vermelho (NÃO); passar o mouse
  mostra as notas do dia, e clicar abre o dia na agenda.
- **Até 5 eventos por dia**, cada um com sua nota (pode ter quebra de linha) e seu próprio link
  do Instagram. Nota que tem link vira clicável (sublinhada, com ↗) pra não parecer texto morto.
  Vale tanto pra dias SIM quanto pra dias NÃO que tenham outro evento grande pra anunciar.
- **Sugestão anônima** com mini calendário clicável (data + organizador + link opcional).
- **Admin** (`/admin`):
  - calendário mensal pra marcar **SIM** ou **NÃO** e desmarcar;
  - editor de eventos (cada um com nota + link, botão `+` até 5, `✕` apaga);
  - prévia ao vivo do dia abaixo do calendário, antes de salvar;
  - sugestões com abas **pendentes / arquivo** (histórico com confirmada ✓ / descartada ✗);
- Tema escuro em todo o site.
