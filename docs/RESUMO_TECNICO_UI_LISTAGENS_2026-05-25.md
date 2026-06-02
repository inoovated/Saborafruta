# Resumo tecnico - UI, listagens, conferencia e temas - 2026-05-25

Este documento consolida a sessao em que foram refinadas as listagens, a conferencia de entrada, a tela de custos, as regras de tema claro/escuro, o comportamento do `Voltar`, casas decimais do cadastro de produto e o padrao global de cabecalhos congelados.

## Objetivo da sessao

Padronizar a experiencia operacional do ERP, principalmente em telas com muitas linhas, para que:

- o usuario nao perca o cabecalho das listagens durante a rolagem;
- tema claro e tema escuro usem cores, contraste e fontes coerentes;
- listagens longas fiquem densas, legiveis e alinhadas;
- a tela de conferencia de entrada sirva como modelo visual para as demais listagens;
- regras descobertas durante ajustes visuais fiquem documentadas para futuras implementacoes.

## O que foi concluido

- Tema escuro das listagens foi padronizado para usar texto branco em linhas e cabecalhos, evitando cinza fraco em tabelas operacionais.
- Cores semanticas foram suavizadas:
  - azul para base/informacao;
  - verde para sucesso/desconto/reducao;
  - vermelho para despesas, risco, aumento ou acao destrutiva;
  - amarelo/ambar para impostos e atencao.
- Na tela de custos da entrada:
  - despesas/custos extras ficam em vermelho suave;
  - impostos ficam em amarelo/ambar claro;
  - descontos/reducoes ficam em verde;
  - `Custo total NF` usa destaque azul;
  - `Unit. agregado` pode ser editado manualmente;
  - custo manual fica identificado como `Manual`;
  - reset de custo manual usa icone pequeno.
- O botao `Voltar` global foi ajustado para voltar para a area/listagem-mae do modulo, e nao simplesmente para a ultima URL do navegador.
- No cadastro de produto:
  - `Fator de conversao` passou a aparecer como `Conversao`;
  - campos de conversao, tributacao, estoque, peso/granel e logistica passaram a exibir 2 casas decimais por padrao;
  - estoque so deve permitir mais casas quando o produto for fracionado/peso/granel.
- Na conferencia de entrada:
  - campo `Conversao` foi aumentado para aceitar valores como `1000` sem quebrar;
  - lote e validade foram compactados;
  - texto `Lote importado do grupo rastro da NF-e.` foi removido da listagem;
  - produto interno ganhou mais espaco horizontal;
  - nome do produto interno foi priorizado para leitura completa na vinculacao;
  - foi removida duplicidade de codigo de barras no nome do item quando o EAN ja aparece na coluna propria;
  - foi criada possibilidade de adicionar mais de um item manual por vez;
  - cabecalho congelado da conferencia foi refinado ate virar o modelo aprovado.
- A tela de conferencia passou a usar cabecalho fixo com:
  - app header e sidebar alinhados;
  - cabecalho da tabela fixo logo abaixo do topo do sistema;
  - mascara de fundo para impedir que linhas aparecam passando por tras;
  - cantos superiores arredondados preservados;
  - tema claro com cabecalho azul `#1b326e`;
  - tema escuro com cabecalho `#1e1e20`;
  - fonte branca, compacta e consistente.
- O padrao de cabecalho congelado foi transformado em mecanismo global para listagens desktop.
- O mecanismo global foi aplicado nos templates base:
  - `templates/_base.html`;
  - `apps/templates/_base.html`.
- A listagem de entrada de mercadoria recebeu classes de tabela/pagina para participar do padrao global:
  - `apps/compras/templates/compras/entrada/list.html`.
- O mecanismo global detecta tabelas dentro de `main`, adiciona classes de apoio e cria um clone visual do cabecalho durante a rolagem.
- Foram protegidos casos em que produtos/estoque/fornecedores tinham wrappers com `overflow` que deixavam o fundo passando atras do cabecalho.
- Foram validadas localmente as telas:
  - compras/entradas;
  - produtos;
  - estoque;
  - fornecedores;
  - clientes;
  - conferencia como modelo base.

## O que ficou pendente

- Confirmar no deploy/Railway se o ultimo commit ja foi publicado e se o navegador do usuario nao esta mostrando cache antigo.
- Revisar todas as listagens que nao sejam `<table>` real dentro de `main`; o mecanismo global cobre tabelas, mas listas feitas como cards/divs precisam de adaptacao propria.
- Validar visualmente em producao as listagens operacionais menos acessadas:
  - relatorios;
  - listas fiscais;
  - telas de producao;
  - lotes;
  - historicos/logs;
  - modais com tabela interna.
- Mobile ainda deve ser tratado como experiencia propria. O congelamento global foi pensado para desktop; em mobile, a regra principal continua sendo nao estourar largura e preservar leitura.
- A etapa 4 de preco de venda da entrada continua pendente, pois depende de mockup/decisao do usuario.
- Existem alteracoes locais nao relacionadas que foram preservadas e nao entraram no commit da padronizacao:
  - `apps/cadastros/templates/cadastros/cliente/list.html`;
  - `apps/compras/templates/compras/entrada/finalizacao.html`;
  - arquivos `repomix-output.txt` e `repomix-output.xml` estavam nao rastreados no workspace.

## Bugs encontrados

- Listagens do tema escuro tinham textos cinza onde o padrao operacional exige branco.
- Cores de azul, verde e vermelho estavam fortes demais em alguns pontos, competindo com os dados da tabela.
- Na listagem de custos, despesas, impostos e descontos nao estavam diferenciados de forma clara.
- `Voltar` usava comportamento parecido com o historico do navegador e podia voltar para uma etapa errada, como custos em vez da listagem de notas.
- Campos numericos no cadastro de produto exibiam mais casas decimais do que o necessario.
- `Fator de conversao` era um nome longo demais para a operacao; o usuario pediu `Conversao`.
- Na conferencia, o campo `Conversao` ficou pequeno e quebrou quando recebeu valor maior, como `1000`.
- O produto da nota podia repetir o codigo de barras no nome e na coluna `Codigo barras`, desperdicando espaco.
- O cabecalho congelado inicialmente ficou quadrado, depois colado demais no topo, depois com faixa/fundo aparecendo atras.
- O cabecalho escuro chegou a usar cor preta demais ou azul demais em iteracoes; a cor final desejada para tema escuro voltou para `#1e1e20`.
- O espaco entre cabecalho e primeira linha oscilou em varias iteracoes; o valor aprovado ficou proximo de `1.5` da referencia visual pedida.
- Em produtos, estoque e fornecedores, a primeira tentativa global nao congelou tudo corretamente porque alguns wrappers e CSS locais tinham `overflow` e estrutura diferentes da conferencia.
- Em fornecedores e estoque, o fundo da pagina ainda aparecia passando atras do cabecalho em certas rolagens.
- Em produtos no tema escuro, o cabecalho chegou a encolher/truncar demais as colunas por causa de largura/zoom/overflow.
- A listagem de entrada de mercadoria e a de custos tambem ficaram de fora da primeira replicacao, mostrando que a regra precisava ser global e nao feita tela a tela.

## Correcoes aplicadas

- Criado padrao visual global para `table-header`, `table-container` e wrappers de tabelas.
- Adicionadas variaveis globais de cabecalho sticky:
  - `--erp-list-sticky-header-offset`;
  - `--erp-list-sticky-gap`;
  - `--erp-list-sticky-head-height`;
  - `--erp-list-sticky-head-bg`;
  - `--erp-list-sticky-page-bg`.
- Criado clone visual global `.erp-table-sticky-clone` para congelar cabecalhos com mascara de fundo.
- Adicionado estado `body.has-sticky-list` para fixar o header do sistema e ajustar a area principal quando houver listagem congelavel.
- O clone global:
  - copia as larguras reais das colunas;
  - respeita o scroll horizontal do container;
  - fica alinhado ao header real;
  - preserva cantos arredondados;
  - usa fundo branco no tema claro e fundo escuro no tema escuro;
  - fica com `pointer-events: none`, para nao bloquear a tabela.
- Adicionado `MutationObserver` para detectar tabelas inseridas depois do carregamento.
- Adicionada excecao para `.entrada-conferencia-table`, porque a conferencia possui comportamento proprio aprovado e mais especifico.
- Reforcados seletores para lidar com wrappers `.card`, `.overflow-x-auto` e `.table-container`.
- A listagem de entrada de mercadoria recebeu `erp-list-page`, `table-container`, `rounded-2xl` e `table-header`.
- Ajustadas cores de cabecalho:
  - claro: `#1b326e`;
  - escuro: `#1e1e20`.
- Ajustada regra de primeira linha de dados para haver respiro entre header e dados, sem faixa visual sobrando.
- Ajustes de custos e conferencia foram iterados em commits pequenos ate chegar ao padrao aprovado.

## Novas regras descobertas

- Toda listagem desktop com muitos itens deve congelar o cabecalho no mesmo padrao da conferencia.
- A regra vale para o sistema todo, nao apenas Produtos, Estoque, Clientes e Fornecedores.
- Nao implementar congelamento tela a tela quando houver padrao global possivel.
- Toda tabela desktop dentro de `main` deve participar do mecanismo global, salvo excecao explicita com `data-no-sticky-table` ou comportamento proprio documentado.
- Cabecalho de tabela em tema claro:
  - fundo `#1b326e`;
  - texto branco;
  - fonte compacta;
  - cantos superiores arredondados;
  - primeira e ultima coluna com respiro.
- Cabecalho de tabela em tema escuro:
  - fundo `#1e1e20`;
  - texto branco;
  - borda discreta `#2a2a2e`;
  - sem linha/acento extra nao solicitado.
- Durante a rolagem, a area acima do cabecalho precisa ter mascara de fundo:
  - branca no tema claro;
  - escura no tema escuro.
- O fundo ou linhas da tabela nunca devem aparecer passando atras do cabecalho congelado.
- O cabecalho congelado deve ficar na mesma posicao visual da conferencia, alinhado com header do sistema e sidebar.
- Nao deixar nome de coluna colado nas pontas da listagem.
- A coluna `Produto interno` na conferencia deve receber mais espaco horizontal do que colunas curtas.
- Nomes de produto devem ser lidos da esquerda para a direita e nao sacrificados por colunas curtas.
- Campos curtos devem ser compactos:
  - conversao;
  - quantidade;
  - lote;
  - validade;
  - acoes.
- Quando o item da nota ja tem EAN na coluna `Codigo barras`, nao repetir esse EAN no texto do produto da nota.
- Ajuste visual so deve ser considerado pronto depois de validacao renderizada em tema claro e escuro.

## Alteracoes importantes de arquitetura

- O padrao de cabecalho congelado deixou de ser apenas CSS por tela e virou infraestrutura global de UI nos templates base.
- A solucao usa uma combinacao de CSS global e JavaScript leve:
  - identifica tabelas elegiveis;
  - marca containers como `.erp-sticky-table-container`;
  - marca a primeira linha de cabecalho como `.table-header`;
  - cria um clone fixo do cabecalho durante a rolagem;
  - sincroniza larguras/posicao com a tabela real.
- A conferencia continua como excecao controlada porque ja tinha comportamento especifico aprovado.
- A listagem de entrada de mercadoria foi ajustada para seguir o contrato global de tabela.
- A regra agora esta centralizada, reduzindo a chance de cada tela resolver sticky de um jeito diferente.
- Foi mantida compatibilidade com templates duplicados em:
  - `templates/_base.html`;
  - `apps/templates/_base.html`.
- Nao houve alteracao de model ou migration nesta etapa de UI.

## Mudancas de replicacao

- Nao houve mudanca de regra de replicacao de dados nesta sessao.
- A regra permanente continua:
  - estoque, lote, reserva, movimentacao, inventario, custo efetivado e auditoria operacional nao replicam entre filiais;
  - produto continua unico com vinculo por filial;
  - equivalencias de fornecedor ajudam entrada XML, mas nao sao movimento replicavel;
  - promocao/combos/kit/brinde seguem replicacao propria quando a regra permitir.
- A mudanca desta sessao foi de padronizacao visual global, nao de sincronizacao de dados.

## Mudancas de produtos

- Cadastro de produto passou a seguir 2 casas decimais por padrao nos campos numericos operacionais.
- `Conversao` substitui o texto `Fator de conversao`.
- Mais casas decimais em estoque devem aparecer somente para produtos fracionados/peso/granel.
- Produto interno na conferencia ganhou prioridade visual.
- Se nome do item da nota vier com EAN duplicado, a UI deve ocultar/remover a duplicidade quando ja existir coluna propria para codigo de barras.
- Listagem de produtos deve seguir o cabecalho congelado global.
- Em produto, o header fixo nao pode criar linha extra, borda preta/branca sobrando ou fundo aparecendo atras.

## Mudancas mobile

- A regra de congelamento foi pensada para desktop.
- Em mobile, a prioridade continua sendo:
  - uma coluna ou cards bem organizados;
  - sem overflow horizontal quebrado;
  - acoes visiveis;
  - campos curtos;
  - modais responsivos.
- A conferencia mobile deve resolver as mesmas pendencias da tabela desktop, mas sem depender de um cabecalho fixo horizontal.
- Formularios e listagens mobile nao devem criar fluxo paralelo diferente do desktop quando isso confundir a operacao.

## Mudancas de UI e temas

- Tema claro:
  - fundo claro;
  - destaque principal laranja;
  - cabecalho de listagem azul `#1b326e`;
  - mascara sticky branca.
- Tema escuro:
  - fundo escuro;
  - destaque principal azul;
  - cabecalho de listagem `#1e1e20`;
  - texto branco;
  - mascara sticky escura.
- Cores semanticas devem ser suaves, nao neon.
- Botoes principais seguem tema:
  - laranja no claro;
  - azul no escuro.
- Cabecalhos de tabela precisam manter:
  - altura compacta;
  - fonte igual entre temas;
  - peso consistente;
  - espacamento sem exagero;
  - respiro antes da primeira linha.
- Alinhamento visual deve ser conferido depois de alterar qualquer listagem.

## Possiveis riscos futuros

- Algumas listagens podem nao ser tabelas reais e, portanto, nao entram automaticamente no sticky global.
- Tabelas dentro de modais, tabs fechadas, componentes carregados por AJAX ou partials tardios podem exigir validacao adicional.
- CSS local antigo com `overflow: visible`, `position`, `transform` ou largura fixa pode interferir no clone sticky.
- Zoom alto do navegador ou telas pequenas podem truncar colunas; nesse caso a solucao deve priorizar redistribuir larguras, nao aceitar sobreposicao.
- Templates duplicados entre `templates/_base.html` e `apps/templates/_base.html` precisam continuar sincronizados.
- A conferencia tem comportamento proprio; mudancas no sticky global nao devem quebrar esse caso aprovado.
- Validacao local nao garante deploy imediato; Railway/cache do navegador podem mostrar estado anterior por alguns minutos.
- Arquivos locais nao relacionados devem continuar fora de commits ate serem revisados.

## Proximos passos recomendados

- Conferir producao depois do deploy do commit final de UI.
- Testar com tema claro e escuro:
  - Produtos;
  - Estoque;
  - Clientes;
  - Fornecedores;
  - Compras/Entradas;
  - Composicao de custo;
  - Lotes;
  - Relatorios;
  - telas fiscais.
- Procurar no codigo listagens com `table` fora de `main` ou listagens feitas sem `<table>`.
- Para cada listagem nova, usar sempre:
  - wrapper com `table-container`;
  - `overflow-x-auto` controlado;
  - cabecalho real em `thead`;
  - classe `table-header` quando necessario.
- Quando a lista nao puder usar tabela real, criar comportamento proprio e documentar a excecao.
- Manter a tela de conferencia como referencia visual de sticky.
- Antes de subir mudanca visual, validar pelo navegador renderizado, em ambos os temas.

## Commits relevantes desta sessao

- `507a86a4 Padroniza listagens no tema escuro`
- `b9092291 Ajusta cores semanticas de custos`
- `5e84c828 Ajusta voltar global para area mae`
- `a4eb69da Padroniza casas decimais no cadastro de produto`
- `b02e3152 Aumenta campo de conversao na conferencia`
- `bd0c4773 Permite adicionar varios itens na conferencia`
- `b798a402 Arredonda cabecalho e limpa EAN duplicado`
- `92be1be8 Fixa topo da conferencia durante rolagem`
- `403290e4 Refina cabecalho fixo da conferencia`
- `7d013cf4 Remove linha e preta cabecalho da conferencia`
- `a06298eb Normaliza fonte da tabela de conferencia`
- `63586c3c Refina espaco entre cabecalho e dados`
- `d4a2b686 Amplia coluna do produto interno na conferencia`
- `d08a723c Adiciona cabecalho fixo nas listagens`
- `08db2d7a Replica sticky da conferencia nas listagens`
- `be884fcf Corrige congelamento geral das listagens`
- `afe1f7d1 Padroniza cabecalho fixo das listagens`

## Validacao realizada

- Templates principais carregados com `django.template.loader.get_template`.
- `git diff --check` executado nos arquivos alterados de UI.
- Validacao visual local com navegador/Playwright em tema claro e escuro.
- Conferidas listas com scroll e clone sticky ativo:
  - `/compras/entradas/`;
  - `/produtos/`;
  - `/estoque/`;
  - `/cadastros/fornecedores/`;
  - `/cadastros/clientes/`.
- Validado que o clone usa:
  - light `rgb(27, 50, 110)`;
  - dark `rgb(30, 30, 32)`;
  - fundo de mascara branco/escuro conforme tema.

## Estado final esperado

O ERP deve tratar cabecalho congelado de listagem como padrao global, nao como capricho de uma tela. A conferencia de itens e a referencia visual aprovada: header fixo, limpo, sem fundo vazando, com bom respiro e informacao alinhada.
