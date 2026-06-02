# Resumo tecnico da sessao - Compras, conferencia e custos

Sessao encerrada em 2026-05-24.

Este documento registra as decisoes, bugs, correcoes e regras descobertas durante a evolucao do fluxo de entrada XML, conferencia de itens, composicao de custo e custo manual por item.

## O que foi concluido

- Corrigido o erro 500 ao acessar entrada e conferencia de compra.
- Ajustado o fluxo da etapa 1 para a conferencia ser a tela principal de vinculacao, conversao, lote e validade.
- Removida a ideia de inserir item manual na tela inicial da NF; o item manual agora pertence a conferencia.
- Simplificado o cadastro manual de item: produto, quantidade, conversao, quantidade final, lote e validade.
- Removida a exigencia de EAN da nota e codigo do fornecedor para item manual.
- Item manual passa a usar o codigo de barras do produto interno selecionado.
- Item manual passa a aparecer como `Manual` no campo de identificacao da nota, sem inventar ID numerico.
- Produto da conferencia usa busca livre por ID, nome, codigo e barras; essa e regra global do sistema.
- Produto sem vinculo bloqueia o avanco para custos; se o operador nao quiser vincular, deve remover o item.
- Cadastro de produto a partir da conferencia aproveita dados do XML, incluindo CFOP quando disponivel.
- Fator de conversao foi tratado visualmente como `Conversao`.
- `Qtd Nota` deve mostrar a unidade da nota com fallback para unidade de estoque/produto.
- Restauracao de item removido deve preservar unidade, quantidade e conversao originais.
- Tela de custos foi redesenhada para ser operacional, sem excesso fiscal exposto.
- Parametros e componentes de custo foram unidos em um unico bloco.
- Ajustes fiscais avancados ficaram recolhidos por padrao: IPI, ST e ICMS normal.
- Removidos botoes redundantes: `Simular`, `Salvar componentes e recalcular` e `Aplicar custo composto`; ficou um unico botao `Salvar e recalcular custo`.
- Cards de resumo ficaram abaixo do bloco de composicao.
- Card `Diferenca contra total da nota` foi removido.
- Criada opcao `Ignorar custos extras`, para usar apenas valor dos produtos e desconto.
- Rateio de custo ficou com duas opcoes:
  - `Valor (Rateia o custo adicional de forma proporcional)`;
  - `Quantidade (Custo adicional igual para todos os itens)`.
- Opcao de rateio por peso foi removida do fluxo atual.
- Campo `Extra` substituiu `Adicionais`, porque custo extra e adicional eram a mesma coisa.
- Campo `Valor total produto NF` substituiu `Produtos`, deixando claro que vem do XML/entrada e nao e ajuste operacional.
- Frete, seguro, extra, desconto e valor total da NF foram mantidos editaveis para corrigir entrada manual ou XML incompleto.
- Desconto ganhou valor em R$ e percentual vinculados.
- Desconto passou a usar indicacao positiva em verde.
- `Custo total NF` ganhou destaque azul para associar com o valor base da nota.
- `Custos extras` usam vermelho claro.
- `Impostos` usam amarelo/ambar.
- `Desc.` mostra a composicao do desconto, incluindo base da NF, custo adicional e desconto.
- `Total agregado` e `Unit. agregado` foram organizados para mostrar o custo final que sera usado no produto/estoque.
- `Custo anterior unit.` foi renomeado para ficar mais claro que e o custo antes desta entrada.
- Coluna `Dif. %` voltou para mostrar aumento ou reducao entre custo anterior e unitario agregado.
- `Dif. %` deve exibir `Aumento de` com vermelho claro ou `Reducao de` com verde claro.
- Custo unitario agregado passou a poder ser editado manualmente direto na tabela.
- Edicao manual do custo unitario agregado nao altera NF nem financeiro.
- Item com custo manual mostra `Manual` em texto pequeno vermelho abaixo do custo.
- Criado botao pequeno de reset por icone para voltar ao custo calculado original.
- Edicao manual de custo foi auditada.
- Criados XMLs fiscais de teste para IPI, ST, ICMS recuperavel e bonificacao.

## O que ficou pendente

- Fazer QA visual final em producao depois do deploy, nos temas claro e escuro.
- Validar mobile da tela de custo com notas grandes.
- Confirmar se a etapa financeira consome somente o total da NF/parcelas e nunca o custo manual por item.
- Validar se o custo medio final esta sendo atualizado exatamente no momento correto da efetivacao de estoque.
- Criar tela/consulta de auditoria mais amigavel para ajustes manuais de custo, se o suporte precisar pesquisar depois.
- Decidir se no futuro havera motor fiscal completo para ST/ICMS por NCM, CEST, UF, regime e finalidade.
- Desenhar a etapa 4 de preco de venda com mockup proprio antes de implementar.
- Revisar backend legado de sugestoes em massa da conferencia; a UI principal nao usa mais esse fluxo.
- Testar mais casos de nota com multiplos lotes, item removido/restaurado e conversao com decimais.

## Bugs encontrados

- Erro 500 ao acessar `/compras/entradas/48/` e `/compras/entradas/48/conferencia/`.
- Item restaurado voltava com unidade e conversao trocadas.
- Item manual aparecia com ID numerico inventado.
- Item manual nao puxava corretamente o codigo de barras do produto.
- Tela de custos mostrava mais linhas do que os itens reais da nota.
- Itens removidos/restaurados ou duplicados podiam contaminar a listagem de custo.
- Alguns itens apareciam com custo zerado quando o valor da NF/XML nao era aplicado corretamente.
- Layout da listagem de custos ficava grosso, com muita quebra de linha.
- Cabecalho da tabela de custos desalinhava no tema escuro.
- Cores de custos, impostos, descontos e variacao ficaram agressivas em varias iteracoes.
- Campo de rateio ficou grande demais e ocupava espaco desnecessario.
- Textos longos como `Ajustado manualmente` quebravam a linha e poluiam a tabela.
- Botao/indicacao de reset do custo manual precisava existir sem ocupar texto.
- Percentual de variacao sumiu em uma das iteracoes e precisou voltar.

## Correcoes aplicadas

- Conferencia passou a tratar item manual como linha operacional da etapa 1.
- Cadastro de produto pelo modal passou a reutilizar informacoes vindas da nota quando existem.
- Layout de conferencia foi simplificado e cards sem acao real foram removidos ou tratados como status.
- Tela de custos foi reorganizada em:
  - controle de rateio;
  - composicao de custo;
  - ajustes fiscais avancados recolhidos;
  - cards de resumo;
  - listagem densa de rateio por item.
- Regras visuais foram refinadas para tema claro e escuro.
- Edicao manual de `Unit. agregado` foi implementada sem impactar NF/financeiro.
- Reset de custo manual foi implementado por icone.
- Auditoria registra edicao e remocao do custo manual.
- Testes de compras foram executados e passaram.

## Novas regras descobertas

- Busca de produto deve ser livre em todo o sistema: ID, nome, codigo e barras.
- Item sem produto vinculado nao deve seguir para custo; a alternativa e remover o item.
- Item manual nao precisa EAN da nota nem codigo fornecedor.
- Item manual deve usar dados do produto interno, incluindo codigo de barras.
- CFOP do XML deve preencher o cadastro do produto quando o produto e criado pela conferencia.
- A etapa de vinculacao nao deve mostrar custo; custo pertence a etapa 2.
- Fiscal avancado deve ficar escondido/recolhido por padrao.
- IPI/ST/ICMS so devem aparecer como ajuste avancado para quem precisa conferir ou preencher manualmente.
- ST nao deve ser calculado automaticamente por NCM nesta fase.
- ICMS normal fica fora do custo por padrao.
- Custo manual por item e uma correcao de custo do produto/estoque, nao uma alteracao da NF.
- Custo manual nao altera total da NF, financeiro, frete, seguro, desconto ou imposto.
- O custo unitario agregado e o custo de entrada que deve alimentar o historico/custo do produto.
- Se o custo unitario agregado for editado, essa edicao deve ser auditavel e visualmente marcada como manual.
- A listagem de custo deve ser densa e caber sem barra lateral quando possivel.

## Alteracoes importantes de arquitetura

- Entrada XML ficou mais claramente dividida em etapas:
  1. Vinculacao/conferencia;
  2. Custos;
  3. Financeiro;
  4. Preco de venda.
- Item manual deixou de ser acao da capa da NF e passou a fazer parte da conferencia.
- O custo efetivo do item passou a aceitar override manual isolado.
- Override manual do custo fica separado da composicao da NF.
- Composicao da NF continua calculada por campos globais: valor dos produtos, frete, seguro, extra, impostos marcados e desconto.
- Rateio calcula a distribuicao dos custos globais, mas o custo manual pode substituir o resultado final do item.
- Auditoria ganhou papel importante para explicar custo manual sem poluir a UI.

## Mudancas de replicacao

- Nao houve replicacao de estoque, lote, custo efetivado ou financeiro.
- Custo, lote, saldo e movimento continuam por filial.
- Equivalencia fornecedor/produto e memoria operacional da entrada, nao movimento replicavel.
- Produto continua unico com vinculo por filial; XML nao deve criar clone de produto por fornecedor.
- Custo manual de entrada nao deve ser replicado para outra filial.
- Dados fiscais/cadastrais aproveitados do XML ajudam o cadastro local, mas nao alteram automaticamente outras filiais.

## Mudancas de produtos

- Produto criado a partir da conferencia deve aproveitar dados da nota quando existirem.
- Codigo de barras do produto interno tem prioridade para item manual.
- CFOP de compra/entrada pode ser preenchido a partir da nota no cadastro do produto.
- Produto precisa estar vinculado antes de calcular custo.
- Custo unitario agregado da entrada e a referencia para atualizar custo/historico do produto.
- Custo medio deve considerar estoque atual e a nova entrada, nao apenas sobrescrever cegamente.

## Mudancas mobile

- A conferencia e a tela de custos devem manter a mesma regra de negocio no mobile.
- Mobile nao deve criar fluxo separado para sugestoes ou custo.
- Campos de custo precisam empilhar de forma controlada, mas no desktop devem ser compactos em linha.
- Tabelas densas podem precisar virar cards/lista no mobile, preservando:
  - produto;
  - quantidade;
  - custo unitario NF;
  - custos extras;
  - impostos;
  - desconto;
  - unitario agregado;
  - variacao.

## Mudancas de UI e temas

- Evitar campos enormes sem necessidade.
- Rateio deve ser seletor compacto, com a opcao de ignorar custos extras ao lado.
- Remover textos explicativos longos da tela principal quando nao agregam decisao.
- `Ajustes fiscais avancados` deve ser um bloco recolhido, discreto e com cor neutra.
- `Custo total NF` usa azul.
- `Custos extras` usam vermelho claro.
- `Impostos` usam amarelo/ambar.
- `Desconto` usa verde.
- `Aumento de` usa vermelho claro.
- `Reducao de` usa verde claro.
- Manual deve ser indicacao pequena em vermelho, abaixo do custo editado, sem quebrar layout.
- Botao de reset deve ser iconico e pequeno.
- Cabecalho da tabela deve alinhar exatamente com as colunas no tema claro e escuro.

## Regra de custo medio

O custo unitario agregado e o custo unitario efetivo da nova entrada.

Quando a entrada for efetivada, o custo medio recomendado e:

```text
custo_medio_novo =
  (estoque_atual * custo_medio_atual + quantidade_entrada * custo_unitario_agregado)
  / (estoque_atual + quantidade_entrada)
```

Exemplo:

- Estoque atual: 10 unidades.
- Custo medio atual: R$ 100,00.
- Nova entrada: 5 unidades.
- Custo unitario agregado: R$ 130,00.

```text
(10 * 100 + 5 * 130) / 15 = 110,00
```

Resultado: custo medio novo de R$ 110,00.

Se o operador editar manualmente o custo unitario agregado, esse valor manual entra na formula como custo da nova entrada. A NF e o financeiro continuam com seus valores originais.

## Fluxo fiscal decidido

- IPI:
  - costuma vir em nota de industria, importador ou estabelecimento equiparado;
  - se nao for recuperavel, normalmente entra no custo;
  - se for recuperavel, pode ficar fora do custo conforme orientacao fiscal/contador.
- ST:
  - depende de produto, NCM, CEST, UF, regime, operacao e legislacao;
  - se vier valor de ST na nota, normalmente entra no custo;
  - se nao veio na nota, nao inventar valor manual sem orientacao.
- ICMS normal:
  - geralmente fica fora do custo quando e recuperavel;
  - no Simples Nacional normalmente o cliente nao usa credito como regime normal;
  - so somar ao custo quando o contador orientar que aquele ICMS nao e recuperavel.

## Possiveis riscos futuros

- ST por NCM/UF/regime e complexo; automatizar sem motor fiscal pode gerar custo errado.
- Custo manual por item pode mascarar erro de XML se nao houver auditoria clara.
- Se custo manual nao for considerado na atualizacao de custo medio, produto ficara com custo incorreto.
- Se custo manual alterar NF/financeiro por engano, o contas a pagar pode divergir da nota real.
- Longas descricoes de produto podem quebrar a listagem e esconder colunas finais.
- Tema escuro exige QA proprio; cores que funcionam no claro podem ficar agressivas ou ilegiveis no escuro.
- Entrada com desconto global grande pode gerar custo negativo em algum item se o rateio nao tiver trava.
- Notas com bonificacao, brinde, item zerado ou desconto por item precisam de mais testes.

## Proximos passos recomendados

1. Validar em producao uma NF real com muitos itens e desconto global.
2. Validar uma NF de industria com IPI.
3. Validar uma NF com ST vindo no XML.
4. Validar entrada manual sem XML.
5. Confirmar que item sem produto bloqueia custos.
6. Confirmar que custo manual aparece como `Manual` e pode ser resetado.
7. Confirmar que custo manual nao altera financeiro.
8. Confirmar que a efetivacao atualiza custo medio usando o custo unitario agregado.
9. Fazer QA visual em tema claro, tema escuro, notebook e mobile.
10. Definir futuramente se havera motor fiscal de ST/ICMS ou se o sistema mantera a regra de importar/preencher manualmente.

## Commits relevantes da sessao

- `5c21c6fe Permite ajuste manual do custo agregado`
- `cea28618 Ajusta reset do custo manual agregado`
- `6e296c9d Mostra indicador manual no custo agregado`

## Testes e verificacoes

- `python manage.py test apps.compras.tests.test_entrada_recebimento --settings=config.settings.test --verbosity 1`
  - Resultado: 103 testes OK.
- `python manage.py test apps.compras.tests.test_entrada_recebimento.EntradaRecebimentoTests.test_tela_custos_permite_custo_unitario_manual_sem_alterar_nf --settings=config.settings.test --verbosity 1`
  - Resultado: OK.
- `python manage.py makemigrations --check --dry-run --settings=config.settings.test`
  - Resultado: sem migrations pendentes.
- `python manage.py check --settings=config.settings.test`
  - Resultado: OK.
- `https://inovated.up.railway.app/health/`
  - Resultado: `status ok`.

## Resumo tecnico reutilizavel

O fluxo de compras foi organizado para separar claramente conferencia, custo e financeiro. A conferencia resolve produto, conversao, lote e validade. A tela de custos calcula custo por item com base no valor da NF, frete, seguro, extra, impostos marcados e desconto. IPI/ST/ICMS ficam recolhidos em ajustes fiscais avancados. O usuario pode ignorar custos extras quando quiser considerar apenas a nota. O rateio pode ser por valor ou quantidade. O custo unitario agregado e o custo final do item para atualizar produto/estoque. Esse custo pode ser editado manualmente direto na tabela; quando editado, nao altera NF nem financeiro, apenas o custo do item, e fica auditado com indicacao `Manual` e botao de reset.
