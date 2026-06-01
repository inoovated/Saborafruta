from django.apps import AppConfig


class CadastrosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.cadastros'
    verbose_name = 'Cadastros'

    def ready(self):
        from apps.core.signals import register_for_audit
        from .models import Cliente, Fornecedor, Representante, Transportadora
        register_for_audit(Cliente, 'cadastros')
        register_for_audit(Fornecedor, 'cadastros')
        register_for_audit(Transportadora, 'cadastros')
        register_for_audit(Representante, 'cadastros')
