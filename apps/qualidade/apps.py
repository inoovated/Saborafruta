from django.apps import AppConfig


class QualidadeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.qualidade"
    verbose_name = "Controle de Qualidade"

    def ready(self):
        from apps.core.signals import register_for_audit
        from .models import (
            AnaliseQualidade,
            ParametroQualidade,
            ParametroQualidadeCategoria,
            ParametroQualidadeProduto,
        )

        register_for_audit(ParametroQualidade, "qualidade")
        register_for_audit(ParametroQualidadeProduto, "qualidade")
        register_for_audit(ParametroQualidadeCategoria, "qualidade")
        register_for_audit(AnaliseQualidade, "qualidade")
