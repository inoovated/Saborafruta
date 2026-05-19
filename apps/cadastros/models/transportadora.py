"""Transportadora, Veículo e Representante."""
from django.db import models

from apps.core.constants.choices import UF
from apps.core.models.base import FilialManager, FilialScopedModel, TimestampedModel


class CadastroFilialManager(FilialManager):
    def for_filial(self, filial):
        if filial is None:
            return self.get_queryset().none()
        return self.get_queryset().filter(filiais_vinculo__filial=filial, filiais_vinculo__ativo=True).distinct()

    def for_empresa(self, empresa):
        if empresa is None:
            return self.get_queryset().none()
        return self.get_queryset().filter(filiais_vinculo__filial__empresa=empresa, filiais_vinculo__ativo=True).distinct()


class Transportadora(FilialScopedModel):
    razao_social = models.CharField(max_length=150)
    nome_fantasia = models.CharField(max_length=100, blank=True)
    cnpj = models.CharField(max_length=14, blank=True, db_index=True)
    inscricao_estadual = models.CharField(max_length=20, blank=True)
    rntrc = models.CharField(
        max_length=20, blank=True,
        help_text='Registro ANTT obrigatório para transporte de carga',
    )

    endereco = models.CharField(max_length=255, blank=True)
    numero = models.CharField(max_length=10, blank=True)
    bairro = models.CharField(max_length=80, blank=True)
    cidade = models.CharField(max_length=80, blank=True)
    uf = models.CharField(max_length=2, choices=UF.choices, blank=True)
    cep = models.CharField(max_length=8, blank=True)
    codigo_municipio_ibge = models.CharField(max_length=7, blank=True)

    telefone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(max_length=120, blank=True)
    ativo = models.BooleanField(default=True, db_index=True)

    objects = CadastroFilialManager()

    class Meta:
        db_table = 'transportadoras'
        ordering = ['razao_social']
        verbose_name = 'Transportadora'

    def __str__(self):
        return self.nome_fantasia or self.razao_social


class TransportadoraFilial(TimestampedModel):
    transportadora = models.ForeignKey(Transportadora, on_delete=models.CASCADE, related_name='filiais_vinculo')
    filial = models.ForeignKey('core.Filial', on_delete=models.CASCADE, related_name='transportadoras_vinculadas')
    ativo = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = 'transportadoras_filiais'
        ordering = ['transportadora', 'filial']
        unique_together = [('transportadora', 'filial')]
        indexes = [
            models.Index(fields=['filial', 'ativo']),
            models.Index(fields=['transportadora', 'ativo']),
        ]

    def __str__(self):
        return f'{self.transportadora} - {self.filial}'


class VeiculoTransportadora(TimestampedModel):
    class TipoRodado(models.TextChoices):
        TRUCK = 'Truck', 'Truck'
        TOCO = 'Toco', 'Toco'
        CARRETA = 'Carreta', 'Carreta'
        VUC = 'VUC', 'VUC'
        FURGAO = 'Furgão', 'Furgão'

    class TipoCarroceria(models.TextChoices):
        ABERTA = 'Aberta', 'Aberta'
        FECHADA = 'Fechada', 'Fechada'
        GRANELEIRA = 'Graneleira', 'Graneleira'
        PORTA_CONTAINER = 'Porta-container', 'Porta-container'
        SIDER = 'Sider', 'Sider'

    transportadora = models.ForeignKey(
        Transportadora, on_delete=models.CASCADE, related_name='veiculos',
    )
    descricao = models.CharField(max_length=100, blank=True)
    placa = models.CharField(max_length=8)
    uf_placa = models.CharField(max_length=2, choices=UF.choices, blank=True)
    rntrc = models.CharField(max_length=20, blank=True)
    tara = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    capacidade_kg = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    capacidade_m3 = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    tipo_rodado = models.CharField(max_length=20, choices=TipoRodado.choices, blank=True)
    tipo_carroceria = models.CharField(max_length=20, choices=TipoCarroceria.choices, blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        db_table = 'veiculos_transportadora'
        ordering = ['transportadora', 'placa']

    def __str__(self):
        return f'{self.placa} ({self.transportadora})'


class Representante(FilialScopedModel):
    nome = models.CharField(max_length=120)
    cpf = models.CharField(max_length=11, blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    celular = models.CharField(max_length=20, blank=True)
    email = models.EmailField(max_length=120, blank=True)
    comissao_percentual = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    regiao_atuacao = models.CharField(max_length=100, blank=True)
    meta_mensal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    usuario = models.ForeignKey(
        'core.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', help_text='Se o representante também é usuário do sistema',
    )
    ativo = models.BooleanField(default=True, db_index=True)

    objects = CadastroFilialManager()

    class Meta:
        db_table = 'representantes'
        ordering = ['nome']
        verbose_name = 'Representante'

    def __str__(self):
        return self.nome


class RepresentanteFilial(TimestampedModel):
    representante = models.ForeignKey(Representante, on_delete=models.CASCADE, related_name='filiais_vinculo')
    filial = models.ForeignKey('core.Filial', on_delete=models.CASCADE, related_name='representantes_vinculados')
    ativo = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = 'representantes_filiais'
        ordering = ['representante', 'filial']
        unique_together = [('representante', 'filial')]
        indexes = [
            models.Index(fields=['filial', 'ativo']),
            models.Index(fields=['representante', 'ativo']),
        ]

    def __str__(self):
        return f'{self.representante} - {self.filial}'
