"""Service inicial do Manifesto Fiscal.

As chamadas reais de DF-e dependem de certificado A1 e biblioteca fiscal. Por
enquanto este service centraliza as transicoes visiveis da tela e registra log.
"""
from dataclasses import dataclass

from django.utils import timezone

from apps.compras.models import EntradaNF
from apps.compras.services.entrada_xml_service import (
    extrair_chave_xml, importar_xml_para_entrada, normalizar_chave,
)
from apps.core.services.exceptions import DadosInvalidosError
from apps.fiscal.integrations.dfe_client import get_dfe_client
from apps.fiscal.models import ManifestoFiscalConfig, ManifestoFiscalDocumento, ManifestoFiscalLog


@dataclass(frozen=True)
class ResultadoImportacaoManifesto:
    entrada: EntradaNF
    criada: bool


@dataclass(frozen=True)
class ResultadoSincronizacaoManifesto:
    total_documentos: int
    criados: int
    atualizados: int
    modo: str
    mensagem: str = ''


class ManifestoFiscalService:
    @staticmethod
    def registrar_log(
        documento=None,
        config=None,
        tipo_evento='',
        mensagem='',
        codigo_status='',
        requisicao_resumo=None,
        retorno_resumo=None,
    ):
        return ManifestoFiscalLog.objects.create(
            documento=documento,
            config=config,
            tipo_evento=tipo_evento,
            mensagem=mensagem,
            codigo_status=codigo_status,
            requisicao_resumo=requisicao_resumo or {},
            retorno_resumo=retorno_resumo or {},
        )

    @staticmethod
    def _status_download_atual(documento, resumo):
        if documento.entrada_nf_id or documento.status_download_xml == ManifestoFiscalDocumento.StatusDownload.IMPORTADA:
            return ManifestoFiscalDocumento.StatusDownload.IMPORTADA
        if resumo.xml_completo:
            return ManifestoFiscalDocumento.StatusDownload.XML_BAIXADO
        if resumo.xml_resumo:
            return ManifestoFiscalDocumento.StatusDownload.RESUMO
        return documento.status_download_xml or ManifestoFiscalDocumento.StatusDownload.RESUMO

    @classmethod
    def _salvar_resumo_documento(cls, filial, resumo):
        chave = normalizar_chave(resumo.chave_acesso)
        if len(chave) != 44:
            raise DadosInvalidosError('Documento DF-e ignorado: chave de acesso invalida.')

        documento, criado = ManifestoFiscalDocumento.objects.get_or_create(
            filial=filial,
            chave_acesso=chave,
            defaults={
                'status_download_xml': (
                    ManifestoFiscalDocumento.StatusDownload.XML_BAIXADO
                    if resumo.xml_completo
                    else ManifestoFiscalDocumento.StatusDownload.RESUMO
                ),
            },
        )
        documento.nsu = resumo.nsu or documento.nsu
        documento.cnpj_emitente = resumo.cnpj_emitente or documento.cnpj_emitente
        documento.razao_social_emitente = resumo.razao_social_emitente or documento.razao_social_emitente
        documento.data_emissao = resumo.data_emissao or documento.data_emissao
        documento.valor_total = resumo.valor_total or documento.valor_total
        documento.xml_resumo = resumo.xml_resumo or documento.xml_resumo
        documento.xml_completo = resumo.xml_completo or documento.xml_completo
        documento.status_download_xml = cls._status_download_atual(documento, resumo)
        documento.save(update_fields=[
            'nsu', 'cnpj_emitente', 'razao_social_emitente', 'data_emissao',
            'valor_total', 'xml_resumo', 'xml_completo', 'status_download_xml',
            'updated_at',
        ])
        return documento, criado

    @classmethod
    def sincronizar_documentos(cls, filial, usuario=None, client=None) -> ResultadoSincronizacaoManifesto:
        config = ManifestoFiscalConfig.objects.for_filial(filial).filter(ativo=True).first()
        if not config:
            raise DadosInvalidosError('Configure o Manifesto Fiscal antes de consultar DF-e.')

        client = client or get_dfe_client()
        resultado = client.consultar_documentos(config)
        criados = 0
        atualizados = 0
        ignorados = 0

        for resumo in resultado.documentos:
            try:
                _, criado = cls._salvar_resumo_documento(filial, resumo)
            except DadosInvalidosError:
                ignorados += 1
                continue
            if criado:
                criados += 1
            else:
                atualizados += 1

        config.ultimo_nsu = resultado.ultimo_nsu or config.ultimo_nsu
        config.max_nsu = resultado.max_nsu or config.max_nsu
        config.data_ultima_consulta = timezone.now()
        config.save(update_fields=['ultimo_nsu', 'max_nsu', 'data_ultima_consulta', 'updated_at'])

        total = len(resultado.documentos)
        cls.registrar_log(
            config=config,
            tipo_evento=f'consulta_dfe_{resultado.modo}',
            mensagem=resultado.mensagem,
            codigo_status=(
                'ERP-LOCAL'
                if resultado.modo == 'local'
                else (resultado.codigo_status or 'ERP-INTEGRACAO')
            ),
            requisicao_resumo={
                'filial_id': filial.id,
                'cnpj': config.cnpj,
                'uf': config.uf,
                'ambiente': config.ambiente,
            },
            retorno_resumo={
                'total': total,
                'criados': criados,
                'atualizados': atualizados,
                'ignorados': ignorados,
                'ultimo_nsu': config.ultimo_nsu,
                'max_nsu': config.max_nsu,
                'codigo_status': resultado.codigo_status,
                'modo': resultado.modo,
            },
        )
        return ResultadoSincronizacaoManifesto(
            total_documentos=total,
            criados=criados,
            atualizados=atualizados,
            modo=resultado.modo,
            mensagem=resultado.mensagem,
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
            tipo_evento='ciencia_local_preparada',
            mensagem='Ciencia registrada apenas no ERP. Nenhum evento foi enviado a SEFAZ.',
            codigo_status='ERP-LOCAL',
        )
        return documento

    @classmethod
    def marcar_desconhecida(cls, documento):
        documento.status_manifestacao = ManifestoFiscalDocumento.StatusManifestacao.DESCONHECIDA
        documento.save(update_fields=['status_manifestacao', 'updated_at'])
        cls.registrar_log(
            documento=documento,
            tipo_evento='desconhecimento_local_preparado',
            mensagem='Desconhecimento registrado apenas no ERP. Nenhum evento foi enviado a SEFAZ.',
            codigo_status='ERP-LOCAL',
        )
        return documento

    @classmethod
    def marcar_nao_realizada(cls, documento):
        documento.status_manifestacao = ManifestoFiscalDocumento.StatusManifestacao.NAO_REALIZADA
        documento.save(update_fields=['status_manifestacao', 'updated_at'])
        cls.registrar_log(
            documento=documento,
            tipo_evento='operacao_nao_realizada_local_preparada',
            mensagem='Operacao nao realizada registrada apenas no ERP. Nenhum evento foi enviado a SEFAZ.',
            codigo_status='ERP-LOCAL',
        )
        return documento

    @classmethod
    def anexar_xml_completo(cls, documento, xml_texto: str, nome_arquivo: str = ''):
        if documento.entrada_nf_id:
            raise DadosInvalidosError('Este manifesto ja esta vinculado a uma entrada; o XML nao pode ser alterado.')

        xml_texto = (xml_texto or '').strip()
        if not xml_texto:
            raise DadosInvalidosError('Informe o XML completo da NF-e.')

        chave_documento = normalizar_chave(documento.chave_acesso)
        chave_xml = extrair_chave_xml(xml_texto)
        if len(chave_xml) != 44:
            raise DadosInvalidosError('XML completo nao trouxe uma chave de acesso valida.')
        if chave_documento and chave_xml != chave_documento:
            raise DadosInvalidosError('XML completo nao pertence a chave de acesso deste manifesto.')

        documento.xml_completo = xml_texto
        documento.status_download_xml = ManifestoFiscalDocumento.StatusDownload.XML_BAIXADO
        documento.save(update_fields=['xml_completo', 'status_download_xml', 'updated_at'])
        cls.registrar_log(
            documento=documento,
            tipo_evento='xml_anexado_local',
            mensagem='XML completo anexado localmente ao Manifesto. Nenhum evento foi enviado a SEFAZ.',
            codigo_status='ERP-LOCAL',
            retorno_resumo={
                'chave_xml': chave_xml,
                'nome_arquivo': nome_arquivo[:180],
                'tamanho_xml': len(xml_texto),
            },
        )
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

    @classmethod
    def importar_entrada(cls, documento, usuario) -> ResultadoImportacaoManifesto:
        if documento.entrada_nf_id:
            return ResultadoImportacaoManifesto(documento.entrada_nf, False)

        chave_documento = normalizar_chave(documento.chave_acesso)
        entrada_existente = EntradaNF.objects.for_filial(documento.filial).filter(
            chave_acesso_nf=chave_documento,
        ).first()
        if entrada_existente:
            cls.vincular_entrada(documento, entrada_existente)
            return ResultadoImportacaoManifesto(entrada_existente, False)

        xml_texto = (documento.xml_completo or '').strip()
        if not xml_texto:
            raise DadosInvalidosError(
                'Este manifesto ainda nao tem XML completo para importar. '
                'Registre ciencia e baixe o XML antes de criar a entrada.'
            )

        chave_xml = extrair_chave_xml(xml_texto)
        if chave_documento and chave_xml and chave_documento != chave_xml:
            raise DadosInvalidosError('XML completo nao pertence a chave de acesso deste manifesto.')

        entrada = importar_xml_para_entrada(
            xml_texto=xml_texto,
            filial=documento.filial,
            usuario=usuario,
            nome_arquivo=f'manifesto_{chave_documento}.xml'[:180],
        )
        entrada.origem_entrada = EntradaNF.OrigemEntrada.MANIFESTO
        entrada.observacao = 'Importada a partir do Manifesto Fiscal.'
        entrada.save(update_fields=['origem_entrada', 'observacao', 'updated_at'])

        cls.vincular_entrada(documento, entrada)
        return ResultadoImportacaoManifesto(entrada, True)
