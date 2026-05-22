# REPLICATION_RULES.md

## Regra principal
Replicacao e por filial, nunca por empresa.

Campo principal:
`Filial.participa_replicacao`

Politica por filial:
`PoliticaReplicacaoFilial`

A politica define quais grupos aquela filial pode enviar/receber. A filial decide se participa ou nao pelo campo `Filial.participa_replicacao`.

`PoliticaReplicacao` por empresa e legado e deve ser usado somente como fallback/migracao de dados antigos. Nova regra nunca deve salvar checkbox de replicacao por empresa.

## Grupos atuais de replicacao
1. clientes
2. fornecedores
3. categorias
4. subcategorias
5. marcas / fabricantes
6. unidades
7. fiscal
8. produtos
9. tabelas de preco
10. ficha tecnica
11. qualidade
12. transportadoras
13. representantes

## Fornecedores e fabricantes
- Fornecedores e fabricantes sao opcoes separadas na central administrativa e na edicao de filial.
- Ambos podem ou nao replicar por filial.
- Fabricantes usam o cadastro `MarcaProduto`.
- Fornecedores usam o cadastro `Fornecedor`.
- Produto pode ter marca/fabricante e fornecedor opcionais.
- A replicacao desses cadastros nao deve exigir que sejam obrigatorios no produto.

## Nunca fazer
- duplicar produtos por filial
- replicar saldo, reserva, lote, inventario ou movimentacao de estoque entre filiais
- apagar vinculos automaticamente
- ignorar `id_externo`
- trocar regra de filial para empresa
- salvar grupo de replicacao em politica global da empresa
- enviar cadastro para filial de destino que desmarcou aquele grupo de replicacao
- deixar erro de um grupo bloquear os demais grupos

## Estoque nao replica
- Estoque fisico e sempre operacional por filial.
- Saldo, reserva, lote, inventario, movimentacao, baixa por validade, estorno/cancelamento de entrada e custo efetivado pertencem a filial onde ocorreram.
- Transferencia entre filiais nao e replicacao: e saida na origem e entrada no destino, em transacao auditada.
- Parametros cadastrais de controle podem ser discutidos futuramente, mas o padrao e filial independente.
- PDV/vendas deve consultar saldo disponivel somente da filial ativa.

## Ordem correta de produtos
1. categorias
2. subcategorias
3. unidades
4. marcas / fabricantes
5. fiscal
6. produtos
7. tabelas preco
8. ficha tecnica
9. qualidade

## Ficha tecnica e qualidade
- Ficha tecnica pertence ao grupo visual "Producao e qualidade", nao ao grupo de produtos comerciais.
- A opcao de ficha tecnica replica a composicao/BOM: produto acabado, versao, quantidades, materias-primas, perdas previstas, tempo e custos padrao.
- Qualidade e uma opcao separada.
- A opcao de qualidade replica padroes de qualidade por categoria/subcategoria e parametros de qualidade por produto: etapa, nome do parametro, tipo de valor, unidade, minimo, maximo, ideal, opcoes, obrigatoriedade e status.
- Padroes por subcategoria devem ter prioridade sobre padroes da categoria ao aplicar no produto.
- Ao aplicar padroes no produto, nunca duplicar parametros ja existentes para a mesma etapa e nome.
- Qualidade depende de o produto existir na filial de destino; nao deve criar produto duplicado.
- Padroes de qualidade dependem de a categoria/subcategoria existir ou estar vinculada na filial de destino.

## Combos e promocoes
- Combo por quantidade, kit de produtos, brinde por produto e desconto por categoria/subcategoria usam flag individual `replicar_filiais`.
- Essa replicacao e seletiva: ao marcar `replicar_filiais`, o usuario escolhe quais filiais destino receberao a copia.
- Filial sem politica habilitada, sem participacao em replicacao ou sem cadastro correspondente deve aparecer bloqueada/ignorada com motivo claro.
- A opcao de replicar deve comecar desmarcada; quando marcada, a tela deve permitir selecionar destinos.
- Filiais sem possibilidade de receber a promocao devem aparecer bloqueadas, com motivo visivel antes do salvamento.
- A copia gerada em outra filial vira independente depois de criada. Alterar, inativar ou desligar a replicacao na regra de origem nao deve atualizar nem apagar copias antigas automaticamente.
- Se desligar `replicar_filiais` depois, copias antigas continuam existindo.
- Promocoes replicadas devem guardar `id_externo` para identificar a origem sem usar nome como chave de sincronizacao.
- Ao replicar novamente, se a filial destino ja tiver copia com o mesmo `id_externo`, nao sobrescrever: informar que ja existe uma copia independente.
- Preco promocional individual pertence ao fluxo de combos e promocoes. O cadastro do produto deve manter o preco de venda base e nao deve ser a superficie principal para editar regra promocional.
- Replicacao comum de preco de venda do produto nao deve empurrar campos promocionais; preco promocional em lote replica somente pelo fluxo de promocoes.
- Preco promocional em lote tenta encontrar o produto correspondente na filial destino por `id_externo`, codigo ou codigo de barras, sem criar produto duplicado.
- Desconto por categoria aceita categoria vazia como "todas as categorias"; categorias/subcategorias especificas podem coexistir para regras mais finas.
- Cada linha de desconto por categoria/subcategoria tem seu proprio tipo de desconto e valor. Ao replicar, copiar tambem esses campos por linha.
- Combo do mesmo produto replica produto, nome, vigencia, status e variacoes/faixas de quantidade.
- Combo do mesmo produto tambem replica se deve usar o preco promocional ativo do produto como base do calculo.
- Kit de produtos replica nome, descricao, vigencia, status, tipo/valor do desconto e itens do kit. O kit nao e um novo produto; e uma forma comercial de vender produtos existentes.
- Kit de produtos tambem replica a flag de uso de preco promocional dos itens.
- Brinde por produto replica nome, produto gerador de brinde, quantidade minima, itens gratuitos, vigencia, dias da semana, status e flag de uso de melhor preco vivo no produto gerador.
- Brinde por produto nao cria produto novo; no PDV futuro deve registrar o item como brinde e baixar estoque do produto entregue gratuitamente.
- Insumos internos/composicao nao pertencem a combos/promocoes; devem seguir a regra futura da ficha tecnica.
- Vigencia de combos/promocoes e opcional. Sem data inicial, a regra comeca imediatamente. Sem data final, fica sem prazo de termino. Essa regra precisa ser preservada em criacao, edicao, listagem e replicacao.
- Status comercial por vigencia:
  - `Ativo`: ativo e dentro da vigencia, ou sem limite de vigencia.
  - `Programado`: ativo com data inicial futura.
  - `Finalizada`: data final menor que a data atual, mesmo que o campo ativo esteja marcado.
  - `Inativo`: desligado manualmente.
- Regras programadas tambem pertencem a listagem do seu tipo. Exemplo: combo programado deve aparecer ao filtrar por `Combos` e tambem ao filtrar por `Programadas`.
- Ao replicar, copiar datas vazias como vazias, sem inventar data atual ou data final.
- Combos, kits, descontos por categoria e precos promocionais podem limitar validade por dias da semana. O padrao e todos os dias. Ao replicar, copiar os dias selecionados junto da vigencia.
- A replicacao comum de produto/preco de venda nao deve atualizar, criar nem apagar regras promocionais. Promocoes sao replicadas somente pelo fluxo de promocoes.
- Caso o preco de venda de um produto mude, combo/kit/brinde/desconto por categoria devem recalcular preco vivo na renderizacao/uso, nao depender de valor congelado da epoca da criacao.
- Preco promocional individual e desconto por categoria tambem sao vivos: percentuais e descontos em valor devem ser recalculados sobre o preco de venda atual quando aplicavel.
- Combo por quantidade aceita condicao da faixa:
  - `Quantidade`: aplica quando a quantidade comprada e exatamente aquela faixa.
  - `A partir de`: aplica quando a quantidade comprada e maior ou igual ao valor informado.
- A regra `A partir de` nunca deve ser tratada como apenas maior que; e sempre maior ou igual.
- Se `replicar_filiais` estiver desmarcado, criacao, edicao, ativacao e inativacao de promocao devem afetar apenas a filial atual.
- A flag `replicar_filiais` deve ser preservada ao editar uma regra que ja foi salva com replicacao marcada. Ela so deve sair se o usuario desmarcar explicitamente.
- Ativar ou inativar uma promocao pela listagem deve seguir a mesma regra de filial: local por padrao; replicar somente quando a regra permitir e o usuario confirmar destinos.
- A listagem deve mostrar o status real da regra na filial atual depois de ativar/inativar. Nao confiar em estado antigo da linha nem em status derivado de outra filial.

## Regra de preco vivo em promocoes
- Preco vivo comercial compara preco de venda, preco promocional individual e desconto por categoria/subcategoria.
- Para combo, kit e brinde, quando a flag de melhor preco estiver marcada, usar o menor preco elegivel.
- Nao acumular descontos automaticamente; comparar candidatos e escolher o menor.
- Uso automatico em combo/kit/brinde exige pelo menos 5 dias da semana selecionados na promocao externa.
- Promocao com 1 a 4 dias da semana e considerada esporadica e deve ficar para escolha manual futura no PDV.
- No PDV futuro, mostrar todas as opcoes aplicaveis em modal e sugerir o menor preco, sem aplicar automaticamente quando houver multiplas opcoes.

## Robustez da sincronizacao
- A sincronizacao imediata da central deve ser tolerante.
- Se um grupo falhar, os demais devem continuar independentes.
- Erros de fornecedores nao podem bloquear produtos/fabricantes.
- Erros de produtos/fabricantes nao podem bloquear fornecedores.
- Ficha tecnica deve ser ignorada com total 0 quando as tabelas de producao ainda nao existirem no banco do deploy.
- Evitar `.iterator()` em loops que chamam saves/transacoes internas, pois no PostgreSQL/Railway pode fechar cursor.
- Em promocoes, erro de log, tooltip, contexto auxiliar ou listagem de filiais de replicacao nao pode derrubar a tela principal.

## Produto ativo/inativo por filial
- Status de ativacao/inativacao de produto e operacional por filial.
- Produto replicado pode existir em outras filiais com estoque proprio; inativar em uma filial nao deve zerar nem inativar automaticamente as demais.
- Ao inativar produto, perguntar se o usuario quer zerar estoque da filial atual.
- Ao inativar/ativar produto com replicacao habilitada, perguntar se o usuario deseja aplicar tambem em outras filiais elegiveis.
- Mesmo quando houver replicacao, estoque fisico continua individual por filial e nunca deve ser replicado.
