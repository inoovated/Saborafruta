# Fluxo de custo fiscal em compras

Este documento define uma regra operacional simples para a tela de custos da entrada.
Ele nao substitui o contador, mas ajuda o time a explicar quando IPI, ST e ICMS normal
devem afetar o custo.

## Ideia principal

O usuario comum nao deve precisar entender fiscal para receber mercadoria.

Na tela de custos, deixar visivel por padrao:

- Produtos
- Frete
- Seguro
- Adicionais
- Desconto
- Custo extra da compra
- Metodo de rateio

Deixar recolhido em "Impostos e ajustes fiscais":

- IPI
- ICMS ST
- ICMS normal
- Opcoes de somar cada imposto ao custo

Texto sugerido para o bloco fiscal:

> Use apenas quando a nota trouxer estes valores ou quando o contador orientar. Em entrada manual, deixe zero se nao souber.

## IPI

IPI aparece principalmente em compras de industria, importador ou equiparado a industria.

No XML, o valor total costuma vir em:

- Total da nota: `total/ICMSTot/vIPI`
- Item: grupo `imposto/IPI`

Regra para o sistema:

- Se o XML vier com `vIPI > 0`, importar o valor.
- Padrao recomendado para compras operacionais: deixar "Somar IPI ao custo" ligado, mas permitir desligar.
- Se a empresa recupera credito de IPI, o contador pode orientar a desligar.
- Se a empresa nao recupera IPI, o IPI deve compor o custo.

Como explicar:

"IPI normalmente vem quando compramos de industria. Se a empresa nao aproveita esse imposto como credito, ele aumenta o custo do produto. Se aproveita credito, nao deve entrar no custo."

## ICMS ST

ST depende de regra fiscal por produto, NCM, CEST, estado de origem, estado de destino, regime do fornecedor, regime do comprador e tipo de operacao.
Nao e seguro tentar resolver ST apenas pelo NCM dentro do ERP sem uma tabela fiscal mantida por contador ou motor fiscal.

No XML, o valor total costuma vir em:

- Total da nota: `total/ICMSTot/vST`
- Item: campos como `vBCST` e `vST` em grupos de ICMS com ST

Regra para o sistema:

- Se o XML vier com `vST > 0`, importar o valor.
- Padrao recomendado: "Somar ST ao custo" ligado quando houver valor de ST.
- Se for entrada manual, o usuario so preenche ST se a nota/DANFE ou o contador informar.
- Nao calcular ST automaticamente por NCM nesta fase.

Como explicar:

"ST e imposto retido antecipadamente. Quando a nota traz valor de ST, normalmente ele entra no custo. Se a nota nao trouxe ST, nao invente valor manual."

## ICMS normal

ICMS normal geralmente ja esta embutido no preco do produto e aparece destacado para fins fiscais.
Ele nao aumenta o total da NF-e como IPI/ST podem aumentar.

No XML, o valor total costuma vir em:

- Total da nota: `total/ICMSTot/vICMS`
- Item: grupos de ICMS, como `ICMS00`, `ICMS20`, `ICMS90`

Regra para o sistema:

- Importar `vICMS` para consulta fiscal.
- Padrao recomendado: "Somar ICMS normal ao custo" desligado.
- So ligar quando o contador disser que aquele ICMS nao e recuperavel.

Quando costuma ser recuperavel:

- Empresa no regime normal.
- Compra para revenda ou insumo.
- Saida/venda tributada pelo ICMS.
- Nota com ICMS destacado.

Quando costuma nao ser recuperavel:

- Simples Nacional, na maioria dos casos.
- Compra para uso/consumo ou despesa.
- Compra para consumidor final.
- Operacao sem direito a credito.
- Quando a venda/saida posterior nao gera debito de ICMS.

Como explicar:

"ICMS normal normalmente fica fora do custo porque pode virar credito fiscal. So entra no custo quando o contador disser que a empresa nao consegue recuperar."

## Regra de decisao por regime

### Cliente Simples Nacional

- IPI: normalmente soma ao custo se vier na nota.
- ST: soma ao custo se vier na nota.
- ICMS normal: normalmente nao marcar manualmente sem contador.

### Cliente Regime Normal

- IPI: depende se a empresa e contribuinte/equiparada de IPI e se a compra da direito a credito.
- ST: normalmente soma ao custo se vier na nota.
- ICMS normal: normalmente nao soma ao custo quando for recuperavel.

## Fluxo sugerido na tela

1. Importou XML.
2. Sistema le:
   - produtos
   - frete
   - seguro
   - adicionais
   - desconto
   - IPI
   - ST
   - ICMS normal
3. Tela mostra o bloco simples.
4. Bloco fiscal fica recolhido.
5. Usuario so abre o bloco fiscal se houver valor fiscal ou orientacao do contador.
6. Sistema calcula custo:
   - custo = produtos + frete + seguro + adicionais + custo extra + IPI marcado + ST marcado + ICMS marcado - desconto
7. Rateio divide os acrescimos/descontos entre os itens conforme metodo escolhido.

## XMLs de teste

Arquivos criados para teste manual:

- `docs/xml_teste_fiscal/01_industria_com_ipi.xml`
- `docs/xml_teste_fiscal/02_compra_com_st.xml`
- `docs/xml_teste_fiscal/03_icms_recuperavel_regime_normal.xml`
- `docs/xml_teste_fiscal/04_bonificacao_sem_impostos.xml`

Resultados esperados:

| XML | Produtos | IPI | ST | ICMS | Total NF | Padrao esperado |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| industria com IPI | 1000,00 | 100,00 | 0,00 | 0,00 | 1100,00 | IPI pode somar ao custo |
| compra com ST | 1000,00 | 0,00 | 180,00 | 0,00 | 1180,00 | ST pode somar ao custo |
| ICMS recuperavel | 1000,00 | 0,00 | 0,00 | 180,00 | 1000,00 | ICMS normal fica fora do custo |
| bonificacao sem impostos | 91,15 | 0,00 | 0,00 | 0,00 | 91,15 | Sem imposto no custo |

## Fontes tecnicas

- Portal NF-e: Manual de Orientacao do Contribuinte da NF-e, leiaute dos campos fiscais.
- XML NF-e: grupo `ICMSTot` contem totais como `vProd`, `vFrete`, `vSeg`, `vDesc`, `vOutro`, `vIPI`, `vICMS`, `vST` e `vNF`.

## Decisoes finais da sessao 2026-05-24

### Fluxo operacional

- Etapa 1: vincular produtos, conferir conversao, lote e validade.
- Etapa 2: revisar composicao de custo.
- Etapa 3: financeiro.
- Etapa 4: preco de venda, ainda pendente de desenho.
- Nao permitir seguir para custos com item sem produto vinculado.
- Se o operador nao quiser vincular um item, deve remover o item da entrada.

### Composicao de custo

Campos principais:

- `Valor total produto NF`: soma dos produtos da nota/entrada.
- `Frete`: puxa do XML quando vier.
- `Seguro`: puxa do XML quando vier.
- `Extra`: despesa extra da nota ou custo operacional da compra.
- `Desconto`: puxa da nota quando vier; se o desconto foi por fora, preencher manualmente.
- `%`: percentual equivalente do desconto.

Formula de leitura:

```text
custo_final_nf = valor_total_produto_nf
  + frete
  + seguro
  + extra
  + impostos_marcados_para_custo
  - desconto
```

`Custo extra da compra`, quando existir no controle de rateio, entra no custo agregado dos itens e nao deve alterar o total da NF nem o financeiro.

### Rateio

Opcoes finais:

- `Valor (Rateia o custo adicional de forma proporcional)`;
- `Quantidade (Custo adicional igual para todos os itens)`.

Regra:

- Rateio por valor: item mais caro recebe parcela maior do custo/desconto.
- Rateio por quantidade: cada unidade recebe parcela igual.
- Rateio por peso foi removido ate existir regra confiavel de peso nos produtos/XML.

### Ignorar custos extras

- Quando marcado, a tela guarda/encolhe os campos de custos extras.
- O calculo usa apenas valor dos produtos e desconto da nota.
- Nao somar frete, seguro, extra, IPI, ST, ICMS normal ou custo extra.
- Deve ser escolha explicita do operador.

### Ajustes fiscais avancados

- Ficam recolhidos por padrao.
- Devem ser abertos apenas quando houver imposto na nota, entrada manual ou orientacao fiscal/contador.
- Campos:
  - `Somar IPI ao custo`;
  - `Somar ST ao custo`;
  - `Somar ICMS normal ao custo`;
  - `IPI, se houver`;
  - `ST, se houver`;
  - `ICMS normal, se houver`.

### Custo manual por item

- `Unit. agregado` e o custo final por unidade que alimenta produto/estoque.
- O operador pode editar esse valor manualmente direto na tabela.
- Edicao manual nao altera:
  - valor da NF;
  - frete;
  - seguro;
  - extra;
  - desconto;
  - impostos;
  - financeiro.
- Edicao manual altera apenas o custo efetivo daquele item para custo/historico de produto.
- A linha deve mostrar `Manual` abaixo do custo editado.
- Deve existir botao pequeno de reset por icone para voltar ao custo calculado.
- Toda edicao/remocao de custo manual deve ser auditada.

### Custo medio do produto

O custo unitario agregado da entrada deve alimentar o custo medio pelo calculo ponderado:

```text
custo_medio_novo =
  (estoque_atual * custo_medio_atual + quantidade_entrada * custo_unitario_agregado)
  / (estoque_atual + quantidade_entrada)
```

Se o operador editou manualmente o `Unit. agregado`, o valor manual entra como `custo_unitario_agregado` na formula.
