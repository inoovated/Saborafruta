# Reposicao real e pedido de compra

## Objetivo

A tela de reposicao deixou de ser apenas relatorio e passou a ser uma fila operacional para transformar estoque baixo em pedido de compra.

## Fluxo

1. Estoque calcula produtos abaixo do minimo ou ponto de reposicao por filial.
2. Operador abre `Estoque > Reposicao`.
3. Tela mostra saldo, criterio, fornecedor, custo, prontidao comercial e status do fluxo.
4. Operador seleciona itens em massa e ajusta a quantidade a comprar.
5. Sistema separa automaticamente um pedido por fornecedor.
6. Pedido fica em rascunho para revisao/aprovacao de Compras.
7. Pedido aprovado/enviado passa a aparecer como `Aguardando entrada`.
8. Entrada de NF pode ser criada ja vinculada ao pedido.
9. Ao efetivar a entrada, o pedido recebe as quantidades e o estoque/lote/custo sao atualizados.

## Status da reposicao

- `Gerar pedido`: item pronto para virar pedido.
- `Pedido ja gerado`: existe pedido em rascunho/aguardando aprovacao para o produto.
- `Aguardando entrada`: pedido aprovado/enviado/confirmado ou parcialmente recebido.
- `Sem fornecedor`: produto precisa de fornecedor antes de gerar pedido.

## Regras

- Produto sem fornecedor nao gera pedido.
- Produto com pendencia de prontidao comercial pode gerar pedido, mas aparece com alerta antes da aprovacao.
- Quantidade sugerida pode ser editada antes de gerar pedido.
- Pedido existente em rascunho de reposicao e reaproveitado para nao duplicar itens.
- Cada item de pedido guarda observacao com saldo, minimo, ponto e criterio da reposicao.
- A geracao do pedido por reposicao cria auditoria operacional.

## Rastreabilidade

Pedido gerado pela reposicao recebe `Origem: reposicao_estoque` na observacao.

No detalhe do pedido, o sistema mostra:

- origem reposicao;
- pedido;
- entradas vinculadas;
- situacao do estoque apos recebimento.

Esse caminho deve ficar auditavel: reposicao -> pedido -> entrada -> estoque.
