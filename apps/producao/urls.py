from django.urls import path

from apps.producao import views

app_name = 'producao'

urlpatterns = [
    # Ordens de Produção
    path('', views.OrdemProducaoListView.as_view(), name='op-list'),
    path('nova/', views.CriarOrdemProducaoView.as_view(), name='op-create'),
    path('<int:pk>/', views.OrdemProducaoDetailView.as_view(), name='op-detail'),
    path('<int:pk>/abrir/', views.AbrirOrdemProducaoView.as_view(), name='op-abrir'),
    path('<int:pk>/iniciar/', views.IniciarOrdemProducaoView.as_view(), name='op-iniciar'),
    path('<int:pk>/encerrar/', views.EncerrarOrdemProducaoView.as_view(), name='op-encerrar'),
    path('<int:pk>/cancelar/', views.CancelarOrdemProducaoView.as_view(), name='op-cancelar'),

    # Fichas Técnicas (BOM)
    path('fichas-tecnicas/', views.FichaTecnicaListView.as_view(), name='ficha-list'),
    path('fichas-tecnicas/nova/', views.FichaTecnicaCreateView.as_view(), name='ficha-create'),
    path('fichas-tecnicas/<int:pk>/', views.FichaTecnicaUpdateView.as_view(), name='ficha-update'),
]
