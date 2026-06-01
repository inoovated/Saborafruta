"""Marcas / fabricantes de produtos vinculados por filial."""
from django.db import models

from apps.core.models.base import FilialManager, TimestampedModel


class MarcaProdutoManager(FilialManager):
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


class MarcaProduto(TimestampedModel):
    empresa = models.ForeignKey(
        'core.Empresa', on_delete=models.CASCADE, related_name='marcas_produto',
    )
    filial = models.ForeignKey(
        'core.Filial', on_delete=models.PROTECT, null=True, blank=True,
        related_name='marcas_produto',
        help_text='Filial proprietaria da marca / fabricante',
    )
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    id_externo = models.CharField(max_length=100, blank=True, db_index=True)
    ativo = models.BooleanField(default=True, db_index=True)

    objects = MarcaProdutoManager()

    class Meta:
        db_table = 'marcas_produto'
        ordering = ['nome']
        unique_together = [('empresa', 'filial', 'nome')]
        indexes = [
            models.Index(fields=['empresa', 'filial', 'ativo']),
            models.Index(fields=['empresa', 'filial', 'nome']),
        ]
        verbose_name = 'Marca / Fabricante'
        verbose_name_plural = 'Marcas / Fabricantes'

    def __str__(self):
        return self.nome


class MarcaProdutoFilial(TimestampedModel):
    marca = models.ForeignKey(
        MarcaProduto, on_delete=models.CASCADE, related_name='filiais_vinculo',
    )
    filial = models.ForeignKey(
        'core.Filial', on_delete=models.CASCADE, related_name='marcas_produto_vinculadas',
    )
    ativo = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = 'marcas_produto_filiais'
        ordering = ['marca', 'filial']
        unique_together = [('marca', 'filial')]
        indexes = [
            models.Index(fields=['filial', 'ativo']),
            models.Index(fields=['marca', 'ativo']),
        ]

    def __str__(self):
        return f'{self.marca} - {self.filial}'
