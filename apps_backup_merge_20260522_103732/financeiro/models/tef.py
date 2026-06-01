"""TEF — configurações e transações."""
from django.db import models
from apps.core.models import Filial
from apps.core.models.base import ActiveModel


class TEFConfiguracao(ActiveModel):
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name="tef_configuracoes")
    caixa = models.ForeignKey("pdv.Caixa", on_delete=models.SET_NULL, null=True, blank=True)
    provedor = models.CharField(max_length=30,
                                 help_text="sitef|paygo|cloudwalk|stone|cielo_lio|getnet")
    ip_servidor = models.GenericIPAddressField(null=True, blank=True)
    porta = models.IntegerField(null=True, blank=True)
    numero_estabelecimento = models.CharField(max_length=20, blank=True)
    cnpj_estabelecimento = models.CharField(max_length=14, blank=True)
    timeout_segundos = models.PositiveSmallIntegerField(default=90)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "tef_configuracoes"
        verbose_name = "Configuração TEF"
        verbose_name_plural = "Configurações TEF"


class TEFTransacao(models.Model):
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT)
    venda_pdv = models.ForeignKey(
        "pdv.VendaPDV", on_delete=models.SET_NULL, null=True, blank=True,
    )
    sessao_pdv = models.ForeignKey(
        "pdv.SessaoPDV", on_delete=models.SET_NULL, null=True, blank=True,
    )
    nsu = models.CharField(max_length=30)
    nsu_host = models.CharField(max_length=30, blank=True)
    autorizacao = models.CharField(max_length=20, blank=True)
    bandeira = models.CharField(max_length=30, blank=True)
    tipo_cartao = models.CharField(max_length=20, blank=True)
    numero_parcelas = models.PositiveSmallIntegerField(default=1)
    valor = models.DecimalField(max_digits=14, decimal_places=2)
    valor_parcela = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, default="pendente")
    codigo_resposta = models.CharField(max_length=10, blank=True)
    mensagem_resposta = models.CharField(max_length=100, blank=True)
    data_transacao = models.DateTimeField()
    comprovante_via_cliente = models.TextField(blank=True)
    comprovante_via_estabelecimento = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "tef_transacoes"
        verbose_name = "Transação TEF"
        verbose_name_plural = "Transações TEF"
        ordering = ["-data_transacao"]
