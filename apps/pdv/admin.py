from django.contrib import admin
from apps.pdv.models import (
    Caixa, DispositivoPDV, ImpressoraConfig, ImpressaoLog,
    SessaoPDV, MovimentacaoCaixa,
    VendaPDV, ItemVendaPDV, PagamentoVendaPDV, PesagemPDV,
    DevolucaoPDV, ItemDevolucaoPDV, PDVCache,
)


@admin.register(Caixa)
class CaixaAdmin(admin.ModelAdmin):
    list_display = ["numero", "descricao", "filial", "ativo"]


@admin.register(DispositivoPDV)
class DispositivoAdmin(admin.ModelAdmin):
    list_display = ["tipo", "marca", "modelo", "numero_serie", "filial", "ativo"]
    list_filter = ["filial", "tipo"]


class MovCaixaInline(admin.TabularInline):
    model = MovimentacaoCaixa
    extra = 0


@admin.register(SessaoPDV)
class SessaoAdmin(admin.ModelAdmin):
    list_display = ["id", "caixa", "usuario", "data_abertura",
                    "data_fechamento", "status", "total_vendas"]
    list_filter = ["status", "filial"]
    inlines = [MovCaixaInline]
    date_hierarchy = "data_abertura"


class ItemVendaInline(admin.TabularInline):
    model = ItemVendaPDV
    extra = 0


class PagamentoVendaInline(admin.TabularInline):
    model = PagamentoVendaPDV
    extra = 0


@admin.register(VendaPDV)
class VendaPDVAdmin(admin.ModelAdmin):
    list_display = ["numero_venda", "cliente", "valor_total", "status", "data_venda"]
    list_filter = ["filial", "status"]
    inlines = [ItemVendaInline, PagamentoVendaInline]
    date_hierarchy = "data_venda"


admin.site.register(PesagemPDV)
admin.site.register(DevolucaoPDV)
admin.site.register(ItemDevolucaoPDV)
admin.site.register(ImpressoraConfig)
admin.site.register(ImpressaoLog)
admin.site.register(PDVCache)
