"""
Integração com a API Focus NFe (https://focusnfe.com.br/doc/).

Uso típico em um app Django:

    from apps.fiscal.integrations.focusnfe import FocusNFeClient

    client = FocusNFeClient()  # lê FOCUSNFE_TOKEN/FOCUSNFE_AMBIENTE do settings/env
    resp = client.nfe.autorizar(ref="PED-123", payload={...})
"""
from .client import FocusNFeClient
from .config import FocusNFeConfig, PRODUCAO, HOMOLOGACAO
from .exceptions import (
    FocusNFeError,
    FocusNFeAuthError,
    FocusNFeValidationError,
    FocusNFeNotFoundError,
    FocusNFeProcessingError,
    FocusNFeRateLimitError,
    FocusNFeServerError,
    FocusNFeNetworkError,
    FocusNFeConfigError,
)

__all__ = [
    "FocusNFeClient",
    "FocusNFeConfig",
    "PRODUCAO",
    "HOMOLOGACAO",
    "FocusNFeError",
    "FocusNFeAuthError",
    "FocusNFeValidationError",
    "FocusNFeNotFoundError",
    "FocusNFeProcessingError",
    "FocusNFeRateLimitError",
    "FocusNFeServerError",
    "FocusNFeNetworkError",
    "FocusNFeConfigError",
]
