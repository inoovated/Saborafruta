"""Parametros de qualidade por produto (por filial)."""
from django.db import models

from apps.core.models.base import ActiveModel, FilialScopedModel
from apps.qualidade.constants.enums import TipoAnalise


class ParametroQualidadeProduto(FilialScopedModel, ActiveModel):
    class TipoValor(models.TextChoices):
        NUMERO = "numero", "Numero"
        TEXTO = "texto", "Texto"
        SIM_NAO = "sim_nao", "Sim/Nao"
        SELECAO = "selecao", "Selecao"

    produto = models.ForeignKey(
        "produtos.Produto",
        on_delete=models.CASCADE,
        related_name="parametros_qualidade_produto",
    )
    etapa = models.CharField(
        max_length=30,
        choices=TipoAnalise.choices,
        default=TipoAnalise.PRODUTO_ACABADO,
        help_text="Em qual etapa esse parametro se aplica.",
    )
    nome_parametro = models.CharField(max_length=60)
    tipo_valor = models.CharField(
        max_length=20,
        choices=TipoValor.choices,
        default=TipoValor.NUMERO,
    )
    unidade_medida = models.CharField(
        max_length=10,
        blank=True,
        help_text="Ex.: Brix | pH | % | g | kg | mm | C",
    )
    valor_minimo = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    valor_maximo = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    valor_ideal = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    valor_texto_ideal = models.CharField(max_length=120, blank=True)
    opcoes = models.JSONField(
        default=list,
        blank=True,
        help_text='Lista de opcoes quando tipo_valor = "selecao".',
    )
    obrigatorio = models.BooleanField(default=True)

    class Meta:
        db_table = "parametros_qualidade_produtos"
        verbose_name = "Parametro de qualidade (produto)"
        verbose_name_plural = "Parametros de qualidade (produto)"
        ordering = ["produto", "etapa", "nome_parametro"]
        unique_together = [("filial", "produto", "etapa", "nome_parametro")]

    def __str__(self):
        return f"{self.produto} - {self.nome_parametro}"

