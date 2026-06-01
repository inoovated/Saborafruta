"""
Pedido de Compra — ciclo de compra antes da chegada da mercadoria.
rascunho → enviado_fornecedor → confirmado_fornecedor → parcialmente_recebido
         → recebido | cancelado
"""
from django.db import models

from apps.core.models.base import FilialScopedModel, TimestampedModel


class PedidoCompra(FilialScopedModel):

    class Status(models.TextChoices):
        RASCUNHO = 'rascunho', 'Rascunho'
        AGUARDANDO_APROVACAO = 'aguardando_aprovacao', 'Aguardando Aprovação'
        APROVADO = 'aprovado', 'Aprovado'
        ENVIADO_FORNECEDOR = 'enviado_fornecedor', 'Enviado ao Fornecedor'
        CONFIRMADO_FORNECEDOR = 'confirmado_fornecedor', 'Confirmado pelo Fornecedor'
        PARCIALMENTE_RECEBIDO = 'parcialmente_recebido', 'Parcialmente Recebido'
        RECEBIDO = 'recebido', 'Recebido'
        CANCELADO = 'cancelado', 'Cancelado'

    class ModalidadeFrete(models.IntegerChoices):
        CIF = 0, '0 - CIF (por conta do emitente)'
        FOB = 1, '1 - FOB (por conta do destinatário)'
        TERCEIROS = 2, '2 - Terceiros'
        SEM_FRETE = 9, '9 - Sem frete'

    numero_pedido = models.CharField(max_length=20, db_index=True)
    fornecedor = models.ForeignKey(
        'cadastros.Fornecedor', on_delete=models.PROTECT, related_name='pedidos_compra',
    )
    usuario = models.ForeignKey(
        'core.Usuario', on_delete=models.PROTECT, related_name='pedidos_compra_criados',
    )

    status = models.CharField(
        max_length=30, choices=Status.choices, default=Status.RASCUNHO, db_index=True,
    )

    # Datas
    data_emissao = models.DateTimeField(db_index=True)
    data_entrega_prevista = models.DateField(null=True, blank=True)
    data_entrega_realizada = models.DateField(null=True, blank=True)

    # Frete
    modalidade_frete = models.SmallIntegerField(
        choices=ModalidadeFrete.choices, default=ModalidadeFrete.CIF,
    )
    valor_frete = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    frete_valor = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        help_text='Campo legado mantido em sincronia com valor_frete.',
    )

    # Valores
    valor_produtos = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    valor_desconto = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    valor_outras_despesas = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    valor_ipi = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    valor_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # Aprovação
    aprovado_por = models.ForeignKey(
        'core.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pedidos_compra_aprovados',
    )
    data_aprovacao = models.DateTimeField(null=True, blank=True)
    motivo_cancelamento = models.TextField(blank=True)
    observacao = models.TextField(blank=True)

    class Meta:
        db_table = 'pedidos_compra'
        ordering = ['-data_emissao']
        indexes = [
            models.Index(fields=['filial', 'status']),
            models.Index(fields=['fornecedor', '-data_emissao']),
        ]
        verbose_name = 'Pedido de Compra'
        verbose_name_plural = 'Pedidos de Compra'

    def __str__(self):
        return f'PC {self.numero_pedido} — {self.fornecedor}'

    @property
    def pode_aprovar(self):
        return self.status in (self.Status.RASCUNHO, self.Status.AGUARDANDO_APROVACAO)

    @property
    def pode_enviar(self):
        return self.status == self.Status.APROVADO

    @property
    def pode_receber(self):
        return self.status in (
            self.Status.APROVADO, self.Status.ENVIADO_FORNECEDOR,
            self.Status.CONFIRMADO_FORNECEDOR, self.Status.PARCIALMENTE_RECEBIDO,
        )

    @property
    def pode_cancelar(self):
        return self.status in (
            self.Status.RASCUNHO, self.Status.AGUARDANDO_APROVACAO,
            self.Status.APROVADO, self.Status.ENVIADO_FORNECEDOR,
        )

    def recalcular_totais(self):
        from django.db.models import Sum
        agg = self.itens.aggregate(
            total_produtos=Sum('valor_total'),
            total_desconto=Sum('valor_desconto'),
            total_ipi=Sum('valor_ipi'),
        )
        self.valor_produtos = agg['total_produtos'] or 0
        self.valor_desconto = agg['total_desconto'] or 0
        self.valor_ipi = agg['total_ipi'] or 0
        self.frete_valor = self.valor_frete
        self.valor_total = (
            self.valor_produtos
            + self.valor_frete
            + self.valor_outras_despesas
            + self.valor_ipi
            - self.valor_desconto
        )


class ItemPedidoCompra(TimestampedModel):
    """Linha de produto num pedido de compra."""

    pedido = models.ForeignKey(
        PedidoCompra, on_delete=models.CASCADE, related_name='itens',
    )
    produto = models.ForeignKey(
        'produtos.Produto', on_delete=models.PROTECT, related_name='+',
    )
    numero_item = models.SmallIntegerField(default=1)

    quantidade = models.DecimalField(max_digits=12, decimal_places=3)
    quantidade_recebida = models.DecimalField(
        max_digits=12, decimal_places=3, default=0,
        help_text='Quantidade efetivamente recebida em entradas de NF',
    )
    valor_unitario = models.DecimalField(max_digits=14, decimal_places=4)
    valor_bruto = models.DecimalField(max_digits=14, decimal_places=2)
    valor_desconto = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    valor_ipi = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    valor_total = models.DecimalField(max_digits=14, decimal_places=2)

    prazo_entrega_dias = models.SmallIntegerField(default=0)
    observacao = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'itens_pedido_compra'
        ordering = ['pedido', 'numero_item']

    def calcular_totais(self):
        self.valor_bruto = self.quantidade * self.valor_unitario
        self.valor_total = self.valor_bruto - self.valor_desconto + self.valor_ipi

    @property
    def saldo_a_receber(self):
        return self.quantidade - self.quantidade_recebida

    @property
    def recebido_completo(self):
        return self.quantidade_recebida >= self.quantidade
