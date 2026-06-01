"""
Configuração da integração com Focus NFe.

Lê credenciais e ambiente de variáveis de ambiente / settings do Django:
  - FOCUSNFE_TOKEN     (obrigatório)
  - FOCUSNFE_AMBIENTE  (1 = produção, 2 = homologação) — default 2

A configuração também pode ser instanciada manualmente para testes
ou para suportar múltiplas filiais com tokens distintos.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


PRODUCAO = 1
HOMOLOGACAO = 2

URLS = {
    PRODUCAO: "https://api.focusnfe.com.br",
    HOMOLOGACAO: "https://homologacao.focusnfe.com.br",
}


@dataclass(frozen=True)
class FocusNFeConfig:
    """Configuração imutável para o client."""
    token: str
    ambiente: int = HOMOLOGACAO
    timeout: int = 60        # segundos
    max_retries: int = 2
    user_agent: str = "erp-inoovated-focusnfe/1.0"

    def __post_init__(self) -> None:
        if not self.token:
            raise ValueError(
                "FOCUSNFE_TOKEN não configurado. Defina a variável de ambiente "
                "FOCUSNFE_TOKEN ou passe token=... ao instanciar FocusNFeConfig."
            )
        if self.ambiente not in URLS:
            raise ValueError(
                f"Ambiente inválido: {self.ambiente}. Use 1 (produção) ou 2 (homologação)."
            )

    @property
    def base_url(self) -> str:
        return URLS[self.ambiente]

    @classmethod
    def from_env(
        cls,
        token: Optional[str] = None,
        ambiente: Optional[int] = None,
    ) -> "FocusNFeConfig":
        """
        Cria config lendo de Django settings (preferencial) ou env vars.

        Args:
            token: se informado, sobrepõe o token do settings/env.
            ambiente: 1 (prod) ou 2 (homolog), sobrepõe o do settings/env.
        """
        # Tenta Django settings primeiro
        try:
            from django.conf import settings as dj_settings
            t = token or getattr(dj_settings, "ERP_FOCUSNFE_TOKEN", "") or os.getenv("FOCUSNFE_TOKEN", "")
            a = ambiente if ambiente is not None else getattr(
                dj_settings, "ERP_FOCUSNFE_AMBIENTE", None
            )
        except Exception:
            t = token or os.getenv("FOCUSNFE_TOKEN", "")
            a = ambiente

        if a is None:
            a = int(os.getenv("FOCUSNFE_AMBIENTE", str(HOMOLOGACAO)))

        return cls(token=t, ambiente=int(a))
