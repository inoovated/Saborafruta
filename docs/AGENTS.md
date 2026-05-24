# AGENTS.md - Instrucoes Globais do ERP iNoovaTed

## Visao geral
O ERP iNoovaTed e um ERP industrial multiempresa e multifilial.

## Regras criticas
- Replicacao e sempre por filial.
- Mobile-first obrigatorio.
- Suporte obrigatorio aos temas:
  - tema claro: branco/cinza claro com laranja como cor de destaque/acao principal.
  - tema escuro: preto/cinza escuro com azul como cor de destaque/acao principal. Nao usar laranja como destaque principal no tema escuro, salvo excecao ja existente e consciente.
- Logs de cadastro precisam registrar criacao, edicao, ativacao/desativacao e alteracoes de campos com antes/depois.
- Precos e valores monetarios sempre devem aparecer com 2 casas decimais. Mais casas decimais ficam apenas para estoque, granel e medidas tecnicas.
- Nao exibir casas decimais extras em preco, desconto monetario, total, combo, kit ou promocao. Quantidade pode ter casas quando fizer sentido, mas deve ser limpa visualmente.
- Buscas de produto em autocomplete devem aceitar ID, codigo/referencia, codigo de barras e nome, sem duplicar a referencia no resultado visual.
- Em telas de cadastro + listagem, manter o formulario minimizado/acionavel no topo e a listagem abaixo, com espaco visual suficiente entre as areas.
- Layout precisa ser alinhado, bonito e com hierarquia clara. Evitar elementos soltos, desalinhados, cabecalhos vazios, textos em alturas diferentes e botoes com estilo improvisado.
- Calendarios customizados precisam permitir navegar meses, selecionar data, limpar data e salvar valores vazios quando a data for opcional.
- Antes de deploy, revisar riscos de erro 500: templates renderizando, atributos usados no template presentes no contexto, migrations aplicadas/seguras e queries opcionais tolerantes.
- Em telas principais, contexto auxiliar nao pode derrubar a renderizacao. Log, tooltip, opcoes de replicacao e dados agregados devem ter fallback seguro.
- Em promocoes, preco vivo comercial compara preco de venda, preco promocional individual e desconto por categoria/subcategoria, usando o menor preco elegivel quando a flag estiver marcada.
- Combo, kit e brinde so puxam automaticamente promocao externa quando ela esta ativa, dentro da vigencia e cobre pelo menos 5 dias da semana.
- Promocoes por cliente/grupo devem ficar para futuro modulo de CRM/Campanhas, nao dentro da tela de promocoes de produto.

## Stack
- Python
- Django
- PostgreSQL
- Railway
- Tailwind
- Alpine.js

## Fluxo operacional
1. alterar codigo
2. validar localmente
3. commit
4. push
5. Railway deploy
6. validar producao

## Preferencias de comunicacao do usuario
- Quando o usuario autorizar commit/push e disser que nao precisa ser avisado ao terminar, executar o fluxo completo sem pedir nova confirmacao e manter a resposta final minima, apenas com o essencial exigido pelo ambiente.

## Fluxo com atualizacoes paralelas do Thiago
- Antes de qualquer commit/push, buscar a ultima versao do GitHub.
- Comandos recomendados:
  - `git fetch origin main thiago/dashboard`
  - `git rev-list --left-right --count main...origin/main`
  - `git log --oneline --decorate -3 origin/main`
  - `git log --oneline --decorate -3 origin/thiago/dashboard`
- Thiago costuma trabalhar na branch `thiago/dashboard`.
- Se a branch do Thiago estiver baseada em commit antigo, nao fazer merge cego.
- Preferir integracao manual seletiva dos arquivos/funcionalidades novas, preservando estoque, compras, produtos, UI e docs ja consolidados.
- Depois de acoplar:
  - rodar `python manage.py check --settings=config.settings.test`;
  - rodar testes relevantes da area alterada;
  - rodar `git diff --check`;
  - commitar na `main`;
  - fazer push;
  - acompanhar Railway ate `SUCCESS`.
- Ultimo caso conhecido: commit do Thiago `0ce65bc` foi acoplado manualmente no commit `4869c47`, porque merge direto teria descartado mudancas recentes.

## Checklist
- replicacao preservada
- mobile revisado
- temas revisados
- tema claro revisado como branco/laranja
- tema escuro revisado como preto/azul
- alinhamento visual revisado em desktop e mobile
- botoes principais solidos, elegantes e coerentes com o tema
- calendarios testados: abrir, avancar/voltar mes, selecionar, limpar e salvar vazio
- logs de auditoria revisados
- logs Railway revisados quando houver erro em producao
- evitar 500 em producao: `manage.py check`, renderizacao dos templates alterados e `git diff --check`
- se alterar schema, criar migration e validar com `manage.py check`, `sqlmigrate` e `git diff --check`
- apos concluir tarefa de codigo, commitar e fazer push para `main` quando o usuario pedir/autorizar deploy continuo
- em integracoes com Thiago, nunca sobrescrever trabalho local/recente; comparar antes, acoplar com cuidado e documentar o que foi trazido
