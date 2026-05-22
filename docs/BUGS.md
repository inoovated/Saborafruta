# BUGS.md

## Bugs historicos

### Erro 500
Causas recorrentes:
- migrations pesadas ou atrasadas no Railway
- conflitos Railway
- imports incorretos
- tabela ainda inexistente no banco de producao
- coluna nova ainda inexistente no banco de producao
- template usando atributo que nao foi preenchido no contexto
- alteracao em listagem agregada sem fallback para dados ausentes
- tentativa de resolver tudo numa mudanca grande demais sem validar renderizacao intermediaria

Regra:
- erro de sincronizacao imediata nunca deve derrubar a tela principal.
- salvar cadastro e politica deve continuar funcionando mesmo se um grupo replicado falhar.
- em telas sensiveis, validar antes de subir:
  - `python manage.py check`
  - renderizacao dos templates alterados via `django.template.loader.get_template`
  - `git diff --check`
  - logs Railway se producao mostrar 500
- quando o 500 surgir apos varias tentativas, comparar com o ultimo commit estavel e reaplicar apenas patches pequenos.
- ao adicionar campo usado por listagens principais, preferir migration idempotente ou migration de reparo para producao (`RunPython`/`SeparateDatabaseAndState`), pois Railway pode ficar com estado parcial entre deploys.

Caso real em 18/05/2026:
- rota afetada: `/produtos/combos-promocoes/`, apenas no fluxo autenticado.
- entrada afetada: aba de promocoes pela tela de Produtos e link de promocoes dentro do cadastro do produto.
- curl sem sessao apenas redireciona para login e nao reproduz esse 500.
- correcao aplicada:
  - `0019_promocoes_id_externo.py` convertida para migration idempotente/tolerante;
  - `0020_repara_id_externo_promocoes.py` criada como reparo para producao com estado parcial;
  - montagem de log de promocoes protegida para nao derrubar a tela principal;
  - montagem de opcoes de replicacao protegida para nao derrubar a tela principal.
- regra nova:
  - auditoria, tooltip, listagem auxiliar ou escolha de filiais de replicacao nunca podem derrubar a tela principal de promocoes.
  - se falharem, registrar no log do servidor e manter a tela aberta com fallback vazio.

### Produtos duplicados
Causa:
modelo clone por filial

Regra:
produto unico + vinculo por filial.

### Imagens sumindo
Causas:
- `MEDIA_ROOT` sem volume persistente
- campo `foto_url` entrando como campo normal no form de produto

Regra:
- imagem de produto so deve mudar pelo uploader/acao especifica de imagem.
- editar marca, fornecedor ou outros dados do produto nao pode limpar a imagem.

### Cursor does not exist
Causa:
uso de `.iterator()` no PostgreSQL/Railway enquanto o loop executa saves/transacoes internas.

Regra:
materializar a lista antes de sincronizar quando o loop chama servicos que salvam dados.

### Relation does not exist
Causa:
deploy com tabela ainda nao criada, exemplo `producao_fichas_tecnicas`.

Regra:
quando a tabela de um grupo opcional nao existir, pular o grupo com total 0 em vez de gerar erro para o usuario.

### Auditoria com ruido decimal
Causa:
comparacao textual de numeros, exemplo `0.00` vs `0`.

Regra:
logs devem normalizar campos numericos reais antes de comparar, sem tratar CPF/CNPJ/CEP/codigos como decimal.

### Precos com casas decimais excessivas
Causa:
uso de `DecimalField(decimal_places=4)` ou `floatformat:"-2"` em valores monetarios, deixando aparecer `10.0000` ou removendo zeros finais quando deveriam existir.

Regra:
- preco, promocao, kit, combo e desconto monetario sempre exibem 2 casas decimais.
- 3 ou 4 casas decimais apenas em quantidade, estoque/granel e medidas tecnicas.
- parse JS de decimal deve aceitar `10.0000` como 10, e nao como 100000.
- Na edicao de combo, valores como quantidade e desconto nao devem aparecer como `5,000` ou `10,0000` quando podem aparecer como `5` e `10`.

### Autocomplete duplicando referencia
Causa:
label do produto ja contem `[REFERENCIA]` e a linha secundaria tambem mostra `Codigo REFERENCIA`.

Regra:
autocomplete de produto deve mostrar ID, codigo de barras, categoria e preco na linha secundaria, evitando duplicar a referencia.

### Calendario nao navega ou nao limpa na edicao
Causas:
- componente customizado de data nao escutava mudancas externas feitas por JS.
- clique nas setas do calendario podia cair no alvo errado.
- limpar visualmente a data sem limpar o valor real do input.

Regra:
- calendario deve reagir a `input` e `change`.
- ao limpar data, setar `value = ''`, limpar `valueAsDate` quando possivel, remover/default e disparar `input` + `change`.
- setas de mes precisam usar `closest('[data-nav]')`, prevenir propagacao quando necessario e renderizar novamente sem fechar o calendario.
- Edicao de combo/promocao com datas vazias deve salvar `NULL`, mantendo inicio imediato e sem prazo de termino.

### Promocao programada sumindo no filtro
Causa:
filtro de status tratava somente `ativas` e `finalizadas`, e o filtro por tipo (`Combos`) nao considerava `programadas`.

Regra:
- Status de tela deve ter estado explicito: `ativas`, `programadas`, `finalizadas`, `inativas`.
- Filtro por tipo deve mostrar registros daquele tipo independentemente de serem ativos/programados/finalizados, respeitando filtro de status quando o usuario escolher um status.
- Combo programado precisa aparecer ao filtrar `Combos`.

### Cabecalho vazio na visao inicial
Causa:
renderizar secao/cabecalho mesmo quando nao havia linhas para aquele tipo.

Regra:
- Na visao inicial de condicoes comerciais, se um tipo nao tiver registros visiveis, esconder a secao inteira ou mostrar estado vazio unico.
- Nao mostrar barra colorida ou cabecalho de tabela vazio.

### Regra "A partir de" aplicada errado
Causa:
interpretacao como maior que (`>`) em vez de maior ou igual (`>=`).

Regra:
- `A partir de 5` significa quantidade maior ou igual a 5.
- `Quantidade 5` significa exatamente 5.

### Preco vivo ignorando desconto por categoria
Causa:
calculo de combo, kit ou brinde olhando apenas o preco promocional individual do produto.

Regra:
- preco vivo comercial deve comparar preco de venda, preco promocional individual e desconto por categoria/subcategoria.
- aplicar sempre o menor preco elegivel, sem acumular descontos.
- para uso automatico em combo, kit e brinde, a promocao precisa estar ativa, dentro da vigencia e ter pelo menos 5 dias da semana selecionados.

### Promocao esporadica aplicada automaticamente
Causa:
promocao com poucos dias da semana era elegivel para combo/kit/brinde automatico, criando dificuldade operacional.

Regra:
- combo, kit e brinde so podem puxar automaticamente preco promocional individual ou desconto por categoria quando a promocao tiver pelo menos 5 dias da semana selecionados.
- promocao com 1 a 4 dias da semana deve aparecer futuramente no PDV como opcao manual/sugerida, nao como preco automatico na criacao de combo/kit/brinde.

### Tooltip nativo preto em origem promocional
Causa:
uso de `title`/tooltip nativo do navegador para explicar origem do preco.

Regra:
- origem promocional deve usar balao visual proprio, legivel em tema claro e escuro.
- nao mostrar termos tecnicos como `Fonte` e `Base` para o usuario.
- texto deve explicar se veio de promocao individual ou desconto por categoria, nome da promocao e prazo quando houver.

### Log de promocao com dias numericos
Causa:
campo `dias_semana` armazenado como `0,1,2...` exibido cru na auditoria.

Regra:
- log de promocao deve converter dias para nomes: Seg, Ter, Qua, Qui, Sex, Sab, Dom.
- se todos estiverem selecionados, exibir `Todos os dias`.

### Listagem de brinde pouco autoexplicativa
Causa:
cabecalhos e textos como `Produto gatilho`, `Brindes no PDV`, `Usa promo` e blocos muito verticais confundiam a leitura.

Regra:
- usar `Produto gerador de brinde` no formulario.
- na listagem, usar `Item vendido` e `Brindes`.
- separar visualmente os itens que sao brindes.
- exibir `Gratis` para o item entregue sem custo.
- manter validade, status e acoes visiveis.
- evitar texto longo como resumo; preferir composicao visual compacta.

### Logo da filial dando salto ao trocar de tela
Causa:
sidebar nascia sem largura final antes do Alpine/JS aplicar `collapsed`, e a imagem da filial podia definir temporariamente a largura/altura do menu.

Regra:
- definir largura inicial da sidebar por CSS/HTML antes do JS;
- nao depender de `onload` da imagem para definir tamanho estrutural do card;
- classes de proporcao da logo devem vir do servidor quando possivel;
- validar com refresh e navegacao entre telas, porque o estado final pode parecer correto mesmo havendo flicker no primeiro frame.

### Logo com cantos quadrados no tema escuro
Causa:
border-radius aplicado apenas ao container, enquanto a imagem visivel preservava cantos retos.

Regra:
- aplicar `border-radius` tambem no elemento `<img>`;
- preservar fundo original da imagem, sem tentar remover fundo automaticamente;
- para logos quadradas/pequenas, usar imagem maior e nome da filial abaixo;
- para logos horizontais, ocupar a largura disponivel e manter nome abaixo.

### Status de promocao conflitante apos ativar pela listagem
Causa:
linha da listagem mantinha estado antigo ou misturava status da promocao com status de produto/filial.

Regra:
- apos ativar/inativar pela listagem, reconsultar ou atualizar a linha com o status retornado pelo backend;
- status principal da promocao deve ser unico: Ativo, Programado, Finalizada ou Inativo;
- badges auxiliares precisam ser claramente secundarios e nao podem contradizer o status principal.

### Merge cego da branch do Thiago
Causa:
branch paralela baseada em commit antigo, com arquivos comuns alterados.

Caso real em 22/05/2026:
- branch `origin/thiago/dashboard`;
- commit do Thiago `0ce65bc`;
- merge direto teria removido mudancas recentes de estoque/compras/produtos/docs.

Regra:
- nunca fazer merge cego quando a branch do Thiago estiver atrasada.
- acoplar manualmente funcionalidades novas, preservando a `main`.
- sempre rodar testes e acompanhar Railway depois.

### Alerta de vencimento quebrando testes legados
Causa:
mudanca de nivel de risco antigo (`ALTO`) para novas faixas (`D7`, `D30`, etc.).

Caso real:
- testes esperavam `AlertaVencimento.NivelRisco.ALTO` para vencimento proximo.
- regra nova classifica ate 7 dias como `AlertaVencimento.NivelRisco.D7`.

Regra:
- manter valores legados por compatibilidade, mas testes novos devem usar faixas `D1`, `D7`, `D30`, `D60`, `D90`, `D180`.

### Kardex abrindo deslocado ou com informacao confusa
Causas:
- overlay herdando scroll anterior;
- cards de movimentacao grandes demais;
- quantidade movimentada sem diferenciar entrada/saida;
- numeros soltos sem rotulo;
- alerta de minimo no card errado.

Regra:
- ao abrir sobreposicao de Kardex, posicionar no inicio do conteudo e deixar respiro do topo.
- movimentacoes devem ficar compactas e ordenadas por data/hora desc.
- entrada mostra `Quantidade adicionada`.
- saida mostra `Quantidade retirada`.
- sempre mostrar `Estoque anterior` e `Saldo apos`.
- alerta de estoque abaixo do minimo fica no card `Disponivel`, com vermelho claro e tooltip.

### Duplicidade de XML com mensagem confusa
Causa:
tela abria a nota existente, mas misturava termos tecnicos, estorno/cancelamento, lista, auditoria e mensagens de sistema.

Regra:
- duplicidade deve explicar que a NF ja foi importada na filial e abrir a entrada existente para evitar duplicar estoque/custo/financeiro.
- acoes principais:
  - `Continuar conferencia`;
  - `Cancelar entrada anterior`.
- Se ja houve efetivacao, cancelar precisa abrir revisao de impacto e registrar auditoria.
- Evitar textos como `Cancelada por tentativa de importacao duplicada...` e `historico auditavel` na tela principal.
