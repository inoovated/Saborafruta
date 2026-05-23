# Prontidao comercial pos-entrada

## Objetivo

Depois que uma entrada de nota e efetivada, o estoque fisico pode estar correto, mas o produto ainda pode nao estar pronto para venda, PDV, promocao ou reposicao comercial. Esta checagem separa recebimento fisico de liberacao comercial.

## Regra para produto criado pelo XML

Produto criado a partir do XML entra com `rascunho_comercial=True`.

Enquanto estiver como rascunho comercial ou com pendencias, ele deve aparecer no estoque e no detalhe da entrada, mas nao deve ser tratado por Vendas/PDV como produto automaticamente liberado.

## Pendencias verificadas

- Sem preco de venda valido.
- Sem codigo de barras principal, alternativo ou equivalente ativo.
- Sem categoria.
- Sem custo valido.
- Margem atual abaixo da margem desejada/minima.
- Produto inativo.
- Promocao ativa com margem negativa contra o custo atual.
- Produto com lote/validade sem politica clara de venda, como validade sem lote, FEFO desativado ou venda sem estoque em produto rastreado.

## Indicadores no estoque

A tela de estoque mostra a prontidao por produto:

- `Pronto para venda`: produto liberado para venda/PDV conforme regras atuais.
- `Pendente comercial`: rascunho comercial, sem preco, inativo, margem insuficiente ou promocao com margem negativa.
- `Pendente fiscal/cadastro`: sem codigo de barras, sem categoria ou politica de lote/validade inconsistente.
- `Pendente custo`: sem custo valido para CMV, margem e promocao.

## Detalhe da entrada

Entradas efetivadas ou estornadas mostram a checagem dos produtos recebidos:

- quantidade de produtos prontos;
- quantidade de produtos problemáticos;
- lista dos problemáticos primeiro;
- pendencias separadas por alerta/bloqueio;
- atalho direto para corrigir o cadastro do produto.

## Contrato tecnico para Vendas, PDV e Promocoes

Todo fluxo futuro de venda/PDV deve consultar o contrato central em `apps.produtos.services.prontidao_comercial_service`.

Regras obrigatorias:

- venda deve consultar saldo disponivel por filial;
- venda deve respeitar lote e validade quando o produto controlar rastreabilidade;
- promocao deve validar margem usando custo atual;
- produto sem preco valido ou custo valido nao deve entrar em promocao sem alerta;
- produto em rascunho comercial nao deve ir automaticamente para venda/PDV;
- front-end pode sugerir, mas backend deve recalcular preco, saldo e margem.

## Vinculos de fornecedor pos-entrada

- Produto pode ter equivalencias com varios fornecedores/CNPJs XML.
- O cadastro do produto deve permitir visualizar e remover esses vinculos na etapa de estoque.
- Remover vinculo de fornecedor nao deve apagar historico da entrada nem remover codigo de barras real do produto.
- Se o produto foi criado pelo XML, continuar tratando como possivel rascunho comercial ate revisar preco, categoria, fiscal, lote/validade e margem.
- Vinculo de fornecedor ajuda proximas entradas; nao e liberacao comercial automatica para venda.

## Riscos que nao podem quebrar

- Nao liberar produto incompleto criado por XML como pronto para venda.
- Nao permitir promocao que esconda margem negativa sem alerta.
- Nao ignorar lote/validade em produto rastreavel.
- Nao calcular margem com custo zerado.
- Nao misturar estoque fisico correto com cadastro comercial pronto.
- Nao confundir equivalencia de fornecedor com produto comercialmente pronto.
