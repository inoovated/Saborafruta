# Matriz de permissoes operacionais

## Padrao de acoes
- `ver`: visualizar telas, listas, detalhes e consultas.
- `criar`: criar registros ou iniciar fluxos operacionais.
- `editar`: alterar registros, vinculos, conferencia, custos e contagens.
- `aprovar`: confirmar operacoes que geram impacto definitivo.
- `cancelar`: cancelar, estornar ou baixar operacoes por excecao.
- `exportar`: gerar arquivos CSV, Excel ou PDF.

Mensagem padrao para bloqueio:
`Você não tem permissão para esta ação.`

## Entradas de nota / Compras
| Fluxo | Modulo | Acao |
| --- | --- | --- |
| Listar entradas | compras | ver |
| Localizar nota | compras | ver |
| Importar XML | compras | criar |
| Consultar chave de acesso | compras | criar |
| Criar entrada manual | compras | criar |
| Adicionar item manual | compras | editar |
| Alterar conferencia | compras | editar |
| Vincular produto | compras | editar |
| Confirmar sugestoes | compras | editar |
| Criar produto pelo XML | compras | editar |
| Reprocessar vinculos | compras | editar |
| Resolver fornecedor pendente | compras | editar |
| Resolver diferencas, lote e validade | compras | editar |
| Revisar/aplicar composicao de custo | compras | editar |
| Gerar contas a pagar da entrada | financeiro | criar |
| Efetivar entrada | compras | aprovar |
| Cancelar entrada | compras | cancelar |
| Estornar entrada efetivada | compras | cancelar |

## Estoque
| Fluxo | Modulo | Acao |
| --- | --- | --- |
| Ver saldo, lotes, movimentacoes, reposicao, alertas e relatorios | estoque | ver |
| Movimento manual | estoque | criar |
| Criar lote manual | estoque | criar |
| Abrir inventario | estoque | criar |
| Ajuste manual de estoque | estoque | editar |
| Editar lote | estoque | editar |
| Contar inventario | estoque | editar |
| Acionar reposicao | estoque | editar + compras/criar |
| Transferir entre filiais | estoque | aprovar |
| Fechar inventario | estoque | aprovar |
| Cancelar inventario | estoque | cancelar |
| Baixar lote por validade | estoque | cancelar |
| Exportar saldo, lotes, reposicao, movimentacoes e inventarios | estoque | exportar |

## Regras de tela
- Botao de acao critica deve aparecer apenas quando o usuario possui a permissao correspondente.
- Bloqueio visual nao substitui bloqueio de URL: toda rota critica deve usar `PermissaoRequiredMixin` ou helper de exportacao.
- Perfil admin e superusuario continuam liberados por `Usuario.tem_permissao`.
- Estoque nunca e replicado; permissoes protegem operacao local da filial ativa.
