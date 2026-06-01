"""Estrutura de Manifesto Fiscal / DF-e.

Esta primeira versao prepara persistencia e tela. As chamadas reais de SEFAZ/DF-e
devem entrar em service proprio com certificado A1 e controle de NSU.
"""
from django.db import models

from apps.core.models.base import FilialScopedModel, TimestampedModel


class ManifestoFiscalConfig(FilialScopedModel):
    class Ambiente(models.TextChoices):
        HOMOLOGACAO = 'homologacao', 'Homologacao'
        PRODUCAO = 'producao', 'Producao'

    cnpj = models.CharField(max_length=18)
    uf = models.CharField(max_length=2)
    ambiente = models.CharField(
        max_length=20,
        choices=Ambiente.choices,
        default=Ambiente.HOMOLOGACAO,
    )
    certificado_digital = models.FileField(upload_to='fiscal/certificados/', blank=True, null=True)
    certificado_nome = models.CharField(max_length=180, blank=True)
    certificado_thumbprint = models.CharField(max_length=64, blank=True)
    certificado_cnpj = models.CharField(max_length=14, blank=True)
    certificado_titular = models.CharField(max_length=255, blank=True)
    certificado_emissor = models.CharField(max_length=255, blank=True)
    certificado_validade_inicio = models.DateTimeField(null=True, blank=True)
    certificado_validade_fim = models.DateTimeField(null=True, blank=True)
    ultimo_nsu = models.CharField(max_length=20, blank=True)
    max_nsu = models.CharField(max_length=20, blank=True)
    data_ultima_consulta = models.DateTimeField(null=True, blank=True)
    ativo = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = 'manifesto_fiscal_configs'
        unique_together = [('filial', 'cnpj', 'ambiente')]
        ordering = ['filial', 'cnpj']

    def __str__(self):
        return f'{self.cnpj} - {self.filial}'


class ManifestoFiscalDocumento(FilialScopedModel):
    class StatusManifestacao(models.TextChoices):
        NAO_MANIFESTADA = 'nao_manifestada', 'Nao manifestada'
        CIENCIA = 'ciencia', 'Ciencia da operacao'
        CONFIRMADA = 'confirmada', 'Confirmada'
        DESCONHECIDA = 'desconhecida', 'Desconhecida'
        NAO_REALIZADA = 'nao_realizada', 'Operacao nao realizada'

    class StatusDownload(models.TextChoices):
        RESUMO = 'resumo', 'Resumo'
        XML_DISPONIVEL = 'xml_disponivel', 'XML disponivel'
        XML_BAIXADO = 'xml_baixado', 'XML baixado'
        IMPORTADA = 'importada', 'Importada'
        ERRO = 'erro', 'Erro'

    chave_acesso = models.CharField(max_length=44, db_index=True)
    nsu = models.CharField(max_length=20, blank=True, db_index=True)
    cnpj_emitente = models.CharField(max_length=18, blank=True, db_index=True)
    razao_social_emitente = models.CharField(max_length=180, blank=True)
    data_emissao = models.DateField(null=True, blank=True)
    valor_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status_manifestacao = models.CharField(
        max_length=30,
        choices=StatusManifestacao.choices,
        default=StatusManifestacao.NAO_MANIFESTADA,
        db_index=True,
    )
    status_download_xml = models.CharField(
        max_length=30,
        choices=StatusDownload.choices,
        default=StatusDownload.RESUMO,
        db_index=True,
    )
    xml_resumo = models.TextField(blank=True)
    xml_completo = models.TextField(blank=True)
    entrada_nf = models.ForeignKey(
        'compras.EntradaNF',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='manifestos_fiscais',
    )
    data_importacao = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'manifesto_fiscal_documentos'
        unique_together = [('filial', 'chave_acesso')]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['filial', 'status_download_xml'], name='manifesto_doc_filial_down_idx'),
            models.Index(fields=['filial', 'status_manifestacao'], name='manifesto_doc_filial_manif_idx'),
        ]

    def __str__(self):
        return self.chave_acesso


class ManifestoFiscalLog(TimestampedModel):
    config = models.ForeignKey(
        ManifestoFiscalConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs',
    )
    documento = models.ForeignKey(
        ManifestoFiscalDocumento,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='logs',
    )
    tipo_evento = models.CharField(max_length=40)
    requisicao_resumo = models.JSONField(default=dict, blank=True)
    retorno_resumo = models.JSONField(default=dict, blank=True)
    codigo_status = models.CharField(max_length=20, blank=True)
    mensagem = models.TextField(blank=True)

    class Meta:
        db_table = 'manifesto_fiscal_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tipo_evento'], name='manifesto_log_evento_idx'),
            models.Index(fields=['codigo_status'], name='manifesto_log_status_idx'),
        ]

    def __str__(self):
        return f'{self.tipo_evento} - {self.codigo_status}'
