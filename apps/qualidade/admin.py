from django.contrib import admin
from apps.qualidade.models import (
    AnaliseQualidade,
    ParametroQualidade,
    ParametroQualidadeCategoria,
    ParametroQualidadeProduto,
)


@admin.register(ParametroQualidade)
class ParametroAdmin(admin.ModelAdmin):
    list_display = ["nome_parametro", "linha_producao", "unidade_medida",
                    "valor_minimo", "valor_ideal", "valor_maximo", "obrigatorio"]
    list_filter = ["linha_producao", "obrigatorio"]


@admin.register(ParametroQualidadeProduto)
class ParametroProdutoAdmin(admin.ModelAdmin):
    list_display = [
        "filial",
        "produto",
        "etapa",
        "nome_parametro",
        "tipo_valor",
        "unidade_medida",
        "valor_minimo",
        "valor_ideal",
        "valor_maximo",
        "obrigatorio",
        "ativo",
    ]
    list_filter = ["filial", "etapa", "tipo_valor", "obrigatorio", "ativo"]
    search_fields = ["nome_parametro", "produto__descricao", "produto__codigo"]


@admin.register(ParametroQualidadeCategoria)
class ParametroCategoriaAdmin(admin.ModelAdmin):
    list_display = [
        "filial",
        "categoria",
        "etapa",
        "nome_parametro",
        "tipo_valor",
        "unidade_medida",
        "valor_minimo",
        "valor_ideal",
        "valor_maximo",
        "obrigatorio",
        "ativo",
    ]
    list_filter = ["filial", "categoria", "etapa", "tipo_valor", "obrigatorio", "ativo"]
    search_fields = ["nome_parametro", "categoria__nome"]


@admin.register(AnaliseQualidade)
class AnaliseAdmin(admin.ModelAdmin):
    list_display = ["id", "tipo_analise", "lote", "resultado",
                    "responsavel_tecnico", "data_analise"]
    list_filter = ["filial", "tipo_analise", "resultado"]
    date_hierarchy = "data_analise"
