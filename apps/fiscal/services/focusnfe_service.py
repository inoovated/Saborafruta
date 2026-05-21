"""
Serviço de integração Focus NFe — Fase 1 (fundação).

Conecta o SDK ``apps.fiscal.integrations.focusnfe`` aos modelos fiscais do ERP.
Responsável por: emitir, consultar e cancelar um ``DocumentoFiscal`` via Focus NFe,
persistir o retorno (chave, protocolo, status, DANFE) e registrar cada chamada
em ``LogIntegracaoFiscal``.

A construção do payload (JSON específico de cada documento) é responsabilidade
da Fase 2 — aqui o ``payload`` já chega pronto em ``emitir()``.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Optional

from django.utils import timezone

from apps.financeiro.constants.enums import StatusDocumentoFiscal
from apps.financeiro.models.fiscal import DocumentoFiscal, LogIntegracaoFiscal
from apps.fiscal.integrations.focusnfe import FocusNFeClient
from apps.fiscal.integrations.focusnfe.config import HOMOLOGACAO, URLS
from apps.fiscal.integrations.focusnfe.exceptions import FocusNFeError

logger = logging.getLogger(__name__)

PROVEDOR = "focusnfe"

# tipo_documento (DocumentoFiscal) -> atributo resource no FocusNFeClient
RESOURCE_POR_TIPO: Dict[str, str] = {
    "nfe": "nfe",
    "nfce": "nfce",
    "nfse": "nfse",
    "nfse_nacional": "nfse_nacional",
    "cte": "cte",
    "cte_os": "cte_os",
    "mdfe": "mdfe",
    "nfcom": "nfcom",
}

# status retornado pela Focus NFe -> StatusDocumentoFiscal do ERP
STATUS_FOCUS_PARA_ERP: Dict[str, str] = {
    "autorizado": StatusDocumentoFiscal.AUTORIZADA,
    "cancelado": StatusDocumentoFiscal.CANCELADA,
    "processando_autorizacao": StatusDocumentoFiscal.PROCESSANDO,
    "erro_autorizacao": StatusDocumentoFiscal.REJEITADA,
    "nao_autorizado": StatusDocumentoFiscal.REJEITADA,
    "denegado": StatusDocumentoFiscal.DENEGADA,
}

# chaves possíveis no JSON de retorno (variam por tipo de documento)
_CHAVE_KEYS = ("chave_nfe", "chave_nfce", "chave_cte", "chave_mdfe", "chave_nfcom", "chave")
_PROTOCOLO_KEYS = ("numero_protocolo", "protocolo")
_PDF_KEYS = ("caminho_danfe", "caminho_dacte", "caminho_damdfe", "caminho_pdf", "url_danfe")
_XML_KEYS = ("caminho_xml_nota_fiscal", "caminho_xml", "caminho_xml_cte", "caminho_xml_mdfe")


def gerar_ref(documento: DocumentoFiscal) -> str:
    """Referência única enviada à Focus NFe. Reconstrói o vínculo no webhook."""
    return f"df-{documento.pk}"


def parse_ref(ref: str) -> Optional[int]:
    """Extrai o pk do DocumentoFiscal a partir da ref ``df-<pk>``."""
    if ref and ref.startswith("df-"):
        try:
            return int(ref[3:])
        except ValueError:
            return None
    return None


class FocusNFeService:
    """Orquestra as operações fiscais via Focus NFe sobre um DocumentoFiscal."""

    def __init__(self, client: Optional[FocusNFeClient] = None) -> None:
        self._client = client

    @property
    def client(self) -> FocusNFeClient:
        """Cliente Focus NFe (token/ambiente lidos das settings)."""
        if self._client is None:
            self._client = FocusNFeClient()
        return self._client

    # ------------------------------------------------------------------ infra
    def _resource(self, tipo_documento: str):
        attr = RESOURCE_POR_TIPO.get((tipo_documento or "").lower())
        if not attr:
            raise ValueError(
                f"Tipo de documento sem resource Focus NFe: '{tipo_documento}'."
            )
        return getattr(self.client, attr)

    def _base_url(self) -> str:
        """URL base da Focus NFe — derivada do ambiente, sem exigir token."""
        if self._client is not None:
            return self._client.config.base_url
        try:
            from django.conf import settings as dj_settings
            ambiente = int(getattr(dj_settings, "ERP_FOCUSNFE_AMBIENTE", HOMOLOGACAO))
        except Exception:
            ambiente = HOMOLOGACAO
        return URLS.get(ambiente, URLS[HOMOLOGACAO])

    def _url_absoluta(self, caminho: str) -> str:
        if not caminho:
            return ""
        if caminho.startswith("http://") or caminho.startswith("https://"):
            return caminho
        base = self._base_url().rstrip("/")
        return f"{base}/{caminho.lstrip('/')}"

    def _registrar_log(
        self,
        documento: DocumentoFiscal,
        acao: str,
        *,
        endpoint: str = "",
        request: Any = None,
        response: Any = None,
        http: Optional[int] = None,
        sucesso: Optional[bool] = None,
        ms: Optional[int] = None,
        status_sefaz: str = "",
    ) -> None:
        """Grava um LogIntegracaoFiscal. Nunca interrompe o fluxo principal."""
        try:
            LogIntegracaoFiscal.objects.create(
                filial=documento.filial,
                documento_fiscal=documento if documento.pk else None,
                provedor=PROVEDOR,
                acao=acao[:30],
                endpoint=endpoint[:200],
                request_json=(
                    json.dumps(request, ensure_ascii=False, default=str)
                    if request is not None else ""
                ),
                response_json=(
                    json.dumps(response, ensure_ascii=False, default=str)
                    if response is not None else ""
                ),
                codigo_http=http,
                codigo_status_sefaz=(status_sefaz or "")[:3],
                sucesso=sucesso,
                tempo_resposta_ms=ms,
                tentativa=documento.tentativas_envio or 1,
            )
        except Exception:  # logging nunca pode quebrar a operação fiscal
            logger.exception("Falha ao registrar LogIntegracaoFiscal")

    # ------------------------------------------------------------- retorno
    def aplicar_retorno(self, documento: DocumentoFiscal, retorno: Dict[str, Any]) -> DocumentoFiscal:
        """
        Atualiza o DocumentoFiscal a partir de um JSON de retorno da Focus NFe.
        Usado tanto após emitir/consultar quanto pelo webhook.
        """
        retorno = retorno or {}

        status_focus = str(retorno.get("status") or "").lower()
        novo_status = STATUS_FOCUS_PARA_ERP.get(status_focus)
        if novo_status:
            documento.status = novo_status

        for k in _CHAVE_KEYS:
            if retorno.get(k):
                documento.chave = str(retorno[k])[:44]
                break

        for k in _PROTOCOLO_KEYS:
            if retorno.get(k):
                documento.protocolo = str(retorno[k])[:20]
                break

        if retorno.get("status_sefaz"):
            documento.codigo_status_sefaz = str(retorno["status_sefaz"])[:3]
        if retorno.get("mensagem_sefaz"):
            documento.mensagem_sefaz = str(retorno["mensagem_sefaz"])

        for k in _PDF_KEYS:
            if retorno.get(k):
                documento.pdf_danfe_url = self._url_absoluta(str(retorno[k]))[:500]
                break

        for k in _XML_KEYS:
            if retorno.get(k):
                documento.xml_retorno = self._url_absoluta(str(retorno[k]))
                break

        agora = timezone.now()
        if documento.status == StatusDocumentoFiscal.AUTORIZADA and not documento.data_autorizacao:
            documento.data_autorizacao = agora
        if documento.status == StatusDocumentoFiscal.CANCELADA and not documento.data_cancelamento:
            documento.data_cancelamento = agora

        documento.save()
        return documento

    # -------------------------------------------------------------- emissão
    def emitir(self, documento: DocumentoFiscal, payload: Dict[str, Any]) -> DocumentoFiscal:
        """
        Envia o documento para autorização na SEFAZ via Focus NFe.

        A autorização é assíncrona: a Focus normalmente responde
        ``processando_autorizacao`` e o status final chega pelo webhook
        (ou via :meth:`consultar`).
        """
        if documento.status == StatusDocumentoFiscal.AUTORIZADA:
            return documento  # já autorizado — idempotente

        resource = self._resource(documento.tipo_documento)
        ref = gerar_ref(documento)
        endpoint = f"/v2/{getattr(resource, 'endpoint', documento.tipo_documento)}"

        documento.tentativas_envio = (documento.tentativas_envio or 0) + 1
        t0 = time.monotonic()
        try:
            retorno = resource.autorizar(ref, payload)
        except FocusNFeError as exc:
            ms = int((time.monotonic() - t0) * 1000)
            self._registrar_log(
                documento, "emitir", endpoint=endpoint, request=payload,
                response=exc.response_json, http=exc.status_code, sucesso=False, ms=ms,
            )
            documento.status = StatusDocumentoFiscal.REJEITADA
            documento.mensagem_sefaz = str(exc)
            documento.save()
            raise

        ms = int((time.monotonic() - t0) * 1000)
        self._registrar_log(
            documento, "emitir", endpoint=endpoint, request=payload,
            response=retorno, sucesso=True, ms=ms,
        )
        # status inicial: processando, salvo se o retorno já trouxer algo definitivo
        if documento.status == StatusDocumentoFiscal.PENDENTE:
            documento.status = StatusDocumentoFiscal.PROCESSANDO
        return self.aplicar_retorno(documento, retorno or {})

    # ------------------------------------------------------------- consulta
    def consultar(self, documento: DocumentoFiscal) -> DocumentoFiscal:
        """Consulta o status atual do documento e atualiza o ERP."""
        resource = self._resource(documento.tipo_documento)
        ref = gerar_ref(documento)
        t0 = time.monotonic()
        try:
            retorno = resource.consultar(ref)
        except FocusNFeError as exc:
            self._registrar_log(
                documento, "consultar", response=exc.response_json,
                http=exc.status_code, sucesso=False,
            )
            raise
        ms = int((time.monotonic() - t0) * 1000)
        self._registrar_log(documento, "consultar", response=retorno, sucesso=True, ms=ms)
        return self.aplicar_retorno(documento, retorno or {})

    # ------------------------------------------------------------ cancelar
    def cancelar(self, documento: DocumentoFiscal, justificativa: str) -> DocumentoFiscal:
        """Cancela um documento autorizado."""
        resource = self._resource(documento.tipo_documento)
        ref = gerar_ref(documento)
        t0 = time.monotonic()
        try:
            retorno = resource.cancelar(ref, justificativa)
        except FocusNFeError as exc:
            self._registrar_log(
                documento, "cancelar", request={"justificativa": justificativa},
                response=exc.response_json, http=exc.status_code, sucesso=False,
            )
            raise
        ms = int((time.monotonic() - t0) * 1000)
        self._registrar_log(
            documento, "cancelar", request={"justificativa": justificativa},
            response=retorno, sucesso=True, ms=ms,
        )
        documento.status = StatusDocumentoFiscal.CANCELADA
        documento.data_cancelamento = timezone.now()
        if isinstance(retorno, dict) and retorno.get("mensagem_sefaz"):
            documento.mensagem_sefaz = str(retorno["mensagem_sefaz"])
        documento.save()
        return documento

    # -------------------------------------------------------------- arquivos
    def baixar_pdf(self, documento: DocumentoFiscal) -> bytes:
        """Baixa o DANFE/DACTE/etc. em PDF (binário)."""
        resource = self._resource(documento.tipo_documento)
        if not hasattr(resource, "baixar_pdf"):
            raise ValueError(f"{documento.tipo_documento} não suporta download de PDF.")
        return resource.baixar_pdf(gerar_ref(documento))

    def baixar_xml(self, documento: DocumentoFiscal) -> bytes:
        """Baixa o XML autorizado (binário)."""
        resource = self._resource(documento.tipo_documento)
        if not hasattr(resource, "baixar_xml"):
            raise ValueError(f"{documento.tipo_documento} não suporta download de XML.")
        return resource.baixar_xml(gerar_ref(documento))
