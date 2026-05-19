from django.apps import AppConfig


class ComprasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.compras'
    verbose_name = 'Compras'

    def ready(self):
        from apps.core.signals import register_for_audit
        from .models import PedidoCompra, EntradaNF, EntradaNFParcela
        register_for_audit(PedidoCompra, 'compras')
        register_for_audit(EntradaNF, 'compras')
        register_for_audit(EntradaNFParcela, 'compras')
