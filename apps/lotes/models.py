"""Inspeção de lote — registro de qualidade por responsável."""
from django.db import models

from apps.core.models.base import TimestampedModel


class InspecaoLote(TimestampedModel):
    class Resultado(models.TextChoices):
        APROVADO = 'aprovado', 'Aprovado'
        REPROVADO = 'reprovado', 'Reprovado'
        QUARENTENA = 'quarentena', 'Em Quarentena'
        PENDENTE = 'pendente', 'Pendente'

    lote = models.ForeignKey(
        'estoque.LoteProduto', on_delete=models.CASCADE, related_name='inspecoes',
    )
    responsavel = models.ForeignKey(
        'core.Usuario', on_delete=models.PROTECT, related_name='inspecoes_lote',
    )
    data_inspecao = models.DateTimeField()
    resultado = models.CharField(
        max_length=20, choices=Resultado.choices, default=Resultado.PENDENTE, db_index=True,
    )
    parecer = models.TextField(blank=True, help_text='Descrição técnica do resultado')
    observacao = models.TextField(blank=True)

    class Meta:
        db_table = 'lotes_inspecoes'
        ordering = ['-data_inspecao']
        verbose_name = 'Inspeção de Lote'
        verbose_name_plural = 'Inspeções de Lote'

    def __str__(self):
        return f'Inspeção {self.lote.numero_lote} — {self.get_resultado_display()}'
