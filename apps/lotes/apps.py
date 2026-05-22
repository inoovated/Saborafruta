from django.apps import AppConfig


class LotesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.lotes"
    verbose_name = "Rastreabilidade de Lotes"

    def ready(self):
        from apps.core.signals import register_for_audit
        from .models import InspecaoLote
        register_for_audit(InspecaoLote, "lotes")
