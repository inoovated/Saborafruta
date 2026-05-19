# Resumo tecnico - Combos e Promocoes - 18/05/2026

## Contexto da tarefa
Esta conversa fechou a etapa de Combos e Promocoes do ERP iNoovaTed antes do usuario seguir para o modulo de estoque do projeto inicial de unificacao do Thiago.

O objetivo foi transformar a tela de promocoes em uma area comercial completa, com:
- combos por quantidade;
- kits comerciais;
- brindes;
- descontos por categoria/subcategoria;
- precos promocionais individuais/em lote;
- auditoria;
- replicacao por filial;
- suporte mobile;
- suporte tema claro e escuro.

Tambem foram amadurecidas regras futuras para PDV e CRM. CRM ficou para etapa posterior.

## Arquivos principais alterados
- `apps/produtos/models/promocao.py`
- `apps/produtos/forms/promocao.py`
- `apps/produtos/forms/produto.py`
- `apps/produtos/views/promocao.py`
- `apps/produtos/views/promocao_audit.py`
- `apps/produtos/services/preco_service.py`
- `apps/produtos/services/replicacao_service.py`
- `apps/produtos/templates/produtos/promocao/list.html`
- `apps/produtos/templates/produtos/promocao/partials/_promocoes_quantidade.html`
- `apps/produtos/templates/produtos/promocao/partials/_kits_produtos.html`
- `apps/produtos/templates/produtos/promocao/partials/_brindes_produtos.html`
- `apps/produtos/templates/produtos/promocao/partials/_kits_categorias.html`
- `apps/produtos/templates/produtos/promocao/partials/_precos_promocionais.html`
- `apps/produtos/templates/produtos/produto/form.html`
- `apps/produtos/tests/test_preco_service.py`
- `apps/produtos/migrations/0019_promocoes_id_externo.py`
- `apps/produtos/migrations/0020_repara_id_externo_promocoes.py`
- `docs/AGENTS.md`
- `docs/BUGS.md`
- `docs/HANDOFF.md`
- `docs/PLANS.md`
- `docs/REPLICATION_RULES.md`
- `docs/UI_RULES.md`

## Decisoes importantes

### Tela de promocoes
- A tela oficial e `Produtos > Combos e Promocoes`.
- Rota principal: `produtos:combo-promocao-list`.
- A entrada pela aba/area de precos no cadastro do produto deve direcionar para essa tela, nao recriar campos promocionais completos dentro do produto.
- Produto guarda preco de venda base; promocoes ficam no modulo de promocoes.

### Abas finais
- Ativos
- Combo
- Kit
- Brindes
- Desconto por categoria
- Precos promocionais

### Preco vivo
Preco vivo comercial compara:
1. preco de venda;
2. preco promocional individual;
3. desconto por categoria/subcategoria.

Quando a flag estiver marcada, usa o menor preco elegivel.

Regra importante: comparar candidatos, nao acumular descontos automaticamente.

### Minimo de dias da semana
Combo, kit e brinde so puxam automaticamente preco promocional individual ou desconto por categoria se a promocao:
- estiver ativa;
- estiver dentro da vigencia;
- tiver pelo menos 5 dias da semana selecionados.

Promocoes com 1 a 4 dias da semana sao esporadicas e ficam para selecao futura no PDV.

### PDV futuro
No PDV:
- mostrar todas as promocoes elegiveis em modal;
- sugerir o menor preco;
- permitir o vendedor escolher;
- nao aplicar automaticamente quando houver varias opcoes sensiveis;
- brinde deve aparecer como item gratuito;
- brinde deve baixar estoque do produto entregue;
- kit deve baixar estoque item por item;
- combo deve respeitar `Quantidade` exata e `A partir de` como maior ou igual.

### CRM futuro
Promocoes por cliente/grupo devem ir para uma futura tela de CRM/Campanhas, nao para a tela atual de promocoes de produto.

Sugestao futura:
- campanhas por cliente;
- campanhas por grupo;
- aniversariantes;
- cliente VIP;
- cliente inativo;
- cupom;
- beneficio por relacionamento;
- integracao com PDV mostrando opcoes disponiveis.

## Funcionalidades concluidas

### Combo por quantidade
- Produto unico.
- Faixas por quantidade.
- Condicao:
  - `Quantidade`: quantidade exata.
  - `A partir de`: maior ou igual.
- Tipo de desconto.
- Calculo visual.
- Melhor preco vivo opcional.
- Vigencia opcional.
- Dias da semana.
- Status.
- Replicacao seletiva.
- Listagem com editar/inativar.

### Kit
- Produtos diferentes.
- Quantidade por item.
- Total sem kit.
- Desconto.
- Total final.
- Melhor preco vivo opcional por item.
- Baixa futura item por item no PDV.
- Listagem e mobile.

### Brinde
- Nova aba criada.
- Produto gerador de brinde.
- Quantidade minima.
- Um ou mais produtos gratuitos.
- Campo de PDV mostra `Gratis`.
- Resumo visual.
- Listagem com item vendido e brindes separados.
- Baixa futura de estoque do item gratuito no PDV.
- Melhor preco vivo opcional no produto gerador.

### Desconto por categoria
- Nome do desconto.
- Todas as categorias, categoria especifica ou subcategoria.
- Desconto percentual ou em valor.
- Possibilidade de aplicar sobre preco promocional individual quando marcado.
- Mensagem alerta desconto sobre desconto.
- Listagem com nome, categorias, desconto, validade, status e acoes.

### Precos promocionais
- Cadastro em lote por produto.
- Campos:
  - produto;
  - preco original;
  - desconto %;
  - desconto em valor;
  - preco promocional.
- Campos recalculam entre si.
- Valores monetarios com 2 casas.
- Sem setas de input numerico.
- Dias da semana, vigencia e status.
- Listagem com dias, status e acoes.

### Auditoria
- Botao `Log`.
- Logs de criacao, edicao e inativacao.
- Dias da semana exibidos por nome.
- Log protegido para nao derrubar tela principal.

### Mobile
- Formularios e listagens adaptados.
- Listagens promocionais devem permitir editar por clique/toque como produtos.
- Evitar overflow e manter acoes acessiveis.

### Temas
- Tema claro: branco/cinza claro com laranja.
- Tema escuro: preto/cinza escuro com azul.
- Tooltips de origem promocional devem ser visuais, nao tooltip preto nativo.

## Problemas encontrados

### Erro 500 autenticado na tela de promocoes
Sintoma:
- `/produtos/combos-promocoes/` mostrava Server Error 500 no fluxo autenticado.
- Curl sem sessao nao reproduzia, pois apenas redirecionava para login.

Causas provaveis:
- schema parcial no Railway envolvendo `id_externo`;
- contexto auxiliar de log;
- contexto auxiliar de replicacao.

Solucoes:
- migration `0019` transformada em idempotente;
- migration `0020` adicionada como reparo;
- log de promocoes protegido;
- opcoes de replicacao protegidas.

### Melhor preco ignorava desconto por categoria
Sintoma:
- combo/kit continuava puxando preco promocional individual de R$ 7,99 mesmo havendo desconto por categoria de 50%.

Solucao:
- `PrecoService` passou a comparar preco individual e desconto por categoria/subcategoria.

### Status por categoria divergente
Sintoma:
- desconto por categoria aparecia como fora do dia, mesmo seguindo regras esperadas.

Solucao:
- status/listagem foram alinhados com as mesmas regras das demais promocoes.

### Layout vertical e desalinhado
Sintoma:
- precos promocionais e brindes ficaram muito verticais ou pouco intuitivos.

Solucao:
- reorganizacao de grids;
- ajuste de labels;
- listagens mais compactas;
- resumo visual.

### Campos monetarios aceitavam caracteres/decimais demais
Sintoma:
- inputs permitiam letras, muitas casas ou setas do navegador.

Solucao:
- regra visual e funcional: valores monetarios com 2 casas; casas extras apenas estoque/granel/medidas.

## Regras criticas para proximas IAs
- Nao mover preco promocional individual de volta para o formulario principal do produto.
- Nao duplicar logica de preco vivo fora de `PrecoService`.
- Nao usar tooltip preto nativo para origem promocional.
- Nao trocar `Melhor preco` por `Usa promo`.
- Nao acumular descontos automaticamente; comparar e escolher menor candidato.
- Nao aplicar automaticamente promocoes com menos de 5 dias da semana em combo/kit/brinde.
- Nao deixar log, tooltip ou replicacao auxiliar derrubar tela principal.
- Nao sobrescrever copias replicadas independentes.
- Nao usar nome como chave de sincronizacao; usar `id_externo`.
- Nao misturar CRM com promocoes de produto nesta etapa.

## Pendencias
- Implementar consumo real no PDV.
- Implementar modal de opcoes promocionais no PDV.
- Baixar estoque real de kits e brindes no PDV.
- Testar replicacao seletiva com multiplas filiais reais em producao.
- Criar CRM/Campanhas futuramente para promocoes por cliente/grupo.
- Seguir para estoque.

## Validacoes realizadas na etapa final
- `python -m py_compile`
- `python manage.py check`
- carregamento do template de promocoes via `django.template.loader.get_template`
- `python manage.py test apps.produtos.tests.test_preco_service --keepdb`
- `git diff --check`

## Commits recentes relevantes
- `29f7647 Protege tela de promocoes contra falhas auxiliares`
- `43666df Corrige migration de id externo das promocoes`
- `a9a715b Corrige default do id externo de promocoes`
- `b1cb0d4 Ajusta replicacao seletiva de promocoes`
- `bd81357 Corrige permissao e replicacao de promocoes`
- `91efb88 Melhora tooltip de origem promocional`
- `aacbb77 Adiciona brindes em combos e promocoes`
- `553452b Limita promocoes automaticas por dias da semana`
- `27b95e2 Considera descontos ativos na criacao de combos`

## Proximos passos recomendados
1. Comecar modulo de estoque.
2. Antes de PDV, revisar `PrecoService` como fonte unica de verdade.
3. Quando chegar no PDV, desenhar modal de selecao de promocoes.
4. Testar replicacao seletiva em cenario real com pelo menos 2 filiais.
5. Criar CRM/Campanhas em etapa futura, separado da tela de promocoes de produto.
