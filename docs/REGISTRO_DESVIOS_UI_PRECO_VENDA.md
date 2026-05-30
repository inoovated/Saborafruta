# Registro de desvios de UI: Preço de venda na entrada XML

Data: 2026-05-30

Este registro documenta erros cometidos na construção da tela de atualização de preço de venda da entrada XML. O objetivo é deixar claro o que não atende à expectativa do produto e evitar repetição em próximas telas.

## Desvios cometidos

1. A tela saiu do fluxo natural da entrada.
   - Erro: a primeira versão parecia uma tela paralela ou dashboard, não uma etapa da entrada da nota.
   - Expectativa: quando a origem é XML, a tela precisa continuar visualmente e operacionalmente dentro do fluxo da entrada.

2. O fluxo foi colocado no fim da tela.
   - Erro: o usuário precisava rolar para ver em que etapa estava.
   - Expectativa: o fluxo deve aparecer no topo, na ordem operacional da entrada.

3. Foram criados botões que não deveriam existir.
   - Erro: botões como "Revisar preços agora", "Abrir rotina completa" e "Continuar conferência" competiam com a ação principal.
   - Expectativa: a tela da XML deve permitir atualizar preço diretamente. Ferramentas avançadas podem existir, mas não devem dominar a tela.

4. A tela não permitia edição manual por produto no começo.
   - Erro: o usuário ficava preso a uma regra geral antes de poder ajustar produto a produto.
   - Expectativa: cada item deve permitir ajuste manual de preço de venda, markup e margem, com recálculo entre os campos.

5. A linguagem dos campos ficou confusa.
   - Erro: "Repassar percentual no preço atual" não explicava bem a ação.
   - Expectativa: usar rótulos objetivos, como "Aumentar/reduzir preço atual (%)", e deixar claro quando o campo espera percentual.

6. Indicadores irrelevantes foram exibidos.
   - Erro: mostrar "0 com custo maior" e "0 com custo menor" quando não houve alteração de custo polui a tela.
   - Expectativa: quando não houver alteração, mostrar apenas "Sem alteração de custo".

7. O tema escuro ficou quebrado.
   - Erro: os componentes novos usaram fundo branco fixo sem equivalente para `body:not(.tema-claro)`, causando contraste ruim e aparência fora do padrão.
   - Expectativa: todo componente novo deve nascer com tema claro e escuro definidos, incluindo cards, tabelas, inputs, botões secundários, badges e estados de hover/foco.

## Regra para próximas telas

Antes de concluir qualquer tela operacional:

- Validar claro e escuro.
- Validar a posição do fluxo no topo quando a tela fizer parte de uma jornada.
- Evitar telas com cara de dashboard quando o usuário precisa executar uma ação.
- A ação principal deve acontecer na própria tela, sem obrigar o usuário a abrir uma segunda rotina.
- Não criar botões redundantes.
- Manter rótulos literais e específicos ao tipo de entrada esperada.
- Em tabelas editáveis, campos dependentes devem recalcular imediatamente no navegador e persistir corretamente no backend.
