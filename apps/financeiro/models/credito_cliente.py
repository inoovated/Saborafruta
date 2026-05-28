"""Modelo de crédito para cliente (devolução, ajuste, etc.)."""
from django.db import models

from apps.core.models import Filial, Usuario
from apps.core.models.base import TimestampedModel, FilialManager as FilialAwareManager


class CreditoCliente(TimestampedModel):
    """
    Crédito gerado para o cliente, normalmente originado de devolução de mercadoria.
    O saldo disponível é calculado como valor - valor_utilizado.
    """

    class Status(models.TextChoices):
        DISPONIVEL = 'disponivel', 'Disponível'
        UTILIZADO = 'utilizado', 'Utilizado'
        CANCELADO = 'cancelado', 'Cancelado'

    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        related_name='creditos_clientes',
    )
    cliente = models.ForeignKey(
        'cadastros.Cliente',
        on_delete=models.PROTECT,
        related_name='creditos',
    )
    valor = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text='Valor total do crédito gerado.',
    )
    valor_utilizado = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        help_text='Valor já utilizado do crédito.',
    )
    motivo = models.CharField(
        max_length=100,
        help_text="Ex.: 'devolucao', 'ajuste'.",
    )
    documento_numero = models.CharField(max_length=30, blank=True)
    cfop = models.CharField(max_length=10, blank=True)
    observacao = models.TextField(blank=True)
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='creditos_clientes_gerados',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DISPONIVEL,
        db_index=True,
    )

    objects = FilialAwareManager()

    class Meta:
        db_table = 'financeiro_credito_cliente'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['filial', 'cliente', 'status']),
        ]
        verbose_name = 'Crédito de Cliente'
        verbose_name_plural = 'Créditos de Clientes'

    def __str__(self):
        return f'Crédito #{self.pk} — {self.cliente} R$ {self.valor:.2f} ({self.get_status_display()})'

    @property
    def valor_saldo(self):
        return self.valor - self.valor_utilizado
