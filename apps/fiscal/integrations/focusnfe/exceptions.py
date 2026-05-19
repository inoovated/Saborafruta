"""
Hierarquia de exceções da integração Focus NFe.

    FocusNFeError                      <- base
        FocusNFeConfigError            <- config inválida
        FocusNFeAuthError              <- 401/403
        FocusNFeValidationError        <- 400 (XML/payload inválido)
        FocusNFeNotFoundError          <- 404
        FocusNFeProcessingError        <- 422 (rejeitado pela SEFAZ)
        FocusNFeServerError            <- 5xx
        FocusNFeRateLimitError         <- 429
        FocusNFeNetworkError           <- timeout/DNS/conexão

Todas as exceções carregam o objeto `response` (quando aplicável) e
o JSON retornado pela API, em `response_json`, para diagnóstico fino.
"""
from __future__ import annotations

from typing import Any, Optional


class FocusNFeError(Exception):
    """Erro genérico da integração Focus NFe."""
    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        response_json: Any = None,
        response_text: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_json = response_json
        self.response_text = response_text

    def __str__(self) -> str:
        base = super().__str__()
        if self.status_code:
            return f"[{self.status_code}] {base}"
        return base


class FocusNFeConfigError(FocusNFeError):
    """Configuração inválida (token ausente, ambiente inválido)."""


class FocusNFeAuthError(FocusNFeError):
    """Falha de autenticação (401/403)."""


class FocusNFeValidationError(FocusNFeError):
    """Payload inválido (400) — campos faltantes, XML mal formado etc."""


class FocusNFeNotFoundError(FocusNFeError):
    """Recurso não encontrado (404). Ex.: ref de NFe inexistente."""


class FocusNFeProcessingError(FocusNFeError):
    """Documento rejeitado pela SEFAZ ou em status de erro (422)."""


class FocusNFeRateLimitError(FocusNFeError):
    """Limite de requisições atingido (429)."""


class FocusNFeServerError(FocusNFeError):
    """Erro do lado da Focus NFe (5xx)."""


class FocusNFeNetworkError(FocusNFeError):
    """Falha de rede: DNS, conexão recusada, timeout etc."""
