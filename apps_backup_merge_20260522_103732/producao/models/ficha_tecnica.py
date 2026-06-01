"""
Ficha Técnica (Bill of Materials / BOM) — define as matérias-primas e quantidades
necessárias para produzir uma unidade de produto acabado.
"""
from django.db import models

from apps.core.models.base import FilialScopedModel, TimestampedModel


class FichaTecnica(FilialScopedModel):
    """Receita de produção de um produto acabado."""

    class Status(models.TextChoices):
        RASCUNHO = 'rascunho', 'Rascunho'
        ATIVA = 'ativa', 'Ativa'
        INATIVA = 'inativa', 'Inativa'

    produto_acabado = models.ForeignKey(
        'produtos.Produto', on_delete=models.PROTECT,
        related_name='producao_fichas_tecnicas',
        help_text='Produto que será gerado ao executar esta ficha',
    )
    codigo = models.CharField(max_length=30, blank=True, help_text='Código interno da ficha')
    descricao = models.CharField(max_length=150)
    versao = models.CharField(max_length=10, default='1.0')
    quantidade_produzida = models.DecimalField(
        max_digits=12, decimal_places=3, default=1,
        help_text='Quantidade de produto acabado gerada pela execução da ficha',
    )
    tempo_producao_minutos = models.IntegerField(
        default=0, help_text='Tempo estimado de produção em minutos',
    )
    custo_mao_obra_padrao = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        help_text='Custo de MO padrão por execução',
    )
    custo_indireto_padrao = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        help_text='Custos indiretos alocados (energia, depreciação etc.)',
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.RASCUNHO,
    )
    observacao = models.TextField(blank=True)

    class Meta:
        db_table = 'producao_fichas_tecnicas'
        ordering = ['produto_acabado', '-versao']
        unique_together = [('produto_acabado', 'versao', 'filial')]
        verbose_name = 'Ficha Técnica'
        verbose_name_plural = 'Fichas Técnicas'

    def __str__(self):
        return f'{self.produto_acabado} v{self.versao}'

    def calcular_custo_mp_total(self):
        """Soma do custo de matéria-prima baseado no custo médio atual."""
        total = sum(
            (item.quantidade * item.materia_prima.preco_custo_medio)
            for item in self.itens.select_related('materia_prima')
        )
        return total

    def custo_total_execucao(self):
        """Custo MP + MO + CIF."""
        return (
            self.calcular_custo_mp_total()
            + self.custo_mao_obra_padrao
            + self.custo_indireto_padrao
        )


class ItemFichaTecnica(TimestampedModel):
    """Matéria-prima consumida pela ficha técnica."""

    ficha = models.ForeignKey(
        FichaTecnica, on_delete=models.CASCADE, related_name='itens',
    )
    materia_prima = models.ForeignKey(
        'produtos.Produto', on_delete=models.PROTECT, related_name='+',
    )
    quantidade = models.DecimalField(
        max_digits=12, decimal_places=4,
        help_text='Quantidade consumida por execução completa da ficha',
    )
    perda_prevista = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text='% de perda esperada (ex: 5 = 5%)',
    )
    observacao = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'producao_itens_ficha_tecnica'
        ordering = ['ficha', 'materia_prima']
        unique_together = [('ficha', 'materia_prima')]

    def quantidade_com_perda(self):
        """Quantidade total a ser consumida incluindo perda prevista."""
        return self.quantidade * (1 + self.perda_prevista / 100)
