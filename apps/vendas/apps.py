from django.apps import AppConfig


class VendasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.vendas'
    verbose_name = 'Vendas'

    def ready(self):
        from apps.core.signals import register_for_audit
        from .models import PedidoVenda, ItemPedidoVenda
        register_for_audit(PedidoVenda, 'vendas')
        register_for_audit(ItemPedidoVenda, 'vendas')
