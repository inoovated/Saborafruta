# UI_RULES.md

## Temas
- Existem dois temas principais:
  - Tema claro: branco/cinza claro com laranja como destaque e cor de acao principal.
  - Tema escuro: preto/cinza escuro com azul como destaque e cor de acao principal.
- Nao inverter as cores: no tema escuro, destaque principal deve ser azul, nao laranja.
- Tokens praticos:
  - Tema claro: primario laranja `#f15a24` / `#e8824a`; hover em tons de laranja mais fechado.
  - Tema escuro: primario azul `#2563eb` / `#1d4ed8`; hover em tons de azul mais claro.
  - Acoes destrutivas continuam vermelhas nos dois temas.
  - Avisos/alertas podem usar amarelo/vermelho conforme semantica, mas nao como cor principal da tela.
- No tema escuro, cores semanticas em listagens, badges e botoes pequenos devem ser suaves e consistentes, nunca fortes/neon:
  - azul: acao/informacao;
  - verde: sucesso/ok;
  - vermelho: erro/destrutivo/risco;
  - ambar: atencao/pendencia.
  Usar fundos translucidos baixos, bordas discretas e texto dessaturado para nao competir com o conteudo branco da listagem.
- Ao criar CSS especifico por tela, sempre declarar os dois estados:
  - `body.tema-claro ...` usando laranja para acao/destaque.
  - `body:not(.tema-claro) ...` usando azul para acao/destaque.
- Botoes principais devem ser solidos, elegantes e coerentes com o tema. Evitar botao principal com borda fraca quando a tela pede chamada de acao.
- Botoes secundarios podem ser outline, mas precisam parecer intencionais e alinhados.

## Mobile-first
Toda tela deve:
- funcionar em mobile
- evitar overflow
- ter modais responsivos
- funcionar em tablets

## Numeros e dinheiro
- Precos e valores monetarios sempre aparecem com 2 casas decimais.
- Nao exibir 4 casas decimais em preco, promocao, combo, kit ou desconto.
- Mais de 2 casas decimais ficam reservadas apenas para quantidades de estoque, itens a granel e medidas tecnicas.
- No cadastro de produto/item, o campo `Fator de conversao` deve se chamar `Conversao` e exibir 2 casas decimais.
- No cadastro de produto/item, tributacoes, estoque, peso/granel e fisico/logistica exibem 2 casas decimais por padrao.
- Campos de estoque no cadastro de produto/item so podem liberar mais de 2 casas quando o produto estiver marcado como fracionado ou vendido por peso/granel.
- Quantidades podem ser exibidas sem zeros desnecessarios quando forem inteiras, por exemplo `5 un.` em vez de `5,000`.
- Desconto percentual deve exibir `%` depois do numero.
- Buscas de produto devem aceitar ID, codigo/referencia, codigo de barras e nome quando a tela tiver autocomplete de produto.
- Resultado de busca de produto nao deve mostrar referencia/codigo duplicado. Se o label ja contem `[CODIGO]`, a linha secundaria deve priorizar ID, barras, categoria e preco.
- Preco promocional ativo deve ter destaque visual sem aumentar demais a largura da linha; mostrar preco original riscado e tooltip/contexto quando houver vigencia.

## Alinhamento e acabamento
- O usuario valoriza muito alinhamento visual. Antes de concluir, verificar se textos, botoes, status, cards e tabelas estao na mesma altura e com espacamentos consistentes.
- Arquivos de interface devem permanecer em UTF-8. Acentuação correta faz parte do acabamento da UI e não deve ser removida por preferência de ASCII.
- Textos de interface devem usar português correto, com acentos, cedilha e til. Não usar versões sem acento em labels, botões, mensagens, tooltips, cards ou textos de ajuda, salvo código técnico, slugs, nomes de variáveis, URLs ou limitações reais de integração.
- Padrao permanente de listagens: cabecalho de tabela no tema claro com fundo azul `#1b326e`, fonte branca, tamanho 12px, peso 700, nomes de colunas centralizados quando houver espaco, borda fina, cantos superiores arredondados e sem acento lateral grosso. A primeira e a ultima coluna precisam ter respiro; nenhuma coluna deve ficar colada nas bordas.
- No tema escuro, listagens devem seguir o padrao aprovado na tela de Produtos: cabecalho escuro/cinza (`#1e1e20`), fonte branca, bordas finas cinza (`#2a2a2e`), cantos arredondados e sem acento lateral colorido.
- Toda listagem desktop deve congelar o cabecalho no mesmo padrao aprovado na conferencia: posicao fixa logo abaixo do topo do sistema, mascara de fundo ativa durante a rolagem para impedir que linhas passem por tras, fundo branco no tema claro e fundo escuro no tema escuro. Nao deixar faixa branca/preta sobrando quando a tabela ainda nao encostou no topo.
- Essa regra vale tambem para listagens montadas fora de `_list_base.html`, como compras, custos, estoque, relatorios e telas operacionais. Se a tela tiver tabela desktop com muitos itens, ela deve entrar no mecanismo global de sticky/mask, usando `table-container`/`table-header` ou a deteccao global equivalente.
- Nao replicar cabecalho congelado tela a tela quando houver padrao global. Tabela desktop dentro de `main` deve ser detectada pelo mecanismo global; excecoes precisam usar `data-no-sticky-table` e ter motivo claro.
- O cabecalho congelado precisa copiar a largura real das colunas e acompanhar scroll horizontal do container. Cabecalho e corpo desalinhados contam como bug visual.
- A mascara do sticky deve cobrir qualquer conteudo que passe por tras do cabecalho durante a rolagem. Em tema claro, a mascara e branca; em tema escuro, usa o fundo escuro da pagina.
- Excecao de alinhamento: em Clientes e Fornecedores, a coluna `Nome` fica alinhada a esquerda no cabecalho e nas linhas para preservar leitura de nomes longos.
- Evitar elementos espalhados ou parecendo soltos. Texto explicativo e botao de acao devem compartilhar a mesma grade/linha visual quando forem relacionados.
- Nunca deixar cabecalho/cor de secao quando a respectiva listagem estiver vazia. Se nao houver linhas, esconder a secao inteira ou mostrar um estado vazio simples.
- Listagens de desktop nao devem depender de barra lateral/horizontal. Otimizar larguras, reduzir colunas secundarias e compactar campos curtos para manter `Acoes` sempre visivel dentro da area util.
- Em tabelas com cards internos, alinhar texto da linha ao centro visual do card, nao acima dele.
- Acoes de tabela devem usar icones ja usados no projeto para editar, ativar/inativar e confirmar, mantendo tooltip/acessibilidade quando necessario.
- Evitar cards dentro de cards sem necessidade. Preferir blocos limpos, bordas leves e respiracao consistente.
- Textos explicativos devem ser diretos e uteis, mas bem alinhados. Se forem alertas ou regras importantes, usar vermelho com cuidado e alinhado ao inicio do formulario.
- O `Voltar` principal da pagina fica no layout base (`templates/_base.html`) e deve seguir o tema: laranja no claro, azul no escuro. Templates de pagina nao devem criar outro `Voltar` no topo.
- O `Voltar` do layout deve levar para a ultima tela distinta visitada no sistema, ignorando repeticoes da mesma URL no historico do navegador.
- Antes de concluir alteracao visual, validar a tela renderizada, nao apenas o codigo. Quando envolver sidebar, tema, imagem, listagem ou responsividade, testar refresh e troca de tela.

## Calendarios
- Todo calendario customizado precisa permitir:
  - abrir e fechar sem quebrar layout;
  - avancar e voltar meses;
  - selecionar data;
  - limpar data;
  - salvar campo vazio quando a data for opcional;
  - refletir visualmente mudancas feitas por JS em edicao.
- Datas exibidas ao usuario devem ficar no formato brasileiro `dd/mm/aaaa`.
- Datas vazias em promocoes significam:
  - sem inicio informado: inicio imediato;
  - sem fim informado: sem prazo de termino.
- Dias da semana em combos/promocoes devem ficar proximos da vigencia, em controle recolhivel/compacto, com todos os dias pre-selecionados por padrao, acoes de marcar/desmarcar todos e visual coerente nos temas claro/escuro.

## Cadastros com listagem
- Quando a tela tiver cadastro e listagem no mesmo lugar, o cadastro deve ficar minimizado/acionavel no topo e a listagem abaixo.
- O botao minimizado deve ser compacto, claro e com `+`; nao usar uma caixa horizontal gigante.
- Deve haver respiro entre o botao/formulario e a listagem.
- Quando o formulario abrir, evitar espacos vazios grandes dentro das linhas. Use grids equilibrados, cards de resumo e quebras responsivas.
- Em mobile, o mesmo formulario deve virar uma coluna unica com botoes em largura total quando fizer sentido.
- Formularios de criacao/edicao devem ter acao principal primeiro e cancelar ao lado direito quando o usuario puder desistir.

## Combos e promocoes
- Nomes dos botoes de cadastro:
  - Criar combo
  - Criar Kit de produtos
  - Criar desconto por categoria
  - Criar brinde
- Quando estiver editando uma promocao existente, o botao principal deve indicar edicao, por exemplo `Salvar alteracoes`, e nao `Criar`.
- Texto explicativo deve ser pratico, explicando quando usar a funcionalidade, nao apenas descrevendo campos.
- Combo por quantidade deve mostrar resultado em cards: preco unitario atual, total atual sem combo, preco unitario com combo e total com combo.
- Kit deve mostrar produtos antes do desconto; depois exibir total antes do desconto, desconto aplicado e total depois do desconto.
- Cadastro/edicao de kit deve seguir a ordem: nome do kit, produtos, revisao do kit, vigencia/dias da semana/status/acoes. Nao usar descricao no formulario do kit nesta fase.
- Kit deve permitir usar precos promocionais ativos dos produtos quando existirem, com flag visivel apenas nesse contexto e calculo/revisao respeitando a escolha.
- Brinde deve seguir o padrao visual do kit: nome, produto gerador de brinde, itens gratuitos, resumo financeiro, vigencia/dias da semana/status/acoes, listagem abaixo e acao de editar por icone ou toque no mobile.
- Brinde pode usar o melhor preco vivo do produto gerador de brinde quando houver promocao individual ou desconto por categoria elegivel; o resumo deve mostrar origem do preco e valor dos itens gratuitos que futuramente baixarao estoque no PDV.
- Em brinde, o item entregue gratuitamente deve aparecer como `Gratis`, nao como desconto monetario.
- Listagem de brinde deve ser compacta e autoexplicativa:
  - coluna `Brinde` com nome legivel;
  - coluna `Item vendido`;
  - coluna `Brindes`;
  - itens gratuitos separados visualmente entre si;
  - validade, status e acoes sempre visiveis no desktop;
  - no mobile, toque/clique na linha deve permitir editar.
- Desconto por categoria deve permitir aplicar valor para todas as linhas e limpar todas, sem poluir o layout.
- Na tela de combo, o botao `Criar combo` deve ficar alinhado ao lado direito da area superior/listagem, com destaque solido do tema.
- A tela de combo deve explicar de forma pratica: `Ex.: 1 unidade custa R$ 10,00. A partir de 3 unidades, o valor unitario fica R$ 8,00. Na compra de 3 unidades, cada unidade sai por R$ 8,00.`
- O campo de produto nao deve ocupar largura exagerada depois de selecionado; ao lado deve aparecer o preco unitario atual.
- A barra/faixa de regras do combo deve manter: valor total sem combo, valor unitario no combo e valor total com combo.
- Campo de desconto deve se chamar `Desconto (% ou R$)`.
- Vigencia precisa mostrar aviso vermelho, alinhado ao lado esquerdo do formulario: `Nao e obrigatorio. Se nao informar datas, o combo comeca a valer de imediato e fica sem prazo de termino.`
- Controle de dias da semana deve valer para combo por quantidade, kit de produtos, brinde por produto, desconto por categoria/subcategoria e preco promocional em lote.
- Combo por quantidade deve usar o melhor preco vivo do produto por padrao quando existir, comparando preco promocional individual e desconto por categoria, mostrar o preco original ao lado e permitir desligar `Usar preco promocional`; essa opcao so deve aparecer quando existir preco vivo automatico.
- Preco vivo automatico em combo/kit exige promocao ativa, dentro da vigencia e com pelo menos 5 dias da semana selecionados. Promocoes com 1 a 4 dias sao esporadicas e nao entram automaticamente no combo/kit.
- A mesma regra de preco vivo automatico vale para brinde: minimo de 5 dias da semana para puxar automaticamente.
- Se existir preco vivo automatico, usar o termo visual `Utiliza Preco promocional` em listagens, como flag pequena, discreta e vermelha. Evitar caixas grandes, circulos ou fundo branco chamativo.
- A flag `Utiliza Preco promocional` nao deve encostar no status principal. Em linhas compactas, manter margem vertical e permitir quebra/empilhamento sem sobrepor acoes.
- Status de promocao deve refletir o cadastro real. Se uma promocao foi ativada pela listagem e esta ativa no cadastro, nao exibir simultaneamente `Ativo` e `Produto inativo` como se fossem status da mesma regra; status auxiliares precisam ser visualmente subordinados e usados apenas quando representam outra entidade.
- Promocao inativa deve continuar aparecendo quando `Mostrar inativos` estiver marcado e deve exibir status `Inativo`.
- Nas abas de promocoes, combos, kits, brindes e categorias, o controle `Mostrar inativos` deve existir quando houver registros inativos relevantes. Na aba/filtro `Inativas`, nao duplicar a mesma opcao sem necessidade.
- Ao inativar/ativar por icone de listagem, atualizar a linha para refletir imediatamente o status final vindo do backend.
- Alertas de produto recebendo desconto de outra promocao devem ser claros e curtos:
  - `Atencao: esse produto ja esta recebendo desconto de outra promocao.`
  - `Se deixar essa opcao marcada, o preco com desconto sera utilizado.`
- Mensagem de desconto por categoria deve alertar desconto sobre desconto quando a opcao estiver marcada.
- Origem de preco promocional deve ficar perto do preco, com icone informativo convidativo.
- Tooltip de origem nao deve usar tooltip preto nativo. Usar balao visual proprio, legivel nos temas claro e escuro.
- Tooltip de origem deve explicar em linguagem humana:
  - se veio de promocao individual ou desconto por categoria;
  - nome da promocao;
  - prazo ou ausencia de prazo;
  - preco aplicado.
- Nao mostrar termos tecnicos como `Fonte` e `Base` no tooltip do usuario.
- Listagem de combos deve separar variacoes/faixas em linhas, uma por faixa, quando isso melhorar leitura.
- Colunas esperadas da listagem de combo: Produto, Nome, Faixas, Validade, Status e Acoes.
- Faixa de combo deve exibir: Quantidade ou A partir de, Desconto, Unitario normal, Unitario combo e Valor total.
- `A partir de` significa maior ou igual a quantidade informada.
- Status da promocao/combo:
  - Ativo em verde.
  - Programado em azul.
  - Finalizada em amarelo/alerta, com tooltip informando que ao editar e colocar nova data pode ativar novamente.
  - Inativo discreto/cinza.
- Filtros da visao inicial devem permitir ver Todos, Ativas, Programadas, Finalizadas e cada tipo separado: Combos, Kits, Brindes, Categorias e Precos promocionais.
- No filtro por tipo, incluir tambem registros programados e finalizados quando o filtro de status permitir. Exemplo: filtro `Combos` precisa trazer combo programado.
- Se uma categoria/listagem da visao inicial nao tiver registros, nao mostrar cabecalho nem barra colorida vazia daquela categoria.
- Produto com preco promocional em lote e combos/kits/descontos por categoria podem ter campos diferentes; por isso a visao inicial deve agrupar por tipo quando as colunas nao forem equivalentes.

## Sidebar
- A sidebar nao pode quebrar, travar, abrir sozinha ao trocar tema nem dar "salto" visual ao trocar de tela.
- A largura inicial da sidebar deve nascer fixa no CSS/HTML antes do Alpine/JS aplicar estado, evitando que a logo defina a largura no primeiro frame.
- A logomarca operacional e a imagem da filial (`Filial.imagem`), a mesma configurada nos parametros locais e na central administrativa.
- A logo do sistema `iNoovaTed` permanece no topo da sidebar. A imagem da filial fica em card proprio abaixo do topo.
- A imagem da filial deve aparecer em todas as telas autenticadas, nao apenas no dashboard.
- Nao remover fundo automaticamente da imagem. Preservar o fundo original em tema claro e escuro.
- Imagens com cantos pontudos precisam ter bordas arredondadas no elemento visivel da imagem, nao apenas no container.
- Logos horizontais devem ocupar a largura disponivel sem estourar e com o nome da filial abaixo.
- Logos quadradas/menos horizontais devem ocupar mais area vertical e tambem deixar o nome da filial abaixo, centralizado.
- Nomes longos de filial devem ser centralizados, com quebra controlada ou truncamento; nunca devem empurrar o menu nem esconder acoes.
- A tela de selecao de filial deve seguir o mesmo criterio visual de logo: fundo branco real da imagem preservado, bordas arredondadas e espaco suficiente para nomes maiores.
- Ao trocar de filial, refreshar ou navegar entre telas, validar que a logo nao aparece gigante por um instante antes de ajustar.

## Logs e modais
- Modal de log precisa funcionar em mobile e desktop.
- Filtros de log nao podem estourar largura.
- Lista de alteracoes deve quebrar linha em textos longos.
- Valores antes/depois devem ser legiveis no tema claro e escuro.
- Evitar mensagens tecnicas ao usuario quando a operacao principal salvou corretamente.
- Log de promocoes deve usar titulo curto `Log`.
- Log de dias da semana deve mostrar nomes dos dias, nao numeros.

## Entrada XML e conferencia
- A conferencia de itens deve ser uma etapa do fluxo de entrada, nao uma tela com acoes soltas.
- Etapas esperadas:
  1. Vinculacao dos itens;
  2. Custos;
  3. Financeiro;
  4. Preco de venda.
- A etapa 4 depende de mockup do usuario e nao deve ser improvisada.
- Cards de resumo da conferencia devem ser pequenos, discretos e pouco coloridos. Evitar cards altos/metade da tela.
- Nao usar card `Sugeridos` nem bloco `Sugestoes prontas para revisar`.
- Produto sem vinculo aparece como `Sem produto` e deve ser resolvido direto na linha.
- A busca de produto interno deve ser um campo de busca/autocomplete, nao um select/listagem gigante.
- Resultado da busca deve seguir o padrao visual da listagem de produtos, sem barra lateral estranha ou dropdown pesado.
- O campo `Produto interno` deve receber o maior espaco da tabela.
- Campos curtos devem ser compactos:
  - `Conversao`;
  - `Qtd Nota`;
  - `Qtd. final`;
  - `Lote`;
  - `Acoes`.
- O nome visivel do fator deve ser `Conversao`, nao `Fator de conversao`.
- `Qtd Nota` deve mostrar a unidade junto da quantidade, com fallback para unidade de estoque/produto quando a unidade do XML vier vazia.
- `Qtd. final` deve ficar centralizada e recalcular visualmente conforme a conversao.
- `ID Nota` deve representar o codigo do item na nota/codigo do fornecedor, nao o indice 1, 2, 3 da linha.
- `Codigo barras` na conferencia e o EAN que veio da nota.
- Lote e validade devem ficar compactos:
  - `Lote: ABC`;
  - `Val: dd/mm/aaaa`.
- Nao quebrar `Lote:` e `Val:` em linhas desnecessarias.
- A acao de editar lote/validade deve usar icone/botao pequeno padrao de listagem.
- Produto vinculado aparece em verde com check, mas refinado, sem pill gigante e sem aumentar muito a altura da linha.
- Informacao de custo critico nao deve aparecer na etapa de vinculacao; custo pertence a etapa de custos.
- `Continuar entrada` deve ficar abaixo da lista, como acao de avancar fluxo, com icone/seta.
- Setas de voltar/avancar etapa podem ficar na barra branca de etapas, no canto direito, desde que nao concorram com a acao principal.
- No sistema todo, o `Voltar` global do topo deve priorizar a listagem/area-mae do modulo atual, nao a ultima URL do navegador. Em fluxos com etapas internas, a navegacao entre etapas e responsabilidade da barra/controles do proprio fluxo.
- Tabela de conferencia deve priorizar linhas baixas e densas para 50+ itens.
- Mobile da conferencia deve resolver as mesmas pendencias da tabela, sem criar fluxo separado de sugestoes.
- Nota com entrada iniciada e nao finalizada deve explicar esse estado no topo da capa e nao deve exibir itens recebidos como se a entrada ja estivesse finalizada.
- A capa da entrada deve mostrar dados da nota e resumo em blocos claros quando a entrada estiver em andamento.
- A acao de retomar entrada deve ficar perto da mensagem de nota nao finalizada.
- O botao de avancar etapa deve se chamar `Proxima Etapa`.
- `Proxima Etapa` no topo e no rodape precisam usar o mesmo visual, texto e icone de seta.
- Se houver item sem produto, qualquer tentativa de avancar pelo topo, rodape, etapa `Custos` ou seta de fluxo deve abrir o mesmo alerta contextual grande.
- Alerta de produtos sem vinculo deve usar vermelho suave e conter:
  - `Vincular agora`;
  - `Prosseguir e vincular mais tarde`.
- `Vincular agora` deve rolar/sinalizar a linha pendente em vermelho claro.
- `Prosseguir e vincular mais tarde` pode permitir revisar custos, mas nao deve comunicar que a entrada ja esta pronta para finalizar.
- Nao repetir `Produto sem equivalencia interna` abaixo do lote; usar linha vermelha suave e alerta superior.
- Produto interno vinculado deve ter acoes por icones pequenos, nesta ordem visual:
  - `+` para cadastrar/vincular;
  - editar para abrir produto em sobreposicao;
  - `x` vermelho para remover vinculo.
- Nao usar texto `Abrir cadastro` dentro da coluna de produto interno.
- Edicao de produto chamada pela conferencia deve abrir em sobreposicao/popup, nao em nova janela como fluxo principal.
- Os tres icones do produto interno devem ser pequenos, mas tocaveis, e nao podem criar espaco vertical entre linhas.
- Se os icones forem ajustados, conferir a linha em hover para evitar buraco entre uma linha e outra.
- A coluna `Produto interno` deve receber o maximo de espaco possivel; colunas curtas devem ceder largura antes de truncar demais o produto.

## Composicao de custo da entrada

- Tela de custos e etapa 2 do fluxo de entrada.
- O bloco principal deve ser operacional e curto; informacao fiscal detalhada fica recolhida em `Ajustes fiscais avancados`.
- Nao usar varios botoes para o mesmo calculo. Botao principal: `Salvar e recalcular custo`.
- Cards de resumo ficam abaixo do formulario, nao acima.
- Nao usar card `Diferenca contra total da nota` na visao principal.
- Pergunta do rateio:
  - `Como voce deseja ratear os custos extras?`
- O seletor de rateio deve ser compacto, nunca largura total sem necessidade.
- Opcoes visiveis do seletor:
  - `Valor (Rateia o custo adicional de forma proporcional)`;
  - `Quantidade (Custo adicional igual para todos os itens)`.
- Nao exibir rateio por peso enquanto nao houver regra de peso bem amarrada.
- `Ignorar custos extras` fica ao lado do seletor, como controle pequeno em vermelho claro.
- Quando `Ignorar custos extras` estiver marcado, encolher/guardar campos extras e calcular apenas valor de produto/desconto conforme regra da entrada.
- Secao de valores deve se chamar `Composicao de custo`.
- Campos da composicao devem caber em uma linha no desktop quando houver espaco:
  - `Frete (R$)`;
  - `Seguro (R$)`;
  - `Extra (R$)`;
  - `Desconto (R$)` + `%` ao lado;
  - `Valor total produto NF`.
- Campos de composicao nao devem ficar gigantes; usar largura proporcional ao conteudo e ao grid.
- `Extra` substitui `Adicionais`.
- `Valor total produto NF` vem do XML ou entrada manual e nao deve ser tratado visualmente como ajuste.
- Desconto deve permitir valor e percentual vinculados.
- Desconto e reducao usam fundo verde claro, nao apenas texto verde solto.
- Aumento de custo usa fundo vermelho claro, nao apenas texto vermelho solto.
- Custos extras usam fundo vermelho claro.
- Impostos usam fundo amarelo/ambar.
- `Custo total NF` usa fundo/sombra azul.
- Em tema escuro, manter contraste sem saturar demais as cores.
- Listagem de rateio deve ser densa e alinhada.
- Colunas esperadas da listagem:
  - `ID nota`;
  - `Cod. barras`;
  - `Produto`;
  - `Qtd`;
  - `Custo unit. NF`;
  - `Custo total NF`;
  - `Custos extras`;
  - `Impostos`;
  - `Desc.`;
  - `Total agregado`;
  - `Unit. agregado`;
  - `Custo anterior`;
  - `Dif. %`.
- Cabecalho deve alinhar com as colunas no tema claro e escuro.
- `Produto` deve receber o maximo de espaco possivel, mas sem esconder as colunas finais.
- `Custos extras` e `Impostos` podem ser empilhados dentro da celula para caber, desde que com linha compacta.
- `Desc.` deve mostrar a base em azul, acrescimo em vermelho quando houver e desconto em verde.
- `Dif. %` compara `Unit. agregado` contra `Custo anterior`.
- Se aumentou, mostrar `Aumento de` e o percentual em vermelho claro.
- Se reduziu, mostrar `Reducao de` e o percentual em verde claro.
- `Unit. agregado` pode ser editado manualmente.
- Custo manual nao deve quebrar a linha com texto longo. Mostrar somente `Manual` em vermelho pequeno abaixo do custo.
- Reset do custo manual deve ser botao pequeno apenas com icone, com tooltip se necessario.
- Custo manual nao altera visualmente os campos da composicao da NF nem o financeiro.

## Entrada com varios produtos

- O termo aprovado para o usuario e `Varios produtos`.
- Evitar `desdobramento`, pois pode nao ser claro para operadores brasileiros.
- `Produto unico` e a equivalencia simples.
- `Varios produtos` e um caso especifico em que uma linha da nota entra como mais de um produto interno.
- A conferencia deve ter controle visual separado para `Produto unico` e `Varios produtos`.
- A maioria dos itens sera `Produto unico`; a lista de `Varios produtos` deve ser simples e filtravel.
- Ao lado do contador de itens da lista de varios produtos, incluir opcao para ver apenas itens ja configurados como varios produtos.
- Item configurado como varios produtos deve ter flag visual propria, diferente do vinculo individual.
- Flag aprovada: verde suave com texto `Recebendo como varios produtos`.
- Item com vinculo individual pode ser convertido para varios produtos sem desvinculacao manual previa.
- Ao salvar varios produtos, o vinculo individual anterior e substituido.
- Na tabela de `Produto unico`, item com varios produtos deve mostrar:
  - badge `Receber como varios produtos`;
  - botao `Ver itens`;
  - `Qtd nota` como referencia da origem;
  - `Conversao` como `Nos itens`;
  - `Qtd. final` como `Ver itens`;
  - `Lote` como `Ver itens`.
- Na linha-mae de varios produtos, nao mostrar inputs de conversao, lote ou quantidade final.
- Lote, validade, quantidade e custo percentual devem ficar somente nas linhas de produtos gerados.
- Mobile deve apontar para `Ver itens vinculados` e nao abrir formulario de edicao simples para item com varios produtos.
- Mensagens longas abaixo de lote/validade devem ser evitadas; direcionar o usuario para a tela/aba correta.

## Quantidade da nota e quantidade final

- Em produto unico, `Qtd nota` pode ser editada.
- Quando `Qtd nota` for editada, mostrar `editado` pequeno, em vermelho, dentro/abaixo da celula.
- Depois de `Qtd nota`, `Conversao` e `Qtd. final`, deve existir botao pequeno para retornar a quantidade original da nota quando houver edicao.
- `Qtd. final` nao deve ser editavel diretamente.
- `Qtd. final` e calculada por `Qtd nota x Conversao`.
- Se o usuario quiser alterar estoque final, deve editar `Qtd nota` ou `Conversao`.
- Nao enviar `quantidade_recebida` no formulario de vinculacao simples como override manual.

## Custos para varios produtos

- Tela de custos deve diferenciar `Produto unico` e `Varios produtos`.
- Produtos gerados devem aparecer em linhas individuais na tabela de rateio.
- Cada produto gerado deve mostrar referencia ao item de origem.
- Nao agrupar todos os produtos gerados dentro de uma unica pill/celula quando isso prejudicar leitura.
- Produto gerado pode ter `Unit. agregado` editavel manualmente.
- Mostrar `Manual` em vermelho pequeno quando o custo unitario de produto gerado foi sobrescrito.
- O reset de custo manual de produto gerado deve seguir o mesmo padrao de icone pequeno.
- Custo percentual vazio em varios produtos significa rateio automatico por quantidade.
- O percentual de custo deve aparecer como informacao auxiliar, sem competir com custo final.

## Review Impeccable - custos da entrada

- A tela de custos recebeu nota 27/40 em critica Impeccable de 2026-05-26.
- Pontos aprovados:
  - fluxo e etapa claros;
  - separacao `Produto unico` / `Varios produtos`;
  - densidade operacional adequada;
  - tema escuro coerente.
- Pontos a melhorar:
  - formulario de composicao cria scroll horizontal em 1280px;
  - cards de resumo usam borda lateral colorida, padrao banido pelo Impeccable;
  - tabela de rateio tem chips demais, principalmente valores zerados;
  - `Ignorar custos extras` parece acao perigosa por usar vermelho forte;
  - edicao manual do custo precisa de affordance mais clara.
- Proxima rodada visual recomendada:
  - `layout` no formulario de composicao;
  - `distill` na tabela de rateio;
  - `polish` nos cards de resumo e estados de botao.

## Entrada XML - tipo, comportamento e financeiro

- A tela de importar XML deve pedir `Tipo de entrada` e `Origem` antes do upload.
- Tipos de entrada aceitos no fluxo atual:
  - `Compra para revenda`;
  - `Compra para produção`;
  - `Uso e consumo`;
  - `Ativo imobilizado`;
  - `Serviço / despesa`;
  - `Bonificação / amostra`;
  - `Consignação`.
- Origem aceita:
  - `Nacional`;
  - `Importação`.
- O comportamento deve ser exibido em chips clicáveis:
  - `Estoque`;
  - `Financeiro`;
  - `Alterar custo`.
- O usuário precisa perceber que pode clicar nos chips para alternar entre `Sim` e `Não`.
- Chips `Sim` usam verde suave.
- Chips `Não` usam vermelho claro.
- Textos explicativos aprovados:
  - `Estoque: Não dá entrada no estoque, não exige lote/validade.`
  - `Financeiro: Não gera contas a pagar, plano de contas e centro de custo.`
  - `Alterar Custo: Não recalcula o custo pela nota, custo atual do produto é mantido.`
- Evitar mensagens longas abaixo dos chips. A tela de importar XML deve ser limpa e direta.
- A tela de continuar entrada deve permitir editar tipo, origem e comportamento antes de ir para a conferência.
- O botão principal da tela de continuar entrada deve se chamar `Salvar e continuar dando entrada`.
- O botão superior de retorno ao fluxo deve se chamar apenas `Continuar`.
- Quando `Estoque: Não`, os detalhes de estoque, produto interno, lote e validade devem ficar recolhidos ou em modo leitura, com opção de `ver mais`.
- Quando `Financeiro: Não`, a etapa financeira deve explicar que não haverá contas a pagar, plano de contas ou centro de custo.
- Quando `Alterar custo: Não`, a etapa de custos deve deixar claro que o custo atual do produto será mantido.

## Financeiro da entrada XML

- A tela financeira deve ser compacta e operacional, sem excesso de cards explicativos.
- Não exibir as mensagens antigas:
  - `Finalize a entrada antes de gerar contas a pagar.`
  - `Cadastre pelo menos um tipo de despesa para classificar esta entrada.`
  - `5 parcela(s) pronta(s) para gerar.`
- Ações superiores esperadas:
  - `Contas a pagar`;
  - `Plano de contas`;
  - `Centros de custo`;
  - `Próxima etapa`.
- `Próxima etapa` deve ficar à direita no topo, induzindo continuidade.
- Repetir `Próxima etapa` no rodapé à direita quando a tela for longa.
- `Gerar contas a pagar` e `Revisar finalização` não devem aparecer como ações principais nessa tela.
- Em acréscimo/desconto:
  - campo `Valor` vem antes de `%`;
  - preencher valor calcula percentual;
  - preencher percentual calcula valor;
  - exibir apenas duas casas decimais.
- Em classificação e rateio:
  - campos esperados: `Categoria`, `Subcategoria de despesa`, `Tipo de despesa`, `Centro de custo`, `%`, `Valor`, `Observação`;
  - percentual máximo: 100%;
  - preencher percentual calcula valor;
  - preencher valor calcula percentual.
- `Tipo de despesa` é o nome aprovado para o terceiro nível. Não usar `Natureza`.
- `Forma de pagamento` das parcelas deve ser combobox com formas cadastradas no Financeiro.
- A replicação de parcelas deve ser separada:
  - ícone de replicar ao lado de `Forma de pagamento`;
  - ícone de replicar ao lado de `Observação`;
  - replicar apenas para parcelas existentes abaixo;
  - não alterar a nova linha vazia de parcela;
  - não limpar a primeira linha.
- O ícone de replicação deve parecer ação de repetir/retuitar, não um símbolo ambíguo.
- Excluir parcela usa lixeira vermelha.
- Nova parcela fica depois da última parcela existente.
- O botão de adicionar nova parcela deve ser compacto, com símbolo `+`, sem texto longo e sem ficar cortado.
- O datepicker da nova parcela deve parecer um campo de data normal, sem dropdown quebrado de `Selecionar data`.
- `Salvar parcelas` precisa ficar dentro do card, alinhado e com cor do tema.
- Em tema escuro, nenhum bloco interno pode ficar branco por herança indevida de estilo.

## PDV - temas, layout e overlays

- O PDV deve replicar as cores do header do sistema:
  - tema claro: laranja do header do ERP;
  - tema escuro: azul do header do ERP.
- No tema claro, a base do PDV deve ser majoritariamente branca, não cinza/azulada.
- No tema escuro, evitar preto absoluto em áreas de total; usar contraste escuro mais suave.
- Textos principais no tema claro devem ficar pretos ou muito próximos de preto; evitar cinza fraco em informação operacional.
- Ícones no tema claro devem acompanhar o contraste do texto, não ficar apagados.
- Botões principais precisam ser sólidos e clicáveis.
- `Novo Cliente` deve usar verde sólido.
- `Trocar Cliente` deve usar azul sólido, mas sem saturação exagerada.
- Formas de pagamento devem ser ligeiramente menores para liberar espaço.
- Laterais do PDV precisam ter largura suficiente para lista de itens e formas de pagamento.
- O bloco de totais não deve depender de linhas divisórias exageradas; separações devem ser um pouco mais escuras que o fundo para orientar leitura.
- Toast de troca de tema usa o padrão global no canto inferior direito.
- Não usar barra verde no rodapé para informar mudança de tema.
- O avatar do usuário deve usar a foto disponível. Usar letra inicial apenas como fallback.
- O ícone de tesoura não deve representar caixa; usar ícone de caixa/fechamento/controle financeiro ao lado de `Caixa`.
- `Mais opções` deve abrir overlay/drawer, não apenas expandir um bloco pequeno no rodapé.
- `Vendas pendentes` deve abrir drawer lateral com busca, filtros, card da venda, ações de continuar/informar cliente e resumo no rodapé.
