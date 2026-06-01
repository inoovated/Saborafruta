"""
Recurso NFCe (Nota Fiscal de Consumidor Eletrônica modelo 65).
"""
from __future__ import annotations

from ._authorized_doc import AuthorizedDocResource


class NFCeResource(AuthorizedDocResource):
    endpoint = "nfce"
    supports_carta_correcao = False  # NFCe não tem CC-e
    supports_inutilizacao = True

    def baixar_danfce(self, ref: str) -> bytes:
        """Alias para baixar_pdf — DANFE NFCe."""
        return self.baixar_pdf(ref)
