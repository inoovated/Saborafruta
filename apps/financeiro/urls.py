from django.urls import path

from apps.financeiro.views import financeiro
from apps.financeiro.views import receber as receber_views
from apps.financeiro.views import pagar as pagar_views

app_name = "financeiro"

urlpatterns = [
    # ── Contas a Receber ──────────────────────────────────────────────────────
    path("receber/",                   receber_views.ContaReceberListView.as_view(),     name="receber_list"),
    path("receber/novo/",              receber_views.ContaReceberCreateView.as_view(),   name="receber_criar"),
    path("receber/<int:pk>/",          receber_views.ContaReceberDetailView.as_view(),   name="receber_detail"),
    path("receber/<int:pk>/baixar/",   receber_views.ContaReceberBaixaView.as_view(),    name="receber_baixar"),
    path("receber/<int:pk>/cancelar/", receber_views.ContaReceberCancelarView.as_view(), name="receber_cancelar"),

    # ── Contas a Pagar ────────────────────────────────────────────────────────
    path("pagar/",                    pagar_views.ContaPagarListView.as_view(),      name="pagar_list"),
    path("pagar/novo/",               pagar_views.ContaPagarCreateView.as_view(),    name="pagar_criar"),
    path("pagar/<int:pk>/",           pagar_views.ContaPagarDetailView.as_view(),    name="pagar_detail"),
    path("pagar/<int:pk>/pagar/",     pagar_views.ContaPagarPagamentoView.as_view(), name="pagar_pagar"),
    path("pagar/<int:pk>/cancelar/",  pagar_views.ContaPagarCancelarView.as_view(),  name="pagar_cancelar"),

    # ── Outros ───────────────────────────────────────────────────────────────
    path("documentos/",  financeiro.documentos_fiscais_list, name="documentos"),
    path("dre/",         financeiro.dre_view,               name="dre"),
]
