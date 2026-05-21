# Auditoria operacional de estoque e entradas

Este documento registra as acoes sensiveis que devem gerar `RegistroAuditoria`.

## Modelo central

O modelo `core.RegistroAuditoria` guarda:

- usuario, filial, modulo e acao;
- objeto afetado e objeto relacionado;
- justificativa;
- dados anteriores e novos;
- metadados operacionais;
- IP, user-agent e data/hora.

O `LogSistema` continua existindo para CRUD automatico via signals. O `RegistroAuditoria` e a trilha operacional explicita para eventos criticos.

## Acoes padronizadas

- `visualizar`
- `criar`
- `editar`
- `aprovar`
- `cancelar`
- `exportar`
- `efetivar`
- `vincular`
- `reprocessar`
- `ajustar`
- `transferir`
- `inventariar`
- `baixar_validade`

## Entradas de nota

Geram auditoria:

- importar XML;
- registrar chave;
- criar entrada manual;
- vincular produto ao item;
- confirmar sugestoes;
- cadastrar produto pelo XML;
- reprocessar vinculos;
- resolver fornecedor pendente;
- alterar conferencia, lote, validade e divergencia;
- alterar componentes e composicao de custo;
- criar parcela financeira;
- gerar contas a pagar;
- efetivar entrada;
- estornar entrada efetivada;
- cancelar entrada.

Cancelamento exige justificativa. Alteracoes de custo gravam justificativa operacional e snapshot antes/depois.
Estorno exige justificativa, cria movimentos reversos e mantem os movimentos originais auditaveis.

## Estoque

Geram auditoria:

- movimentacao manual;
- ajuste manual;
- transferencia;
- criacao e alteracao de lote;
- baixa por validade;
- abertura de inventario;
- contagem de item;
- fechamento de inventario;
- cancelamento de inventario.

Ajuste manual, transferencia, baixa por validade e cancelamento de inventario devem manter justificativa rastreavel.

## Telas com consulta

- Detalhe da entrada: mostra auditoria da nota.
- Extrato de movimentacoes filtrado por produto: mostra auditoria relacionada ao produto.
- Edicao de lote: mostra auditoria do lote.
- Detalhe de inventario: mostra auditoria do inventario.

## Regra critica

Estoque continua sem replicacao entre filiais. A auditoria deve preservar a filial real da operacao e nunca deve ser usada para copiar saldo.
