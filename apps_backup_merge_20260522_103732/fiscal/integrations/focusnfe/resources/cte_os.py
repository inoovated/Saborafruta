"""
CTe OS — CTe modelo 67 para Outros Serviços (transporte de passageiros etc.).
"""
from __future__ import annotations

from ._authorized_doc import AuthorizedDocResource


class CTeOSResource(AuthorizedDocResource):
    endpoint = "cteos"
    supports_carta_correcao = True
