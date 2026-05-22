"""Alertas de vencimento e estoque mínimo."""
from django.db import models

from apps.core.models.base import FilialScopedModel


class AlertaVencimento(FilialScopedModel):
    """Alerta gerado pela task Celery diária. Um registro por lote × nível de risco."""

    class NivelRisco(models.TextChoices):
        D1   = 'd1',   'Urgente — 1 dia'
        D7   = 'd7',   'Crítico — 7 dias'
        D30  = 'd30',  'Alto — 30 dias'
        D60  = 'd60',  'Médio — 60 dias'
        D90  = 'd90',  'Atenção — 90 dias'
        D180 = 'd180', 'Aviso — 180 dias'
        # legado (registros anteriores à atualização)
        CRITICO = 'critico', 'Crítico (legado)'
        ALTO    = 'alto',    'Alto (legado)'
        MEDIO   = 'medio',   'Médio (legado)'
        BAIXO   = 'baixo',   'Baixo (legado)'

    produto = models.ForeignKey(
        'produtos.Produto', on_delete=models.CASCADE, related_name='alertas_vencimento',
    )
    lote = models.ForeignKey(
        'estoque.LoteProduto', on_delete=models.CASCADE, null=True, blank=True,
        related_name='alertas_vencimento',
    )
    data_validade = models.DateField()
    quantidade_em_risco = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    dias_para_vencer = models.SmallIntegerField()
    nivel_risco = models.CharField(max_length=20, choices=NivelRisco.choices)
    notificado_em = models.DateTimeField(null=True, blank=True)
    resolvido = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = 'alertas_vencimento'
        ordering = ['data_validade']
        indexes = [
            models.Index(fields=['filial', 'resolvido', 'data_validade']),
            models.Index(fields=['lote', 'nivel_risco']),
        ]
        verbose_name = 'Alerta de Vencimento'
        verbose_name_plural = 'Alertas de Vencimento'
