"""
CTe — Conhecimento de Transporte Eletrônico (modelo 57).
"""
from __future__ import annotations

from typing import Any, Dict

from ._authorized_doc import AuthorizedDocResource


class CTeResource(AuthorizedDocResource):
    endpoint = "cte"
    supports_carta_correcao = True

    def baixar_dacte(self, ref: str) -> bytes:
        return self.baixar_pdf(ref)
