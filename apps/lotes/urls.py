from django.urls import path

from .views.dashboard import LotesDashboardView
from .views.rastreabilidade import LoteRastreabilidadeView
from .views.inspecao import LoteInspecaoListView, LoteInspecaoCreateView
from .views.alertas import AlertasVencimentoView

app_name = 'lotes'

urlpatterns = [
    path('', LotesDashboardView.as_view(), name='dashboard'),
    path('alertas/', AlertasVencimentoView.as_view(), name='alertas'),
    path('rastreabilidade/', LoteRastreabilidadeView.as_view(), name='rastreabilidade'),
    path('<int:pk>/inspecoes/', LoteInspecaoListView.as_view(), name='inspecao-list'),
    path('<int:pk>/inspecoes/nova/', LoteInspecaoCreateView.as_view(), name='inspecao-create'),
]
