"""Separação de pedido — processo intermediário antes do faturamento."""
from django.db import models

from apps.core.models.base import FilialScopedModel, TimestampedModel


class SeparacaoPedido(FilialScopedModel):
    """Documento de separação gerado para um pedido confirmado."""

    class Status(models.TextChoices):
        ABERTA = 'aberta', 'Aberta'
        EM_ANDAMENTO = 'em_andamento', 'Em Andamento'
        CONCLUIDA = 'concluida', 'Concluída'
        CANCELADA = 'cancelada', 'Cancelada'

    pedido = models.ForeignKey(
        'vendas.PedidoVenda', on_delete=models.PROTECT, related_name='separacoes',
    )
    numero = models.CharField(max_length=20)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ABERTA,
    )
    usuario_separador = models.ForeignKey(
        'core.Usuario', on_delete=models.PROTECT,
        related_name='separacoes_realizadas',
    )
    data_inicio = models.DateTimeField(auto_now_add=True)
    data_fim = models.DateTimeField(null=True, blank=True)
    observacao = models.TextField(blank=True)

    class Meta:
        db_table = 'separacoes_pedido'
        ordering = ['-data_inicio']

    def __str__(self):
        return f'Separação {self.numero} — {self.pedido.numero_pedido}'


class ItemSeparacao(TimestampedModel):
    """Item separado com lote específico (respeitando FEFO)."""

    separacao = models.ForeignKey(
        SeparacaoPedido, on_delete=models.CASCADE, related_name='itens',
    )
    item_pedido = models.ForeignKey(
        'vendas.ItemPedidoVenda', on_delete=models.PROTECT, related_name='separacoes',
    )
    lote = models.ForeignKey(
        'estoque.LoteProduto', on_delete=models.PROTECT, related_name='+',
    )
    quantidade_separada = models.DecimalField(max_digits=12, decimal_places=3)

    class Meta:
        db_table = 'itens_separacao'
