from django.db import models
from django.utils import timezone

from apps.core.models.base import ActiveModel, FilialScopedModel, TimestampedModel


DIAS_SEMANA_TODOS = '0,1,2,3,4,5,6'


class TipoDesconto(models.TextChoices):
    PRECO_UNITARIO = 'preco_unitario', 'Preco unitario'
    PERCENTUAL = 'percentual', 'Percentual'
    VALOR = 'valor', 'Valor em R$'
    PRECO_FINAL = 'preco_final', 'Preco final'


class CondicaoQuantidade(models.TextChoices):
    IGUAL = 'igual', 'Quantidade'
    A_PARTIR_DE = 'a_partir_de', 'A partir de'


class PromocaoQuantidade(FilialScopedModel, ActiveModel):
    produto = models.ForeignKey('produtos.Produto', on_delete=models.CASCADE, related_name='promocoes_quantidade')
    nome = models.CharField(max_length=120)
    id_externo = models.CharField(max_length=100, blank=True, default='', db_index=True)
    data_inicio = models.DateField(null=True, blank=True)
    data_fim = models.DateField(null=True, blank=True)
    dias_semana = models.CharField(max_length=13, default=DIAS_SEMANA_TODOS, blank=True)
    usar_preco_promocional = models.BooleanField(default=True)
    replicar_filiais = models.BooleanField(default=False)

    class Meta:
        db_table = 'promocoes_quantidade'
        ordering = ['produto__descricao', 'nome']
        indexes = [models.Index(fields=['filial', 'ativo']), models.Index(fields=['data_inicio', 'data_fim'])]

    def __str__(self):
        return self.nome

    @property
    def vigente(self):
        hoje = timezone.localdate()
        if not self.ativo:
            return False
        if self.data_inicio and self.data_inicio > hoje:
            return False
        if self.data_fim and self.data_fim < hoje:
            return False
        if str(hoje.weekday()) not in (self.dias_semana or DIAS_SEMANA_TODOS).split(','):
            return False
        return True


class PromocaoQuantidadeFaixa(TimestampedModel):
    promocao = models.ForeignKey(PromocaoQuantidade, on_delete=models.CASCADE, related_name='faixas')
    condicao_quantidade = models.CharField(max_length=20, choices=CondicaoQuantidade.choices, default=CondicaoQuantidade.IGUAL)
    quantidade_minima = models.DecimalField(max_digits=12, decimal_places=3)
    tipo_desconto = models.CharField(max_length=20, choices=TipoDesconto.choices, default=TipoDesconto.PRECO_UNITARIO)
    valor = models.DecimalField(max_digits=14, decimal_places=4)

    def aplica_para_quantidade(self, quantidade):
        if self.condicao_quantidade == CondicaoQuantidade.A_PARTIR_DE:
            return quantidade >= self.quantidade_minima
        return quantidade == self.quantidade_minima

    class Meta:
        db_table = 'promocoes_quantidade_faixas'
        ordering = ['quantidade_minima']
        unique_together = [('promocao', 'condicao_quantidade', 'quantidade_minima')]


class KitProduto(FilialScopedModel, ActiveModel):
    nome = models.CharField(max_length=120)
    id_externo = models.CharField(max_length=100, blank=True, default='', db_index=True)
    descricao = models.TextField(blank=True)
    tipo_desconto = models.CharField(max_length=20, choices=TipoDesconto.choices, default=TipoDesconto.PERCENTUAL)
    valor_desconto = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    data_inicio = models.DateField(null=True, blank=True)
    data_fim = models.DateField(null=True, blank=True)
    dias_semana = models.CharField(max_length=13, default=DIAS_SEMANA_TODOS, blank=True)
    replicar_filiais = models.BooleanField(default=False)
    permite_preco_promocional = models.BooleanField(default=False)

    class Meta:
        db_table = 'kits_produtos'
        ordering = ['nome']
        indexes = [models.Index(fields=['filial', 'ativo']), models.Index(fields=['data_inicio', 'data_fim'])]

    def __str__(self):
        return self.nome


class KitProdutoItem(TimestampedModel):
    kit = models.ForeignKey(KitProduto, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey('produtos.Produto', on_delete=models.PROTECT, related_name='kits_comerciais')
    quantidade = models.DecimalField(max_digits=12, decimal_places=3, default=1)

    class Meta:
        db_table = 'kits_produtos_itens'
        ordering = ['produto__descricao']
        unique_together = [('kit', 'produto')]


class BrindeProduto(FilialScopedModel, ActiveModel):
    nome = models.CharField(max_length=120)
    id_externo = models.CharField(max_length=100, blank=True, default='', db_index=True)
    descricao = models.TextField(blank=True)
    produto_gatilho = models.ForeignKey('produtos.Produto', on_delete=models.PROTECT, related_name='brindes_gatilho')
    quantidade_gatilho = models.DecimalField(max_digits=12, decimal_places=3, default=1)
    data_inicio = models.DateField(null=True, blank=True)
    data_fim = models.DateField(null=True, blank=True)
    dias_semana = models.CharField(max_length=13, default=DIAS_SEMANA_TODOS, blank=True)
    replicar_filiais = models.BooleanField(default=False)
    permite_preco_promocional = models.BooleanField(default=True)

    class Meta:
        db_table = 'brindes_produtos'
        ordering = ['nome']
        indexes = [models.Index(fields=['filial', 'ativo']), models.Index(fields=['data_inicio', 'data_fim'])]

    def __str__(self):
        return self.nome


class BrindeProdutoItem(TimestampedModel):
    brinde = models.ForeignKey(BrindeProduto, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey('produtos.Produto', on_delete=models.PROTECT, related_name='brindes_recebidos')
    quantidade = models.DecimalField(max_digits=12, decimal_places=3, default=1)

    class Meta:
        db_table = 'brindes_produtos_itens'
        ordering = ['produto__descricao']
        unique_together = [('brinde', 'produto')]


class KitCategoria(FilialScopedModel, ActiveModel):
    nome = models.CharField(max_length=120)
    id_externo = models.CharField(max_length=100, blank=True, default='', db_index=True)
    descricao = models.TextField(blank=True)
    tipo_desconto = models.CharField(max_length=20, choices=TipoDesconto.choices, default=TipoDesconto.PERCENTUAL)
    valor_desconto = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    data_inicio = models.DateField(null=True, blank=True)
    data_fim = models.DateField(null=True, blank=True)
    dias_semana = models.CharField(max_length=13, default=DIAS_SEMANA_TODOS, blank=True)
    replicar_filiais = models.BooleanField(default=False)
    permite_preco_promocional = models.BooleanField(default=False)

    class Meta:
        db_table = 'kits_categorias'
        ordering = ['nome']
        indexes = [models.Index(fields=['filial', 'ativo']), models.Index(fields=['data_inicio', 'data_fim'])]

    def __str__(self):
        return self.nome


class KitCategoriaRegra(TimestampedModel):
    kit = models.ForeignKey(KitCategoria, on_delete=models.CASCADE, related_name='regras')
    categoria = models.ForeignKey(
        'produtos.CategoriaProduto',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='kits_categoria',
    )
    subcategoria = models.ForeignKey(
        'produtos.CategoriaProduto',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='kits_subcategoria',
    )
    quantidade_minima = models.DecimalField(max_digits=12, decimal_places=3, default=1)
    tipo_desconto = models.CharField(max_length=20, choices=TipoDesconto.choices, default=TipoDesconto.PERCENTUAL)
    valor_desconto = models.DecimalField(max_digits=14, decimal_places=4, default=0)

    class Meta:
        db_table = 'kits_categorias_regras'
        ordering = ['categoria__nome', 'subcategoria__nome']
