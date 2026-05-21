# Contrato Estoque x Vendas x PDV x Promocoes

Atualizado em 21/05/2026.

## Objetivo

Padronizar a consulta de produto vendavel para que PDV, vendas, promocoes e estoque usem a mesma fonte de verdade antes de permitir venda, reserva, baixa ou promocao.

## Fonte unica

O contrato tecnico fica em:

- `apps.pdv.services.produto_vendavel_service.ProdutoVendavelService`

Metodo principal:

```python
ProdutoVendavelService.consultar(
    produto=produto,
    filial=filial,
    quantidade=Decimal("1"),
)
```

Metodo bloqueante:

```python
ProdutoVendavelService.validar_venda(
    produto=produto,
    filial=filial,
    quantidade=Decimal("1"),
)
```

`validar_venda` deve ser chamado antes de:

- adicionar item no pedido de venda;
- confirmar/reservar pedido de venda;
- finalizar venda no PDV;
- aplicar promocao que dependa de margem segura;
- montar item de kit/brinde/combo que baixa estoque.

## Resposta esperada para o PDV

O contrato retorna:

- `saldo_disponivel`: saldo disponivel real da filial.
- `custo_atual`: custo usado para margem, CMV e validacao de promocao.
- `preco_base`: preco de venda cadastrado.
- `preco_aplicado`: menor preco elegivel entre preco base, promocao individual, desconto por categoria e combo por quantidade.
- `preco_origem`: origem legivel do preco aplicado.
- `preco_origem_tipo`: `normal`, `promocional`, `categoria` ou `combo`.
- `preco_origem_detalhe`: texto explicando a regra aplicada.
- `margem_percentual`: margem contra custo atual.
- `status_comercial`: prontidao comercial/fiscal/custo do produto.
- `lote_obrigatorio`: verdadeiro quando produto controla lote ou validade.
- `tem_lote_disponivel`: verdadeiro quando ha lote ativo/vigente.
- `promocoes_aplicaveis`: lista de promocoes elegiveis para a quantidade.
- `bloqueios`: pendencias que impedem venda.
- `alertas`: pendencias que permitem seguir, mas devem ser exibidas.
- `pode_vender`: verdadeiro apenas quando nao ha bloqueios.

## Bloqueios obrigatorios

A venda deve ser bloqueada quando:

- produto esta inativo;
- produto esta em rascunho comercial;
- preco de venda/preco aplicado e menor ou igual a zero;
- custo atual e menor ou igual a zero para produto fisico;
- preco aplicado fica abaixo do custo atual;
- promocao ativa gera margem negativa;
- produto controla validade sem controle de lote;
- produto com validade esta sem politica minima de FEFO;
- produto controlado por lote tenta sair sem lote/FEFO.

## Promocoes

O preco vivo agora considera:

- preco de venda normal;
- preco promocional individual;
- desconto por categoria/subcategoria;
- combo por quantidade.

Regra permanente:

- promocao calcula preco;
- promocao nunca escreve saldo;
- margem de promocao deve ser validada contra `custo_atual`;
- promocao com margem negativa bloqueia a venda no backend.

## Baixa de estoque no PDV

O PDV deve baixar estoque apenas pelo backend e sempre via `MovimentacaoService`.

Fluxos tratados:

- Produto unitario: baixa o produto vendido.
- Combo por quantidade: baixa o produto vendido normalmente, usando o preco de combo quando elegivel.
- Kit: cria/baixa os componentes item a item.
- Brinde: cria item gratis e baixa o produto entregue como brinde com movimento `BRINDE`.
- Servico: nao baixa estoque.

## Vendas fora do PDV

Pedido de venda usa o mesmo contrato:

- ao adicionar item;
- ao confirmar pedido;
- antes de reservar estoque.

Pedido ainda usa `MovimentacaoService` para:

- reservar;
- liberar reserva;
- faturar/baixar;
- devolver.

## Riscos que nunca podem quebrar

- Nao duplicar regra de preco no front do PDV.
- Nao confiar no `valor_unitario` enviado pelo front.
- Nao vender produto sem custo/preco valido.
- Nao permitir promocao com margem negativa passar silenciosamente.
- Nao baixar kit como um produto unico quando ele deve baixar componentes.
- Nao tratar brinde como desconto sem baixa fisica.
- Nao ignorar lote/validade quando produto exige controle.
- Nao alterar saldo direto fora de `MovimentacaoService`.

