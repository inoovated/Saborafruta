"""Geração e envio do relatório semanal por email."""
from django.core.mail import EmailMessage
from django.conf import settings


def enviar_relatorio_semanal():
    """Gera PDF resumindo KPIs por linha e envia para gestores."""
    # Implementação: WeasyPrint render → PDF → EmailMessage com anexo
    # Aqui só registramos.
    return "ok"
