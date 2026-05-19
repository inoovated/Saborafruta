"""Auditoria: log de acesso e log de alterações."""
from django.db import models


class LogSistema(models.Model):
    """
    Auditoria de operações CRUD. Preenchido automaticamente pelo AuditMiddleware
    via signals post_save/post_delete.
    """

    class Acao(models.TextChoices):
        CRIAR = 'criar', 'Criar'
        EDITAR = 'editar', 'Editar'
        EXCLUIR = 'excluir', 'Excluir'
        CANCELAR = 'cancelar', 'Cancelar'
        APROVAR = 'aprovar', 'Aprovar'
        REJEITAR = 'rejeitar', 'Rejeitar'
        ACESSAR = 'acessar', 'Acessar'
        EXPORTAR = 'exportar', 'Exportar'

    filial = models.ForeignKey(
        'core.Filial', on_delete=models.SET_NULL, null=True, blank=True,
    )
    usuario = models.ForeignKey(
        'core.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
    )
    modulo = models.CharField(max_length=60)
    acao = models.CharField(max_length=30, choices=Acao.choices)
    tabela_afetada = models.CharField(max_length=60, blank=True)
    registro_id = models.BigIntegerField(null=True, blank=True)
    dados_anteriores = models.JSONField(null=True, blank=True)
    dados_novos = models.JSONField(null=True, blank=True)
    ip_acesso = models.GenericIPAddressField(null=True, blank=True)
    device_serial = models.CharField(max_length=255, blank=True)
    user_agent = models.TextField(blank=True)
    data_hora = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'log_sistema'
        ordering = ['-data_hora']
        indexes = [
            models.Index(fields=['tabela_afetada', 'registro_id']),
            models.Index(fields=['usuario', '-data_hora']),
        ]


class LogAcesso(models.Model):
    """Auditoria de login, logout, bloqueios e tentativas."""

    class Tipo(models.TextChoices):
        LOGIN = 'login', 'Login'
        LOGOUT = 'logout', 'Logout'
        SENHA_ERRADA = 'senha_errada', 'Senha Errada'
        BLOQUEIO = 'bloqueio', 'Bloqueio'
        PIN_PDV = 'pin_pdv', 'PIN PDV'

    usuario = models.ForeignKey('core.Usuario', on_delete=models.CASCADE)
    filial = models.ForeignKey(
        'core.Filial', on_delete=models.SET_NULL, null=True, blank=True,
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    ip_acesso = models.GenericIPAddressField(null=True, blank=True)
    device_serial = models.CharField(max_length=255, blank=True)
    user_agent = models.TextField(blank=True)
    sucesso = models.BooleanField()
    data_hora = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'log_acesso'
        ordering = ['-data_hora']
