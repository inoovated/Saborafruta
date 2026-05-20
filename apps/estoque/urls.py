from django.urls import path

from apps.estoque import views

app_name = 'estoque'

urlpatterns = [
    # Consulta de estoque
    path('', views.EstoqueListView.as_view(), name='estoque-list'),
    path('custos-entrada/', views.EntradaCustoEstoqueListView.as_view(), name='entrada-custos-list'),
    path('reposicao/', views.ReposicaoListView.as_view(), name='reposicao-list'),
    path('movimentacoes/', views.MovimentacaoListView.as_view(), name='movimentacao-list'),

    # Operacoes
    path('movimentacoes/nova/', views.MovimentacaoManualView.as_view(), name='movimentacao-create'),
    path('ajuste/', views.AjusteEstoqueView.as_view(), name='ajuste'),
    path('transferencia/', views.TransferenciaView.as_view(), name='transferencia'),

    # Inventario
    path('inventarios/', views.InventarioListView.as_view(), name='inventario-list'),
    path('inventarios/novo/', views.InventarioCreateView.as_view(), name='inventario-create'),
    path('inventarios/<int:pk>/', views.InventarioDetailView.as_view(), name='inventario-detail'),
    path('inventarios/<int:pk>/divergencias/', views.InventarioDivergenciasView.as_view(), name='inventario-divergencias'),
    path('inventarios/<int:pk>/cancelar/', views.InventarioCancelView.as_view(), name='inventario-cancel'),

    # Lotes
    path('lotes/', views.LoteListView.as_view(), name='lote-list'),
    path('lotes/novo/', views.LoteCreateView.as_view(), name='lote-create'),
    path('lotes/<int:pk>/', views.LoteUpdateView.as_view(), name='lote-update'),
    path('lotes/<int:pk>/baixa-validade/', views.LoteBaixaValidadeView.as_view(), name='lote-baixa-validade'),

    # Alertas
    path('alertas/', views.AlertaListView.as_view(), name='alerta-list'),
]
