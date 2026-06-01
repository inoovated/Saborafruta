"""
NFCOM — Nota Fiscal Fatura de Serviços de Comunicação (modelo 62).
"""
from __future__ import annotations

from ._authorized_doc import AuthorizedDocResource


class NFCOMResource(AuthorizedDocResource):
    endpoint = "nfcom"
    supports_carta_correcao = False
