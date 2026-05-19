"""Bloco 16 — Caixas e dispositivos PDV."""
from django.db import models
from apps.core.models import Filial, Usuario
from apps.core.models.base import TimestampedModel, ActiveModel
from apps.core.models.base import FilialManager as FilialAwareManager


class Caixa(ActiveModel):
    filial = models.ForeignKey(Filial, on_delete=models.CASCADE, related_name="caixas")
    numero = models.IntegerField()
    descricao = models.CharField(max_length=60, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = FilialAwareManager()

    class Meta:
        db_table = "caixas"
        verbose_name = "Caixa"
        verbose_name_plural = "Caixas"
        unique_together = [("filial", "numero")]
        ordering = ["filial", "numero"]

    def __str__(self):
        return f"Caixa {self.numero} – {self.filial}"


class DispositivoPDV(TimestampedModel, ActiveModel):
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name="dispositivos_pdv")
    caixa = models.ForeignKey(Caixa, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name="dispositivos")
    tipo = models.CharField(
        max_length=30,
        help_text="impressora_fiscal|impressora_nao_fiscal|balanca|leitor_codigo_barras|"
                  "pinpad|gaveta_dinheiro|display_cliente|tef_terminal|etiquetadora",
    )
    descricao = models.CharField(max_length=80, blank=True)
    marca = models.CharField(max_length=40, blank=True)
    modelo = models.CharField(max_length=60, blank=True)
    numero_serie = models.CharField(max_length=60, unique=True, null=True, blank=True)
    driver_protocolo = models.CharField(max_length=40, blank=True)
    tipo_conexao = models.CharField(max_length=20, blank=True)
    porta_ou_ip = models.CharField(max_length=100, blank=True)
    porta_tcp = models.IntegerField(null=True, blank=True)
    modelo_protocolo_balanca = models.CharField(max_length=30, blank=True)
    velocidade_serial = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "dispositivos_pdv"
        verbose_name = "Dispositivo PDV"
        verbose_name_plural = "Dispositivos PDV"


class ImpressoraConfig(models.Model):
    dispositivo = models.OneToOneField(DispositivoPDV, on_delete=models.CASCADE)
    largura_colunas = models.PositiveSmallIntegerField(default=48)
    corte_automatico = models.BooleanField(default=True)
    logo_impressao_url = models.URLField(max_length=500, blank=True)
    template_cabecalho = models.TextField(blank=True)
    template_rodape = models.TextField(blank=True)
    template_etiqueta = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "impressoras_config"


class ImpressaoLog(models.Model):
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT)
    dispositivo = models.ForeignKey(DispositivoPDV, on_delete=models.SET_NULL, null=True, blank=True)
    tipo_documento = models.CharField(max_length=30)
    documento_referencia_id = models.BigIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, default="ok")
    motivo_falha = models.TextField(blank=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "impressoes_log"
        ordering = ["-created_at"]
