from django.contrib import admin

from apps.producao.models import (
    FichaTecnica, ItemFichaTecnica, OrdemProducao, PerdaProducao,
)


class ItemFichaTecnicaInline(admin.TabularInline):
    model = ItemFichaTecnica
    extra = 1
    autocomplete_fields = ['materia_prima']


@admin.register(FichaTecnica)
class FichaTecnicaAdmin(admin.ModelAdmin):
    list_display = [
        'codigo', 'descricao', 'produto_acabado', 'versao',
        'quantidade_produzida', 'status', 'filial',
    ]
    list_filter = ['status', 'filial']
    search_fields = ['codigo', 'descricao', 'produto_acabado__descricao']
    autocomplete_fields = ['produto_acabado', 'filial']
    inlines = [ItemFichaTecnicaInline]


class PerdaProducaoInline(admin.TabularInline):
    model = PerdaProducao
    extra = 0
    autocomplete_fields = ['produto']
    readonly_fields = ['impacto_custo', 'created_at']


@admin.register(OrdemProducao)
class OrdemProducaoAdmin(admin.ModelAdmin):
    list_display = [
        'numero', 'produto_acabado', 'quantidade_planejada',
        'quantidade_produzida', 'rendimento', 'status', 'filial',
    ]
    list_filter = ['status', 'filial']
    search_fields = ['numero', 'produto_acabado__descricao']
    autocomplete_fields = ['ficha_tecnica', 'produto_acabado', 'filial', 'lote_gerado']
    readonly_fields = [
        'numero', 'quantidade_produzida', 'rendimento',
        'peso_entrada_mp', 'peso_saida_produzido',
        'custo_materia_prima', 'custo_mao_obra', 'custo_indireto',
        'custo_total', 'custo_unitario_lote',
        'data_inicio_real', 'data_fim_real',
        'usuario_encerramento', 'lote_gerado',
    ]
    inlines = [PerdaProducaoInline]

    fieldsets = (
        ('Identificação', {
            'fields': ('filial', 'numero', 'ficha_tecnica', 'produto_acabado', 'status'),
        }),
        ('Planejamento', {
            'fields': ('quantidade_planejada', 'data_inicio_prevista', 'data_fim_prevista',
                       'data_inicio_real', 'data_fim_real', 'usuario_abertura',
                       'usuario_encerramento'),
        }),
        ('Resultado', {
            'fields': ('quantidade_produzida', 'rendimento', 'peso_entrada_mp',
                       'peso_saida_produzido', 'lote_gerado'),
        }),
        ('Custos', {
            'fields': ('custo_materia_prima', 'custo_mao_obra', 'custo_indireto',
                       'custo_total', 'custo_unitario_lote'),
        }),
        ('Observação', {'fields': ('observacao',)}),
    )
