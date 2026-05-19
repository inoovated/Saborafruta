"""Serviços fiscais — emissão de NF-e/NFC-e via Focus NFe (esqueleto)."""
import hashlib
import logging
from datetime import datetime, timedelta
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from apps.financeiro.models import (
    DocumentoFiscal, IdempotenciaFiscal, LogIntegracaoFiscal,
)

logger = logging.getLogger("erp.fiscal")


class FiscalService:
    """Camada de emissão fiscal. Wrapper sobre Focus NFe / SEFAZ direto."""

    @staticmethod
    def gerar_chave_idempotencia(origem_tipo, origem_id, filial_id, tipo_doc):
        raw = f"{origem_tipo}:{origem_id}:{filial_id}:{tipo_doc}"
        return hashlib.sha256(raw.encode()).hexdigest()

    @staticmethod
    @transaction.atomic
    def reservar_idempotencia(filial, chave, tipo_doc):
        idemp, created = IdempotenciaFiscal.objects.select_for_update().get_or_create(
            filial=filial, chave=chave,
            defaults={
                "tipo_documento": tipo_doc, "status": "processando",
                "expires_at": timezone.now() + timedelta(hours=24),
            },
        )
        if not created and idemp.status == "sucesso":
            return idemp, False
        return idemp, True

    @staticmethod
    def emitir_nfe(documento_fiscal: DocumentoFiscal):
        """Emissão de NF-e — chamada simplificada ao Focus NFe."""
        # Implementação real: chamar API Focus NFe e processar XML/protocolo.
        # Aqui registramos só um log para demonstrar o fluxo.
        LogIntegracaoFiscal.objects.create(
            filial=documento_fiscal.filial,
            documento_fiscal=documento_fiscal,
            provedor="focusnfe",
            acao="emissao",
            endpoint=f"/v2/nfe?ref={documento_fiscal.id}",
            sucesso=False,
            tempo_resposta_ms=0,
        )
        # TODO: integração real
        return documento_fiscal


def limpar_idempotencia_expirada():
    """Job noturno — remove registros de idempotência expirados."""
    n = IdempotenciaFiscal.objects.filter(expires_at__lt=timezone.now()).delete()
    return n
