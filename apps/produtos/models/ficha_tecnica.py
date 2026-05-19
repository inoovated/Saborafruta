"""Bloco 6 — Ficha Técnica / BOM."""
from django.db import models
from apps.core.models.base import TimestampedModel
from apps.core.models import Empresa, Usuario
from .linha_producao import LinhaProducao
from .produto import Produto


class FichaTecnica(TimestampedModel):
    ativo = models.BooleanField(default=True)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="fichas_tecnicas")
    produto_acabado = models.ForeignKey(
        Produto, on_delete=models.PROTECT, related_name="fichas_tecnicas",
    )
    linha_producao = models.ForeignKey(LinhaProducao, on_delete=models.PROTECT)
    versao = models.PositiveSmallIntegerField(default=1)
    descricao = models.CharField(max_length=150)

    tempo_processo_minutos = models.IntegerField(null=True, blank=True)
    temperatura_processo = models.DecimalField(
        max_digits=5, decimal_places=1, null=True, blank=True,
    )
    rendimento_esperado_percentual = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
    )
    lote_minimo_producao = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    lote_maximo_producao = models.DecimalField(
        max_digits=12, decimal_places=3, null=True, blank=True,
    )

    instrucoes_processo = models.TextField(blank=True)
    observacoes = models.JSONField(default=dict, blank=True)

    data_vigencia_inicio = models.DateField()
    data_vigencia_fim = models.DateField(null=True, blank=True)

    aprovado_por = models.ForeignKey(
        Usuario, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="fichas_aprovadas",
    )
    aprovado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "fichas_tecnicas"
        verbose_name = "Ficha técnica"
        verbose_name_plural = "Fichas técnicas"
        unique_together = [("produto_acabado", "versao")]
        ordering = ["-data_vigencia_inicio", "-versao"]

    def __str__(self):
        return f"FT v{self.versao} - {self.produto_acabado}"


class ItemFichaTecnica(models.Model):
    ficha_tecnica = models.ForeignKey(
        FichaTecnica, on_delete=models.CASCADE, related_name="itens",
    )
    materia_prima = models.ForeignKey(
        Produto, on_delete=models.PROTECT, related_name="usado_em_fichas",
    )
    quantidade_padrao = models.DecimalField(max_digits=12, decimal_places=3)
    unidade_medida = models.CharField(max_length=6)
    tolerancia_percentual = models.DecimalField(max_digits=5, decimal_places=2, default=5)
    ordem_mistura = models.PositiveSmallIntegerField(null=True, blank=True)
    observacao = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "itens_ficha_tecnica"
        verbose_name = "Item de ficha técnica"
        verbose_name_plural = "Itens de ficha técnica"
        ordering = ["ordem_mistura", "id"]
