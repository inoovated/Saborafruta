from django.urls import path

from apps.fiscal import views

app_name = 'fiscal'

urlpatterns = [
    path('manifesto/', views.ManifestoFiscalListView.as_view(), name='manifesto-list'),
    path('manifesto/config/', views.ManifestoFiscalConfigView.as_view(), name='manifesto-config'),
    path(
        'manifesto/<int:pk>/importar-entrada/',
        views.ManifestoFiscalImportarEntradaView.as_view(),
        name='manifesto-importar-entrada',
    ),
    path(
        'manifesto/<int:pk>/anexar-xml/',
        views.ManifestoFiscalAnexarXMLView.as_view(),
        name='manifesto-anexar-xml',
    ),
    path('manifesto/<int:pk>/<slug:acao>/', views.ManifestoFiscalAcaoView.as_view(), name='manifesto-acao'),
]
