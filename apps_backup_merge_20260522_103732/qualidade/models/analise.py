"""Bloco 10 — Análise de qualidade."""
from django.db import models
from apps.core.models import Filial, Usuario
from apps.core.models.base import FilialManager as FilialAwareManager
from ..constants.enums import TipoAnalise, ResultadoAnalise, AcaoReprovacao


class AnaliseQualidade(models.Model):
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name="analises_qualidade")
    lote = models.ForeignKey(
        "estoque.LoteProduto", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="analises",
    )
    ordem_producao = models.ForeignKey(
        "producao.OrdemProducao", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="analises",
    )

    tipo_analise = models.CharField(max_length=30, choices=TipoAnalise.choices)
    parametros = models.JSONField(
        help_text='{"brix": 12.5, "ph": 3.8, "acidez": 0.65}',
    )
    resultado = models.CharField(
        max_length=30, choices=ResultadoAnalise.choices,
        default=ResultadoAnalise.PENDENTE,
    )
    responsavel_tecnico = models.ForeignKey(
        Usuario, on_delete=models.PROTECT, related_name="analises_realizadas",
    )
    data_analise = models.DateTimeField()
    laudo_pdf_url = models.URLField(max_length=500, blank=True)
    observacao = models.TextField(blank=True)
    acao_reprovacao = models.CharField(
        max_length=40, choices=AcaoReprovacao.choices, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = FilialAwareManager()

    class Meta:
        db_table = "analises_qualidade"
        verbose_name = "Análise de qualidade"
        verbose_name_plural = "Análises de qualidade"
        ordering = ["-data_analise"]
        indexes = [
            models.Index(fields=["filial", "tipo_analise", "resultado"]),
            models.Index(fields=["lote"]),
        ]

    def __str__(self):
        return f"Análise #{self.id} – {self.tipo_analise} – {self.resultado}"
