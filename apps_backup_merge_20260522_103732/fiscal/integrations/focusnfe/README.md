# Integração Focus NFe

Cliente Python para a API da Focus NFe (https://focusnfe.com.br/doc/), cobrindo **15 famílias de endpoints**: NFe, NFCe, NFSe (3 variantes + recebidas), CTe, CTe OS, NFCOM, MDFe, NFe recebidas, CTe recebidas, e as consultas NCM / CFOP / CNAE / CNPJ.

## Estrutura

```
apps/fiscal/integrations/focusnfe/
├── __init__.py            # exports principais
├── client.py              # FocusNFeClient (facade)
├── config.py              # FocusNFeConfig + leitura de env/settings
├── exceptions.py          # hierarquia de erros tipados
├── _base.py               # BaseAPIClient (HTTP, auth, retry, parsing)
├── README.md              # este arquivo
└── resources/
    ├── _authorized_doc.py # mixin p/ NFe, NFCe, CTe, CTeOS, NFCOM, MDFe
    ├── nfe.py
    ├── nfce.py
    ├── nfse.py
    ├── nfse_nacional.py
    ├── nfse_arquivo.py
    ├── nfse_recebidas.py
    ├── cte.py
    ├── cte_os.py
    ├── nfcom.py
    ├── mdfe.py
    ├── nfe_recebidas.py
    ├── cte_recebidas.py
    └── consultas.py       # NCM, CFOP, CNAE, CNPJ
```

## Configuração

Defina as variáveis de ambiente (já lidas em `config/settings/base.py`):

```bash
FOCUSNFE_TOKEN=seu_token_aqui
FOCUSNFE_AMBIENTE=2          # 1 = produção, 2 = homologação
```

Ou instancie manualmente:

```python
from apps.fiscal.integrations.focusnfe import FocusNFeClient, FocusNFeConfig, PRODUCAO

cfg = FocusNFeConfig(token="abc...", ambiente=PRODUCAO)
client = FocusNFeClient(config=cfg)
```

## Uso rápido

```python
from apps.fiscal.integrations.focusnfe import FocusNFeClient

client = FocusNFeClient()  # lê do settings/env
```

### NFe

```python
# Emitir
client.nfe.autorizar(ref="PED-001", payload={
    "natureza_operacao": "Venda",
    "data_emissao": "2025-04-29",
    "cnpj_emitente": "...",
    # ... demais campos da NFe
})

# Consultar
client.nfe.consultar("PED-001", completa=True)

# Cancelar
client.nfe.cancelar("PED-001", justificativa="Erro nos dados do destinatário")

# Inutilizar faixa de numeração
client.nfe.inutilizar(
    cnpj="...", serie=1,
    numero_inicial=100, numero_final=110,
    justificativa="Quebra de sequência por erro de sistema",
)

# Carta de correção
client.nfe.carta_correcao("PED-001", correcao="Correção do endereço do destinatário")

# Baixar XML / DANFE
xml = client.nfe.baixar_xml("PED-001")        # bytes
pdf = client.nfe.baixar_pdf("PED-001")        # bytes (DANFE)

# Reenviar por e-mail
client.nfe.enviar_email("PED-001", emails=["cliente@empresa.com"])

# Duplicatas (boletos vinculados à NFe)
client.nfe.duplicatas("PED-001")
```

### NFCe

API equivalente à NFe, mas sem carta de correção:

```python
client.nfce.autorizar("CUPOM-1", payload)
client.nfce.consultar("CUPOM-1")
client.nfce.cancelar("CUPOM-1", justificativa="Erro de digitação no item")
client.nfce.baixar_pdf("CUPOM-1")             # DANFE NFCe
```

### NFSe — 4 variantes

```python
# 1) NFSe municipal (cada prefeitura tem seu webservice)
client.nfse.autorizar("OS-100", payload)
client.nfse.consultar("OS-100")
client.nfse.cancelar("OS-100", justificativa="...")
client.nfse.baixar_pdf("OS-100")

# 2) NFSe Nacional (padrão Receita Federal)
client.nfse_nacional.autorizar("OS-100", payload)
client.nfse_nacional.consultar("OS-100")

# 3) NFSe por arquivo (envio de XML pronto)
with open("rps.xml", "rb") as f:
    client.nfse_arquivo.enviar(
        ref="OS-101",
        cnpj_emitente="00000000000191",
        xml=f.read(),
    )

# 4) NFSes recebidas (CNPJ tomador)
client.nfse_recebidas.listar(
    cnpj="00000000000191",
    data_emissao_inicial="2025-04-01",
    data_emissao_final="2025-04-30",
)
client.nfse_recebidas.consultar("identificador-da-nfse")
```

### CTe e CTe OS

```python
client.cte.autorizar("CTE-001", payload)
client.cte.consultar("CTE-001")
client.cte.cancelar("CTE-001", justificativa="...")
client.cte.carta_correcao("CTE-001", correcao="...")
client.cte.baixar_dacte("CTE-001")            # PDF do DACTE

# CTe OS (modelo 67)
client.cte_os.autorizar("CTEOS-1", payload)
```

### NFCOM (Nota Fiscal de Comunicação — modelo 62)

```python
client.nfcom.autorizar("COM-1", payload)
client.nfcom.consultar("COM-1")
client.nfcom.cancelar("COM-1", justificativa="...")
```

### MDFe (Manifesto)

```python
client.mdfe.autorizar("MDFE-001", payload)
client.mdfe.encerrar(
    "MDFE-001",
    codigo_municipio="3550308",
    uf="SP",
)
client.mdfe.incluir_condutor("MDFE-001", nome="João Silva", cpf="12345678901")
client.mdfe.baixar_damdfe("MDFE-001")
```

### NFe / CTe recebidas

```python
from apps.fiscal.integrations.focusnfe.resources.nfe_recebidas import (
    MANIFESTO_CIENCIA, MANIFESTO_CONFIRMACAO,
    MANIFESTO_DESCONHECIMENTO, MANIFESTO_OPERACAO_NAO_REALIZADA,
)

# Listar NFes recebidas (use 'nsu' para incremental)
client.nfe_recebidas.listar(cnpj="00000000000191", nsu=0)

# Consultar uma NFe pela chave de 44 dígitos
client.nfe_recebidas.consultar("35200600000000000000000000000000000000000000")

# Baixar XML
client.nfe_recebidas.baixar_xml("35200...")

# Manifestar
client.nfe_recebidas.manifestar(
    chave_nfe="35200...",
    tipo=MANIFESTO_CONFIRMACAO,
    justificativa="Mercadoria recebida conforme pedido",
)

# CTes recebidos (mesma lógica, sem manifestação)
client.cte_recebidas.listar(cnpj="00000000000191")
client.cte_recebidas.consultar("CHAVE_CTE_44_DIGITOS")
```

### Consultas auxiliares

```python
# NCM
client.consultas.ncm.consultar("33049910")
client.consultas.ncm.listar(descricao="medicamento", pagina=1)

# CFOP
client.consultas.cfop.consultar("5102")

# CNAE
client.consultas.cnae.consultar("4711301")

# CNPJ (dados cadastrais)
client.consultas.cnpj.consultar("00.000.000/0001-91")  # aceita pontuação

# Equivalentes via atributo direto (sem o namespace 'consultas'):
client.ncms.consultar("33049910")
client.cfops.consultar("5102")
client.cnaes.consultar("4711301")
client.cnpjs.consultar("00000000000191")
```

## Tratamento de erros

Hierarquia tipada — capture o nível de granularidade que precisar:

```python
from apps.fiscal.integrations.focusnfe import (
    FocusNFeError,                # base de tudo
    FocusNFeAuthError,            # 401, 403
    FocusNFeValidationError,      # 400
    FocusNFeNotFoundError,        # 404
    FocusNFeProcessingError,      # 422 (rejeição da SEFAZ)
    FocusNFeRateLimitError,       # 429
    FocusNFeServerError,          # 5xx
    FocusNFeNetworkError,         # timeout / DNS / conexão
)

try:
    client.nfe.autorizar("PED-1", payload)
except FocusNFeProcessingError as e:
    # SEFAZ rejeitou — e.response_json tem detalhes do motivo
    print("Status:", e.status_code)
    print("JSON:", e.response_json)
except FocusNFeValidationError as e:
    # Payload incompleto/inválido
    ...
except FocusNFeAuthError:
    # Token inválido/inativo
    ...
except FocusNFeError as e:
    # Qualquer outro erro da integração
    ...
```

Cada exceção carrega `status_code`, `response_json` e `response_text` para diagnóstico fino.

## Atalho a partir do app vendas

```python
from apps.vendas.integrations.focusnfe import FocusNFeClient
```

Re-exporta exatamente o mesmo cliente — útil para emissão de NFe a partir de pedidos de venda.

## Detalhes técnicos

- **Auth**: HTTP Basic (token como username, senha vazia) — convenção da Focus NFe.
- **Retry**: 2 tentativas em 5xx e timeouts (configurável via `FocusNFeConfig.max_retries`).
- **Timeout**: 60s default (configurável).
- **Logs**: integração usa `logging.getLogger("apps.fiscal.integrations.focusnfe._base")` — adicione no `LOGGING` do Django para auditoria.
- **Sem dependências extras**: usa `requests` (já no requirements.txt).
