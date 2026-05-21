"""
Parâmetros do Sistema — identidade visual, contatos e configuração fiscal.

A identificação (nome fantasia, razão social, CNPJ, IE, IM) e o endereço
permanecem na ``Filial``; a tela de Parâmetros os edita, mas não duplica o
armazenamento. Este módulo guarda apenas o que ainda não existia: a logo,
o e-mail secundário e a configuração de emissão por documento fiscal.
"""
from django.db import models

from .base import TimestampedModel


class ParametrosSistema(TimestampedModel):
    """Parâmetros gerais de uma filial (um registro por filial)."""

    filial = models.OneToOneField(
        'core.Filial',
        on_delete=models.CASCADE,
        related_name='parametros_sistema',
    )
    logo = models.ImageField(
        upload_to='sistema/logo/',
        blank=True,
        null=True,
        help_text='Logomarca exibida no topo do sistema e na tela de login.',
    )
    email_secundario = models.EmailField(max_length=120, blank=True)

    class Meta:
        db_table = 'parametros_sistema'
        verbose_name = 'Parâmetros do Sistema'
        verbose_name_plural = 'Parâmetros do Sistema'

    def __str__(self):
        return f'Parâmetros — {self.filial}'


class ParametroDocumentoFiscal(TimestampedModel):
    """Configuração de emissão de um tipo de documento fiscal."""

    class TipoDocumento(models.TextChoices):
        NFE = 'nfe', 'NF-e'
        NFCE = 'nfce', 'NFC-e'
        CTE = 'cte', 'CT-e'
        CTE_OS = 'cte_os', 'CT-e OS'
        MDFE = 'mdfe', 'MDF-e'
        NFCOM = 'nfcom', 'NFCom'
        NFSE = 'nfse', 'NFS-e'
        NFSE_NACIONAL = 'nfse_nacional', 'NFS-e Nacional'

    class Ambiente(models.IntegerChoices):
        PRODUCAO = 1, 'Produção'
        HOMOLOGACAO = 2, 'Homologação'

    parametros = models.ForeignKey(
        ParametrosSistema,
        on_delete=models.CASCADE,
        related_name='documentos_fiscais',
    )
    tipo_documento = models.CharField(max_length=20, choices=TipoDocumento.choices)
    habilitado = models.BooleanField(
        default=False,
        help_text='Quando ativo, o documento fica disponível para emissão.',
    )
    serie = models.PositiveSmallIntegerField(default=1)
    proximo_numero = models.BigIntegerField(default=1)
    ambiente = models.SmallIntegerField(
        choices=Ambiente.choices,
        default=Ambiente.HOMOLOGACAO,
    )
    cfop_padrao = models.CharField(max_length=5, blank=True)
    natureza_operacao = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = 'parametros_documento_fiscal'
        verbose_name = 'Parâmetro de Documento Fiscal'
        verbose_name_plural = 'Parâmetros de Documentos Fiscais'
        unique_together = [('parametros', 'tipo_documento')]
        ordering = ['parametros', 'tipo_documento']

    def __str__(self):
        return f'{self.get_tipo_documento_display()} — {self.parametros.filial}'
