# Resumo tecnico - Estoque e integracao Thiago - 22/05/2026

## Contexto

Esta nota consolida a sessao de continuidade do modulo de estoque do ERP iNoovaTed e a integracao manual da ultima atualizacao do Thiago.

O projeto e um ERP multiempresa/multifilial em Django, PostgreSQL e Railway. O estoque e fisico por filial e nao replica saldo em nenhuma hipotese.

Durante esta sessao, o foco foi:

- manter a memoria tecnica do estoque;
- ajustar regras e UX de entrada XML, duplicidade, conferencia e Kardex;
- mapear pendencias reais;
- acoplar a branch do Thiago sem perder mudancas recentes;
- commitar, subir e validar Railway.

## Estado final conhecido

- Branch local: `main`.
- `main` alinhada com `origin/main` apos push.
- Commit final da integracao: `4869c47 Acopla modulo de lotes do Thiago`.
- Deploy Railway: `SUCCESS`.
- `/health/` em producao: OK.
- `/lotes/` em producao: redirect para login, rota protegida registrada.

## Arquivos alterados/documentados

### Codigo

- `apps/lotes/**`
- `apps/core/templates/core/_sidebar.html`
- `apps/core/templatetags/erp_extras.py`
- `apps/estoque/models/alerta.py`
- `apps/estoque/services/alerta_service.py`
- `apps/estoque/views/alerta.py`
- `apps/estoque/tests/test_movimentacao_service.py`
- `apps/compras/tests/test_entrada_recebimento.py`
- `config/settings/base.py`
- `config/settings/test.py`
- `config/urls.py`

### Migrations

- `apps/estoque/migrations/0003_alter_alertavencimento_nivel_risco.py`
- `apps/lotes/migrations/0001_initial.py`
- `apps/lotes/migrations/0002_alter_inspecaolote_created_at.py`

### Docs atualizados

- `docs/HANDOFF.md`
- `docs/AGENTS.md`
- `docs/ESTOQUE_FECHAMENTO_MVP.md`
- `docs/BUGS.md`
- `docs/DEPLOY_LOG.md`
- `docs/REPLICATION_RULES.md`
- `docs/RESUMO_TECNICO_ESTOQUE_2026-05-22.md`

## Processo do Thiago

Thiago trabalha em branch paralela, normalmente `origin/thiago/dashboard`.

Regra obrigatoria:

1. Buscar ultima versao antes de trabalhar:
   ```powershell
   git fetch origin main thiago/dashboard
   ```
2. Conferir divergencia:
   ```powershell
   git rev-list --left-right --count main...origin/main
   git log --oneline --decorate -3 origin/main
   git log --oneline --decorate -3 origin/thiago/dashboard
   ```
3. Se a branch do Thiago estiver baseada em commit antigo, nao fazer merge cego.
4. Acoplar manualmente apenas as novidades.
5. Preservar mudancas recentes de estoque, compras, produtos, UI, temas e docs.
6. Rodar check/testes.
7. Commitar na `main`.
8. Push.
9. Acompanhar Railway ate `SUCCESS`.

Ultimo caso real:

- Branch do Thiago: `origin/thiago/dashboard`.
- Commit: `0ce65bc feat: modulo Lotes com rastreabilidade bidirecional e alertas de vencimento 6 faixas`.
- Integracao feita manualmente.
- Commit final: `4869c47`.

Motivo da integracao manual:

- A branch do Thiago estava atrasada em relacao a `main`.
- Merge direto poderia remover mudancas recentes do estoque e da entrada XML.

## Decisoes importantes

### Estoque

- Estoque nunca replica saldo.
- Transferencia entre filiais e movimento bilateral auditado, nao replicacao.
- Toda alteracao de saldo deve passar por `MovimentacaoService`.
- Produto com controle de lote exige lote em movimentacao fisica.
- Lote vencido/bloqueado nao pode sair por venda comum.
- Entrada efetivada bloqueia edicoes operacionais indevidas.

### Entrada XML

- Nota de qualquer CPF/CNPJ deve ser aceita.
- CNPJ/CPF diferente da filial vira alerta, nao bloqueio.
- Mensagem padrao:
  - `Atencao, essa nota nao possui o mesmo CNPJ que o cadastrado na filial. Essa nota esta vinculada ao CNPJ: <documento>.`
- XML duplicado deve abrir entrada existente.
- Usuario deve ver acoes simples:
  - `Continuar conferencia`;
  - `Cancelar entrada anterior`.
- Se a entrada ja movimentou estoque, cancelar deve abrir revisao de impacto e registrar auditoria.

### Kardex / Extrato

- Coluna correta: `Extrato`.
- Sobreposicao: `Extrato (Ficha Kardex)`.
- Deve mostrar foto, saldo, minimo, reposicao, giro diario, giro/mes, cobertura, custos, valor de venda total, ultimas movimentacoes, historico de preco/custo e lotes.
- Movimentacoes sempre em ordem desc por data/hora.
- Entrada: `Quantidade adicionada`.
- Saida: `Quantidade retirada`.
- Mostrar `Estoque anterior` e `Saldo apos`.
- Alerta de minimo fica no card `Disponivel`, com destaque vermelho e tooltip.

### UI e temas

- Tema claro: branco/cinza claro com laranja.
- Tema escuro: preto/cinza escuro com azul.
- Evitar amarelo forte no tema escuro.
- Mensagens criticas devem usar vermelho claro legivel.
- Botao principal deve ser solido e coerente com o tema.
- Sidebar deve suportar logos grandes/horizontais sem quebrar.

## Problemas encontrados

- Branch do Thiago atrasada em relacao a `main`.
- Merge cego era arriscado.
- Mudanca de alerta de vencimento quebrou testes antigos que esperavam `ALTO`.
- `makemigrations` local sem `DATABASE_URL` falhou; usar variavel temporaria ou settings de teste quando apropriado.
- Kardex tinha problemas visuais anteriores:
  - abria deslocado;
  - cards grandes;
  - numeros soltos;
  - alerta no card errado;
  - texto `Estrato` incorreto.
- Entrada XML duplicada tinha mensagens e acoes confusas.
- Tema escuro expunha cores amarelas ruins em mensagens.

## Solucoes aplicadas

- App `apps.lotes` integrado.
- App `apps.lotes` registrado em `LOCAL_APPS`.
- Rota `/lotes/` adicionada.
- Link `Lotes` adicionado na sidebar desktop/mobile.
- Filtro `dict_get` criado para templates.
- Faixas de vencimento atualizadas para `D1`, `D7`, `D30`, `D60`, `D90`, `D180`.
- Valores legados de alerta mantidos por compatibilidade.
- Testes atualizados para esperar `D7` em vencimento proximo.
- Migrations geradas.
- Deploy acompanhado ate sucesso.
- Docs permanentes atualizados.

## Validacoes executadas

```powershell
python manage.py check --settings=config.settings.test
python manage.py test apps.estoque.tests.test_movimentacao_service apps.estoque.tests.test_forms_views apps.compras.tests.test_entrada_recebimento --settings=config.settings.test --verbosity 1
```

Resultado:

- Check: OK.
- Testes: 116 OK.
- `makemigrations --check --dry-run`: OK apos gerar migrations necessarias.
- Railway deploy: `SUCCESS`.

## Pontos criticos

- Nao fazer merge cego de branch paralela.
- Nao escrever saldo direto fora de service.
- Nao replicar estoque.
- Nao permitir entrada efetivada ser editada como se estivesse aberta.
- Nao deixar produto criado pelo XML ir ao PDV/venda se estiver incompleto.
- Nao usar laranja/amarelo forte como destaque no tema escuro.
- Nao mostrar informacao tecnica demais para operador final.
- Nao testar certificados reais/eventos fiscais sem autorizacao explicita.

## Pendencias

- Refinar tela de XML duplicado:
  - remover textos tecnicos;
  - organizar botoes;
  - usar `Cancelar entrada anterior`;
  - revisar impacto se estoque ja foi movimentado.
- Melhorar conferencia de entrada:
  - remover rolagem horizontal;
  - mover edicao de lote/validade para sobreposicao;
  - permitir remover item da entrada com auditoria.
- Melhorar explicacao visual da auditoria de entrada.
- Validar novamente em producao os fluxos:
  - entrada XML;
  - duplicidade;
  - conferencia;
  - custo;
  - finalizacao;
  - pos-efetivacao;
  - Kardex;
  - lotes.
- Fazer bateria final de XMLs reais variados apenas no fechamento do modulo.
- Depois congelar estoque e mexer somente em bug.

## Cuidados para proximas IAs

- Ler `docs/AGENTS.md`, `docs/HANDOFF.md`, `docs/ESTOQUE_FECHAMENTO_MVP.md`, `docs/REPLICATION_RULES.md` e `docs/BUGS.md` antes de agir.
- Conferir `git status` antes de editar.
- Fazer `git fetch origin main thiago/dashboard` antes de commit/push.
- Nao reverter alteracoes locais nao feitas por voce.
- Se houver mudancas do Thiago, comparar e acoplar manualmente.
- Rodar testes antes de push.
- Acompanhar Railway apos push.
- Documentar qualquer nova regra permanente em `/docs`.
