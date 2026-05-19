from django.apps import AppConfig


class ProducaoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.producao'
    verbose_name = 'Produção'

    def ready(self):
        from apps.core.signals import register_for_audit
        from .models import FichaTecnica, OrdemProducao
        register_for_audit(FichaTecnica, 'producao')
        register_for_audit(OrdemProducao, 'producao')
