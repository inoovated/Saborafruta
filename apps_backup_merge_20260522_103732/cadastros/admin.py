from django.contrib import admin

from apps.cadastros.models import (
    Cliente, ClienteEndereco, ClienteFilial, Fornecedor, FornecedorFilial,
    Representante, RepresentanteFilial, Transportadora, TransportadoraFilial,
    VeiculoTransportadora,
)


class ClienteEnderecoInline(admin.TabularInline):
    model = ClienteEndereco
    extra = 0


class ClienteFilialInline(admin.TabularInline):
    model = ClienteFilial
    extra = 0
    autocomplete_fields = ['filial']


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['razao_social', 'nome_fantasia', 'cpf_cnpj', 'tipo', 'filial', 'ativo']
    list_filter = ['ativo', 'tipo', 'tipo_pessoa', 'uf', 'filial']
    search_fields = ['razao_social', 'nome_fantasia', 'cpf_cnpj', 'email']
    autocomplete_fields = ['filial']
    inlines = [ClienteFilialInline, ClienteEnderecoInline]


class FornecedorFilialInline(admin.TabularInline):
    model = FornecedorFilial
    extra = 0
    autocomplete_fields = ['filial']


@admin.register(Fornecedor)
class FornecedorAdmin(admin.ModelAdmin):
    list_display = ['razao_social', 'nome_fantasia', 'cpf_cnpj', 'filial', 'nota_qualidade', 'ativo']
    list_filter = ['ativo', 'tipo_pessoa', 'uf', 'filial']
    search_fields = ['razao_social', 'nome_fantasia', 'cpf_cnpj']
    readonly_fields = ['nota_qualidade', 'total_entregas', 'entregas_no_prazo']
    inlines = [FornecedorFilialInline]


class VeiculoInline(admin.TabularInline):
    model = VeiculoTransportadora
    extra = 0


class TransportadoraFilialInline(admin.TabularInline):
    model = TransportadoraFilial
    extra = 0
    autocomplete_fields = ['filial']


@admin.register(Transportadora)
class TransportadoraAdmin(admin.ModelAdmin):
    list_display = ['razao_social', 'cnpj', 'rntrc', 'cidade', 'uf', 'ativo']
    list_filter = ['ativo', 'uf', 'filial']
    search_fields = ['razao_social', 'cnpj', 'rntrc']
    inlines = [TransportadoraFilialInline, VeiculoInline]


class RepresentanteFilialInline(admin.TabularInline):
    model = RepresentanteFilial
    extra = 0
    autocomplete_fields = ['filial']


@admin.register(Representante)
class RepresentanteAdmin(admin.ModelAdmin):
    list_display = ['nome', 'cpf', 'regiao_atuacao', 'comissao_percentual', 'ativo']
    list_filter = ['ativo', 'filial']
    search_fields = ['nome', 'cpf']
    autocomplete_fields = ['usuario']
    inlines = [RepresentanteFilialInline]
