"""Bloco 19 — Logs e auditoria."""
from django.db import models
from apps.core.models import Filial, Usuario
from apps.produtos.models import Produto


class LogSistemaAnalytics(models.Model):
    filial = models.ForeignKey(Filial, on_delete=models.SET_NULL, null=True, blank=True, related_name="analytics_logsistema_filial")
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="analytics_logsistema_usuario")
    modulo = models.CharField(max_length=60)
    acao = models.CharField(max_length=30)
    tabela_afetada = models.CharField(max_length=60, blank=True)
    registro_id = models.BigIntegerField(null=True, blank=True)
    dados_anteriores = models.JSONField(null=True, blank=True)
    dados_novos = models.JSONField(null=True, blank=True)
    ip_acesso = models.GenericIPAddressField(null=True, blank=True)
    device_serial = models.CharField(max_length=255, blank=True)
    user_agent = models.TextField(blank=True)
    data_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "analytics_log_sistema"
        verbose_name = "Log de sistema"
        verbose_name_plural = "Logs de sistema"
        ordering = ["-data_hora"]
        indexes = [
            models.Index(fields=["data_hora"]),
            models.Index(fields=["tabela_afetada", "registro_id"]),
        ]


class LogErro(models.Model):
    filial = models.ForeignKey(Filial, on_delete=models.SET_NULL, null=True, blank=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True)
    modulo = models.CharField(max_length=60, blank=True)
    descricao_erro = models.TextField()
    stack_trace = models.TextField(blank=True)
    request_data = models.JSONField(null=True, blank=True)
    ip_acesso = models.GenericIPAddressField(null=True, blank=True)
    resolvido = models.BooleanField(default=False)
    data_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "log_erros"
        verbose_name = "Log de erro"
        verbose_name_plural = "Logs de erro"
        ordering = ["-data_hora"]


class LogAcessoAnalytics(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name="analytics_acessos")
    filial = models.ForeignKey(Filial, on_delete=models.SET_NULL, null=True, blank=True, related_name="analytics_logacesso_filial")
    tipo = models.CharField(max_length=20, help_text="login|logout|senha_errada|bloqueio|pin_pdv")
    ip_acesso = models.GenericIPAddressField(null=True, blank=True)
    device_serial = models.CharField(max_length=255, blank=True)
    user_agent = models.TextField(blank=True)
    sucesso = models.BooleanField()
    data_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "analytics_log_acesso"
        verbose_name = "Log de acesso"
        verbose_name_plural = "Logs de acesso"
        ordering = ["-data_hora"]


class HistoricoCustoProduto(models.Model):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name="historico_custo")
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT)
    custo_anterior = models.DecimalField(max_digits=14, decimal_places=4)
    custo_novo = models.DecimalField(max_digits=14, decimal_places=4)
    custo_medio_anterior = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    custo_medio_novo = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    motivo = models.CharField(max_length=60, blank=True)
    documento_referencia_id = models.BigIntegerField(null=True, blank=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "historico_custo_produto"
        ordering = ["-created_at"]


class HistoricoPrecoVenda(models.Model):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name="historico_preco")
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT)
    preco_anterior = models.DecimalField(max_digits=14, decimal_places=4)
    preco_novo = models.DecimalField(max_digits=14, decimal_places=4)
    motivo = models.TextField(blank=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "historico_preco_venda"
        ordering = ["-created_at"]


class TravaPeriodo(models.Model):
    filial = models.ForeignKey(Filial, on_delete=models.CASCADE, related_name="travas_periodo")
    data_inicio = models.DateField()
    data_fim = models.DateField()
    motivo = models.TextField(blank=True)
    modulos_travados = models.JSONField(
        default=list,
        help_text='["financeiro","fiscal","estoque","producao"]',
    )
    criado_por = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "trava_periodos"
        verbose_name = "Trava de período"
        verbose_name_plural = "Travas de período"
        ordering = ["-data_inicio"]
