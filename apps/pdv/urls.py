from django.urls import path
from apps.pdv.views import pdv

app_name = "pdv"

urlpatterns = [
    path("", pdv.pdv_home, name="home"),
    path("vendas/", pdv.vendas_list, name="vendas_list"),
    # Busca
    path("api/produtos/", pdv.buscar_produto, name="api_produtos"),
    path("api/clientes/", pdv.buscar_cliente, name="api_clientes"),
    # Estado e caixa
    path("api/estado/", pdv.api_estado, name="api_estado"),
    path("api/caixa/abrir/", pdv.api_caixa_abrir, name="api_caixa_abrir"),
    # Vendas
    path("api/venda/finalizar/", pdv.api_venda_finalizar, name="api_venda_finalizar"),
    path("api/venda/pendente/", pdv.api_venda_pendente, name="api_venda_pendente"),
    path("api/venda/orcamento/", pdv.api_venda_orcamento, name="api_venda_orcamento"),
    path("api/pendentes/", pdv.api_pendentes, name="api_pendentes"),
    # Clientes
    path("api/cliente/criar/", pdv.api_cliente_criar, name="api_cliente_criar"),
]
