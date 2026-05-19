"""Bloco 8 — Apontamento de produção."""
from django.db import models
from apps.core.models import Usuario
from apps.core.models.base import TimestampedModel
from .ordem_producao import OrdemProducao
from ..constants.enums import EtapaProducao


class ApontamentoProducao(TimestampedModel):
    ordem_producao = models.ForeignKey(
        OrdemProducao, on_delete=models.CASCADE, related_name="apontamentos",
    )
    etapa = models.CharField(max_length=40, choices=EtapaProducao.choices)
    data_hora_inicio = models.DateTimeField()
    data_hora_fim = models.DateTimeField(null=True, blank=True)
    operador = models.ForeignKey(
        Usuario, on_delete=models.PROTECT, related_name="apontamentos",
    )

    quantidade_produzida_etapa = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    quantidade_perdida_etapa = models.DecimalField(max_digits=12, decimal_places=3, default=0)

    parametros_processo = models.JSONField(
        default=dict, blank=True,
        help_text='{"temperatura":-18,"brix":12.5,"ph":3.8,"umidade":12,"pressao":5.2}',
    )
    equipamento_utilizado = models.CharField(max_length=60, blank=True)
    observacao = models.TextField(blank=True)

    class Meta:
        db_table = "apontamentos_producao"
        verbose_name = "Apontamento"
        verbose_name_plural = "Apontamentos"
        ordering = ["-data_hora_inicio"]
