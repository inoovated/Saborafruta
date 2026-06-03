"""
Construtor de payload NFC-e / NF-e para Focus NFe — Fase 2 (PDV).

Constrói o dicionário JSON pronto para envio via FocusNFeService.emitir().

Regra GTIN (SEFAZ NT 2011/004):
  - Produto COM código de barras  → codigo_ean / codigo_ean_tributavel = EAN
  - Produto SEM código de barras  → codigo_ean / codigo_ean_tributavel = "SEM GTIN"
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Optional

from django.db import transaction
from django.utils import timezone

from apps.core.services.exceptions import DadosInvalidosError
from apps.financeiro.models import DocumentoFiscal
from apps.financeiro.constants.enums import TipoDocumentoFiscal, StatusDocumentoFiscal
from apps.pdv.models import VendaPDV


# ---------------------------------------------------------------------------
# Mapeamento: tipo de pagamento PDV (FormaPagamento.tipo) → código FocusNFe
# Referência: Tabela D - Meio de Pagamento (SEFAZ)
# ---------------------------------------------------------------------------
_FORMA_PGTO_FOCO = {
    "dinheiro":       "01",
    "cheque":         "02",
    "cartao_credito": "03",
    "cartao_debito":  "04",
    "vale":           "10",   # vale alimentação/refeição
    "convenio":       "05",   # crédito loja / convênio
    "crediario":      "05",
    "pix":            "17",
    "boleto":         "15",
    "ted":            "16",
    "doc":            "16",
}


def _codigo_ean(produto) -> str:
    """
    Retorna o GTIN do produto ou 'SEM GTIN' quando não cadastrado.
    Exigência SEFAZ — campos cEAN e cEANTrib do XML NF-e.
    """
    ean = (produto.codigo_barras or "").strip()
    # Aceita apenas EAN-8, EAN-13 e DUN-14 (8, 12, 13 ou 14 dígitos numéricos)
    if ean and ean.isdigit() and len(ean) in (8, 12, 13, 14):
        return ean
    return "SEM GTIN"


def _cfop_item(produto, filial) -> str:
    """Resolve CFOP de venda. Prioriza dado do produto; fallback para 5102/5405."""
    filial_uf = (filial.uf or "").upper()
    produto_uf = ""
    # Tenta ler UF da filial do produto (campo direto não existe, usa filial)
    cfop = produto.cfop_venda_interna or ""
    if not cfop:
        # fallback genérico — venda interna de mercadoria
        cfop = "5102"
    return cfop


def _regime_tributario_cod(filial) -> int:
    """
    Retorna o código do regime tributário da filial.
    1=Simples Nacional, 2=SN excesso, 3=Normal/Lucro Real/Presumido
    """
    cod = getattr(filial, "codigo_regime_tributario", None)
    if cod:
        return int(cod)
    empresa_cod = getattr(getattr(filial, "empresa", None), "codigo_regime_tributario", None)
    if empresa_cod:
        return int(empresa_cod)
    return 1  # default: Simples Nacional


def _cst_icms_efetivo(produto, filial) -> str:
    """CST ICMS/CSOSN efetivo para o item."""
    # Se tem cst_csosn no produto, usa ele
    cst = (produto.cst_csosn or "").strip()
    if cst:
        return cst
    regime = _regime_tributario_cod(filial)
    if regime == 1:
        return "102"   # SN - tributado sem permissão de crédito (venda)
    return "00"        # Normal tributado integralmente


def _montar_icms_sn(produto, filial, valor_total: Decimal) -> dict:
    """ICMS Simples Nacional (CSOSN 102/400/etc.)."""
    csosn = _cst_icms_efetivo(produto, filial)
    return {
        "csosn_icms": csosn,
        "origem_mercadoria": str(int(getattr(produto, "origem_produto", 0))),
    }


def _montar_icms_normal(produto, filial, valor_total: Decimal) -> dict:
    """ICMS regime normal."""
    cst = _cst_icms_efetivo(produto, filial)
    return {
        "cst_icms": cst,
        "origem_mercadoria": str(int(getattr(produto, "origem_produto", 0))),
        "modalidade_determinacao_bc_icms": "3",   # valor da operação
        "valor_base_calculo_icms": float(valor_total),
        "aliquota_icms": float(getattr(produto, "aliquota_icms", 0) or 0),
        "valor_icms": 0.00,
    }


def _montar_pis(produto, valor_total: Decimal) -> dict:
    cst_pis = (getattr(produto, "cst_pis", "") or "07").strip() or "07"
    return {
        "cst_pis": cst_pis,
        "valor_base_calculo_pis": 0.00,
        "aliquota_pis_percentual": 0.00,
        "valor_pis": 0.00,
    }


def _montar_cofins(produto, valor_total: Decimal) -> dict:
    cst_cofins = (getattr(produto, "cst_cofins", "") or "07").strip() or "07"
    return {
        "cst_cofins": cst_cofins,
        "valor_base_calculo_cofins": 0.00,
        "aliquota_cofins_percentual": 0.00,
        "valor_cofins": 0.00,
    }


def _montar_item(numero: int, item_venda, filial) -> dict:
    """Monta o dicionário de um item no payload FocusNFe."""
    produto = item_venda.produto
    quantidade = float(item_venda.quantidade)
    valor_unitario = float(item_venda.valor_unitario)
    valor_bruto = float(item_venda.quantidade * item_venda.valor_unitario)
    valor_total = item_venda.valor_total
    unidade = item_venda.unidade_medida or (
        produto.unidade_medida.sigla if produto.unidade_medida_id else "UN"
    )
    descricao = (produto.descricao_pdv or produto.descricao or "")[:120]
    ncm = (produto.ncm or "").replace(".", "").strip()
    cfop = _cfop_item(produto, filial)
    ean = _codigo_ean(produto)  # ← "SEM GTIN" quando sem código de barras

    regime = _regime_tributario_cod(filial)
    if regime == 1:
        icms_bloco = _montar_icms_sn(produto, filial, valor_total)
    else:
        icms_bloco = _montar_icms_normal(produto, filial, valor_total)

    item: Dict[str, Any] = {
        "numero_item": numero,
        "codigo_produto": produto.codigo or str(produto.pk),
        "descricao": descricao,
        "codigo_ncm": ncm,
        "cfop": cfop,
        "unidade_comercial": unidade,
        "quantidade_comercial": quantidade,
        "valor_unitario_comercial": valor_unitario,
        "valor_bruto": valor_bruto,
        "valor_total": float(valor_total),
        # ─── GTIN (cEAN / cEANTrib) ───────────────────────────────────────
        "codigo_ean": ean,
        "codigo_ean_tributavel": ean,
        # ──────────────────────────────────────────────────────────────────
        "unidade_tributavel": unidade,
        "quantidade_tributavel": quantidade,
        "valor_unitario_tributavel": valor_unitario,
        "inclui_no_total": "1",
        "icms": icms_bloco,
        "pis": _montar_pis(produto, valor_total),
        "cofins": _montar_cofins(produto, valor_total),
    }

    # CEST — campo opcional
    cest = (getattr(produto, "cest", "") or "").strip()
    if cest:
        item["codigo_cest"] = cest

    return item


def _montar_pagamentos(pagamentos_qs) -> list:
    """Converte os pagamentos da venda no formato FocusNFe."""
    pgtos = []
    for pgto in pagamentos_qs:
        # FormaPagamento.tipo usa os values de TipoFormaPagamento (ex: "dinheiro", "pix")
        tipo = (pgto.forma_pagamento.tipo or "").lower().strip()
        codigo = _FORMA_PGTO_FOCO.get(tipo, "99")
        pgtos.append({
            "forma_pagamento": codigo,
            "valor_pagamento": float(pgto.valor),
        })
    return pgtos or [{"forma_pagamento": "99", "valor_pagamento": 0.00}]


def _montar_emitente(filial) -> dict:
    return {
        "cnpj": filial.cnpj,
        "nome": filial.razao_social,
        "nome_fantasia": filial.nome_fantasia or filial.razao_social,
        "logradouro": filial.endereco or "",
        "numero": filial.numero or "S/N",
        "complemento": filial.complemento or "",
        "bairro": filial.bairro or "",
        "municipio": filial.cidade or "",
        "uf": filial.uf or "",
        "cep": filial.cep or "",
        "codigo_pais": "1058",
        "pais": "Brasil",
        "telefone": (filial.telefone or "").replace(" ", "").replace("-", "").replace("(", "").replace(")", ""),
        "ie": filial.inscricao_estadual or "",
        "regime_tributario": str(_regime_tributario_cod(filial)),
    }


def _montar_destinatario(cliente) -> Optional[dict]:
    """Destinatário. Retorna None para Consumidor Final sem identificação."""
    if not cliente:
        return None
    cpf_cnpj = (cliente.cpf_cnpj or "").replace(".", "").replace("-", "").replace("/", "").strip()
    if not cpf_cnpj:
        return None
    dest: Dict[str, Any] = {
        "nome": cliente.razao_social or "Consumidor Final",
        "email": cliente.email or "",
        "telefone": (cliente.celular or cliente.telefone or "").replace(" ", "").replace("-", "").replace("(", "").replace(")", ""),
    }
    if len(cpf_cnpj) == 11:
        dest["cpf"] = cpf_cnpj
    elif len(cpf_cnpj) == 14:
        dest["cnpj"] = cpf_cnpj
    return dest


class NfcePayloadBuilder:
    """
    Constrói o payload JSON de NFC-e (Nota Fiscal de Consumidor Eletrônica)
    para envio via Focus NFe a partir de uma VendaPDV finalizada.
    """

    @classmethod
    def build(cls, venda: VendaPDV) -> Dict[str, Any]:
        """
        Retorna o dicionário pronto para FocusNFeService.emitir().

        Produtos SEM codigo_barras → codigo_ean = "SEM GTIN" (exigência SEFAZ).
        """
        filial = venda.filial
        cliente = venda.cliente

        itens_qs = list(
            venda.itens.select_related("produto__unidade_medida").order_by("numero_item")
        )
        pagamentos_qs = list(
            venda.pagamentos.select_related("forma_pagamento").order_by("id")
        )

        if not itens_qs:
            raise DadosInvalidosError("Venda sem itens — não é possível emitir NFC-e.")

        data_emissao = (venda.data_venda or timezone.now()).strftime("%Y-%m-%dT%H:%M:%S-03:00")

        items = [
            _montar_item(idx + 1, item, filial)
            for idx, item in enumerate(itens_qs)
        ]

        payload: Dict[str, Any] = {
            "natureza_operacao": "Venda ao Consumidor",
            "forma_pagamento": 0,          # 0=à vista
            "numero": venda.numero_venda,
            "serie": str(filial.serie_nfce or 1),
            "data_emissao": data_emissao,
            "data_entrada_saida": data_emissao,
            "tipo_documento": 1,           # 1=saída
            "finalidade_emissao": 1,       # 1=NF-e normal
            "consumidor_final": 1,
            "presenca_comprador": 1,       # 1=operação presencial
            "emitente": _montar_emitente(filial),
            "items": items,
            "pagamentos": _montar_pagamentos(pagamentos_qs),
            "valor_produtos": float(venda.valor_subtotal or 0),
            "valor_desconto": float(venda.valor_desconto or 0),
            "valor_total": float(venda.valor_total),
            "modalidade_frete": 9,         # 9=sem frete
        }

        destinatario = _montar_destinatario(cliente)
        if destinatario:
            payload["destinatario"] = destinatario

        return payload


class NfePayloadBuilder:
    """
    Constrói o payload JSON de NF-e (Nota Fiscal Eletrônica)
    para envio via Focus NFe a partir de uma VendaPDV finalizada.

    Produtos SEM codigo_barras → codigo_ean = "SEM GTIN" (exigência SEFAZ).
    """

    @classmethod
    def build(cls, venda: VendaPDV, numero_nfe: int, serie_nfe: int = 1) -> Dict[str, Any]:
        filial = venda.filial
        cliente = venda.cliente

        itens_qs = list(
            venda.itens.select_related("produto__unidade_medida").order_by("numero_item")
        )
        pagamentos_qs = list(
            venda.pagamentos.select_related("forma_pagamento").order_by("id")
        )

        if not itens_qs:
            raise DadosInvalidosError("Venda sem itens — não é possível emitir NF-e.")

        data_emissao = (venda.data_venda or timezone.now()).strftime("%Y-%m-%dT%H:%M:%S-03:00")

        items = [
            _montar_item(idx + 1, item, filial)
            for idx, item in enumerate(itens_qs)
        ]

        payload: Dict[str, Any] = {
            "natureza_operacao": "Venda de mercadorias",
            "forma_pagamento": 0,
            "numero": numero_nfe,
            "serie": str(serie_nfe),
            "data_emissao": data_emissao,
            "data_entrada_saida": data_emissao,
            "tipo_documento": 1,
            "finalidade_emissao": 1,
            "consumidor_final": 1,
            "presenca_comprador": 1,
            "emitente": _montar_emitente(filial),
            "items": items,
            "pagamentos": _montar_pagamentos(pagamentos_qs),
            "valor_produtos": float(venda.valor_subtotal or 0),
            "valor_desconto": float(venda.valor_desconto or 0),
            "valor_total": float(venda.valor_total),
            "modalidade_frete": 9,
        }

        destinatario = _montar_destinatario(cliente)
        if destinatario:
            payload["destinatario"] = destinatario

        return payload


@transaction.atomic
def emitir_nfce_para_venda(venda: VendaPDV, usuario) -> DocumentoFiscal:
    """
    Wrapper de alto nível: constrói payload NFC-e, cria DocumentoFiscal e dispara emissão.
    Retorna o DocumentoFiscal criado/atualizado.
    """
    from apps.fiscal.services.focusnfe_service import FocusNFeService

    filial = venda.filial

    # Verifica se já existe documento fiscal para esta venda
    existente = DocumentoFiscal.objects.filter(
        origem_tipo="venda_pdv",
        origem_id=venda.pk,
        tipo_documento="nfce",
    ).exclude(status=StatusDocumentoFiscal.CANCELADA).first()
    if existente and existente.status == StatusDocumentoFiscal.AUTORIZADA:
        return existente

    payload = NfcePayloadBuilder.build(venda)

    doc = DocumentoFiscal.objects.create(
        filial=filial,
        tipo_documento="nfce",
        origem_tipo="venda_pdv",
        origem_id=venda.pk,
        numero=venda.numero_venda,
        serie=filial.serie_nfce or 1,
        emitente_cnpj=filial.cnpj,
        destinatario_tipo="cliente" if venda.cliente_id else "consumidor",
        destinatario_id=venda.cliente_id,
        destinatario_snapshot=(
            {
                "nome": venda.cliente.razao_social,
                "cpf_cnpj": venda.cliente.cpf_cnpj or "",
            }
            if venda.cliente else {"nome": "Consumidor Final"}
        ),
        valor_produtos=venda.valor_subtotal or 0,
        valor_desconto=venda.valor_desconto or 0,
        valor_total=venda.valor_total,
        status=StatusDocumentoFiscal.PENDENTE,
        data_emissao=venda.data_venda or timezone.now(),
        usuario=usuario,
    )

    service = FocusNFeService()
    return service.emitir(doc, payload)
