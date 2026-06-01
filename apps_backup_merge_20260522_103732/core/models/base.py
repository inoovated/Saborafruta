"""
Modelos base: timestamps, manager com escopo de filial e abstract model para isolamento multi-filial.
"""
from django.db import models


class TimestampedModel(models.Model):
    """Adiciona campos de auditoria temporal em todos os registros."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class FilialManager(models.Manager):
    """
    Manager que filtra automaticamente registros pela filial ativa da request.

    Uso:
        class Produto(FilialScopedModel):
            objects = FilialManager()
            all_objects = models.Manager()  # Sem filtro (para admin/matriz)
    """

    def for_filial(self, filial):
        """Retorna apenas registros da filial informada."""
        if filial is None:
            return self.get_queryset().none()
        return self.get_queryset().filter(filial=filial)

    def for_empresa(self, empresa):
        """Para perfil matriz: registros de todas as filiais da empresa."""
        if empresa is None:
            return self.get_queryset().none()
        return self.get_queryset().filter(filial__empresa=empresa)


class FilialScopedModel(TimestampedModel):
    """
    Model base para TODAS as tabelas operacionais (produtos, estoque, vendas, etc).

    Garante:
    - Campo filial (FK obrigatório)
    - Manager customizado com métodos de filtro
    - Índice em filial para performance
    """

    filial = models.ForeignKey(
        'core.Filial',
        on_delete=models.PROTECT,
        db_index=True,
        related_name='+',
        help_text='Filial proprietária do registro',
    )

    objects = FilialManager()

    class Meta:
        abstract = True

class ActiveModel(models.Model):
    """Mixin que adiciona campo ativo para soft-delete."""
    ativo = models.BooleanField(default=True, verbose_name='Ativo')

    class Meta:
        abstract = True
