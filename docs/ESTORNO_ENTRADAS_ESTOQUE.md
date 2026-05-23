# Estorno seguro de entradas

## Objetivo

Entrada efetivada nao deve ser editada por cima. Quando houver erro operacional, o caminho correto e estornar com justificativa, movimentos reversos e auditoria.

## Fluxo

1. A entrada esta `efetivada`.
2. Usuario com `compras/cancelar` abre **Solicitar estorno**.
3. O sistema calcula impacto:
   - movimentos originais;
   - lotes afetados;
   - quantidade e custo a reverter;
   - contas a pagar vinculadas;
   - bloqueios por saldo, lote consumido, conta paga ou movimentacao posterior.
4. Usuario informa justificativa obrigatoria.
5. O sistema cria movimentos de estoque com `documento_tipo=estorno_entrada`.
6. Parcelas e contas a pagar abertas sao marcadas como canceladas.
7. Entrada passa para `estornada`, com usuario/data de estorno.
8. Auditoria operacional registra antes/depois e movimentos gerados.

## Bloqueios

O estorno automatico e bloqueado quando:

- a entrada nao esta efetivada;
- a entrada ja tem estorno;
- nao existem movimentos originais;
- existe movimentacao posterior do mesmo produto;
- saldo atual do produto e menor que a quantidade a estornar;
- lote atual e menor que a quantidade a estornar;
- lote da entrada ja foi parcialmente consumido;
- conta a pagar vinculada ja foi paga ou tem valor pago.

Esses bloqueios evitam custo medio incoerente e perda de rastreabilidade.

## Resultado esperado

- Movimentos originais continuam visiveis.
- Movimentos de estorno aparecem separados no detalhe da entrada.
- O saldo volta com movimentacao reversa, sem apagar historico.
- A entrada fica fechada como `estornada`.
- Uma nova entrada correta pode ser criada depois.

## Linguagem para o usuario

- Para o operador, `cancelada`, `estornada` ou `revertida` significam que a entrada anterior foi desfeita.
- Evitar apresentar `cancelar` e `estornar` como duas decisoes concorrentes na reentrada de XML; isso confunde.
- Se a NF anterior foi cancelada/estornada, importar a mesma chave deve permitir uma nova entrada limpa.
- A entrada antiga permanece no historico fechado, com auditoria e movimentos reversos quando houver estoque efetivado.
- A tela de duplicidade so deve bloquear/reabrir a entrada existente quando ela ainda representa uma entrada ativa/real que pode duplicar estoque, custo ou financeiro.
