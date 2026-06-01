"""Devolução de venda — total ou parcial."""
from django.db import models

from apps.core.models.base import FilialScopedModel, TimestampedModel


class DevolucaoVenda(FilialScopedModel):

    class Motivo(models.TextChoices):
        DEFEITO = 'defeito', 'Produto com defeito'
        NAO_CONFORMIDADE = 'nao_conformidade', 'Não conformidade'
        ARREPENDIMENTO = 'arrependimento', 'Arrependimento do cliente'
        ATRASO = 'atraso', 'Atraso na entrega'
        ERRO_PEDIDO = 'erro_pedido', 'Erro no pedido'
        OUTROS = 'outros', 'Outros'

    class Status(models.TextChoices):
        RASCUNHO = 'rascunho', 'Rascunho'
        PENDENTE = 'pendente', 'Pendente'
        APROVADA = 'aprovada', 'Aprovada'
        RECUSADA = 'recusada', 'Recusada'
        FINALIZADA = 'finalizada', 'Finalizada'

    pedido = models.ForeignKey(
        'vendas.PedidoVenda', on_delete=models.PROTECT, related_name='devolucoes',
    )
    numero = models.CharField(max_length=20, db_index=True)
    motivo = models.CharField(max_length=30, choices=Motivo.choices)
    descricao = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.RASCUNHO,
    )
    data_devolucao = models.DateField()
    valor_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    usuario = models.ForeignKey(
        'core.Usuario', on_delete=models.PROTECT, related_name='devolucoes_criadas',
    )
    aprovado_por = models.ForeignKey(
        'core.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='devolucoes_aprovadas',
    )

    class Meta:
        db_table = 'devolucoes_venda'
        ordering = ['-data_devolucao']

    def __str__(self):
        return f'Devolução {self.numero} — Pedido {self.pedido.numero_pedido}'


class ItemDevolucao(TimestampedModel):
    devolucao = models.ForeignKey(
        DevolucaoVenda, on_delete=models.CASCADE, related_name='itens',
    )
    item_pedido = models.ForeignKey(
        'vendas.ItemPedidoVenda', on_delete=models.PROTECT, related_name='devolucoes',
    )
    lote = models.ForeignKey(
        'estoque.LoteProduto', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+',
    )
    quantidade = models.DecimalField(max_digits=12, decimal_places=3)
    valor_unitario = models.DecimalField(max_digits=14, decimal_places=4)
    valor_total = models.DecimalField(max_digits=14, decimal_places=2)
    retornar_ao_estoque = models.BooleanField(
        default=True,
        help_text='Se True, retorna ao estoque; se False (produto danificado), apenas registra a devolução financeira',
    )

    class Meta:
        db_table = 'itens_devolucao'
