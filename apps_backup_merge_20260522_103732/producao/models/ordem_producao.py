"""
Ordem de Produção (OP) com máquina de estados:
    rascunho → aberta → em_producao → encerrada
                              ↓
                          cancelada

Ao encerrar, a OP:
  1. Consome matéria-prima do estoque (baseado em BOM)
  2. Gera lote de produto acabado
  3. Calcula rendimento e dispara alerta se <80%
  4. Registra perdas
  5. Calcula custo real do lote
"""
from django.db import models

from apps.core.models.base import FilialScopedModel, TimestampedModel


class OrdemProducao(FilialScopedModel):
    """Ordem de produção vinculada a uma ficha técnica."""

    class Status(models.TextChoices):
        RASCUNHO = 'rascunho', 'Rascunho'
        ABERTA = 'aberta', 'Aberta'
        EM_PRODUCAO = 'em_producao', 'Em Produção'
        ENCERRADA = 'encerrada', 'Encerrada'
        CANCELADA = 'cancelada', 'Cancelada'

    numero = models.CharField(max_length=20, db_index=True)
    ficha_tecnica = models.ForeignKey(
        'producao.FichaTecnica', on_delete=models.PROTECT, related_name='ordens',
    )
    produto_acabado = models.ForeignKey(
        'produtos.Produto', on_delete=models.PROTECT, related_name='ordens_producao',
    )
    quantidade_planejada = models.DecimalField(
        max_digits=12, decimal_places=3,
        help_text='Quantidade de produto acabado prevista',
    )
    quantidade_produzida = models.DecimalField(
        max_digits=12, decimal_places=3, default=0,
        help_text='Quantidade efetivamente gerada (informada no encerramento)',
    )

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.RASCUNHO, db_index=True,
    )

    # Planejamento
    data_inicio_prevista = models.DateTimeField(null=True, blank=True)
    data_fim_prevista = models.DateTimeField(null=True, blank=True)
    data_inicio_real = models.DateTimeField(null=True, blank=True)
    data_fim_real = models.DateTimeField(null=True, blank=True)

    # Resultado
    rendimento = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text='% de rendimento (produzida / planejada) * 100',
    )
    peso_entrada_mp = models.DecimalField(
        max_digits=12, decimal_places=3, default=0,
        help_text='Peso total de matéria-prima consumida',
    )
    peso_saida_produzido = models.DecimalField(
        max_digits=12, decimal_places=3, default=0,
        help_text='Peso total do produto acabado gerado',
    )

    # Custos calculados no encerramento
    custo_materia_prima = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    custo_mao_obra = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    custo_indireto = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    custo_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    custo_unitario_lote = models.DecimalField(max_digits=14, decimal_places=4, default=0)

    # Lote gerado ao encerrar
    lote_gerado = models.ForeignKey(
        'estoque.LoteProduto', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ordens_origem',
    )

    # Rastreabilidade de usuários
    usuario_abertura = models.ForeignKey(
        'core.Usuario', on_delete=models.PROTECT, related_name='ops_abertas',
    )
    usuario_encerramento = models.ForeignKey(
        'core.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ops_encerradas',
    )
    observacao = models.TextField(blank=True)

    class Meta:
        db_table = 'ordens_producao'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['filial', 'status']),
            models.Index(fields=['produto_acabado', 'status']),
        ]
        verbose_name = 'Ordem de Produção'
        verbose_name_plural = 'Ordens de Produção'

    def __str__(self):
        return f'OP {self.numero} — {self.produto_acabado} ({self.get_status_display()})'

    @property
    def pode_abrir(self):
        return self.status == self.Status.RASCUNHO

    @property
    def pode_iniciar(self):
        return self.status == self.Status.ABERTA

    @property
    def pode_encerrar(self):
        return self.status == self.Status.EM_PRODUCAO

    @property
    def pode_cancelar(self):
        return self.status in (self.Status.RASCUNHO, self.Status.ABERTA)

