# Fechamento do Estoque MVP

Atualizado em 21/05/2026.

## Objetivo

Consolidar o estado do modulo de estoque no MVP do ERP iNoovaTed, incluindo os fluxos entregues, regras que nao podem quebrar, pontos de integracao com compras/produtos/promocoes/PDV e checklist final de aceite.

## Escopo entregue

- Saldo atual por filial, sem replicacao de saldo.
- Movimentacao manual, ajuste manual, transferencia entre filiais e extrato.
- Lotes, validade, baixa por validade e obrigatoriedade de lote quando o produto controla lote.
- Inventario com bloqueio de movimentacao, contagem, fechamento, divergencias e auditoria.
- Entrada de nota por XML/manual/manifesto com conferencia, vinculacao, sugestao de produto, lote/validade, custo composto e resumo antes de efetivar.
- Pos-efetivacao com bloqueio de edicao indevida, rastreabilidade de movimentos, lotes, custos e itens nao movimentados.
- Estorno de entrada efetivada com validacao de saldo/lote, movimentos inversos, auditoria e bloqueio de reestorno.
- Reposicao como fluxo de trabalho: sugestao, selecao em massa, edicao de quantidade, agrupamento por fornecedor, pedido de compra em rascunho e rastreabilidade reposicao -> pedido -> entrada -> estoque.
- Prontidao comercial pos-entrada: produto criado pelo XML nasce como rascunho comercial e nao deve ser tratado como pronto para venda/PDV quando estiver incompleto.
- Permissoes granulares para visualizar, criar, editar, aprovar/efetivar, cancelar e exportar.
- Auditoria operacional centralizada para acoes sensiveis.
- Layout mobile reforcado nas telas densas.

## Fluxos principais

### Saldo e movimentacoes

1. Produto ativo e vinculado a filial aparece no saldo, mesmo sem movimento.
2. Toda entrada, saida, reserva, ajuste, transferencia, baixa por validade e inventario passa por `MovimentacaoService`.
3. O movimento registra quantidade anterior, quantidade posterior, filial, produto, lote quando aplicavel, usuario e documento.
4. Produto com controle de lote exige lote em movimentacao fisica.
5. Saida nao pode deixar saldo negativo.

### Entrada de nota

1. Usuario importa XML, chave/manifesto ou cria entrada manual.
2. Fornecedor e cadastrado automaticamente quando o XML tem documento e razao social suficientes.
3. CNPJ/CPF do destinatario diferente da filial gera alerta, nao bloqueio.
4. Itens sao vinculados por EAN/equivalencia ou sugestao por nome/NCM/unidade.
5. Itens sem produto, divergencia critica, lote pendente ou custo bloqueante impedem a efetivacao.
6. Custo composto separa despesas, descontos, impostos recuperaveis e nao recuperaveis.
7. Tela final revisa status da nota, produtos, lotes, custos, financeiro, alertas e bloqueios.
8. Efetivacao cria movimentos, lotes, custo medio e registros auditaveis.

### Pos-efetivacao e estorno

1. Entrada efetivada nao permite editar conferencia, produto vinculado, lote/validade ou custo.
2. Detalhe pos-efetivacao mostra resumo, movimentos, lotes, custos e itens recusados.
3. Estorno exige permissao e justificativa.
4. Estorno valida se saldo/lote ainda permite reversao.
5. Movimentos inversos sao gerados e a entrada passa para status estornada.
6. Entrada estornada nao pode ser estornada novamente.

### Reposicao

1. Tela identifica produtos abaixo de minimo, ponto de reposicao ou maximo.
2. Operador pode selecionar itens em massa e editar quantidade sugerida.
3. Sistema agrupa pedidos por fornecedor.
4. Produto sem fornecedor fica como pendencia, sem pedido automatico.
5. Produto com pendencia comercial/fiscal/custo aparece com alerta antes da compra.
6. Pedido gerado fica rastreavel ate entrada e estoque.

## Regras que nunca podem quebrar

- Nunca replicar saldo, reserva, lote, inventario ou movimentacao entre filiais.
- Transferencia entre filiais e movimento bilateral auditado, nao replicacao.
- Nunca escrever diretamente em `Estoque.quantidade_atual`, `Estoque.quantidade_disponivel`, `quantidade_reservada` ou saldo de lote fora de service transacional.
- Nunca vender/baixar lote vencido ou bloqueado por fluxo comum.
- Nunca permitir produto controlado por lote sair sem lote.
- Nunca efetivar entrada com item sem produto interno.
- Nunca permitir custo negativo ou custo critico sem bloqueio/confirmacao explicita.
- Produto criado pelo XML deve nascer como rascunho comercial quando incompleto.
- Promocoes/PDV devem consultar custo e saldo atuais; nao podem inventar disponibilidade nem ignorar lote/validade.
- Exportacoes e rotas criticas precisam respeitar permissao no backend, mesmo por URL direta.

## Integracoes preparadas

- Produtos: estoque lista preco de venda, custo unitario, custo total e imagem do produto.
- Promocoes: margem deve ser calculada com custo atual; promocao com margem negativa precisa alertar.
- Compras: reposicao gera pedido de compra em rascunho e entrada pode ser vinculada ao pedido.
- Vendas/PDV: contrato preparado para consultar saldo disponivel por filial, respeitar lote/validade e usar custo atual.
- Fiscal/manifesto: DF-e permanece seguro; consulta real exige flag, certificado A1, senha em ambiente e homologacao/liberacao controlada.

## Checklist final de aceite

- [x] Migrations pendentes de `core` e `fiscal` formalizadas.
- [x] Mudancas paralelas de identidade/parametros da filial integradas ao pacote atual.
- [x] Teste completo real executado explicitamente com 221 testes.
- [x] Bateria final com XMLs reais variados executada com rollback: 12 arquivos, 10 NF-e importadas, 1 XML invalido recusado e 1 duplicidade recusada.
- [x] Estoque nao replica saldo em nenhuma hipotese.
- [x] Todas as operacoes de saldo passam por service.
- [x] Entrada de nota tem revisao final antes de efetivar.
- [x] Custo composto revisa frete, seguro, despesas, desconto, ST, IPI e ICMS recuperavel/nao recuperavel.
- [x] Pos-efetivacao bloqueia edicoes que nao fazem sentido.
- [x] Estorno exige permissao, justificativa, saldo/lote reversivel e auditoria.
- [x] Reposicao gera pedido real agrupado por fornecedor.
- [x] Auditoria cobre entrada, produto/lote, ajuste, transferencia, inventario, reposicao e estorno.
- [x] Documentacao de permissoes, auditoria, estorno, prontidao comercial e reposicao existe em `/docs`.
- [x] Revisao visual final em producao feita apos deploy do commit de fechamento.

## Comandos de validacao

```powershell
python manage.py check --settings=config.settings.test
python manage.py test apps.cadastros.tests apps.compras.tests apps.core.tests apps.estoque.tests apps.fiscal.tests apps.pdv.tests apps.produtos.tests --settings=config.settings.test --verbosity 1
railway run python manage.py makemigrations core fiscal --check --dry-run --settings=config.settings.production
```

## QA final com XMLs reais

Executado em 21/05/2026 com os arquivos locais em `tmp/xmls_teste_20260520/XML`, dentro de transacao forçada com rollback.

- 12 arquivos XML analisados.
- 10 NF-e validas importaram como entrada de mercadoria.
- 10 fornecedores foram cadastrados automaticamente dentro da transacao, todos com `fornecedor_pendente=False`.
- 116 itens de XML foram lidos no total, incluindo notas com multiplos itens, parcelas financeiras e lotes/validade por rastro.
- Todas as notas validas ficaram com alerta de destinatario diferente quando o CNPJ/CPF do XML nao era o da filial de QA, sem bloquear a importacao.
- 1 XML invalido foi recusado com erro de parsing.
- 1 XML duplicado foi recusado por chave ja importada na mesma filial.
- A importacao duplicada de uma NF-e valida tambem foi recusada por chave ja existente.
- `ROLLBACK_OK=True`; nenhum dado de QA ficou persistido nessa bateria.

## QA visual em producao

Executado em 21/05/2026 no dominio `https://inovated.up.railway.app`, apos deploy do commit de fechamento.

- Dashboard abriu sem erro e troca de tema claro/escuro atualizou a classe visual sem exigir F5.
- Estoque abriu com atalhos, totais, filtros, exportacoes e tabela de produtos.
- Reposicao abriu com fluxo de trabalho, cards, selecao e atalhos de pedido.
- Movimentacoes, lotes e inventarios abriram sem erro 500.
- Entrada de Mercadoria abriu com a visao de trabalho e filtros por pendencia.
- Produtos e Combos/Promocoes abriram sem erro, preservando o contrato com estoque.
- Viewport estreita e desktop largo nao apresentaram overflow horizontal indevido no corpo da pagina.
- Console do navegador ficou sem erros capturados durante a revisao.
