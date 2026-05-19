"""Bloco 16 — Sessões e movimentações de caixa."""
from django.db import models
from apps.core.models import Filial, Usuario
from apps.core.models.base import FilialManager as FilialAwareManager
from .caixa import Caixa
from apps.financeiro.constants.enums import TipoMovimentacaoCaixa


class SessaoPDV(models.Model):
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name="sessoes_pdv")
    caixa = models.ForeignKey(Caixa, on_delete=models.PROTECT, related_name="sessoes")
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name="sessoes_pdv")
    device_serial = models.CharField(max_length=255, blank=True)
    data_abertura = models.DateTimeField(auto_now_add=True)
    valor_abertura = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    data_fechamento = models.DateTimeField(null=True, blank=True)
    valor_fechamento_informado = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    valor_fechamento_sistema = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    diferenca_caixa = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    contagem_cedulas = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, default="aberto")
    conferido_por = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sessoes_conferidas",
    )
    conferido_em = models.DateTimeField(null=True, blank=True)
    observacao_conferencia = models.TextField(blank=True)
    comprovante_fechamento_url = models.URLField(max_length=500, blank=True)
    total_vendas = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_cancelamentos = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_sangrias = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_suprimentos = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    observacao = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = FilialAwareManager()

    class Meta:
        db_table = "sessoes_pdv"
        verbose_name = "Sessão PDV"
        verbose_name_plural = "Sessões PDV"
        ordering = ["-data_abertura"]

    def __str__(self):
        return f"Sessão {self.id} – {self.caixa} – {self.usuario}"


class MovimentacaoCaixa(models.Model):
    sessao_pdv = models.ForeignKey(SessaoPDV, on_delete=models.CASCADE, related_name="movimentacoes")
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT)
    tipo = models.CharField(max_length=30, choices=TipoMovimentacaoCaixa.choices)
    valor = models.DecimalField(max_digits=14, decimal_places=2)
    forma_pagamento = models.ForeignKey(
        "financeiro.FormaPagamento", on_delete=models.SET_NULL, null=True, blank=True,
    )
    documento_referencia_tipo = models.CharField(max_length=20, blank=True)
    documento_referencia_id = models.BigIntegerField(null=True, blank=True)
    requer_autorizacao = models.BooleanField(default=False)
    autorizado_por = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="mov_caixa_autorizadas",
    )
    autorizado_em = models.DateTimeField(null=True, blank=True)
    observacao = models.CharField(max_length=200, blank=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    data_movimentacao = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "movimentacoes_caixa"
        verbose_name = "Movimentação de caixa"
        verbose_name_plural = "Movimentações de caixa"
        ordering = ["-data_movimentacao"]
