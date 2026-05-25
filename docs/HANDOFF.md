# HANDOFF.md

## Estado atual
- multiempresa
- multifilial
- replicacao por filial
- clientes
- fornecedores
- produtos
- marcas / fabricantes
- categorias
- subcategorias
- unidades
- mobile
- temas
- logs de auditoria em cadastros

## Produtos
- Produto tem marca/fabricante opcional.
- Produto tem fornecedor opcional.
- Lista de produtos filtra por categoria, subcategoria, marca/fabricante e fornecedor.
- Tela de produto preserva imagem ao editar dados que nao sao imagem.
- Produto tem botoes/atalhos para log, ficha tecnica e qualidade na edicao.
- Lista de produtos tem botoes superiores na prioridade definida pelo usuario: categorias, subcategorias, marcas, fornecedores, unidades, qualidade; filtros e acoes de exportacao ficam organizados para caber no desktop e mobile.
- Preco promocional individual deve ser configurado na tela de Combos e Promocoes. O cadastro do produto deve manter o preco de venda base e pode apenas direcionar para a tela promocional.

## Replicacao
- Checkboxes de grupos de replicacao sao por filial em `PoliticaReplicacaoFilial`.
- `PoliticaReplicacao` por empresa e legado/fallback; nao usar para novas gravacoes de tela.
- A filial de origem precisa ter o grupo marcado para enviar, e a filial de destino tambem precisa ter o mesmo grupo marcado para receber.
- Fornecedores e fabricantes sao opcoes separadas.
- Ambos replicam por filial.
- Sincronizacao imediata deve ser tolerante e independente por grupo.
- Ficha tecnica deve ser pulada quando tabelas de producao ainda nao existirem no banco.
- Na central administrativa, ficha tecnica e qualidade ficam no grupo visual "Producao e qualidade".
- Qualidade usa `PoliticaReplicacaoFilial.replicar_qualidade` e replica:
  - `ParametroQualidadeCategoria` para padroes por categoria/subcategoria quando a categoria existir/vincular na filial destino.
  - `ParametroQualidadeProduto` quando a tabela existir e o produto ja existir na filial destino.
- A tela de qualidade permite cadastrar padroes por categoria/subcategoria e aplicar no produto sem duplicar parametros existentes.
- A tela de qualidade deve priorizar padroes por categoria/subcategoria quando aberta pela lista de produtos; qualidade por produto fica como uso especifico por busca/edicao.
- Qualidade tem busca de produto por ID, nome, codigo/referencia e codigo de barras.
- Produtos agora tem a tela "Combos e Promocoes":
  - a primeira visao lista todas as condicoes comerciais ativas da filial;
  - a visao inicial tem filtros por status/tipo: Todos, Ativas, Programadas, Finalizadas, Combos, Kits, Brindes, Categorias e Precos promocionais;
  - quando filtrar por `Combos`, os combos programados tambem precisam aparecer;
  - cada aba mantem o cadastro minimizado no topo e a listagem do tipo abaixo, com acoes de editar e inativar;
  - botoes de cadastro devem usar os nomes: "Criar combo", "Criar Kit de produtos", "Criar desconto por categoria";
  - combo por quantidade do mesmo produto, com faixas de desconto percentual/desconto em R$ e calculo visual de preco unitario atual, total atual sem combo, preco unitario com combo e total com combo;
  - se o produto do combo tiver preco promocional ou desconto por categoria ativo, o combo compara os candidatos e usa o menor preco por padrao, permitindo alternar para o preco original no cadastro/edicao;
  - combo e kit so puxam automaticamente preco promocional/desconto por categoria quando a promocao esta ativa, dentro da vigencia e cobre pelo menos 5 dias da semana; promocoes de 1 a 4 dias sao tratadas como esporadicas e ficam para escolha futura no PDV;
  - combo por quantidade suporta condicao da faixa `Quantidade` e `A partir de`; `A partir de` e maior ou igual ao valor informado;
  - no formulario do combo, a ordem e: nome do combo, produto, faixas, adicionar variacao, vigencia/status/botao de criar;
  - a vigencia de combo/promocao e opcional. Sem inicio, vale imediatamente; sem fim, nao tem prazo de termino;
  - combos, kits, descontos por categoria e precos promocionais em lote podem restringir os dias da semana em que valem; por padrao valem todos os dias;
  - formularios de criacao/edicao precisam permitir limpar datas e salvar datas vazias;
  - calendario customizado deve permitir navegar meses, selecionar, limpar e refletir mudancas feitas por JS;
  - status esperados: Ativo, Programado, Finalizada e Inativo. Programado usa cor azul; Finalizada usa alerta/amarelo com tooltip sobre editar e reativar com nova data;
  - kit de produtos diferentes, com produtos primeiro, soma total dos itens, desconto depois e total final; a baixa futura de estoque deve ser item por item;
  - cadastro/edicao de kit segue a ordem nome, itens, revisao financeira, vigencia/dias/status/acoes; descricao nao aparece no formulario nesta fase;
  - kit pode usar o melhor preco vivo dos itens quando a flag estiver marcada, respeitando preco promocional individual, desconto por categoria e o minimo de 5 dias da semana para aplicacao automatica;
  - brinde por produto permite definir um produto gerador de brinde, quantidade minima e um ou mais itens gratuitos;
  - brinde segue o mesmo desenho do kit, com resumo financeiro, vigencia, dias da semana, status, replicacao e edicao por clique/toque na listagem;
  - brinde pode usar o melhor preco vivo do produto gerador de brinde quando marcado, seguindo a mesma comparacao entre preco promocional individual e desconto por categoria e o minimo de 5 dias da semana;
  - no PDV futuro, o brinde deve aparecer como item gratuito vinculado a promocao e dar baixa no estoque do produto entregue como brinde;
  - desconto por categoria/subcategoria, inclusive opcao "todas as categorias", com desconto definido por linha de categoria/subcategoria;
  - cadastro em lote e listagem separada de produtos com preco promocional ativo.
- Combos, kits, brindes e descontos tem validade opcional, ativo e flag individual "replicar para filiais".
- A replicacao de combos, kits, brindes e descontos tambem copia os dias da semana selecionados.
- Replicacao de combos, kits, brindes, descontos por categoria e precos promocionais em lote e seletiva por filial destino.
- Depois de criada, a copia replicada vira independente. Desligar replicacao ou editar a origem nao altera copias antigas automaticamente.
- Quando a filial destino nao puder receber a promocao, a tela deve antecipar o bloqueio e informar o motivo. No backend, salvamentos parciais devem avisar quais filiais nao receberam a copia.
- Promocoes replicadas usam `id_externo` para rastrear origem e evitar sobrescrita por nome.
- Replicacao comum de preco de venda do produto nao deve carregar campos promocionais; preco promocional replica apenas pelo fluxo de promocoes.
- Regra visual permanente: precos e valores monetarios sempre com 2 casas decimais; casas extras apenas para quantidades/estoque/granel.
- Consumos internos/insumos de produto foram discutidos, mas ficaram fora de combos/promocoes; devem entrar futuramente em ficha tecnica/composicao/BOM, nao como promocao.

## Preferencias visuais do usuario
- O usuario exige alinhamento visual cuidadoso. Revisar altura de textos, status, botoes, cards e tabelas antes de entregar.
- Tema claro: branco/cinza claro com laranja como destaque.
- Tema escuro: preto/cinza escuro com azul como destaque; nao usar laranja como destaque principal no escuro.
- Botoes de acao principal devem ser solidos, bonitos e chamativos na medida certa.
- Evitar cabecalhos/cor de secao quando a listagem correspondente estiver vazia.
- Evitar campos e cards parecendo soltos/desalinhados.
- Precos e totais sempre com 2 casas decimais; nao mostrar `10,0000` ou `5,000` quando nao for necessario.
- Listagens de desktop nao devem depender de barra horizontal. Se `Acoes` ficar escondido, reduzir/redistribuir colunas antes de aceitar scroll horizontal.
- Padrao permanente de listagens aprovado pelo usuario: cabecalho azul `#1b326e` no tema claro, fonte branca, 12px, peso 700, colunas centralizadas quando houver espaco, cantos arredondados, borda fina e respiro na primeira/ultima coluna. Nao usar barra/acento lateral grosso no cabecalho.
- No tema escuro, replicar o padrao da listagem de Produtos para todas as listagens: cabecalho escuro/cinza, fonte branca, bordas finas cinza, cantos arredondados e sem acento lateral colorido.
- Regra geral de congelamento: toda listagem desktop deve usar cabecalho sticky como a conferencia de itens, com mascara de fundo durante a rolagem para nao deixar dados/fundo passando por tras do cabecalho. A mascara so deve aparecer quando o cabecalho estiver chegando/colado ao topo.
- Nao restringir essa regra a `_list_base.html`: telas operacionais com tabela propria, como Compras/Entradas, Composicao de custo, Estoque e relatorios, tambem precisam do mesmo congelamento e da mesma mascara.
- Em Clientes e Fornecedores, a coluna `Nome` deve ficar alinhada a esquerda no cabecalho e no corpo, mesmo com o restante centralizado.
- Tema claro usa laranja para acoes principais; tema escuro usa azul. Nao inverter.
- O botao `Voltar` deve existir em telas internas, mas sem duplicidade. Usar o voltar global/base quando possivel.
- O usuario quer validacao visual antes de subir quando o ajuste e de UI. Nao encerrar apenas com base no codigo.
- Para logos de filial, preservar fundo original, arredondar cantos visiveis e adaptar por formato:
  - horizontal: usar largura disponivel e nome abaixo;
  - quadrada/menos horizontal: aumentar a area da imagem e colocar nome abaixo;
  - nomes longos: centralizar e limitar quebra/truncamento.

## Logs
- Produto tem log especifico e completo.
- Cadastros e central usam log generico:
  - clientes
  - fornecedores
  - transportadoras
  - representantes
  - empresas
  - filiais
  - usuarios
  - perfis
  - permissoes
- Logs precisam registrar antes/depois real.
- Campos tecnicos devem ser ignorados.
- Campos numericos reais devem ser normalizados para evitar ruido como `0.00` vs `0`.

## Handoff - Produtos, promocoes, fiscal e identidade visual - 22/05/2026

### Promocoes e combos
- A flag visual de preco vivo deve aparecer como `Utiliza Preco promocional`, pequena, vermelha e discreta.
- Essa flag nao deve encostar no status `Ativo`/`Inativo` e nao pode ficar com caixa grande.
- Ao inativar uma promocao, ela deve permanecer visivel quando `Mostrar inativos` estiver marcado e mostrar status `Inativo`.
- Ao ativar/inativar pela listagem, a listagem precisa refletir o status real salvo no cadastro.
- Evitar dois status conflitantes na mesma linha. Se houver informacao auxiliar de produto inativo, ela nao pode parecer status principal da promocao.
- Nas promocoes, se a replicacao nao estiver ativa, ativacao/inativacao e edicao sao apenas da filial atual.
- Quando uma regra foi salva com replicacao marcada, a flag deve continuar marcada ao editar ate o usuario desmarcar explicitamente.

### Produtos e estoque
- Listagem de produtos deve abrir com filtro `Todos`, mostrando ativos e inativos.
- Produto inativo continua opaco, mas o badge `Inativo` deve ter vermelho forte para ser percebido.
- Ao editar nome de produto inativo, o badge nao pode sumir.
- Ao inativar produto, perguntar se o usuario deseja zerar estoque da filial atual.
- Produto replicado pode ter estoque em outra filial; ativacao/inativacao deve ser individual por filial, com opcao de aplicar em outras filiais apenas mediante confirmacao.
- Listagem de produtos removeu `Tipo` e inclui `Markup` antes de `Margem`.
- Listagem de estoque deve permitir edicao inline de categoria, fornecedor, nome, estoque atual e estoque minimo, alem de mostrar preco promocional quando houver.

### Clientes e fornecedores
- Listagem de clientes deve ser editavel como produtos, com nome, CPF/CNPJ, contato e cidade.
- Em clientes, remover `Limite` e colocar `Contato` ao lado de CPF/CNPJ.
- Listagem de fornecedores deve ser editavel com nome, CNPJ, contato e cidade.
- Em fornecedores, remover `% Prazo`, trocar qualidade por contato e dimensionar CPF/CNPJ/contato para nao quebrar linha.

### Fiscal e tributario
- A tela deve se chamar `Fiscal e tributario`.
- Editar pela listagem fiscal deve abrir o produto diretamente na aba fiscal.
- Nao mostrar botoes/tabs extras no topo direito dessa tela.
- A listagem fiscal precisa ser compacta e sem barra horizontal.
- Separar NCM e CEST.
- Mostrar CFOP interno e CFOP externo separados; CFOP de compra/exportacao/devolucoes nao precisa aparecer na listagem principal.
- Remover `Info padrao`, origem ICMS, status fiscal e percentual de prontidao fiscal da listagem.
- Nao usar `CLS` como texto visivel. Mostrar regime simples/normal em tag simples, e CST centralizado abaixo.
- PIS e COFINS podem ficar juntos na listagem, mas organizados com tags/labels pequenos e cores distintas.
- Enquadramento de IPI pode ficar no cadastro do produto, nao na listagem.
- Regime tributario pode variar por filial; quando possivel, puxar da filial em vez de expor classe fiscal confusa ao cliente.

### Parametros fiscais
- Ordem da tela de parametros:
  1. Identidade visual
  2. Identificacao
  3. Endereco
  4. Documentos fiscais
  5. Integracao Focus
  6. Email e observacoes fiscais
- Remover caixa visual de tabela fiscal auxiliar da tela de parametros, mas manter a pendencia tecnica de criar base auxiliar fiscal.
- Checks como `Emissao habilitada` e `Enviar e-mail deste documento` precisam ter espacamento claro.
- Botao de remover imagem deve existir em identidade visual.
- Cores dos botoes de parametros devem seguir o tema: laranja no claro, azul no escuro.

### Identidade visual da filial
- A imagem exibida nos parametros locais deve ser a mesma imagem da filial cadastrada na central administrativa.
- Nao exibir essa imagem na tela de login.
- Nao substituir a marca `iNoovaTed` do topo da sidebar.
- Exibir a imagem da filial em card proprio na sidebar em todas as telas autenticadas.
- Exibir a imagem tambem na tela de selecao de filial.
- Preservar fundo original da imagem em qualquer tema; nao tentar remover fundo automaticamente.
- Para imagens horizontais, usar largura disponivel e nome da filial embaixo.
- Para imagens quadradas/menores, usar area maior para a logo e nome da filial embaixo.
- Arredondar a imagem visivel quando tiver cantos pontudos.
- Evitar flicker/salto de tamanho no carregamento: a sidebar deve nascer com largura final fixa antes do JS.

### Pendencias tecnicas
- Criar tabela/base fiscal auxiliar interna ou integracao confiavel para NCM, CEST, TIPI/IPI, CST PIS/COFINS, CFOPs e regras por UF.
- Revisar campos exigidos pela Focus NFe antes da primeira emissao real.
- Validar visualmente sidebar/logo com refresh, navegacao entre telas e troca de filial.

## Proximo passo
Etapa de Combos e Promocoes encerrada em 18/05/2026. Foco atual: estoque, dentro do projeto inicial de unificacao do Thiago. Depois seguem producao, fiscal e financeiro mantendo as regras de replicacao, mobile, temas e auditoria.

## Handoff - Estoque iniciado em 18/05/2026

### Decisao principal
- Estoque nao replica saldo em nenhuma hipotese.
- O que pode existir futuramente, se for muito bem justificado, e replicacao seletiva de parametros cadastrais de controle, como minimo/maximo/ponto de reposicao. Mesmo assim, o padrao recomendado e filial independente, porque a realidade fisica muda por filial.
- Transferencia entre filiais nao e replicacao. E movimento operacional: saida na origem e entrada na filial destino, com rastreio.

### Base reaproveitada da versao do Thiago
- A versao do Thiago trouxe boas ideias de KPIs, lotes, alertas e inventario.
- O projeto atual ja tinha uma base mais forte em `apps/estoque`, com `Estoque`, `MovimentacaoEstoque`, `LoteProduto`, `Inventario`, `ItemInventario`, `AlertaVencimento` e `MovimentacaoService`.
- O reaproveitamento nesta etapa foi conceitual e incremental; nao copiar codigo antigo diretamente porque ele usa APIs/estrutura anteriores.

### Primeira organizacao aplicada
- Tela de saldo passou a ter KPIs de itens controlados, abaixo do minimo, zerados e valor em estoque.
- Busca de estoque passou a aceitar ID, codigo/referencia, codigo de barras e nome.
- Tela de saldo passou a listar todos os produtos ativos vinculados a filial, exibindo saldo zero quando ainda nao existe linha em `Estoque`.
- Cada linha de saldo ganhou atalho para movimentar o produto ja selecionado.
- Criada rota/tela de nova movimentacao manual.
- Historico de movimentacoes ganhou entrada direta para nova movimentacao e busca ampliada.
- Ajuste manual e transferencia foram mantidos como fluxos separados.
- Quantidades passaram a evitar zeros finais desnecessarios.
- Criacao de lote com quantidade inicial agora gera entrada de estoque pelo `MovimentacaoService`, mantendo saldo e historico sincronizados.
- Em lote ja criado, quantidade inicial fica bloqueada; correcao de quantidade deve ser feita por movimentacao/ajuste.
- Inventario basico criado:
  - abre snapshot dos produtos ativos da filial;
  - permite salvar contagem;
  - ao fechar, gera ajustes pelo `MovimentacaoService` com documento de inventario;
  - se marcado para bloquear movimentacoes, entradas/saidas comuns da filial ficam bloqueadas ate fechar/cancelar.

### Regras permanentes do estoque
- Toda alteracao de saldo deve passar por `MovimentacaoService`.
- Nunca editar `Estoque.quantidade_atual` diretamente fora do service.
- Servicos antigos de custo medio e FIFO/FEFO foram mantidos como fachada, mas agora delegam entrada/baixa para `MovimentacaoService`.
- Movimento precisa registrar quantidade anterior e posterior.
- Saida nao pode deixar estoque negativo, salvo regra futura explicita e controlada.
- Lote vencido nao deve ser vendido.
- Kit no PDV futuro baixa estoque item por item.
- Brinde no PDV futuro baixa estoque do produto entregue gratuitamente.
- Combo baixa o produto vendido normalmente.

## Handoff - Combos e Promocoes encerrado em 18/05/2026

### Contexto
- O usuario concluiu a etapa de promocoes antes de seguir para estoque.
- A tela principal e `Produtos > Combos e Promocoes`, rota `produtos:combo-promocao-list`.
- A entrada pela edicao do produto na area de precos promocionais tambem direciona para essa mesma tela, normalmente com `?aba=precos`.
- Preco promocional individual nao deve mais ser editado diretamente no cadastro do produto como superficie principal; o cadastro do produto conserva o preco de venda base e apenas direciona para promocoes.

### Arquitetura funcional atual
- Models principais em `apps/produtos/models/promocao.py`:
  - `PromocaoQuantidade`
  - `PromocaoQuantidadeFaixa`
  - `KitProduto`
  - `KitProdutoItem`
  - `BrindeProduto`
  - `BrindeProdutoItem`
  - `KitCategoria`
  - `KitCategoriaRegra`
- View principal em `apps/produtos/views/promocao.py`.
- Auditoria de promocoes em `apps/produtos/views/promocao_audit.py`.
- Calculo de preco vivo em `apps/produtos/services/preco_service.py`.
- Replicacao em `apps/produtos/services/replicacao_service.py` e helpers da view de promocao.
- Template principal em `apps/produtos/templates/produtos/promocao/list.html` e partials em `apps/produtos/templates/produtos/promocao/partials/`.

### Regras de negocio consolidadas
- Preco vivo comercial deve comparar preco de venda, preco promocional individual e desconto por categoria/subcategoria.
- Quando a flag de uso de melhor preco estiver marcada, usar o menor preco elegivel.
- Nao acumular desconto automaticamente; comparar candidatos e aplicar o menor.
- Desconto por categoria pode usar preco promocional individual como base apenas quando a opcao estiver marcada. A mensagem deve alertar que isso gera desconto em cima de desconto.
- Combo, kit e brinde so puxam automaticamente preco promocional individual ou desconto por categoria quando a promocao:
  - esta ativa;
  - esta dentro da vigencia;
  - tem pelo menos 5 dias da semana selecionados.
- Promocao com menos de 5 dias da semana e esporadica; nao entra automaticamente em combo/kit/brinde.
- Datas vazias significam:
  - sem inicio: inicio imediato;
  - sem fim: sem prazo de termino.
- Status padrao das listagens:
  - Ativo
  - Programado
  - Finalizada
  - Inativo
- Evitar nomes improvisados como `Usa promo`; usar termos mais intuitivos, como `Melhor preco`, quando representar uso de preco vivo externo.

### PDV futuro
- O PDV deve mostrar todas as promocoes elegiveis em modal.
- O PDV deve sugerir o menor preco, mas permitir escolha do vendedor.
- Brinde deve aparecer como item gratuito vinculado a promocao e baixar estoque do produto entregue.
- Kit deve baixar estoque item por item.
- Combo por quantidade deve respeitar:
  - `Quantidade`: quantidade exata;
  - `A partir de`: maior ou igual.

### Replicacao de promocoes
- Replicacao de promocoes e seletiva por filial destino.
- Filiais bloqueadas devem aparecer desabilitadas com motivo antes do salvamento.
- Backend tambem deve avisar quais filiais nao receberam copia.
- Depois de criada, copia replicada vira independente.
- Desligar replicacao na origem nao apaga nem atualiza copias antigas.
- Replicar novamente para filial que ja possui copia com mesmo `id_externo` nao deve sobrescrever; deve informar que ja existe uma copia independente.
- `id_externo` foi adicionado a combos, kits, brindes e descontos por categoria para rastrear origem sem depender de nome.
- Migrations relevantes:
  - `apps/produtos/migrations/0019_promocoes_id_externo.py`
  - `apps/produtos/migrations/0020_repara_id_externo_promocoes.py`
- Essas migrations foram ajustadas para serem idempotentes e tolerantes a estado parcial em producao.

### Bugs encontrados e corrigidos nesta etapa
- Erro 500 ao abrir tela autenticada de promocoes:
  - causa provavel: contexto auxiliar de log/replicacao ou schema parcial em producao;
  - correcao: migrations de reparo para `id_externo` e protecao para log/replicacao nao derrubarem a tela.
- Desconto por categoria nao entrava no melhor preco de combo/kit:
  - correcao: `PrecoService` compara preco individual e desconto por categoria.
- Status de desconto por categoria aparecia fora do dia indevidamente:
  - correcao: status/listagem foram alinhados com a logica das demais promocoes.
- Dias da semana no log apareciam como numeros:
  - correcao: exibicao convertida para nomes.
- Falta de log de criacao:
  - correcao: auditoria de promocoes passou a registrar criacao e edicao.
- Campos de preco aceitavam letras, setinhas e casas demais:
  - correcao: entradas monetarias passaram a ser tratadas como texto/decimal controlado e exibicao limitada a 2 casas.
- Tela de precos promocionais estava vertical demais:
  - correcao: layout reorganizado em linhas mais horizontais e resumo compacto.
- Listagens de brindes estavam pouco autoexplicativas:
  - correcao: listagem ganhou item vendido, brindes separados, resumo visual, validade/status/acoes.
- Tooltip nativo preto era ruim visualmente:
  - correcao: origem promocional deve usar balao visual proprio com texto claro e sem termos tecnicos como `Fonte` e `Base`.

### Riscos futuros
- PDV ainda nao consome essas regras; cuidado para nao duplicar logica em outro lugar. Usar `PrecoService`.
- Schema parcial no Railway pode causar 500 se novas colunas forem usadas direto em listagens. Preferir migrations idempotentes quando campo novo entrar em tela principal.
- Replicacao seletiva precisa ser testada em base real com varias filiais antes de considerar 100% fechada operacionalmente.
- Logs devem ser tolerantes: erro de auditoria nunca deve derrubar tela principal.
- Evitar voltar preco promocional para o cadastro do produto; isso quebraria a separacao entre preco base e regra promocional.
- CRM por cliente/grupo foi discutido como futuro, mas nao deve ser misturado na tela de promocoes de produto.

### Commits importantes recentes
- `29f7647 Protege tela de promocoes contra falhas auxiliares`
- `43666df Corrige migration de id externo das promocoes`
- `a9a715b Corrige default do id externo de promocoes`
- `b1cb0d4 Ajusta replicacao seletiva de promocoes`
- `bd81357 Corrige permissao e replicacao de promocoes`
- `aacbb77 Adiciona brindes em combos e promocoes`
- `553452b Limita promocoes automaticas por dias da semana`
- `27b95e2 Considera descontos ativos na criacao de combos`

## Deploy Railway
- O projeto usa Dockerfile; migrations e `ensure_quality_schema` rodam no `CMD` de inicializacao do container.
- Nao ha `railway.json` com Post-deploy no repositorio neste momento.
- Se o Railway ficar com deploy ativo em commit antigo mesmo apos push, enviar commit nao-vazio para disparar novamente o webhook/deploy.
- Quando o deploy nao iniciar, verificar primeiro plano/credito Railway e se o webhook do GitHub disparou.
- `manage.py migrate` local em SQLite pode falhar por migrations antigas com SQL especifico; para mudancas de schema recentes validar pelo menos `manage.py check`, `sqlmigrate app migration` e deploy em PostgreSQL/Railway.
- Depois da sequencia de ajustes de combos, ultimo estado conhecido funcional inclui os commits:
  - `2556c83 Restaura versao estavel de combos`
  - `9f472d4 Ajusta programados e calendario de combos`
  - `50b32de Corrige navegacao mensal do calendario`
- Depois do fechamento de promocoes, ultimo estado conhecido funcional em producao: `29f7647 Protege tela de promocoes contra falhas auxiliares`.
- Se a tela `/produtos/combos-promocoes/` voltar a dar 500, comparar contra esses commits e reaplicar correcao pequena, validando template/contexto antes do deploy.

## Fechamento do estoque MVP - 21/05/2026
- Documentacao consolidada em `docs/ESTOQUE_FECHAMENTO_MVP.md`.
- Checklist final de aceite do estoque consolidado no mesmo documento.
- Migrations pendentes de `core` e `fiscal` foram formalizadas para eliminar o aviso de producao.
- Mudancas paralelas de parametros/identidade visual da filial foram integradas ao pacote atual, preservando o fluxo combinado de sempre partir do ultimo `origin/main`.
- Validacao local completa executada explicitamente com 213 testes:
  - `apps.cadastros.tests`
  - `apps.compras.tests`
  - `apps.core.tests`
  - `apps.estoque.tests`
  - `apps.fiscal.tests`
  - `apps.pdv.tests`
  - `apps.produtos.tests`
- Regra permanente reforcada: estoque fisico, lote, reserva, inventario e movimentacao nunca replicam entre filiais.

## Contrato Estoque x PDV x Promocoes - 21/05/2026
- Contrato consolidado em `docs/CONTRATO_ESTOQUE_PDV_PROMOCOES.md`.
- Fonte unica para consulta de produto vendavel: `ProdutoVendavelService`.
- PDV e vendas passam a validar produto vendavel antes de vender/reservar.
- Resposta do contrato inclui saldo disponivel, custo atual, preco aplicado, margem, status comercial, lote obrigatorio e promocoes aplicaveis.
- Produto sem preco/custo valido ou promocao com margem negativa bloqueia venda no backend.
- Combo por quantidade entrou no preco vivo.
- Kit no PDV baixa componentes item a item.
- Brinde no PDV baixa o produto entregue gratuitamente com movimento de estoque `BRINDE`.

## Handoff - Consolidacao Estoque, Kardex e Thiago - 22/05/2026

### Estado consolidado da sessao
- O foco principal permaneceu no modulo de estoque, especialmente entrada de mercadoria, conferencia de XML, Kardex/Extrato, telas densas e integracao com atualizacoes paralelas do Thiago.
- A regra operacional continua: antes de qualquer push, buscar a ultima versao do GitHub, comparar `origin/main` e a branch do Thiago, integrar com cuidado, testar, commitar, subir e acompanhar Railway.
- Ultimo commit integrado e deployado nesta sessao: `4869c47 Acopla modulo de lotes do Thiago`.
- Deploy Railway do commit `4869c47` terminou com `SUCCESS`.
- `/health/` em producao respondeu OK.
- `/lotes/` em producao redirecionou para login, confirmando rota registrada e protegida.

### Processo do Thiago
- Thiago trabalha em branch separada, normalmente `origin/thiago/dashboard`.
- Nunca fazer merge cego da branch do Thiago quando ela estiver baseada em commit antigo.
- Fluxo obrigatorio para acoplar mudancas dele:
  1. `git fetch origin main thiago/dashboard`.
  2. Conferir `git log --oneline origin/main` e `git log --oneline origin/thiago/dashboard`.
  3. Verificar se `main` local esta alinhada com `origin/main`.
  4. Comparar a branch do Thiago com cuidado.
  5. Se a branch dele estiver atrasada, trazer manualmente apenas os arquivos/funcionalidades novas.
  6. Preservar ajustes recentes de estoque, compras, produtos, UI e docs.
  7. Rodar `manage.py check`, testes relevantes e `git diff --check`.
  8. Commitar na `main`, fazer push e acompanhar o deploy Railway.
- Na ultima integracao, um merge direto de `origin/thiago/dashboard` teria removido varias mudancas recentes. Foi feita integracao manual seletiva.

### Atualizacao do Thiago integrada em 22/05/2026
- Branch: `origin/thiago/dashboard`.
- Commit do Thiago integrado: `0ce65bc feat: modulo Lotes com rastreabilidade bidirecional e alertas de vencimento 6 faixas`.
- Itens acoplados:
  - novo app `apps.lotes`;
  - rota `/lotes/`;
  - dashboard de lotes;
  - alertas de vencimento por faixas;
  - rastreabilidade bidirecional de lotes;
  - inspecoes de lote;
  - servico FEFO;
  - link de `Lotes` na sidebar desktop/mobile;
  - filtro template `dict_get`;
  - novas faixas de alerta `D1`, `D7`, `D30`, `D60`, `D90`, `D180`.
- Arquivos principais envolvidos:
  - `apps/lotes/**`;
  - `apps/core/templates/core/_sidebar.html`;
  - `apps/core/templatetags/erp_extras.py`;
  - `apps/estoque/models/alerta.py`;
  - `apps/estoque/services/alerta_service.py`;
  - `apps/estoque/views/alerta.py`;
  - `config/settings/base.py`;
  - `config/settings/test.py`;
  - `config/urls.py`.
- Migrations geradas/adicionadas:
  - `apps/estoque/migrations/0003_alter_alertavencimento_nivel_risco.py`;
  - `apps/lotes/migrations/0001_initial.py`;
  - `apps/lotes/migrations/0002_alter_inspecaolote_created_at.py`.

### Validacoes executadas na integracao do Thiago
- `python manage.py check --settings=config.settings.test`: OK.
- `python manage.py test apps.estoque.tests.test_movimentacao_service apps.estoque.tests.test_forms_views apps.compras.tests.test_entrada_recebimento --settings=config.settings.test --verbosity 1`: OK, 116 testes.
- `makemigrations --check --dry-run`: OK depois de gerar as migrations necessarias.
- `git diff --cached --check`: OK.
- Railway: deploy do commit `4869c47` com status `SUCCESS`.

### Regras novas de alerta de vencimento
- As faixas novas de `AlertaVencimento.NivelRisco` sao:
  - `D1`: urgente ate 1 dia;
  - `D7`: critico ate 7 dias;
  - `D30`: alto ate 30 dias;
  - `D60`: medio ate 60 dias;
  - `D90`: atencao ate 90 dias;
  - `D180`: aviso ate 180 dias.
- Valores legados `critico`, `alto`, `medio`, `baixo` continuam aceitos para compatibilidade.
- Testes antigos que esperavam `ALTO` para vencimento em ate 7 dias foram atualizados para `D7`.

### Kardex / Extrato de estoque
- A coluna da listagem de estoque deve chamar `Extrato`, nao `Estrato`.
- O botao `Abrir` deve abrir a sobreposicao `Extrato (Ficha Kardex)`.
- O Kardex deve mostrar:
  - foto do produto no cabecalho;
  - saldo atual;
  - disponivel;
  - reservado;
  - minimo;
  - reposicao;
  - giro diario;
  - giro/mes;
  - cobertura em dias, arredondada e sem virgula;
  - unidade;
  - preco de venda;
  - custo unitario;
  - custo total;
  - valor de venda total;
  - categoria;
  - fornecedor;
  - ultimas movimentacoes ordenadas por data/hora, mais recente primeiro;
  - historico de preco e custo;
  - lotes e validade;
  - botoes para abrir produto, registrar movimento, ver lotes e ver mais movimentacoes.
- Alerta de estoque abaixo do minimo deve ficar no card `Disponivel`, com destaque vermelho e tooltip explicando a falta.
- Cards de movimentacao devem ser compactos.
- Movimentacao positiva deve exibir `Quantidade adicionada`.
- Movimentacao negativa deve exibir `Quantidade retirada`.
- Cada movimentacao deve mostrar `Estoque anterior` e `Saldo apos`.
- Evitar numeros soltos nos cards de movimentacao.

### Entrada XML e duplicidade
- Entrada por XML aceita nota de qualquer CPF/CNPJ; divergencia de documento e alerta, nao bloqueio.
- Mensagem correta para CNPJ divergente:
  - `Atencao, essa nota nao possui o mesmo CNPJ que o cadastrado na filial. Essa nota esta vinculada ao CNPJ: <documento>.`
- Remover mensagem generica de `Qualquer CPF/CNPJ e aceito` das telas onde ela polui a operacao.
- Ao importar XML duplicado, o sistema deve abrir a entrada existente e explicar opcoes reais:
  - continuar conferencia, se a entrada ainda estiver aberta;
  - cancelar entrada anterior, se criada por engano;
  - se ja efetivou estoque, cancelar deve abrir revisao de impacto para devolver itens e registrar auditoria.
- Para o usuario final, preferir o termo `Cancelar entrada anterior`; `estorno` e conceito tecnico interno.
- Botao de cancelar entrada anterior deve ficar ao lado do botao de continuar conferencia, menor e com estilo vermelho claro.
- Remover mensagens operacionais confusas da tela de duplicidade, como:
  - `Cancelada por tentativa de importacao duplicada da mesma chave de acesso.`
  - `Nota fechada para edicao operacional...`
  - textos longos de historico auditavel quando nao agregarem decisao.
- `Ver movimentacoes da nota` deve virar `Ver itens da nota` quando o objetivo for revisar itens recebidos.
- Em telas de entrada, evitar bloco gigante vazio de lotes quando a nota nao gerou lote.
- Itens recebidos devem aparecer abaixo das acoes principais de duplicidade, em ordem clara.

### Conferencia de entrada
- Tela de conferencia nao deve exigir rolagem horizontal em desktop comum.
- Coluna de lote/validade nao pode ocupar espaco excessivo.
- Edicao de lote/validade deve ser feita por botao que abre sobreposicao, economizando espaco na tabela.
- Deve existir possibilidade de remover item da entrada, com registro auditavel.
- Adicao manual de item ja existe; remocao precisa ser igualmente rastreavel.
- Auditoria de entrada deve ser apresentada de forma explicativa para o operador, nao como bloco tecnico solto.

### UI, mobile e temas
- Tema claro: branco/cinza claro com laranja como destaque.
- Tema escuro: preto/cinza escuro com azul como destaque; evitar laranja/amarelo forte como destaque principal.
- Mensagens amarelas no tema escuro ficaram ruins; usar contrastes mais controlados.
- Alertas realmente criticos devem usar vermelho claro e texto legivel.
- Logos da filial na sidebar devem caber em miniatura, inclusive imagens grandes/horizontais.
- Sidebar deve manter somente `Parametros` na area de sistema, acessivel apenas para admin.
- `Central Administrativa`, `Usuarios` e `Perfis` nao devem aparecer na sidebar padrao.

### Pendencias reais apos esta sessao
- Refinar tela de duplicidade de XML conforme regras acima.
- Finalizar UX da remocao de item da entrada com auditoria clara.
- Melhorar apresentacao da auditoria de entrada para o operador.
- Validar visualmente em producao os fluxos de entrada/conferencia/duplicidade apos os ultimos ajustes.
- Fazer bateria final com XMLs reais variados apenas quando o modulo for encerrar, nao durante cada ajuste.
- Congelar estoque depois do checklist final e mexer somente em bug.

## Handoff - Estoque iniciado em 18/05/2026

### Estado atual
- Estoque e operacional por filial e nao deve ser replicado.
- Tela de saldo lista todos os produtos ativos vinculados a filial, inclusive sem linha em `Estoque`, com saldo zero.
- Movimentacoes manuais, ajustes, transferencias, lotes com entrada inicial e inventario passam por `MovimentacaoService`.
- Reservas e liberacoes de pedidos de venda tambem passam por `MovimentacaoService`, sem gerar baixa fisica antes do faturamento.
- Servicos legados de custo medio e FIFO/FEFO foram centralizados para nao escrever saldo fora do service.
- Alertas de estoque agora exibem vencimento de lote e estoque minimo na mesma tela.
- Alerta de estoque minimo considera produto-filial ativo mesmo sem linha consolidada de estoque, tratando disponibilidade como zero.
- Baixa por validade de lote vencido gera `MovimentacaoEstoque` com tipo `baixa_validade` e baixa todo o saldo atual do lote.
- Saida FEFO usa lotes quando o produto controla lote; quando nao controla, baixa diretamente o saldo consolidado pelo mesmo service.
- Reserva de produto com controle de lote valida lotes ativos e nao vencidos antes de confirmar disponibilidade.
- `python manage.py conferir_estoque` confere divergencias de saldo/disponibilidade/snapshot/lotes sem alterar dados; `--fix-disponivel` corrige apenas o campo derivado `quantidade_disponivel`.
- Produto que controla lote deve sempre movimentar com `lote_id`; devolucao de venda usa os lotes das saidas faturadas para retornar ao estoque.
- Ajuste de saldo pelo cadastro do produto deve ser ignorado para produto com lote; usar tela de lotes/movimentacoes.
- Inventario com `bloquear_movimentacoes=True` bloqueia movimentacao comum e nova reserva; ajuste do proprio inventario continua permitido pelo documento `INVENTARIO`.
- Suite inicial de estoque: `python manage.py test apps.estoque.tests.test_movimentacao_service --settings=config.settings.test`.
- Transferencia entre filiais exige produto ativo/vinculado na origem e no destino; isso evita criar saldo que nao aparece na tela da filial destino.
- Cada transferencia gera saida e entrada com mesmo `documento_numero` no formato `TRF-...`; cada movimento aponta para o outro via `documento_id`.
- Lote com status `ESGOTADO` volta para `ATIVO` quando uma entrada aumenta saldo positivo e o lote nao esta vencido.
- Detalhe do inventario mostra progresso, pendencias, divergencias, sobras e faltas valorizadas antes do fechamento.
- Detalhe do inventario exporta CSV da contagem para conferencia/auditoria.
- Lista/CSV de movimentacoes mostram origem/destino e movimento relacionado em transferencias; a busca tambem aceita ID de movimento/documento e filial destino.
- Suite atual de estoque: `python manage.py test apps.estoque.tests --settings=config.settings.test`.
- Permissoes do estoque ficaram mais granulares:
  - `ver`: abrir listas, detalhes, historico, inventarios, divergencias e reposicao.
  - `criar`: abrir novo lote e novo inventario.
  - `editar`: ajuste manual, movimentacao manual, transferencia e contagem/fechamento de inventario.
  - `cancelar`: cancelar inventario aberto/em contagem e baixar lote vencido por validade.
  - `exportar`: baixar CSV de saldo, movimentacoes, lotes, inventario e divergencias.
- Exportacao CSV de estoque agora e bloqueada no backend quando o perfil nao tem `pode_exportar`, mesmo que o usuario force `?export=csv`.
- Nova tela `Estoque > Reposicao` em `/estoque/reposicao/` lista produtos abaixo do ponto/minimo e transforma sugestao em pedido real.
- A reposicao gera pedidos de compra em rascunho via `CompraService`, agrupando por fornecedor. Produto sem fornecedor fica fora do pedido e recebe aviso.
- Para gerar pedido de reposicao, o usuario precisa de `estoque:editar` e `compras:criar`.
- Nova tela de divergencias de inventario fechado em `/estoque/inventarios/<id>/divergencias/`, com resumo de sobras/faltas/liquido, CSV e atalho para movimentacoes do inventario.
- Telas densas ganharam reforco mobile: tabelas comuns agora tem largura minima e rolagem horizontal estavel; reposicao e divergencias tem cards proprios no mobile.
- Suite de estoque agora cobre services, forms e views: `python manage.py test apps.estoque.tests --settings=config.settings.test` com 18 testes.
- Validacao Railway com dados reais foi concluida em 18/05/2026:
  - projeto `zucchini-renewal`, ambiente `production`, servico `erp-inoovated`;
  - deploy ativo no commit `3519c03`, status `SUCCESS`, 1 replica rodando;
  - dominio `https://inovated.up.railway.app`;
  - `python manage.py check` contra o Postgres publico passou sem erros;
  - logs recentes e HTTP logs nao mostraram 500;
  - login respondeu 200; `/estoque/` e `/estoque/reposicao/` redirecionaram para login com 302 sem 500;
  - renderizacao read-only das telas saldo, reposicao, movimentacoes, lotes e inventarios retornou 200 para as filiais 1 e 2.
- Snapshot de dados reais nessa validacao:
  - 3 filiais ativas;
  - Filial 1 `Polpa do Nordeste - Matriz Natal`: 3 produtos vinculados, 3 saldos, 4 movimentacoes;
  - Filial 2 `Polpa do Nordeste - Mossoro`: 3 produtos vinculados, sem saldos/movimentacoes ainda;
  - Filial 3 `Fiber - SP`: sem produtos vinculados no momento.
- Compras e vendas seguem modulos inacabados; por enquanto, tratar apenas os contratos que ja encostam no estoque:
  - entrada de compra efetivada deve criar lote/saldo/movimentacao via `MovimentacaoService`;
  - venda confirmada deve reservar estoque;
  - venda cancelada deve liberar reserva, inclusive quando ja estiver em separacao;
  - venda faturada deve liberar reserva e baixar saldo real;
  - preco promocional pode definir o preco comercial do item, mas nao pode alterar saldo, lote, reserva nem custo medio.
- Correcao aplicada apos QA Railway: opcoes auxiliares de replicacao de promocoes usavam `Filial.nome`, campo inexistente. Usar sempre `nome_fantasia` ou `razao_social`.
- Suite relacionada estoque/produtos/promocoes/contratos parciais de compras-vendas: `python manage.py test apps.estoque.tests apps.produtos.tests --settings=config.settings.test` com 52 testes.
- Validacao read-only contra Postgres de producao renderizou com status 200 para Filial 1 e Filial 2:
  - saldo;
  - reposicao;
  - movimentacoes;
  - lotes;
  - inventarios;
  - promocoes.
- QA real com rollback no Railway concluido em 19/05/2026:
  - migrations `compras.0002_compat_legacy_required_fields` e `vendas.0002_compat_legacy_required_fields` aplicadas para compatibilidade com colunas obrigatorias legadas do banco real;
  - compras e vendas continuam inacabados; a correcao cobre somente o contrato minimo ja encostado pelo estoque, sem concluir esses modulos;
  - filiais reais usadas: Filial 1 `Polpa do Nordeste - Matriz Natal` e Filial 2 `Polpa do Nordeste - Mossoro`;
  - o QA abriu transacao, criou dados prefixados com `QA ESTOQUE`, executou fluxos reais e forçou rollback no final;
  - fluxos validados: entrada de estoque, venda com preco promocional reservando e baixando estoque, transferencia entre filiais, compra com lote, baixa por validade, fechamento de inventario, geracao de pedido por reposicao, comando `conferir_estoque` e renderizacao de telas de estoque/promocoes;
  - dentro da transacao existiram 5 produtos, 1 fornecedor, 1 cliente, 5 movimentos, 1 pedido de compra e 1 inventario temporarios;
  - apos rollback: produtos=0, fornecedores=0, clientes=0, movimentos=0, pedidos_compra=0, inventarios=0 para o prefixo QA. Nenhum dado temporario ficou persistido.
- Entrada de Mercadoria / Recebimento Fiscal fase 1 iniciada em 19/05/2026:
  - entrada de NF evolui em `apps/compras` sem criar modulo paralelo;
  - origens suportadas na base: manual, XML, chave de acesso e manifesto fiscal;
  - importacao XML guarda XML original, emitente, destinatario, chave, totais e itens;
  - regra do usuario: destinatario da nota pode ser qualquer CPF/CNPJ. Divergencia com CNPJ da filial gera apenas alerta operacional (`destinatario_documento_diferente`), nunca bloqueio;
  - fornecedor desconhecido vindo de XML com documento e razao social e cadastrado automaticamente na filial; `Fornecedor nao cadastrado`/`fornecedor_pendente=True` fica como fallback para XML/chave sem dados suficientes;
  - item da nota pode ficar sem produto interno, mas a finalizacao bloqueia enquanto houver produto sem vinculo;
  - equivalencia por EAN/codigo fornecedor foi preparada em `ProdutoCodigoBarras` e `ProdutoFornecedorEquivalencia`;
  - conferencia de itens sugere produtos internos por similaridade de nome, NCM e unidade quando EAN/equivalencia nao encontram vinculo; sugestao nunca vincula automaticamente;
  - confirmacao em massa da conferencia permite escolher entre sugestoes recalculadas no servidor, editar fator/unidade/lote/validade e ignora qualquer produto que nao faca parte das sugestoes seguras daquele item;
  - item sem vinculo pode cadastrar produto pelo XML, preenchendo nome, EAN, NCM, fornecedor, unidade, custo e equivalencia, mas estoque continua parado ate finalizar a entrada;
  - cadastro rapido pelo XML herda controle de lote/validade quando o item veio com rastro e reaproveita produto ja criado por EAN/equivalencia em NF com multiplos lotes, evitando duplicidade;
  - tela de fornecedor pendente continua disponivel para casos incompletos: permite criar fornecedor real a partir dos dados do XML, vincular fornecedor existente ou continuar pendente; ao resolver, equivalencias pendentes daquele CNPJ XML sao atualizadas;
  - fator de conversao transforma quantidade da nota em quantidade de estoque, e o custo unitario e convertido para a unidade de estoque antes de movimentar;
  - parcelas/faturas do XML entram como pre-lancamento financeiro pendente; conta a pagar so e criada por acao manual depois da entrada efetivada;
  - telas de diferencas e finalizacao recalculam a leitura de lote/validade/quantidade antes de renderizar, para nao mostrar uma entrada como pronta quando flags antigas estiverem desatualizadas;
  - finalizacao continua usando `MovimentacaoService`, preservando a regra de nunca escrever saldo direto;
  - Manifesto Fiscal/DF-e tem base de config, documentos e logs, com tela inicial e consulta SEFAZ por distribuicao DF-e em homologacao quando as travas estiverem habilitadas;
  - documento do Manifesto com `xml_completo` pode virar Entrada de NF pelo botao `Importar entrada`; o fluxo valida se a chave do XML pertence ao manifesto, reaproveita o importador XML, cadastra fornecedor automaticamente quando houver dados do emitente e vincula uma entrada ja existente pela mesma chave sem duplicar;
  - lista do Manifesto ganhou acoes de `Abrir entrada`/`Importar entrada` e versao mobile em cards para evitar overflow da chave de acesso;
  - Manifesto sem XML completo ganhou acao `Anexar XML`, com tela para upload ou XML colado. O XML e salvo somente se a chave interna da NF-e bater com a chave do manifesto; tambem ha acao `Salvar e importar entrada`;
  - consulta DF-e passa por `DFeClient` seguro. O modo padrao `local` nao acessa SEFAZ, nao usa certificado e nao cria documentos falsos; o modo `sefaz` consulta `NFeDistribuicaoDFe` apenas com `FISCAL_DFE_ENABLE_REAL_CONSULTA`, certificado A1 valido e senha em ambiente;
  - manifestacoes fiscais reais continuam bloqueadas. `Dar ciencia`, `desconhecer` e `nao realizada` registram apenas estado local/log no ERP nesta etapa;
  - tela de configuracao DF-e mostra prontidao da integracao: modo, flag de consulta real, certificado A1, senha via `FISCAL_DFE_CERT_PASSWORD` e eventos reais, sem gravar senha no banco nem logar segredo;
  - `SefazDFeClient` bloqueia consulta real em camadas: flag, certificado, senha, validacao offline do A1, bloqueio de producao por padrao e cooldown de `ultimo_nsu == max_nsu` para evitar consumo indevido;
  - testes adicionais cobrem importacao de manifesto para entrada, bloqueio de manifesto sem XML, vinculo com entrada existente e recusa de XML de outra chave;
  - testes do anexo de XML cobrem renderizacao da tela, salvamento local, recusa de chave divergente, botao na lista e salvar+importar para conferencia;
  - testes de seguranca DF-e cobrem consulta local vazia, bloqueio de SEFAZ real por padrao, bloqueio de eventos reais, sync por client fake e preservacao de documento ja importado;
  - QA com `xmls teste.zip`: 12 arquivos lidos, 10 NF-e importaram localmente com rollback, 1 XML era invalido e 1 tinha chave duplicada; apos regra de fornecedor automatico, as 10 NF-e validas criaram 10 fornecedores unicos na transacao e ficaram com `fornecedor_pendente=False`; no Railway/Postgres foram testadas 4 XMLs representativas em 2 filiais reais, com 2 imports por filial, 2 invalidacoes esperadas por filial e `rollback_ok=True`;
  - suite local relacionada: `python manage.py test apps.compras.tests.test_entrada_recebimento apps.estoque.tests apps.produtos.tests --settings=config.settings.test`.

### Riscos permanentes do estoque
- Nunca atualizar `Estoque.quantidade_atual`, `quantidade_disponivel`, lote ou custo medio diretamente fora de service transacional.
- Nunca atualizar `Estoque.quantidade_reservada` diretamente fora de service transacional.
- Todo `lote_id` recebido por movimentacao precisa pertencer ao mesmo produto e filial da operacao.
- Lote vencido/bloqueado nao pode sair por venda normal; a excecao permitida e somente a baixa por validade auditada.
- Nunca permitir saida/entrada manual de produto controlado por lote sem lote identificado.
- Nunca replicar saldo, reserva, lote, inventario ou movimentacao entre filiais.
- Transferencia entre filiais e movimento bilateral auditado, nao replicacao.
- Transferencia nao pode criar estoque para produto sem vinculo ativo na filial destino.
- Produto sem movimento ainda precisa aparecer em saldo e alertas quando estiver vinculado a filial.
- Nao remover campos legados obrigatorios de compras/vendas sem migration planejada; o banco Railway ainda os exige e o estoque depende desses contratos para testar entrada, reserva e baixa.

## Handoff - PDV, promocoes e estoque preparado em 20/05/2026

### Contrato inicial
- O PDV ainda nao esta fechado funcionalmente, mas a venda finalizada ja deve respeitar o caminho correto:
  - buscar produto somente na filial ativa;
  - recalcular preco no backend por `PrecoService`;
  - gravar snapshot de origem do preco no item do PDV;
  - gravar snapshot de custo unitario no item do PDV;
  - baixar estoque pelo `MovimentacaoService`;
  - rastrear os IDs de `MovimentacaoEstoque` gerados no item do PDV.
- O front pode mandar `valor_unitario`, mas venda finalizada nao deve confiar nesse valor como fonte de verdade. O backend recalcula o preco vivo.
- Busca de produtos do PDV e estado inicial agora retornam `preco`, `preco_base`, origem do preco e saldo disponivel para preparar a interface futura.

### Regras para evoluir vendas
- Nao duplicar calculo de promocao dentro do PDV. Usar `PrecoService`.
- Nao baixar saldo direto no PDV. Usar `MovimentacaoService`.
- Promocao de produto e desconto por categoria podem resolver preco automaticamente quando vigentes.
- Combo, kit e brinde ainda precisam de fluxo proprio no PDV:
  - combo baixa o produto vendido normalmente;
  - kit baixa item por item;
  - brinde registra item gratis e baixa o produto entregue;
  - quando houver multiplas opcoes promocionais, o PDV deve mostrar modal e sugerir o menor preco, sem aplicar tudo automaticamente.
- Produto tipo servico nao baixa estoque.
- Venda finalizada sem estoque suficiente deve falhar e fazer rollback da venda inteira.

## Handoff - Entrada XML, conferencia e vinculos de fornecedor - 23/05/2026

### O que foi concluido nesta sessao
- O fluxo de Entrada de Mercadoria por XML foi refinado para ficar mais operacional e menos tecnico.
- A tela de conferencia passou a funcionar como etapa 1 de um fluxo maior:
  1. vinculacao dos itens e divergencias;
  2. custos;
  3. financeiro;
  4. preco de venda, ainda pendente e dependente do mockup do usuario.
- A barra de etapas foi criada para a entrada, seguindo a ideia do cadastro de produto, com navegacao por etapas.
- O botao principal da etapa 1 deve ser `Continuar entrada`, posicionado abaixo da lista, nao no canto superior direito.
- Foram removidos o botao `Reprocessar vinculos` da interface e a tela/bloco `Sugestoes prontas para revisar`.
- O card `Sugeridos` tambem foi removido. Produto nao vinculado deve aparecer como `Sem produto` e ser resolvido direto na busca/cadastro da linha.
- A busca do produto interno na conferencia deve ser o proprio campo de vinculacao; nao deve existir seletor/listagem gigante de produtos.
- A vinculacao pela busca salva automaticamente a equivalencia do produto com o item da nota.
- Foi adicionado botao `+` ao lado da busca para cadastrar produto a partir do XML em sobreposicao.
- A sobreposicao de cadastro de produto nao deve abrir a sidebar como fluxo lateral; ela abre o cadastro real de produto dentro do modal.
- O cadastro de produto aberto a partir da nota deve puxar o maximo de informacoes do XML: nome/descricao do item, codigo do fornecedor, EAN, NCM, unidade, custo e fornecedor quando disponivel.
- O cadastro do produto ganhou area de `Vinculos com fornecedores` dentro da etapa de estoque, para visualizar e remover equivalencias salvas a partir das notas fiscais.
- Remover vinculo de fornecedor desativa a equivalencia sem apagar o historico.
- Ao remover vinculo, itens de entrada ainda abertos que usavam aquela equivalencia sao liberados para nova vinculacao.
- Se o item liberado ainda tiver EAN que bate diretamente com o codigo de barras do produto, a conferencia volta a vincular automaticamente por EAN. Isso e correto: remover equivalencia de fornecedor nao remove o codigo de barras real do produto.
- A abertura da tela de conferencia agora reprocessa automaticamente itens pendentes por EAN/codigo seguro, substituindo o antigo botao manual.
- A conferencia mostra `Qtd Nota`, `Conversao` e `Qtd. final`; conforme a conversao muda, a quantidade final deve refletir o calculo.
- A coluna de unidade isolada foi removida. A unidade da nota fica junto da `Qtd Nota`.
- Quando `unidade_xml` vier vazia, a tela usa fallback de unidade: unidade da nota, depois unidade de estoque, depois unidade cadastrada no produto.
- A coluna `ID Nota` na conferencia deve mostrar o codigo do item na nota/codigo do fornecedor, nao o contador 1, 2, 3 da linha.
- O codigo de barras exibido na conferencia e o EAN que veio na nota fiscal.
- Lote/validade foram compactados: `Lote: <numero>` e `Val: <data>`, sem quebra exagerada.
- Edicao de lote/validade deve ser por icone/botao pequeno de listagem, nao botao grande.
- A conferencia deve usar o maximo de espaco possivel para `Produto interno`.
- Produto interno vinculado deve aparecer em verde, refinado, com check, mas sem card grosseiro.
- A listagem de resultados da busca de produto na conferencia deve seguir o padrao da listagem de produtos, sem barra de rolagem lateral estranha.
- A busca de produto da conferencia deve aceitar ID, nome, codigo/referencia e codigo de barras.
- O bug em que pesquisar por ID `1` nao trazia o produto correto foi tratado no fluxo de busca/ordenacao.
- A remocao de item da entrada foi adicionada com auditoria.
- Item removido aparece riscado/indicado na conferencia e em itens recebidos, sem sumir totalmente da auditoria operacional.
- Item removido pode ser restaurado quando ainda for seguro.
- Restauracao de item removido passou a aceitar decimal localizado e snapshots legados.
- Restauracao de item dividido em lotes foi corrigida para restaurar o item original/grupo quando aplicavel.
- Itens divididos em multiplos lotes foram suportados no fluxo de conferencia.
- A tela de duplicidade/cancelamento foi ajustada para a regra do usuario: nota cancelada/revertida deve permitir nova entrada como uma entrada do zero; a nota antiga fica no historico.
- Para o usuario final, `cancelada` e `estornada/revertida` sao a mesma ideia operacional: a entrada foi desfeita. Criar duas opcoes visiveis causa confusao.
- A mensagem de duplicidade `Esta NF ja foi importada nesta filial` so deve aparecer quando existe entrada ativa/real que ainda precisa ser continuada/cancelada; nao deve bloquear reentrada de nota cancelada.

### Bugs encontrados nesta sessao
- Nota cancelada ainda abria tela de duplicidade e impedia reentrada limpa.
- Tela de conferencia mantinha produto vinculado mesmo depois de remover a equivalencia no cadastro do produto.
- Ao liberar item por equivalencia removida, a conferencia podia nao reprocessar automaticamente o EAN direto do produto.
- A unidade da primeira linha na conferencia nao aparecia quando `unidade_xml` estava vazio.
- Tela de sugestoes criava um fluxo paralelo confuso, exigindo revisao/confirmacao em massa fora da linha.
- Campo de produto interno inicialmente era listagem/seletor, ruim para milhares de produtos.
- Campo de conversao ocupava espaco excessivo para poucos digitos.
- A listagem da conferencia ficou vertical/grossa demais em algumas iteracoes.
- Resultados da busca de produto apareceram com barra lateral/altura ruim.
- Restauracao de item removido falhava em alguns casos por decimal localizado ou snapshot legado.
- Restauracao de divisao de lote podia restaurar uma parte em vez do grupo original.

### Correcoes aplicadas
- `EntradaNFConferenciaView` libera itens que dependiam de equivalencia removida e reprocessa vinculos automaticos ao abrir a tela.
- `reprocessar_vinculos_automaticos` fica como rotina backend, mas nao como botao visivel na etapa 1.
- A tabela da conferencia usa fallback de unidade para evitar quantidade sem unidade.
- A interface de sugestoes em lote foi removida da tela de conferencia.
- Varios ajustes compactaram colunas, headers, acoes, lote/validade, produto interno e conversao.
- `ProdutoFornecedorVinculoDeleteView` passou a desativar equivalencia e liberar itens abertos impactados.
- Cadastro/edicao de produto passou a mostrar vinculos de fornecedor na etapa de estoque, com acao para remover.
- Testes adicionados/atualizados para:
  - remover vinculo sem apagar historico;
  - liberar item aberto apos remover equivalencia;
  - reprocessar EAN automaticamente na abertura da conferencia;
  - restaurar itens removidos, inclusive com decimal localizado e lote dividido.
- Commits relevantes da sessao:
  - `61f5ee7 Organiza fluxo de entrada em etapas`;
  - `8e3e09e Integra cadastro de produto na conferencia`;
  - `0367bcf Permite dividir item de entrada em multiplos lotes`;
  - `f700472 Adiciona remocao de item na conferencia`;
  - `708322f Permite restaurar itens removidos da entrada`;
  - `87e90a7 Adiciona gestao de vinculos de fornecedor no produto`;
  - `e2a27b1 Ajusta remocao de vinculos de fornecedor`;
  - `d37edcc Libera item de entrada apos remover vinculo`;
  - `7558341 Remove revisao de sugestoes da conferencia`;
  - `996c733 Reprocessa EAN ao abrir conferencia`;
  - `631d97b Exibe unidade fallback na conferencia`;
  - `d103ef4 Melhora visual de itens removidos na conferencia`.

### Novas regras descobertas
- O operador nao quer etapa de sugestao separada. Se o produto nao foi encontrado, ele resolve na propria linha por busca ou cadastro.
- EAN real do produto tem prioridade operacional sobre uma equivalencia de fornecedor removida. Se o EAN continua no cadastro do produto, o item pode voltar a vincular automaticamente por EAN.
- Remover equivalencia de fornecedor significa: nao usar mais aquele vinculo fornecedor/codigo/EAN como memoria de compra. Nao significa apagar o EAN do produto.
- Produto pode ficar vinculado a fornecedores diferentes, desde que as equivalencias sejam por fornecedor/CNPJ XML/codigo/EAN e ativas.
- O vinculo de produto com item de nota precisa ser auditavel e removivel pelo cadastro do produto.
- `Divergencia` na etapa 1 deve ficar combinada com os cards/resumo, representando pendencias do item antes de seguir: produto sem vinculo, lote/validade obrigatorio, quantidade/regras pendentes ou diferenca bloqueante.
- Custo critico nao deve aparecer como informacao principal da etapa 1; custo pertence a etapa 2.
- A primeira etapa deve mostrar somente o que impede seguir na vinculacao/conferencia do item.
- Fator de conversao para o usuario deve se chamar apenas `Conversao`.
- Na tela da conferencia, todos os campos curtos devem ceder espaco para `Produto interno`.

### Alteracoes importantes de arquitetura
- Entrada XML passou a ter fluxo mais claro por etapas, em vez de uma tela unica com todos os botoes soltos.
- Vinculos fornecedor-produto deixaram de ser apenas memoria interna e ganharam superficie administrativa no cadastro do produto.
- O cadastro de produto pode ser chamado a partir da conferencia em modal para completar produto criado/vinculado pelo XML.
- O reprocessamento automatico de EAN/equivalencia deixou de depender de botao manual visivel e passou a ser feito ao abrir a conferencia.
- Remocao/restauracao de itens da entrada agora e parte do dominio da entrada, com snapshots/auditoria, nao um simples delete.

### Mudancas de replicacao
- Nenhuma regra de replicacao de estoque foi alterada.
- Saldo, lote, movimento, reserva, inventario, estorno/cancelamento e custo efetivado continuam sem replicacao.
- Equivalencias de fornecedor/produto sao memoria cadastral/operacional da filial e nao podem ser confundidas com replicacao de estoque.
- Produto continua unico com vinculo por filial; nao criar clones de produto por causa de XML de fornecedor.

### Mudancas de produtos
- Cadastro do produto deve permitir revisar vinculos com fornecedores na etapa `Estoque`.
- Produto criado pelo XML deve herdar dados maximos da nota, mas continua precisando de revisao comercial/fiscal antes de venda.
- O EAN vindo da nota pode ser salvo como codigo de barras/equivalencia; isso permite reprocessamento automatico posterior.
- Remover vinculo de fornecedor nao remove codigo de barras principal ou alternativo do produto.
- Produto pode ter multiplas equivalencias de fornecedores diferentes.

### Mudancas mobile
- Mobile da conferencia nao deve ter fluxo separado de sugestoes.
- Cards mobile devem levar para a mesma resolucao da linha: vincular produto, preencher lote ou corrigir divergencia.
- A listagem mobile deve usar a mesma unidade fallback para nao exibir quantidade sem unidade.
- Modais de cadastro de produto e lote/validade precisam continuar responsivos.

### Mudancas de UI/temas
- Conferencia deve seguir listagem compacta, com cabecalho azul no tema claro e padrao escuro equivalente.
- Cards de resumo da conferencia devem ser menores, discretos, menos coloridos e no final/apos a navegacao da etapa quando fizer sentido.
- Produto interno vinculado deve aparecer verde com check, mas refinado e sem ocupar altura excessiva.
- Botoes de tabela devem usar icones/padrao de listagens, nao botoes grandes.
- Campos curtos como conversao, quantidade final e lote devem ser compactos e centralizados.
- Resultado de busca deve parecer listagem, nao dropdown com scroll lateral estranho.
- Nao colocar informacao de custo na etapa de vinculacao; custo fica na etapa propria.

### Possiveis riscos futuros
- Como a tela de sugestoes foi removida do front, ainda existe backend legado de sugestoes em massa. Se nao houver mais uso real, revisar depois para remover rota/view/testes ou manter apenas como compatibilidade interna.
- Reprocessar vinculos ao abrir a conferencia pode relincar por EAN quando o usuario queria remover somente a equivalencia. Isso e correto se o EAN pertence ao produto, mas precisa ficar claro para suporte.
- Se um fornecedor usar EAN generico/incorreto, o EAN direto pode vincular item errado. A origem e criticidade do EAN precisam ser bem observadas.
- Restauracao de itens removidos depende de snapshots antigos; manter compatibilidade com snapshots legados enquanto houver dados reais criados antes das correcoes.
- Divisao por lote e restauracao de grupo sao areas sensiveis para valor total, custo unitario e quantidade; sempre testar com XML real antes de encerrar o modulo.
- Mudancas visuais na conferencia sao sensiveis ao tamanho da tela; validar em desktop comum, notebook e mobile antes de considerar fechado.

### Proximos passos recomendados
- Validar em producao/Railway com uma NF real:
  - importar XML;
  - vincular por EAN;
  - remover equivalencia no cadastro do produto;
  - voltar para conferencia;
  - confirmar se relinca apenas quando o EAN ainda pertence ao produto;
  - testar divisao/remocao/restauracao de lote.
- Fechar o desenho final da etapa 1 de vinculacao/divergencias antes de mexer em custos.
- Implementar etapa 2 de custos com layout proprio, sem poluir a etapa 1.
- Implementar etapa 3 financeiro usando parcelas/pre-lancamentos ja existentes.
- Aguardar mockup do usuario antes de criar a etapa 4 de atualizacao de preco de venda.
- Revisar se a rota/view de sugestoes em massa deve ser removida de vez.
- Melhorar explicacao operacional de `Divergencia` na propria tela, sem texto tecnico excessivo.
- Fazer QA visual nos dois temas e em mobile antes de congelar conferencia.

## Sessao encerrada - compras, conferencia e custos - 2026-05-24

Resumo completo para reutilizacao futura:

- `docs/RESUMO_TECNICO_COMPRAS_CUSTOS_2026-05-24.md`

### Concluido nesta sessao

- Erro 500 em entrada/conferencia de compra foi tratado.
- Insercao manual de item saiu da capa da NF e passou para a conferencia.
- Conferencia passou a exigir produto vinculado antes de seguir para custos; se nao quiser vincular, o operador remove o item.
- Busca de produto na conferencia segue regra global: ID, nome, codigo e barras.
- Item manual usa dados do produto interno, inclusive codigo de barras, e aparece como `Manual`.
- Cadastro de produto aberto pela conferencia aproveita dados do XML, inclusive CFOP quando existir.
- Tela de custos foi simplificada:
  - rateio por valor ou quantidade;
  - opcao `Ignorar custos extras`;
  - composicao de custo compacta;
  - ajustes fiscais avancados recolhidos;
  - um unico botao `Salvar e recalcular custo`;
  - cards de resumo abaixo;
  - listagem densa por item.
- `Unit. agregado` pode ser editado manualmente, sem alterar NF nem financeiro.
- Custo manual fica auditado, marcado com `Manual` e pode ser restaurado por icone.

### Pendencias importantes

- QA visual final em producao, tema claro/escuro e mobile.
- Confirmar na efetivacao que o custo medio usa o `Unit. agregado`, inclusive quando manual.
- Garantir que financeiro consome o total real da NF/parcelas, nao o custo manual de item.
- Decidir futuro motor fiscal de ST/ICMS por NCM, CEST, UF e regime.
- Desenhar a etapa 4 de preco de venda antes de implementar.

## Sessao encerrada - UI, listagens, conferencia e temas - 2026-05-25

Resumo completo para reutilizacao futura:

- `docs/RESUMO_TECNICO_UI_LISTAGENS_2026-05-25.md`

### Concluido nesta sessao

- Listagens no tema escuro foram padronizadas para texto branco e cabecalho escuro/cinza.
- Cores semanticas foram suavizadas e organizadas:
  - despesas/custos extras em vermelho;
  - impostos em amarelo/ambar;
  - desconto/reducao em verde;
  - bases de nota/custo total NF em azul.
- O botao `Voltar` global passou a priorizar a area/listagem-mae do modulo, evitando voltar para etapa anterior indevida do navegador.
- Cadastro de produto passou a exibir `Conversao` e 2 casas decimais em conversao, tributacao, estoque, peso/granel e logistica por padrao.
- Conferencia de entrada foi refinada:
  - campo `Conversao` maior;
  - lote/validade compactos;
  - remocao do texto repetitivo de importacao de rastro;
  - produto interno com mais espaco;
  - codigo de barras duplicado removido do nome do item;
  - possibilidade de adicionar mais de um item manual por vez.
- A conferencia virou o modelo visual aprovado de cabecalho congelado.
- O congelamento foi elevado para regra global de listagens desktop em `templates/_base.html` e `apps/templates/_base.html`.
- A listagem de entrada de mercadoria foi ajustada para participar do padrao global.

### Pendencias importantes

- Confirmar em producao/Railway se o ultimo deploy ja esta servindo os templates novos.
- Fazer varredura futura em listagens que nao sejam tabela HTML real, pois o mecanismo global cobre tabelas dentro de `main`.
- Validar listagens menos usadas: relatorios, fiscais, lotes, producao, logs e modais com tabela.
- Mobile continua exigindo tratamento proprio; nao assumir que cabecalho congelado desktop resolve mobile.
- Manter `templates/_base.html` e `apps/templates/_base.html` sincronizados quando mexer no sticky global.

### Regra operacional nova

- Toda listagem desktop com muitos itens deve congelar o cabecalho no mesmo padrao da conferencia de itens.
- Nao fazer uma listagem por vez quando houver padrao global possivel.
- Se uma tela precisar sair da regra, deve marcar excecao e documentar motivo.
- Antes de encerrar ajuste visual, validar renderizacao em tema claro e escuro.
