"""Bloco 18 — Configurações e automações."""
from django.db import models
from apps.core.models import Filial, Usuario
from apps.core.models.base import ActiveModel, TimestampedModel


class ConfiguracaoSistema(models.Model):
    filial = models.ForeignKey(Filial, on_delete=models.CASCADE, related_name="configuracoes")
    chave = models.CharField(max_length=100)
    valor = models.TextField(blank=True)
    tipo_valor = models.CharField(max_length=20, default="string",
                                   help_text="string|boolean|integer|decimal|json")
    descricao = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "configuracoes_sistema"
        unique_together = [("filial", "chave")]


class ModuloAtivo(models.Model):
    filial = models.ForeignKey(Filial, on_delete=models.CASCADE, related_name="modulos_ativos")
    modulo = models.CharField(max_length=60)
    ativo = models.BooleanField(default=False)
    data_ativacao = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "modulos_ativos"
        unique_together = [("filial", "modulo")]


class IntegracaoExterna(TimestampedModel, ActiveModel):
    filial = models.ForeignKey(Filial, on_delete=models.CASCADE, related_name="integracoes")
    nome = models.CharField(max_length=60)
    tipo = models.CharField(max_length=30, blank=True)
    endpoint_base = models.URLField(max_length=255, blank=True)
    client_id = models.CharField(max_length=200, blank=True)
    client_secret_encrypted = models.CharField(max_length=500, blank=True)
    access_token_encrypted = models.CharField(max_length=1000, blank=True)
    refresh_token_encrypted = models.CharField(max_length=1000, blank=True)
    token_expira_em = models.DateTimeField(null=True, blank=True)
    configuracoes_extras = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, default="ativo")
    ultima_conexao_sucesso = models.DateTimeField(null=True, blank=True)
    ultima_conexao_erro = models.DateTimeField(null=True, blank=True)
    mensagem_ultimo_erro = models.TextField(blank=True)

    class Meta:
        db_table = "integracoes_externas"
        verbose_name = "Integração externa"
        verbose_name_plural = "Integrações externas"


class WebhookConfiguracao(ActiveModel):
    filial = models.ForeignKey(Filial, on_delete=models.CASCADE, related_name="webhooks")
    nome = models.CharField(max_length=80)
    url_destino = models.URLField(max_length=500)
    secret_hash = models.CharField(max_length=255, blank=True)
    eventos = models.JSONField(
        help_text='["venda.finalizada","nfe.autorizada","estoque.minimo","op.encerrada"]',
    )
    headers_extras = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "webhooks_configuracao"
        verbose_name = "Webhook"
        verbose_name_plural = "Webhooks"


class WebhookLog(models.Model):
    webhook = models.ForeignKey(WebhookConfiguracao, on_delete=models.CASCADE, related_name="logs")
    evento = models.CharField(max_length=60)
    payload_enviado = models.JSONField(null=True, blank=True)
    codigo_http_resposta = models.PositiveSmallIntegerField(null=True, blank=True)
    resposta = models.TextField(blank=True)
    sucesso = models.BooleanField()
    tentativa = models.PositiveSmallIntegerField(default=1)
    proximo_retry_em = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "webhooks_log"
        ordering = ["-created_at"]


class AutomacaoRegra(ActiveModel):
    filial = models.ForeignKey(Filial, on_delete=models.CASCADE, related_name="automacoes")
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    gatilho = models.CharField(
        max_length=60,
        help_text="estoque.minimo|nfe.autorizada|venda.finalizada|boleto.vencido|"
                  "validade.proximo|op.encerrada|rendimento.baixo|perda.excessiva",
    )
    condicoes = models.JSONField(default=dict, blank=True)
    acao = models.CharField(
        max_length=60,
        help_text="gerar_pedido_compra|baixar_conta_receber|enviar_webhook|enviar_email|"
                  "bloquear_cliente|criar_ordem_producao|bloquear_lote",
    )
    parametros_acao = models.JSONField(default=dict, blank=True)
    ultima_execucao = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "automacoes_regras"
        verbose_name = "Regra de automação"
        verbose_name_plural = "Regras de automação"
