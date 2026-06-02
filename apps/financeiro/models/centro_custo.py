"""Centros de custo gerenciais."""
from django.db import models

from apps.core.models import Empresa
from apps.core.models.base import ActiveModel, TimestampedModel


class CentroCusto(TimestampedModel, ActiveModel):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="centros_custo")
    codigo = models.CharField(max_length=20)
    nome = models.CharField(max_length=100)
    descricao = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "centros_custo"
        verbose_name = "Centro de custo"
        verbose_name_plural = "Centros de custo"
        ordering = ["codigo", "nome"]
        constraints = [
            models.UniqueConstraint(fields=["empresa", "codigo"], name="uniq_centro_custo_codigo_empresa"),
        ]
        indexes = [
            models.Index(fields=["empresa", "ativo"], name="centro_custo_empresa_ativo_idx"),
        ]

    def __str__(self):
        return f"{self.codigo} - {self.nome}"
