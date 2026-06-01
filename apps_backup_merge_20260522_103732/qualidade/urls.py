from django.urls import path
from apps.qualidade.views import analises

app_name = "qualidade"

urlpatterns = [
    path("analises/", analises.analise_list, name="analise_list"),
    path("api/produtos/", analises.produto_search, name="produto_search"),
    path("parametros/criar/", analises.parametro_create, name="parametro_create"),
    path("parametros/<int:pk>/status/", analises.parametro_toggle, name="parametro_toggle"),
    path("padroes/criar/", analises.padrao_create, name="padrao_create"),
    path("padroes/<int:pk>/editar/", analises.padrao_update, name="padrao_update"),
    path("padroes/<int:pk>/status/", analises.padrao_toggle, name="padrao_toggle"),
    path("padroes/aplicar/", analises.aplicar_padroes_produto, name="aplicar_padroes_produto"),
]
