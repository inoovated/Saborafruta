"""Bloco 10 — Parâmetros de qualidade por linha."""
from django.db import models
from apps.core.models.base import ActiveModel
from apps.produtos.models import LinhaProducao


class ParametroQualidade(ActiveModel):
    linha_producao = models.ForeignKey(
        LinhaProducao, on_delete=models.CASCADE, related_name="parametros_qualidade",
    )
    nome_parametro = models.CharField(max_length=60)
    unidade_medida = models.CharField(
        max_length=10, blank=True,
        help_text="°Brix | pH | % | g/cm³ | N | mm | mPa·s | CFU/g",
    )
    valor_minimo = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    valor_maximo = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    valor_ideal = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    obrigatorio = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "parametros_qualidade"
        verbose_name = "Parâmetro de qualidade"
        verbose_name_plural = "Parâmetros de qualidade"
        ordering = ["linha_producao", "nome_parametro"]

    def __str__(self):
        return f"{self.linha_producao.nome} – {self.nome_parametro}"
