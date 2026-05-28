from django.urls import path

from apps.financeiro.views import financeiro
from apps.financeiro.views import receber as receber_views

app_name = "financeiro"

urlpatterns = [
    # ── Contas a Receber ──────────────────────────────────────────────────────
    path("receber/",                   receber_views.ContaReceberListView.as_view(),     name="receber_list"),
    path("receber/novo/",              receber_views.ContaReceberCreateView.as_view(),   name="receber_criar"),
    path("receber/<int:pk>/",          receber_views.ContaReceberDetailView.as_view(),   name="receber_detail"),
    path("receber/<int:pk>/baixar/",   receber_views.ContaReceberBaixaView.as_view(),    name="receber_baixar"),
    path("receber/<int:pk>/cancelar/", receber_views.ContaReceberCancelarView.as_view(), name="receber_cancelar"),

    # ── Outros ───────────────────────────────────────────────────────────────
    path("pagar/",       financeiro.pagar_list,            name="pagar_list"),
    path("documentos/",  financeiro.documentos_fiscais_list, name="documentos"),
    path("dre/",         financeiro.dre_view,              name="dre"),
]
