"""Bloco 2 — Linhas de Produção (Polpa, Massas, Embalagens)."""
from django.db import models
from apps.core.models.base import TimestampedModel
from apps.core.models import Empresa


class LinhaProducao(TimestampedModel):
    ativo = models.BooleanField(default=True)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="linhas_producao")
    nome = models.CharField(max_length=60, help_text="Polpa de Frutas | Massas Alimentícias | Embalagens")
    prefixo_lote = models.CharField(max_length=2, unique=True, help_text="PF | MA | EB")
    prefixo_op = models.CharField(max_length=6, unique=True, help_text="OP-PF- | OP-MA- | OP-EB-")
    descricao_processo = models.TextField(blank=True)

    meta_rendimento_percentual = models.DecimalField(
        max_digits=5, decimal_places=2,
        help_text="Polpa>75 | Massas>85 | Embalagens>92",
    )
    meta_perda_maxima_percentual = models.DecimalField(max_digits=5, decimal_places=2, default=5)

    taxa_hora_maquina = models.DecimalField(
        max_digits=14, decimal_places=4,
        help_text="Custo/hora para rateio de CIF",
    )
    taxa_hora_mod = models.DecimalField(
        max_digits=14, decimal_places=4,
        help_text="Custo/hora de mão de obra direta",
    )

    cor_identificacao = models.CharField(max_length=7, default="#3b82f6", help_text="Hex (UI)")
    icone = models.CharField(max_length=30, default="🏭")

    class Meta:
        db_table = "linhas_producao"
        verbose_name = "Linha de Produção"
        verbose_name_plural = "Linhas de Produção"
        ordering = ["nome"]

    def __str__(self):
        return f"{self.icone} {self.nome}"

    def proximo_numero_op(self, filial):
        """Calcula o próximo número OP nesta linha/filial (formato OP-PF-2026-000123)."""
        from datetime import datetime
        from apps.producao.models import OrdemProducao
        ano = datetime.now().year
        ultima = (
            OrdemProducao.objects.filter(
                linha_producao=self, filial=filial,
                numero__startswith=f"{self.prefixo_op}{ano}-",
            )
            .order_by("-numero").first()
        )
        seq = int(ultima.numero.split("-")[-1]) + 1 if ultima else 1
        return f"{self.prefixo_op}{ano}-{seq:06d}"

    def proximo_numero_lote(self, filial):
        """Calcula o próximo número de lote (formato PF-2026-000123)."""
        from datetime import datetime
        from apps.estoque.models import LoteProduto
        ano = datetime.now().year
        ultimo = (
            LoteProduto.objects.filter(
                filial=filial, numero_lote__startswith=f"{self.prefixo_lote}-{ano}-",
            )
            .order_by("-numero_lote").first()
        )
        seq = int(ultimo.numero_lote.split("-")[-1]) + 1 if ultimo else 1
        return f"{self.prefixo_lote}-{ano}-{seq:06d}"
