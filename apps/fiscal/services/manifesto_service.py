"""Service inicial do Manifesto Fiscal.

As chamadas reais de DF-e dependem de certificado A1 e biblioteca fiscal. Por
enquanto este service centraliza as transicoes visiveis da tela e registra log.
"""
from django.utils import timezone

from apps.core.services.exceptions import DadosInvalidosError
from apps.fiscal.models import ManifestoFiscalDocumento, ManifestoFiscalLog


class ManifestoFiscalService:
    @staticmethod
    def registrar_log(documento=None, config=None, tipo_evento='', mensagem='', codigo_status=''):
        return ManifestoFiscalLog.objects.create(
            documento=documento,
            config=config,
            tipo_evento=tipo_evento,
            mensagem=mensagem,
            codigo_status=codigo_status,
        )

    @classmethod
    def manifestar_ciencia(cls, documento):
        documento.status_manifestacao = ManifestoFiscalDocumento.StatusManifestacao.CIENCIA
        if documento.xml_completo:
            documento.status_download_xml = ManifestoFiscalDocumento.StatusDownload.XML_BAIXADO
        else:
            documento.status_download_xml = ManifestoFiscalDocumento.StatusDownload.XML_DISPONIVEL
        documento.save(update_fields=['status_manifestacao', 'status_download_xml', 'updated_at'])
        cls.registrar_log(
            documento=documento,
            tipo_evento='ciencia_preparada',
            mensagem='Ciencia registrada no ERP. Integracao SEFAZ real ainda pendente.',
            codigo_status='ERP-LOCAL',
        )
        return documento

    @classmethod
    def marcar_desconhecida(cls, documento):
        documento.status_manifestacao = ManifestoFiscalDocumento.StatusManifestacao.DESCONHECIDA
        documento.save(update_fields=['status_manifestacao', 'updated_at'])
        cls.registrar_log(documento=documento, tipo_evento='desconhecimento_preparado')
        return documento

    @classmethod
    def marcar_nao_realizada(cls, documento):
        documento.status_manifestacao = ManifestoFiscalDocumento.StatusManifestacao.NAO_REALIZADA
        documento.save(update_fields=['status_manifestacao', 'updated_at'])
        cls.registrar_log(documento=documento, tipo_evento='operacao_nao_realizada_preparada')
        return documento

    @classmethod
    def vincular_entrada(cls, documento, entrada):
        if documento.filial_id != entrada.filial_id:
            raise DadosInvalidosError('Documento e entrada precisam pertencer a mesma filial.')
        documento.entrada_nf = entrada
        documento.data_importacao = timezone.now()
        documento.status_download_xml = ManifestoFiscalDocumento.StatusDownload.IMPORTADA
        documento.save(update_fields=['entrada_nf', 'data_importacao', 'status_download_xml', 'updated_at'])
        cls.registrar_log(documento=documento, tipo_evento='importada_para_entrada')
        return documento
