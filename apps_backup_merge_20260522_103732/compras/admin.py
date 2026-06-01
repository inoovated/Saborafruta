from django.contrib import admin

from apps.compras.models import (
    AvaliacaoFornecedor, EntradaNF, ItemEntradaNF, ItemPedidoCompra,
    PedidoCompra,
)


class ItemPedidoCompraInline(admin.TabularInline):
    model = ItemPedidoCompra
    extra = 0
    autocomplete_fields = ['produto']
    readonly_fields = ['valor_bruto', 'valor_total', 'quantidade_recebida']


@admin.register(PedidoCompra)
class PedidoCompraAdmin(admin.ModelAdmin):
    list_display = [
        'numero_pedido', 'data_emissao', 'fornecedor', 'usuario',
        'valor_total', 'status', 'filial',
    ]
    list_filter = ['status', 'filial']
    search_fields = ['numero_pedido', 'fornecedor__razao_social']
    autocomplete_fields = ['fornecedor', 'filial']
    readonly_fields = [
        'numero_pedido', 'valor_produtos', 'valor_total',
        'data_aprovacao', 'aprovado_por',
    ]
    inlines = [ItemPedidoCompraInline]
    date_hierarchy = 'data_emissao'


class ItemEntradaNFInline(admin.TabularInline):
    model = ItemEntradaNF
    extra = 0
    autocomplete_fields = ['produto']
    readonly_fields = ['valor_bruto', 'valor_total', 'lote_gerado']


@admin.register(EntradaNF)
class EntradaNFAdmin(admin.ModelAdmin):
    list_display = [
        'numero_nf', 'serie_nf', 'data_entrada', 'fornecedor',
        'valor_total', 'status', 'filial',
    ]
    list_filter = ['status', 'tipo', 'filial']
    search_fields = ['numero_nf', 'chave_acesso_nf', 'fornecedor__razao_social']
    autocomplete_fields = ['fornecedor', 'pedido_compra', 'filial']
    readonly_fields = [
        'valor_produtos', 'valor_total', 'usuario_efetivacao', 'data_efetivacao',
    ]
    inlines = [ItemEntradaNFInline]
    date_hierarchy = 'data_entrada'


@admin.register(AvaliacaoFornecedor)
class AvaliacaoFornecedorAdmin(admin.ModelAdmin):
    list_display = [
        'fornecedor', 'data_real', 'dias_atraso', 'entregue_no_prazo',
        'nota_pontualidade', 'nota_geral',
    ]
    list_filter = ['entregue_no_prazo', 'filial']
    search_fields = ['fornecedor__razao_social']
    readonly_fields = [
        'fornecedor', 'pedido_compra', 'entrada_nf',
        'data_prevista', 'data_real', 'dias_atraso', 'entregue_no_prazo',
    ]
    date_hierarchy = 'data_real'
