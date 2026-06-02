# Resumo técnico - Entradas XML, financeiro, PDV e permissões - 2026-05-29

## Escopo da sessão

Esta sessão consolidou três frentes grandes do ERP:

- entrada de XML/NF-e com tipo de entrada, origem e comportamento operacional;
- financeiro da entrada XML, incluindo ajustes, rateio, parcelas, forma de pagamento e permissões;
- PDV, abertura de caixa, sugestão de compras, integração de melhorias vindas do Thiago e refinamento visual dos temas.

Também foram atualizadas regras permanentes de texto em português com acentuação correta e UTF-8.

## O que foi concluído

### Entrada XML e comportamento da entrada

- A importação de XML passou a pedir `Tipo de entrada` e `Origem`.
- Tipos de entrada mapeados para o fluxo:
  - `Compra para revenda`;
  - `Compra para produção`;
  - `Uso e consumo`;
  - `Ativo imobilizado`;
  - `Serviço / despesa`;
  - `Bonificação / amostra`;
  - `Consignação`.
- Origens previstas:
  - `Nacional`;
  - `Importação`.
- Cada tipo sugere três flags operacionais, editáveis pelo usuário:
  - movimenta estoque;
  - movimenta financeiro;
  - altera custo.
- As telas de importação e de continuação da entrada exibem chips clicáveis para essas flags.
- Os chips passaram a explicar claramente o efeito quando estão em `Não`:
  - `Estoque: Não dá entrada no estoque, não exige lote/validade.`
  - `Financeiro: Não gera contas a pagar, plano de contas e centro de custo.`
  - `Alterar Custo: Não recalcula o custo pela nota, custo atual do produto é mantido.`
- Foi reforçada a regra de negócio: devolução de cliente não entra como entrada de compra/XML. Esse caso deve virar fluxo futuro de ajuste/estorno, não recebimento manual de entrada.

### Conferência, custos e comportamento inativo

- Quando `Estoque: Não`, a conferência deixa claro que o XML é apenas leitura operacional e não gerará saldo, lote, validade ou movimento de estoque.
- Informações de estoque e cadastro foram pensadas para ficarem recolhidas atrás de `ver mais` quando o comportamento não movimenta estoque.
- Quando `Alterar custo: Não`, o fluxo deve manter o custo atual do produto e não recalcular pelo valor da nota.
- Quando `Financeiro: Não`, a etapa financeira deve ficar sem obrigação de contas a pagar, plano de contas, centro de custo ou rateio.

### Financeiro da entrada XML

- A tela financeira foi redesenhada para reduzir ruído e concentrar as ações:
  - `Contas a pagar`;
  - `Plano de contas`;
  - `Centros de custo`;
  - `Próxima etapa`.
- Foi removido o card separado de `Geração de contas a pagar`.
- Foram removidas mensagens excessivas como:
  - `Finalize a entrada antes de gerar contas a pagar.`
  - `Cadastre pelo menos um tipo de despesa para classificar esta entrada.`
  - `5 parcela(s) pronta(s) para gerar.`
- O valor financeiro considerado ganhou suporte a acréscimo/desconto por valor e por percentual.
- Regra aprovada: ao preencher valor, o percentual deve ser calculado; ao preencher percentual, o valor deve ser calculado. Exibição com duas casas decimais.
- Classificação e rateio passaram a considerar três níveis de plano de contas de despesas:
  - `Categoria`;
  - `Subcategoria de despesa`;
  - `Tipo de despesa`.
- `Centro de custo` ficou separado do plano de contas. Ele explica quem ou qual área absorve o gasto, enquanto o plano de contas explica o que foi gasto.
- O rateio aceita percentual e valor; um calcula o outro.
- Percentual máximo de rateio: 100%.
- Parcela financeira passou a permitir edição de:
  - vencimento;
  - valor;
  - forma de pagamento;
  - observação.
- `Forma de pagamento` passou a ser combobox baseado nas formas cadastradas no Financeiro, por filial.
- Replicação de forma de pagamento e observação foi separada:
  - ícone de replicação ao lado de `Forma de pagamento`;
  - ícone de replicação ao lado de `Observação`;
  - a ação deve replicar apenas para parcelas existentes abaixo, sem afetar a nova parcela vazia;
  - a primeira linha não pode perder a informação ao replicar.
- Excluir parcela virou ação visual com lixeira vermelha.
- A inclusão de nova parcela deve ficar no fim da lista, com botão compacto `+`.
- A data de vencimento da nova parcela deve usar um controle limpo, sem dropdown quebrado de `Selecionar data`.
- Botão `Salvar parcelas` precisa ficar dentro do card, alinhado e sem quebrar em tema claro ou escuro.

### Plano de contas e centros de custo

- Foram deixadas telas de `Plano de contas` e `Centros de custo` prontas para uso pelo financeiro.
- O nome aprovado para o terceiro nível de despesa é `Tipo de despesa`.
- Foi rejeitado o nome `Natureza`.
- Plano de contas e centro de custo não devem ser amarrados obrigatoriamente. Eles podem ser escolhidos juntos no rateio, mas têm funções diferentes.

### Permissões do financeiro da entrada

- A tela de financeiro da entrada continua sendo visualizada pela permissão de compras.
- Alterar o financeiro da entrada exige:
  - `compras/editar`;
  - `financeiro/criar`.
- Gerar contas a pagar pela entrada exige:
  - `compras/editar`;
  - `financeiro/criar`.
- Links para telas financeiras exigem:
  - `financeiro/ver`.
- Foram adicionados testes para garantir que um usuário sem permissão financeira não consegue postar alterações no financeiro da entrada.

### PDV

- Foi corrigido o bloqueio de abertura de caixa quando a filial não possuía caixa ativo.
- O modal de abertura de caixa deixou de prender o usuário quando `caixasDisponiveis` vem vazio.
- Foi criado endpoint para criar caixa no PDV:
  - `POST /pdv/api/caixa/criar/`.
- O endpoint cria o próximo caixa ativo da filial atual, por exemplo `Caixa 1`, `Caixa 2`.
- O caixa criado retorna selecionado no modal.
- O botão `Abrir Caixa` só fica habilitado com caixa selecionado.
- Mensagem definida para filial sem caixa cadastrado:
  - `Nenhum caixa cadastrado para esta filial. Crie um novo caixa para iniciar as vendas.`
- Formas de pagamento do PDV passaram a vir do Financeiro, por filial.
- Foi criada/ajustada rotina para garantir formas de pagamento padrão por filial quando necessário.
- A opção de replicar forma de pagamento é por filial, não por empresa.
- A tela de `Sugestão de compras` foi reaproveitada da tela existente de reposição.
- A rota usada é `/estoque/reposicao/`.
- O menu desktop e mobile passou a expor `Sugestão de compras`.
- O título da tela passou de `Reposição de estoque` para `Sugestão de compras`.
- Estado vazio definido:
  - `Nenhum produto precisa de compra agora. A sugestão aparece quando o estoque disponível fica abaixo do mínimo ou ponto de reposição.`

### Integração das atualizações do Thiago

- As atualizações do Thiago foram avaliadas e acopladas manualmente, sem merge cego.
- A integração preservou melhorias locais feitas depois da branch dele, principalmente no PDV e no financeiro da entrada.
- A regra de integração continua: comparar antes, acoplar seletivamente e não sobrescrever trabalho recente.

### Produtos e prontidão comercial

- O produto criado a partir do XML continua nascendo como rascunho comercial, não pronto automaticamente para venda/PDV.
- Produto com pendência de custo, venda, cadastro ou vínculo comercial não deve ser liberado automaticamente para PDV.
- A lista de produtos recebeu correção para reduzir o pisca-pisca no primeiro carregamento.
- Textos de produto e entrada foram corrigidos para usar acentuação correta.

### Mobile

- `Sugestão de compras` foi adicionada também no menu mobile.
- Formulários densos do financeiro da entrada devem continuar priorizando layout horizontal no desktop, mas com quebra responsável no mobile.
- Quando o comportamento da entrada estiver inativo, informações secundárias devem poder ficar recolhidas para reduzir excesso visual.
- Parcelas precisam manter leitura em telas menores sem botões cortados.

### UI e temas

- O PDV deve seguir o tema do sistema:
  - tema claro: header laranja do ERP, base clara/branca, texto principalmente preto;
  - tema escuro: header azul do ERP, base escura, azul como ação principal.
- O PDV claro não deve ficar cinza/azulado demais.
- O PDV escuro não deve usar preto absoluto no bloco de totais.
- Botões principais precisam ser sólidos, clicáveis e coerentes com o tema.
- `Novo Cliente` deve usar verde sólido.
- `Trocar Cliente` deve usar azul sólido, mas sem azul exageradamente saturado.
- Ícones no tema claro devem ficar pretos ou com contraste equivalente, não cinza apagado.
- Toast de troca de tema deve usar o padrão do sistema no canto inferior direito, não uma barra verde no rodapé.
- `Mais opções` no PDV deve abrir sobreposição/drawer, inspirado no exemplo do OnePet.
- `Vendas pendentes` deve abrir drawer lateral com busca, filtros, cards de venda, ações de continuar e informar cliente, e resumo no rodapé.
- O ícone de tesoura foi rejeitado para caixa; usar ícone que comunique fechamento/controle de caixa ao lado de `Caixa`.
- O usuário deve aparecer com foto quando houver, não apenas letra inicial.

### Texto, UTF-8 e acentuação

- Regra permanente adicionada: arquivos de texto do projeto devem permanecer em UTF-8.
- Textos visíveis ao usuário devem usar português correto com acentos, cedilha e til.
- Não remover acentos por prevenção técnica.
- Slugs, nomes internos e chaves técnicas podem continuar sem acento quando apropriado.

## Bugs encontrados

- Entrada XML não tinha tipo de entrada nem comportamento operacional, gerando lacuna entre estoque, financeiro e custo.
- Devolução de cliente foi tratada inicialmente como tipo de entrada, mas isso foi corrigido conceitualmente: será ajuste/estorno futuro.
- Chips `Não` não explicavam claramente o impacto operacional.
- Tela de financeiro da entrada estava vertical demais, com mensagens redundantes e ações duplicadas.
- Cálculo de acréscimo/desconto por percentual não era simétrico quando o usuário preenchia primeiro o `%`.
- Rateio aceitava percentual acima de 100%.
- Replicação de forma de pagamento/observação estava atingindo a nova parcela vazia e podia deixar a primeira linha sem informação.
- Datepicker da nova parcela ficava visualmente quebrado como `Selecionar data`.
- Botão de nova parcela ficava cortado, desalinhado ou visualmente fraco.
- Em tema escuro, existiam blocos brancos dentro do financeiro.
- Permissão do financeiro da entrada permitia POST apenas com permissão financeira, sem exigir também `compras/editar`.
- Links financeiros podiam aparecer sem `financeiro/ver`.
- PDV travava abertura de caixa quando a filial não tinha caixa ativo cadastrado.
- `Sugestão de compras` estava difícil de encontrar porque a tela real era a reposição.
- PDV tinha paleta fora do tema do ERP.
- Alguns botões do PDV não estavam clicáveis ou não estavam conectados às formas de pagamento.
- Tela de produtos piscava no F5 por transição no primeiro carregamento.
- Algumas mensagens antigas estavam sem acento.

## Correções aplicadas

- Adicionados tipo, origem e comportamento da entrada no fluxo XML.
- Ajustados textos dos chips de comportamento nas telas de importar XML e continuar entrada.
- Reorganizado o financeiro da entrada com valor financeiro considerado, ajustes, classificação, rateio e parcelas editáveis.
- Adicionados cálculos vinculados entre valor e percentual em ajustes e rateio.
- Adicionada validação de percentual máximo de rateio em 100%.
- Forma de pagamento virou select baseado no cadastro financeiro por filial.
- Separada replicação de forma de pagamento e observação.
- Ajustado o fluxo de nova parcela e botão compacto `+`.
- Criadas/ligadas telas de plano de contas e centro de custo.
- Adicionado endpoint para criar caixa do PDV por filial.
- Corrigido estado vazio do modal de abertura de caixa.
- Reaproveitada tela de reposição como `Sugestão de compras`.
- Refinado tema do PDV, com atenção a header, botões, ícones, painéis laterais e contraste.
- Integradas atualizações do Thiago de forma manual.
- Corrigida a matriz de permissões do financeiro da entrada.
- Corrigidos testes com textos acentuados.

## Alterações importantes de arquitetura

- Entrada de NF ganhou comportamento operacional separado do XML:
  - o XML é origem/documento;
  - o tipo de entrada define padrão de comportamento;
  - as flags finais governam impacto em estoque, financeiro e custo.
- Financeiro da entrada passou a operar como pré-lançamento estruturado:
  - valor financeiro considerado;
  - ajustes;
  - parcelas;
  - classificação contábil/gerencial;
  - centros de custo.
- Plano de contas de despesas e centros de custo passaram a ser cadastros financeiros reutilizáveis.
- Forma de pagamento passou a ser cadastro financeiro por filial consumido também pelo PDV.
- PDV passou a ter criação de caixa operacional por filial via endpoint próprio.
- Sugestão de compras não virou módulo duplicado; ela reaproveita a lógica de reposição.
- Permissões do financeiro da entrada agora combinam módulo de origem (`compras`) com módulo impactado (`financeiro`).

## Mudanças de replicação

- Caixa do PDV é por filial e não replica entre filiais.
- Forma de pagamento é por filial; replicação deve ser explícita e por filial destino, nunca por empresa inteira automaticamente.
- Entrada XML, parcelas, rateio, centro de custo, plano de contas selecionado, custo efetivado e comportamento da entrada são locais da filial.
- Produtos gerados/vinculados por entrada não replicam estoque, lote, financeiro, movimento, custo ou auditoria.
- `Sugestão de compras` calcula necessidade pela filial ativa e não deve misturar estoque de outras filiais sem deixar origem clara.

## O que ficou pendente

- QA visual final do financeiro da entrada em tema claro e escuro, especialmente:
  - botão `+` da nova parcela;
  - alinhamento de `Salvar parcelas`;
  - ausência de bloco branco no tema escuro;
  - comportamento do datepicker da nova parcela.
- QA browser do fluxo completo da entrada XML:
  - importar XML;
  - alterar tipo/origem/comportamento;
  - avançar conferência/custos/financeiro;
  - salvar parcelas;
  - usar rateio;
  - próxima etapa.
- Validar em produção/Railway os endpoints novos do PDV com filial sem caixa.
- Validar permissões em perfis reais, não apenas em testes automatizados.
- Refinar etapa 4 `Preço de venda`.
- Definir se o financeiro da entrada deve bloquear avanço quando o rateio não fecha 100% ou se apenas alerta.
- Evoluir contas a pagar geradas a partir da entrada para gravar snapshot completo de classificação/rateio/forma.
- Testar o menu mobile de `Sugestão de compras` em aparelho real.
- Revisar se o PDV deve aceitar formas de pagamento inativas apenas em vendas antigas ou nunca exibir inativas.

## Possíveis riscos futuros

- Se outro merge do Thiago for aplicado de forma ampla, pode sobrescrever refinamentos recentes do PDV e financeiro.
- Se o front permitir alterar comportamento da entrada depois de etapas avançadas, pode haver inconsistência entre estoque, custo, financeiro e rateio já preenchidos.
- Se rateio parcial for permitido sem bloqueio, contas a pagar podem nascer sem classificação gerencial completa.
- Se forma de pagamento for replicada para filial errada, PDV pode oferecer meio de pagamento que aquela filial não usa.
- Se permissões forem tratadas só por UI, endpoints críticos podem continuar acessíveis por POST manual.
- O datepicker precisa ser testado em navegadores diferentes, porque comportamento nativo varia bastante.
- Tema escuro pode voltar a apresentar blocos claros se novos cards/forms não herdarem tokens.
- O financeiro de entrada XML ainda precisa de regra clara para impostos retidos, frete destacado, desconto comercial e despesas acessórias em cenários de indústria.

## Próximos passos recomendados

1. Fazer QA visual do financeiro da entrada em claro/escuro e corrigir qualquer desalinhamento restante.
2. Testar o fluxo real com uma NF-e de compra para revenda e outra de uso/consumo.
3. Testar uma entrada com `Estoque: Não`, `Financeiro: Sim`, `Alterar custo: Não`.
4. Testar uma bonificação/amostra com `Estoque: Sim`, `Financeiro: Não`, `Alterar custo: Não`.
5. Validar criação de caixa do PDV em filial nova e abrir caixa com o caixa recém-criado.
6. Validar sugestão de compras pelo menu desktop e mobile.
7. Completar a etapa `Preço de venda`.
8. Decidir bloqueio de avanço quando o rateio financeiro não fechar o total.
9. Criar QA end-to-end de permissões para perfis sem `financeiro/criar`.
10. Antes de novo acoplamento do Thiago, comparar branch/commits e trazer apenas o que não conflita com esta base.

## Commits relevantes da sessão

- `840aa332` - Recolhe detalhes quando comportamento está inativo.
- `130f87ca` - Evidencia clique nos chips de comportamento.
- `a440d1c9` - Melhora financeiro da entrada.
- `dffaaa7d` - Documenta regra de acentuação em textos.
- `7e4113f0` - Corrige acentuação dos textos da entrada.
- `29760a76` - Elimina transições no primeiro carregamento.
- `e68085c5` - Integra sugestão de compras e abertura de caixa.
- `dbb9cc1f` - Ajusta PDV e formas de pagamento por filial.
- `2543d299` - Corrige temas do PDV.
- `62361837` - Ajusta layout e temas do PDV.
- `661fcddf` - Replica tema do header no PDV.
- `4b714f0b` - Unifica financeiro e movimentações de estoque.
- `e5f2c283` - Acopla atualizações do Thiago.
- `f922d3b4` - Ajusta financeiro da entrada XML.
- `1eae9bb8` - Ajusta cálculos do financeiro da entrada XML.
- `b98fc0c2` - Corrige interações do financeiro da entrada XML.
- `6038cfe6` - Ajusta ações do financeiro da entrada XML.
- `95a29cda` - Refina botão de adicionar parcela no financeiro XML.
- `f5e77c7b` - Amarra permissões do financeiro de compras.

## Validações executadas no fechamento

- `python manage.py test apps.compras.tests.test_entrada_recebimento --settings=config.settings.test`
  - 121 testes passaram.
- `python manage.py check --settings=config.settings.test`
  - sem erros.
- `python manage.py makemigrations --check --dry-run --settings=config.settings.test`
  - sem migrations pendentes.
- `git diff --check`
  - sem erros bloqueantes; apenas avisos de line ending em alguns arquivos.
