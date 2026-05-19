from django.apps import AppConfig


class EstoqueConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.estoque'
    verbose_name = 'Estoque'

    def ready(self):
        from apps.core.signals import register_for_audit
        from .models import LoteProduto, MovimentacaoEstoque, Inventario
        register_for_audit(LoteProduto, 'estoque')
        register_for_audit(MovimentacaoEstoque, 'estoque')
        register_for_audit(Inventario, 'estoque')
