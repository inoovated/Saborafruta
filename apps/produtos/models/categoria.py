"""Categoria de produto hierárquica."""
from django.db import models

from apps.core.models.base import FilialManager, TimestampedModel


class CategoriaProdutoManager(FilialManager):
    def for_filial(self, filial):
        if filial is None:
            return self.get_queryset().none()
        return self.get_queryset().filter(
            filiais_vinculo__filial=filial,
            filiais_vinculo__ativo=True,
        ).distinct()

    def for_empresa(self, empresa):
        if empresa is None:
            return self.get_queryset().none()
        return self.get_queryset().filter(
            filiais_vinculo__filial__empresa=empresa,
            filiais_vinculo__ativo=True,
        ).distinct()


class CategoriaProduto(TimestampedModel):
    """Categoria de produto com subcategorias (árvore infinita)."""

    empresa = models.ForeignKey(
        'core.Empresa', on_delete=models.CASCADE, related_name='categorias_produto',
    )
    filial = models.ForeignKey(
        'core.Filial', on_delete=models.PROTECT, null=True, blank=True,
        related_name='categorias_produto',
        help_text='Filial proprietaria da categoria',
    )
    categoria_pai = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='subcategorias', help_text='Categoria pai (opcional)',
    )
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    id_externo = models.CharField(max_length=100, blank=True, db_index=True)
    ativo = models.BooleanField(default=True, db_index=True)

    objects = CategoriaProdutoManager()

    class Meta:
        db_table = 'categorias_produto'
        ordering = ['nome']
        unique_together = [('empresa', 'filial', 'categoria_pai', 'nome')]
        indexes = [
            models.Index(fields=['empresa', 'filial', 'ativo']),
            models.Index(fields=['empresa', 'filial', 'categoria_pai']),
        ]
        verbose_name = 'Categoria de Produto'
        verbose_name_plural = 'Categorias de Produto'

    def __str__(self):
        if self.categoria_pai:
            return f'{self.categoria_pai} / {self.nome}'
        return self.nome

    def full_path(self):
        """Retorna caminho completo da árvore."""
        nodes = [self.nome]
        parent = self.categoria_pai
        while parent:
            nodes.insert(0, parent.nome)
            parent = parent.categoria_pai
        return ' / '.join(nodes)


class CategoriaProdutoFilial(TimestampedModel):
    categoria = models.ForeignKey(
        CategoriaProduto, on_delete=models.CASCADE, related_name='filiais_vinculo',
    )
    filial = models.ForeignKey(
        'core.Filial', on_delete=models.CASCADE, related_name='categorias_produto_vinculadas',
    )
    ativo = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = 'categorias_produto_filiais'
        ordering = ['categoria', 'filial']
        unique_together = [('categoria', 'filial')]
        indexes = [
            models.Index(fields=['filial', 'ativo']),
            models.Index(fields=['categoria', 'ativo']),
        ]

    def __str__(self):
        return f'{self.categoria} - {self.filial}'
