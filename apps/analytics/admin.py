from django.contrib import admin
from apps.analytics.models import (
    ConfiguracaoSistema, ModuloAtivo, IntegracaoExterna,
    WebhookConfiguracao, WebhookLog, AutomacaoRegra,
    LogSistemaAnalytics, LogErro, LogAcessoAnalytics,
    HistoricoCustoProduto, HistoricoPrecoVenda, TravaPeriodo,
)


@admin.register(ConfiguracaoSistema)
class ConfigAdmin(admin.ModelAdmin):
    list_display = ["chave", "filial", "tipo_valor", "updated_at"]
    list_filter = ["filial", "tipo_valor"]
    search_fields = ["chave"]


@admin.register(ModuloAtivo)
class ModuloAdmin(admin.ModelAdmin):
    list_display = ["modulo", "filial", "ativo", "data_ativacao"]
    list_filter = ["filial", "ativo"]


@admin.register(IntegracaoExterna)
class IntegracaoAdmin(admin.ModelAdmin):
    list_display = ["nome", "tipo", "filial", "status", "ultima_conexao_sucesso"]
    list_filter = ["filial", "tipo", "status"]


@admin.register(WebhookConfiguracao)
class WebhookAdmin(admin.ModelAdmin):
    list_display = ["nome", "url_destino", "filial", "ativo"]


@admin.register(AutomacaoRegra)
class AutomacaoAdmin(admin.ModelAdmin):
    list_display = ["nome", "gatilho", "acao", "filial", "ativo"]
    list_filter = ["filial", "gatilho", "ativo"]


@admin.register(LogSistemaAnalytics)
class LogSistemaAnalyticsAdmin(admin.ModelAdmin):
    list_display = ["data_hora", "modulo", "acao", "tabela_afetada", "usuario"]
    list_filter = ["modulo", "acao"]
    date_hierarchy = "data_hora"


@admin.register(LogErro)
class LogErroAdmin(admin.ModelAdmin):
    list_display = ["data_hora", "modulo", "descricao_erro", "resolvido"]
    list_filter = ["modulo", "resolvido"]


@admin.register(LogAcessoAnalytics)
class LogAcessoAnalyticsAdmin(admin.ModelAdmin):
    list_display = ["data_hora", "usuario", "tipo", "sucesso", "ip_acesso"]
    list_filter = ["tipo", "sucesso"]


admin.site.register(WebhookLog)
admin.site.register(HistoricoCustoProduto)
admin.site.register(HistoricoPrecoVenda)
admin.site.register(TravaPeriodo)
