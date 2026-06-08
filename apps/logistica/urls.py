from django.urls import path

from apps.logistica import views

app_name = "logistica"

urlpatterns = [
    path("", views.RomaneioCargaListView.as_view(), name="romaneio-list"),
    path("romaneios/", views.RomaneioCargaListView.as_view(), name="romaneio-list"),
    path("romaneios/novo/", views.RomaneioCargaCreateView.as_view(), name="romaneio-create"),
    path("romaneios/<int:pk>/", views.RomaneioCargaDetailView.as_view(), name="romaneio-detail"),
    path("romaneios/<int:pk>/editar/", views.RomaneioCargaUpdateView.as_view(), name="romaneio-update"),
    path("romaneios/<int:pk>/itens/novo/", views.ItemRomaneioCreateView.as_view(), name="romaneio-item-create"),
    path("romaneios/<int:pk>/itens/<int:item_pk>/remover/", views.ItemRomaneioDeleteView.as_view(), name="romaneio-item-delete"),
    path("ordens-coleta/", views.OrdemColetaListView.as_view(), name="ordem-coleta-list"),
    path("ordens-coleta/nova/", views.OrdemColetaCreateView.as_view(), name="ordem-coleta-create"),
    path("ordens-coleta/<int:pk>/", views.OrdemColetaDetailView.as_view(), name="ordem-coleta-detail"),
    path("ordens-coleta/<int:pk>/editar/", views.OrdemColetaUpdateView.as_view(), name="ordem-coleta-update"),
    path("ordens-coleta/<int:pk>/itens/novo/", views.ItemOrdemColetaCreateView.as_view(), name="ordem-coleta-item-create"),
    path("ordens-coleta/<int:pk>/itens/<int:item_pk>/remover/", views.ItemOrdemColetaDeleteView.as_view(), name="ordem-coleta-item-delete"),
    path("manifestos/", views.ManifestoCargaListView.as_view(), name="manifesto-list"),
    path("manifestos/novo/", views.ManifestoCargaCreateView.as_view(), name="manifesto-create"),
    path("manifestos/<int:pk>/", views.ManifestoCargaDetailView.as_view(), name="manifesto-detail"),
    path("manifestos/<int:pk>/editar/", views.ManifestoCargaUpdateView.as_view(), name="manifesto-update"),
    path("manifestos/<int:pk>/documentos/novo/", views.DocumentoManifestoCreateView.as_view(), name="manifesto-documento-create"),
    path("manifestos/<int:pk>/documentos/<int:documento_pk>/remover/", views.DocumentoManifestoDeleteView.as_view(), name="manifesto-documento-delete"),
]
