from django.urls import path
from apps.financeiro.views import financeiro

app_name = "financeiro"

urlpatterns = [
    path("receber/", financeiro.receber_list, name="receber_list"),
    path("pagar/", financeiro.pagar_list, name="pagar_list"),
    path("centros-custo/", financeiro.centros_custo, name="centros_custo"),
    path("plano-contas-despesas/", financeiro.plano_contas_despesas, name="plano_contas_despesas"),
    path("formas-pagamento/", financeiro.formas_pagamento, name="formas_pagamento"),
    path("documentos/", financeiro.documentos_fiscais_list, name="documentos"),
    path("dre/", financeiro.dre_view, name="dre"),
]
