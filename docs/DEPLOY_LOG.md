# Deploy log

Registro simples de disparos de deploy quando o Railway precisa receber um
commit novo pelo webhook do GitHub.

## 2026-05-20

- Motivo: Railway voltou apos outage parcial e o app publico ainda respondia
  `/health/` com 404, indicando deploy antigo.
- Base enviada: `488d653 Aprimora cadastro XML com lote e validade`.
- Escopo: consolidado do Thiago + estoque, entrada XML, fiscal/manifesto,
  resiliencia e preparacao Supabase/Cloudflare.
- Observacao: migrations e `ensure_quality_schema` rodam no `CMD` do Dockerfile.

## 2026-05-21

- Motivo: fechamento de estabilizacao do estoque MVP e integracao das mudancas paralelas de parametros/identidade da filial.
- Base enviada: `3aee713 Fecha estabilizacao do estoque MVP`.
- Railway: deploy `e43a9aa1-aef2-4212-a753-a2aa9aa1ba03` finalizado com `SUCCESS`.
- Migrations aplicadas em producao:
  - `core.0015_rename_registros_a_modulo_5a598c_idx_registros_a_modulo_a33783_idx_and_more`
  - `fiscal.0006_rename_regras_fisc_uf_aa0e88_idx_regras_fisc_uf_390d95_idx_and_more`
- Validacao local antes do deploy: 213 testes passaram.
- QA visual pos-deploy: dashboard, estoque, reposicao, movimentacoes, lotes, inventarios, entradas, produtos e promocoes abriram sem erro 500 e sem erros de console capturados.

## 2026-05-22

- Motivo: acoplar atualizacao paralela do Thiago com novo modulo de lotes, sem merge cego.
- Branch do Thiago: `origin/thiago/dashboard`.
- Commit do Thiago acoplado: `0ce65bc feat: modulo Lotes com rastreabilidade bidirecional e alertas de vencimento 6 faixas`.
- Base enviada: `4869c47 Acopla modulo de lotes do Thiago`.
- Railway: deploy `ea3e39cd-5b8c-4eab-8c0b-e09da2cc0a42` finalizado com `SUCCESS`.
- Validacao local antes do deploy:
  - `python manage.py check --settings=config.settings.test`;
  - `python manage.py test apps.estoque.tests.test_movimentacao_service apps.estoque.tests.test_forms_views apps.compras.tests.test_entrada_recebimento --settings=config.settings.test --verbosity 1` com 116 testes OK;
  - `makemigrations --check --dry-run` sem mudancas pendentes apos migrations geradas;
  - `git diff --check` OK.
- Validacao pos-deploy:
  - `/health/` respondeu OK;
  - `/lotes/` respondeu redirect para login, indicando rota protegida registrada.

## 2026-05-24

- Motivo: evolucao do fluxo de compras, conferencia, composicao de custo e custo manual por item.
- Commits relevantes enviados:
  - `5c21c6fe Permite ajuste manual do custo agregado`;
  - `cea28618 Ajusta reset do custo manual agregado`;
  - `6e296c9d Mostra indicador manual no custo agregado`.
- Escopo:
  - conferencia com item manual na etapa correta;
  - busca livre de produto;
  - aproveitamento de dados do XML no cadastro de produto;
  - composicao de custo simplificada;
  - ajustes fiscais avancados recolhidos;
  - custo unitario agregado editavel manualmente;
  - auditoria/reset do custo manual;
  - refinamentos de UI claro/escuro.
- Validacao local:
  - `python manage.py test apps.compras.tests.test_entrada_recebimento --settings=config.settings.test --verbosity 1` com 103 testes OK;
  - teste focado de custo manual OK;
  - `python manage.py makemigrations --check --dry-run --settings=config.settings.test` sem mudancas pendentes;
  - `python manage.py check --settings=config.settings.test` OK.
- Validacao pos-deploy:
  - `/health/` respondeu `status ok`.
