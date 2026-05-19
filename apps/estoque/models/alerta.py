"""Alertas de vencimento e estoque mínimo."""
from django.db import models

from apps.core.models.base import FilialScopedModel


class AlertaVencimento(FilialScopedModel):
    """Alerta gerado pela task Celery diária. Um registro por lote × nível de risco."""

    class NivelRisco(models.TextChoices):
        CRITICO = 'critico', 'Crítico (D-1)'
        ALTO = 'alto', 'Alto (D-7)'
        MEDIO = 'medio', 'Médio (D-30)'
        BAIXO = 'baixo', 'Baixo (D-45/60)'

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
