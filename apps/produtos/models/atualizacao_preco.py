"""Modelos para atualizacao de preco de venda em massa."""
from django.db import models

from apps.core.models.base import FilialScopedModel, TimestampedModel


class AtualizacaoPrecoLote(FilialScopedModel):
    class Origem(models.TextChoices):
        AVULSA = 'avulsa', 'Uso avulso'
        ENTRADA_XML = 'entrada_xml', 'Entrada XML'

    class Status(models.TextChoices):
        RASCUNHO = 'rascunho', 'Rascunho'
        SIMULADO = 'simulado', 'Simulado'
        APLICADO = 'aplicado', 'Aplicado'
        CANCELADO = 'cancelado', 'Cancelado'

    class RegraTipo(models.TextChoices):
        PERCENTUAL = 'percentual', 'Percentual'
        VALOR_FIXO = 'valor_fixo', 'Valor fixo'
        NOVO_PRECO = 'novo_preco', 'Novo preco'
        MARKUP = 'markup', 'Markup'
        MARGEM = 'margem', 'Margem'

    usuario = models.ForeignKey(
        'core.Usuario',
        on_delete=models.PROTECT,
        related_name='lotes_atualizacao_preco',
    )
    origem = models.CharField(max_length=20, choices=Origem.choices, default=Origem.AVULSA)
    entrada = models.ForeignKey(
        'compras.EntradaNF',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lotes_atualizacao_preco',
    )
    numero_nfe = models.CharField(max_length=30, blank=True)
    chave_nfe = models.CharField(max_length=44, blank=True)
    fornecedor_nome = models.CharField(max_length=180, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RASCUNHO)
    regra_tipo = models.CharField(max_length=20, choices=RegraTipo.choices, default=RegraTipo.PERCENTUAL)
    regra_config = models.JSONField(default=dict, blank=True)
    filtros_config = models.JSONField(default=dict, blank=True)
    total_produtos = models.PositiveIntegerField(default=0)
    observacao = models.TextField(blank=True)
    data_aplicacao = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'produtos_atualizacao_preco_lotes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['filial', 'origem', 'status'], name='prod_preco_lote_origem_idx'),
            models.Index(fields=['entrada'], name='prod_preco_lote_entrada_idx'),
        ]
        verbose_name = 'Lote de atualizacao de preco'
        verbose_name_plural = 'Lotes de atualizacao de preco'

    def __str__(self):
        origem = self.get_origem_display()
        return f'{origem} - {self.total_produtos} produto(s)'


class AtualizacaoPrecoItem(TimestampedModel):
    class Status(models.TextChoices):
        SIMULADO = 'simulado', 'Simulado'
        APLICADO = 'aplicado', 'Aplicado'
        BLOQUEADO = 'bloqueado', 'Bloqueado'
        ERRO = 'erro', 'Erro'

    lote = models.ForeignKey(
        AtualizacaoPrecoLote,
        on_delete=models.CASCADE,
        related_name='itens',
    )
    produto = models.ForeignKey(
        'produtos.Produto',
        on_delete=models.PROTECT,
        related_name='atualizacoes_preco',
    )
    preco_anterior = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    preco_novo = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    custo_base = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    margem_anterior = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    margem_nova = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    markup_anterior = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    markup_novo = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SIMULADO)
    motivo_bloqueio = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'produtos_atualizacao_preco_itens'
        ordering = ['lote', 'produto__descricao']
        indexes = [
            models.Index(fields=['lote', 'status'], name='prod_preco_item_status_idx'),
            models.Index(fields=['produto'], name='prod_preco_item_produto_idx'),
        ]
        verbose_name = 'Item de atualizacao de preco'
        verbose_name_plural = 'Itens de atualizacao de preco'

    def __str__(self):
        return f'{self.produto} - {self.preco_anterior} -> {self.preco_novo}'
