"""Modelos de Praça e Rota para logística."""
from django.db import models

from apps.core.constants.choices import UF
from apps.core.models.base import FilialScopedModel


class Praca(FilialScopedModel):
    """
    Praça de atendimento — agrupa cidades/regiões para fins de precificação e roteamento.
    """
    nome = models.CharField(max_length=100)
    codigo = models.CharField(max_length=20, blank=True, help_text='Código interno da praça')
    uf = models.CharField(max_length=2, choices=UF.choices, blank=True)
    cidades = models.TextField(
        blank=True,
        help_text='Lista de cidades separadas por vírgula (ex: São Paulo, Guarulhos, Osasco)',
    )
    observacao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = 'cadastros_pracas'
        ordering = ['nome']
        verbose_name = 'Praça'
        verbose_name_plural = 'Praças'

    def __str__(self):
        if self.codigo:
            return f'{self.codigo} — {self.nome}'
        return self.nome

    @property
    def lista_cidades(self):
        """Retorna a lista de cidades como uma lista Python."""
        if not self.cidades:
            return []
        return [c.strip() for c in self.cidades.split(',') if c.strip()]


class Rota(FilialScopedModel):
    """
    Rota de entrega — agrupa praças e define o circuito de coletas/entregas.
    """
    nome = models.CharField(max_length=100)
    codigo = models.CharField(max_length=20, blank=True, help_text='Código interno da rota')
    descricao = models.TextField(blank=True)
    pracas = models.ManyToManyField(
        Praca,
        blank=True,
        related_name='rotas',
        verbose_name='Praças da rota',
    )
    motorista_padrao = models.CharField(max_length=100, blank=True, help_text='Nome do motorista padrão')
    veiculo_padrao = models.CharField(max_length=20, blank=True, help_text='Placa do veículo padrão')
    ativo = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = 'cadastros_rotas'
        ordering = ['nome']
        verbose_name = 'Rota'
        verbose_name_plural = 'Rotas'

    def __str__(self):
        if self.codigo:
            return f'{self.codigo} — {self.nome}'
        return self.nome
