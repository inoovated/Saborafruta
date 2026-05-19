from django.urls import path
from apps.financeiro.views import financeiro

app_name = "financeiro"

urlpatterns = [
    path("receber/", financeiro.receber_list, name="receber_list"),
    path("pagar/", financeiro.pagar_list, name="pagar_list"),
    path("documentos/", financeiro.documentos_fiscais_list, name="documentos"),
    path("dre/", financeiro.dre_view, name="dre"),
]
