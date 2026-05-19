"""Bloco 13 — DRE Consolidado."""
from django.db import models
from apps.core.models import Filial
from apps.core.models.base import FilialManager as FilialAwareManager
from apps.produtos.models import LinhaProducao
from .conta_bancaria import PlanoContas


class DREConsolidado(models.Model):
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name="dres")
    linha_producao = models.ForeignKey(
        LinhaProducao, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="NULL = consolidado de todas as linhas",
    )
    competencia = models.DateField(help_text="Primeiro dia do mês")

    receita_bruta = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    deducoes = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    receita_liquida = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    cmv = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    custo_mp = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    custo_mod = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    custo_cif = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    despesas_operacionais = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    despesas_administrativas = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    despesas_comerciais = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    despesas_financeiras = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    lucro_bruto = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    ebitda = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    lucro_operacional = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    lucro_liquido = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    margem_bruta_percentual = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    margem_ebitda_percentual = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    margem_liquida_percentual = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    margem_contribuicao_percentual = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    calculado_em = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = FilialAwareManager()

    class Meta:
        db_table = "dre_consolidado"
        verbose_name = "DRE Consolidado"
        verbose_name_plural = "DRE Consolidados"
        unique_together = [("filial", "competencia", "linha_producao")]
        ordering = ["-competencia", "linha_producao"]
        indexes = [
            models.Index(fields=["filial", "-competencia"]),
        ]

    def __str__(self):
        sufixo = self.linha_producao.nome if self.linha_producao else "Consolidado"
        return f"DRE {self.competencia.strftime('%Y-%m')} – {sufixo}"


class DRECentroCusto(models.Model):
    dre = models.ForeignKey(DREConsolidado, on_delete=models.CASCADE, related_name="centros_custo")
    plano_contas = models.ForeignKey(PlanoContas, on_delete=models.PROTECT)
    valor = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dre_centros_custo"
