"""Bloco 9 — Perdas de produção."""
from django.db import models
from apps.core.models import Usuario
from apps.core.models.base import TimestampedModel
from apps.produtos.models import Produto
from .ordem_producao import OrdemProducao
from .apontamento import ApontamentoProducao
from ..constants.enums import TipoPerda


class PerdaProducao(TimestampedModel):
    ordem_producao = models.ForeignKey(
        OrdemProducao, on_delete=models.CASCADE, related_name="perdas",
    )
    apontamento = models.ForeignKey(
        ApontamentoProducao, on_delete=models.SET_NULL, null=True, blank=True,
    )
    etapa = models.CharField(max_length=40, blank=True)
    tipo_perda = models.CharField(max_length=30, choices=TipoPerda.choices)
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT)
    lote = models.ForeignKey(
        "estoque.LoteProduto", on_delete=models.SET_NULL, null=True, blank=True,
    )
    quantidade = models.DecimalField(max_digits=12, decimal_places=3)
    unidade_medida = models.CharField(max_length=6, blank=True)
    motivo_detalhado = models.TextField(blank=True)
    impacto_custo = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    perda_evitavel = models.BooleanField(default=True)
    usuario_registro = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "perdas_producao"
        verbose_name = "Perda de produção"
        verbose_name_plural = "Perdas de produção"
        ordering = ["-created_at"]
