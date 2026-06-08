from django.contrib import admin

from apps.logistica.models import (
    DocumentoManifestoCarga,
    ItemOrdemColeta,
    ItemRomaneioCarga,
    ManifestoCarga,
    OrdemColeta,
    RomaneioCarga,
)


class ItemRomaneioCargaInline(admin.TabularInline):
    model = ItemRomaneioCarga
    extra = 0


@admin.register(RomaneioCarga)
class RomaneioCargaAdmin(admin.ModelAdmin):
    list_display = ("numero", "filial", "data", "status", "motorista_nome", "veiculo_placa", "valor_total")
    list_filter = ("status", "data", "filial")
    search_fields = ("numero", "motorista_nome", "veiculo_placa", "destino_rota")
    inlines = [ItemRomaneioCargaInline]


@admin.register(ItemRomaneioCarga)
class ItemRomaneioCargaAdmin(admin.ModelAdmin):
    list_display = ("romaneio", "ordem", "cliente_nome", "status_entrega", "volumes", "peso_kg", "valor")
    list_filter = ("status_entrega",)
    search_fields = ("cliente_nome", "documento")


class ItemOrdemColetaInline(admin.TabularInline):
    model = ItemOrdemColeta
    extra = 0


@admin.register(OrdemColeta)
class OrdemColetaAdmin(admin.ModelAdmin):
    list_display = ("numero", "filial", "data_solicitacao", "data_coleta_prevista", "status", "solicitante_nome")
    list_filter = ("status", "tipo_solicitante", "data_solicitacao", "filial")
    search_fields = ("numero", "solicitante_nome", "contato_nome", "contato_telefone")
    inlines = [ItemOrdemColetaInline]


@admin.register(ItemOrdemColeta)
class ItemOrdemColetaAdmin(admin.ModelAdmin):
    list_display = ("ordem", "descricao", "quantidade", "unidade", "volumes", "peso_kg", "valor")
    search_fields = ("descricao",)


class DocumentoManifestoCargaInline(admin.TabularInline):
    model = DocumentoManifestoCarga
    extra = 0


@admin.register(ManifestoCarga)
class ManifestoCargaAdmin(admin.ModelAdmin):
    list_display = ("numero", "filial", "data_emissao", "status", "modal", "veiculo_placa", "valor_total")
    list_filter = ("status", "modal", "data_emissao", "filial")
    search_fields = ("numero", "motorista_nome", "veiculo_placa", "cidade_origem", "cidade_destino")
    inlines = [DocumentoManifestoCargaInline]


@admin.register(DocumentoManifestoCarga)
class DocumentoManifestoCargaAdmin(admin.ModelAdmin):
    list_display = ("manifesto", "tipo_documento", "numero_documento", "remetente_nome", "destinatario_nome", "valor")
    list_filter = ("tipo_documento",)
    search_fields = ("numero_documento", "chave_acesso", "remetente_nome", "destinatario_nome")
