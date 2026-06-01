"""
Avaliação de entrega de fornecedor.
Gerada automaticamente ao efetivar entrada de NF vinculada a pedido de compra.
Alimenta métricas de Fornecedor.nota_qualidade e percentual_no_prazo.
"""
from django.db import models

from apps.core.models.base import FilialScopedModel


class AvaliacaoFornecedor(FilialScopedModel):
    """Registro granular de cada entrega para calcular métricas."""

    fornecedor = models.ForeignKey(
        'cadastros.Fornecedor', on_delete=models.CASCADE, related_name='avaliacoes',
    )
    pedido_compra = models.ForeignKey(
        'compras.PedidoCompra', on_delete=models.CASCADE, related_name='avaliacoes',
    )
    entrada_nf = models.ForeignKey(
        'compras.EntradaNF', on_delete=models.CASCADE, related_name='avaliacao',
    )

    data_prevista = models.DateField(null=True, blank=True)
    data_real = models.DateField()
    dias_atraso = models.IntegerField(
        default=0,
        help_text='Negativo = entregou antes. Positivo = atrasou.',
    )
    entregue_no_prazo = models.BooleanField(default=True)

    # 1-5 estrelas baseado em pontualidade e conformidade
    nota_pontualidade = models.SmallIntegerField(default=5)
    nota_qualidade = models.SmallIntegerField(
        default=5,
        help_text='Pode ser ajustada manualmente posteriormente',
    )
    nota_geral = models.DecimalField(max_digits=3, decimal_places=2, default=5)

    observacao = models.TextField(blank=True)

    class Meta:
        db_table = 'avaliacoes_fornecedor'
        ordering = ['-data_real']
        indexes = [
            models.Index(fields=['fornecedor', '-data_real']),
        ]
        verbose_name = 'Avaliação de Fornecedor'
        verbose_name_plural = 'Avaliações de Fornecedor'

    def __str__(self):
        return f'{self.fornecedor} — {self.data_real}: {self.nota_geral}★'
