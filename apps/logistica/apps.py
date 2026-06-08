from django.apps import AppConfig


class LogisticaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.logistica"
    verbose_name = "Logistica"

    def ready(self):
        from apps.core.signals import register_for_audit
        from .models import (
            CTe,
            DocumentoCTe,
            DocumentoManifestoCarga,
            ItemOrdemColeta,
            ItemRomaneioCarga,
            ManifestoCarga,
            OrdemColeta,
            RomaneioCarga,
        )

        register_for_audit(RomaneioCarga, "logistica")
        register_for_audit(ItemRomaneioCarga, "logistica")
        register_for_audit(OrdemColeta, "logistica")
        register_for_audit(ItemOrdemColeta, "logistica")
        register_for_audit(ManifestoCarga, "logistica")
        register_for_audit(DocumentoManifestoCarga, "logistica")
        register_for_audit(CTe, "logistica")
        register_for_audit(DocumentoCTe, "logistica")
