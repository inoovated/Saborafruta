# Resumo tecnico - entradas, varios produtos, custos e UI - 2026-05-26

## Contexto da tarefa

Esta sessao evoluiu a etapa de conferencia de entrada para suportar um caso operacional novo: uma linha da nota fiscal pode ser recebida como varios produtos internos. O exemplo usado foi uma entrada de peixe inteiro que, no estoque, precisa virar cabeca, file e outros cortes/produtos.

O objetivo foi deixar esse fluxo pronto para uso real, sem obrigar o usuario a ir e voltar entre telas. A tela de vinculacao continuou sendo o fluxo principal para equivalencia simples, e a nova aba `Varios produtos` passou a concentrar os casos especiais.

Tambem foram refinadas as telas de custos para tratar produtos gerados individualmente, evitando que os custos de varios produtos aparecessem misturados em uma unica linha.

## Arquivos alterados

Principais arquivos alterados ao longo da sessao:

- `apps/compras/models/entrada_nf.py`
- `apps/compras/migrations/0012_itementradanfprodutogerado.py`
- `apps/compras/migrations/0013_produto_gerado_custo_manual.py`
- `apps/compras/migrations/0014_item_quantidade_xml_original.py`
- `apps/compras/services/compra_service.py`
- `apps/compras/services/entrada_custo_service.py`
- `apps/compras/services/entrada_produto_service.py`
- `apps/compras/templates/compras/entrada/conferencia.html`
- `apps/compras/templates/compras/entrada/custos.html`
- `apps/compras/tests/test_entrada_recebimento.py`
- `static/css/tailwind-built.css`
- `.impeccable/critique/2026-05-26T07-28-59Z__apps-compras-templates-compras-entrada-custos-html.md`

Documentacao atualizada nesta entrega:

- `docs/HANDOFF.md`
- `docs/DEPLOY_LOG.md`
- `docs/BUGS.md`
- `docs/UI_RULES.md`
- `docs/REPLICATION_RULES.md`
- `docs/RESUMO_TECNICO_ENTRADAS_VARIOS_PRODUTOS_2026-05-26.md`

## Decisoes importantes

- O nome operacional escolhido foi `Varios produtos`, evitando termos como `desdobramento`, porque esse termo pode nao ser claro para usuarios brasileiros.
- A equivalencia simples continua na aba `Produto unico`.
- A conversao de uma linha para varios produtos fica em aba propria, ao lado de `Produto unico`, para nao poluir a tela de vinculacao comum.
- Se um item ja tem vinculo individual e o usuario salva varios produtos, o vinculo individual e substituido automaticamente.
- Uma linha configurada como varios produtos deixa de exigir produto interno unico.
- Na tabela de vinculacao, item com varios produtos nao deve mostrar conversao, lote e quantidade final como se fossem da linha mae.
- Para itens com varios produtos, os detalhes de quantidade, lote, validade, custo percentual e observacao pertencem aos produtos gerados.
- `Qtd. final` na equivalencia simples nao deve ser editada diretamente; ela e calculada por `Qtd nota x Conversao`.
- `Qtd nota` pode ser editada, mas deve marcar `editado` em vermelho pequeno e permitir voltar para a quantidade original da nota.
- A tela de custos deve separar visualmente `Produto unico` de `Varios produtos`.
- No rateio de custos, cada produto gerado deve aparecer em linha propria, com referencia ao item de origem.

## O que foi concluido nesta sessao

- Criado o conceito persistente de produtos gerados por item de entrada, via `ItemEntradaNFProdutoGerado`.
- Criada tela/aba `Varios produtos` na conferencia.
- Permitido configurar varias linhas de produto interno para uma unica linha da nota.
- Cada linha de varios produtos suporta:
  - produto interno;
  - quantidade;
  - lote;
  - validade;
  - percentual de custo;
  - observacao.
- Se o percentual de custo ficar vazio, o custo e rateado automaticamente por quantidade.
- Item com varios produtos passa a ser considerado vinculado para avancar de etapa.
- Ao salvar varios produtos, o vinculo individual anterior do item e removido.
- A tela principal de vinculacao mostra `Receber como varios produtos` e `Ver itens`.
- A listagem de varios produtos pode ser filtrada para mostrar apenas itens ja configurados como varios produtos.
- Itens configurados como varios produtos receberam flag verde especifica, diferente do vinculo individual.
- A linha principal de item com varios produtos foi simplificada:
  - `Qtd nota` mostra somente a origem da nota;
  - `Conversao` mostra `Nos itens`;
  - `Qtd. final` mostra `Ver itens`;
  - `Lote` mostra `Ver itens`.
- Mobile da conferencia deixou de abrir edicao simples para itens com varios produtos.
- Tela de custos passou a ter abas `Produto unico` e `Varios produtos`.
- Produtos gerados aparecem individualmente no rateio de custos.
- Cada produto gerado mostra origem do item da nota.
- Custo unitario manual foi restaurado tanto para item unico quanto para produto gerado.
- Quantidade de estoque e quantidade da nota passaram a ser tratadas com mais cuidado na conversao.
- `Qtd. final` deixou de ser campo editavel, para evitar inconsistencia entre causa e resultado.
- A tela de custos foi revisada com `impeccable critique`.

## Bugs encontrados

- A etapa seguinte acusava item sem vinculo quando o item estava configurado como varios produtos.
- Na tela de custos, itens com varios produtos apareciam inicialmente agrupados em uma unica linha, dificultando a leitura do custo por produto final.
- Ao ir para a tela de custos, havia percepcao de piscada/carregamento intermediario antes da tela correta.
- O botao de selecao de modo estava com laranja muito forte em alguns estados.
- A mensagem abaixo de lote/validade consumia espaco e gerava ruido visual.
- A linha de item com varios produtos ainda mostrava campos de conversao, lote e quantidade final como se fossem aplicaveis a linha mae.
- A edicao direta de `Qtd. final` poderia criar divergencia silenciosa entre `Qtd nota`, `Conversao` e estoque final.
- A tela local de custos com `settings.test` fora do runner retornou 500 porque o SQLite de teste nao tinha tabelas persistidas.
- O detector automatico do `impeccable` falhou com `bundled detector not found`; a critica precisou usar revisao manual + Browser.

## Correcoes aplicadas

- Varios produtos passaram a contar como item vinculado nas validacoes de avancar etapa.
- Custo de produtos gerados passou a ser calculado e exibido por produto gerado.
- A listagem de custos ganhou modo separado para `Produto unico` e `Varios produtos`.
- A composicao de custo para varios produtos passou a distribuir o item de origem entre os produtos gerados por percentual manual ou rateio automatico.
- A linha principal de conferencia foi alterada para nao mostrar campos indevidos em item de varios produtos.
- `Qtd. final` deixou de ser enviada no formulario de vinculacao simples.
- Backend passou a ignorar edicao manual de quantidade final nesse fluxo.
- `Qtd nota` ganhou persistencia de quantidade original e botao de reset.
- Testes foram ajustados para garantir que `Qtd. final` seja calculada, nao editada.
- UI da aba `Varios produtos` ganhou filtro `Ver apenas varios produtos` / `Ver todos`.
- Flag de item configurado como varios produtos foi diferenciada visualmente.
- Review `impeccable` da tela de custos foi persistido em `.impeccable/critique/`.

## Novas regras descobertas

- Item recebido como varios produtos nao tem produto interno unico.
- Lote, validade e quantidade final de varios produtos pertencem aos produtos gerados, nao ao item de origem.
- Um item com vinculo individual pode ser convertido para varios produtos sem desvinculacao manual previa.
- Se o usuario salva varios produtos, o sistema deve substituir o vinculo simples.
- Se o usuario quer alterar o resultado final da quantidade em produto unico, deve editar `Qtd nota` ou `Conversao`, nao `Qtd. final`.
- `Qtd. final` e sempre resultado calculado.
- A quantidade original da nota deve ser preservada quando a `Qtd nota` for editada.
- Em custos, produtos gerados devem ser linhas independentes, sempre com referencia ao item de origem.
- Percentual de custo vazio em varios produtos significa rateio automatico por quantidade.
- Produto gerado pode ter custo unitario manual proprio.
- UI de varios produtos deve aparecer apenas quando fizer sentido; a maioria dos itens continuara no fluxo de produto unico.

## Alteracoes importantes de arquitetura

- Adicionado modelo `ItemEntradaNFProdutoGerado`, ligado a `ItemEntradaNF` por `related_name='produtos_gerados'`.
- `ItemEntradaNF` ganhou `quantidade_xml_original` para preservar a quantidade original da nota quando a quantidade exibida/editada for ajustada.
- Produto gerado ganhou `custo_unitario_manual`, permitindo override de custo por produto gerado.
- `CompraService` passou a registrar movimentos de estoque para produtos gerados quando um item tem varios produtos.
- Validacoes de efetivacao passaram a considerar produtos gerados como forma valida de vinculo.
- Servicos de produto/custo passaram a excluir ou tratar separadamente itens com produtos gerados.
- A tela de custos passou a construir linhas de composicao com `custo_modo` (`unico` ou `varios`).
- A auditoria de entrada registra snapshot dos produtos gerados ao salvar configuracao.

## Mudancas de replicacao

- Varios produtos de uma entrada sao operacao local da filial atual.
- Produtos gerados nao replicam saldo, lote, custo, movimento ou auditoria para outras filiais.
- `ItemEntradaNFProdutoGerado` e detalhe operacional da entrada, nao cadastro global de equivalencia.
- Custo manual em produto gerado e local da entrada/filial.
- Quantidade original/editada da nota pertence ao item daquela entrada, sem replicacao.
- A conversao de um item para varios produtos nao cria clone de produto por fornecedor nem por nota.

## Mudancas de produtos

- Produto interno individual continua sendo o fluxo normal.
- Varios produtos permite que um item da nota gere multiplos produtos internos existentes.
- Produto gerado precisa apontar para produto interno cadastrado.
- Produto gerado pode ter quantidade propria, lote proprio, validade propria e custo proprio.
- Produto interno de item unico pode ser substituido por varios produtos sem passo manual de desvinculo.
- Produtos gerados aparecem na etapa de custos como itens custeaveis independentes.

## Mudancas mobile

- Mobile da conferencia respeita a regra de varios produtos.
- Item com varios produtos nao abre o formulario de edicao simples de produto unico.
- Mobile mostra `Ver itens vinculados` para levar o usuario a aba/area correta.
- A informacao de lote/validade em item de varios produtos aponta para os itens vinculados.
- Acoes e badges foram mantidos compactos para nao criar cards muito altos.

## Mudancas de UI/temas

- Aba `Produto unico` / `Varios produtos` foi adicionada na conferencia.
- Aba semelhante foi adicionada na tela de custos.
- Card/status `Varios produtos` foi removido/evitado quando ocupava espaco demais no topo.
- Flag verde `Recebendo como varios produtos` identifica item ja configurado.
- Botao/filtro `Ver apenas varios produtos` permite reduzir a lista.
- Linha principal de varios produtos passou a ser uma referencia, nao uma linha de edicao de conversao/lote.
- Mensagens longas abaixo de lote/validade foram removidas ou movidas para a tela correta.
- Cor do botao seletor foi suavizada ao longo dos ajustes.
- Revisao `impeccable` apontou que a tela de custos esta boa, mas ainda pesada:
  - formulario de composicao cria scroll horizontal em 1280px;
  - cards de resumo usam borda lateral colorida, padrao banido pelo Impeccable;
  - tabela de rateio tem chips demais competindo;
  - `Ignorar custos extras` parece acao perigosa por estar vermelho demais;
  - edicao manual de custo precisa ficar mais descobrivel.

## Possiveis riscos futuros

- Se a efetivacao nao validar todos os produtos gerados, pode movimentar estoque incompleto.
- Se soma de quantidades dos produtos gerados divergir da expectativa operacional, o sistema pode permitir resultado correto para alguns negocios e errado para outros. A regra precisa ser validada com casos reais.
- Percentual de custo manual que nao fecha 100% pode causar custo inesperado se o usuario nao entender o rateio automatico.
- Lote/validade por produto gerado precisa ser testado com produtos que exigem lote obrigatoriamente.
- Custo manual em produto gerado pode mascarar erro de rateio se usado sem auditoria clara.
- Produto gerado com produto interno errado pode movimentar estoque errado, ja que a linha de origem nao tem produto unico.
- Mobile precisa de QA real em aparelhos, porque a aba de varios produtos tem formulario mais denso.
- A tela de custos ainda precisa de polimento visual para reduzir scroll horizontal e excesso de chips.
- O `impeccable` esta instalado, mas nesta sessao nao apareceu na lista inicial de skills; em novas conversas pode ser necessario reiniciar/recarregar para carregar automaticamente.

## Proximos passos recomendados

1. Testar em producao uma NF real com caso de peixe/corte ou item que vira varios produtos.
2. Validar efetivacao de estoque com:
   - item unico;
   - item com varios produtos;
   - produto gerado com lote;
   - produto gerado sem lote;
   - produto gerado com custo manual.
3. Revisar se o percentual de custo deve exigir soma 100% ou se rateio automatico deve completar a diferenca.
4. Melhorar a tela de custos conforme review Impeccable:
   - grid responsivo no formulario;
   - remover bordas laterais coloridas dos cards;
   - esconder chips zerados ou deixa-los muito discretos;
   - tornar `Ignorar custos extras` um toggle neutro;
   - explicitar edicao manual de custo.
5. Remover ou simplificar o card generico `Com divergencia` da conferencia, se a regra final for resolver cada pendencia no proprio lugar.
6. Confirmar com o usuario se `Varios produtos` e o termo definitivo.
7. Criar testes adicionais para efetivacao com lote/validade obrigatorios em produtos gerados.
8. Rodar QA mobile completo da conferencia e custos.

## Pontos criticos para proximas IAs

- Nao voltar a editar `Qtd. final` diretamente na conferencia de produto unico.
- Nao recolocar conversao/lote/quantidade final na linha-mae de item com varios produtos.
- Nao tratar varios produtos como `produto_id` nulo pendente.
- Nao juntar produtos gerados em uma unica linha na tela de custos.
- Nao remover custo manual de produtos gerados; ele foi pedido explicitamente.
- Nao criar replicacao de produtos gerados para outras filiais.
- Nao alterar financeiro com custo manual de item; custo manual afeta custo/estoque, nao total financeiro da NF.
- Antes de mexer em tela de custos, considerar o snapshot do Impeccable em `.impeccable/critique/`.
- Existem arquivos sujos no workspace que podem nao ser desta sessao; nao reverter sem ordem expressa.

## Commits principais da sessao

- `c9bb83c6 Permite converter item vinculado em varios produtos`
- `66c4f8f6 Corrige custos de itens com varios produtos`
- `556bd82c Separa itens de varios produtos nos custos`
- `9c11adf9 Detalha produtos gerados no custo`
- `1e121515 Restaura edicao de custo e quantidade convertida`
- `57834dec Permite editar quantidade da nota`
- `2db5a2ca Remove edicao manual da quantidade final`
- `892bd0b9 Simplifica linha de varios produtos na conferencia`
- `0cb95073 Destaca e filtra itens com varios produtos`
- `6f7194e4 Refina layout da conferencia de entrada`

## Validacoes executadas

- `python manage.py check --settings=config.settings.test`
- `python manage.py test apps.compras.tests.test_entrada_recebimento --settings=config.settings.test --keepdb`
- Testes focados de varios produtos e quantidade da nota dentro de `EntradaRecebimentoTests`.
- QA visual com Browser em tela de conferencia e custos.
- `impeccable critique` manual/Browser para `apps/compras/templates/compras/entrada/custos.html`.

