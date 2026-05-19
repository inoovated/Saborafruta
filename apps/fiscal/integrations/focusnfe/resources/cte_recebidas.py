"""
CTe recebidas — consulta de CTes em que um CNPJ é tomador.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from .._base import ResourceBase


class CTeRecebidasResource(ResourceBase):
    endpoint = "ctes_recebidos"

    def listar(
        self,
        cnpj: str,
        *,
        nsu: Optional[int] = None,
        pagina: Optional[int] = None,
        por_pagina: Optional[int] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"cnpj": cnpj}
        if nsu is not None:
            params["nsu"] = nsu
        if pagina is not None:
            params["pagina"] = pagina
        if por_pagina is not None:
            params["por_pagina"] = por_pagina
        return self._http.get(f"/v2/{self.endpoint}", params=params)

    def consultar(self, chave_cte: str) -> Dict[str, Any]:
        return self._http.get(f"/v2/{self.endpoint}/{chave_cte}")

    def baixar_xml(self, chave_cte: str) -> bytes:
        return self._http.get(f"/v2/{self.endpoint}/{chave_cte}.xml", binary=True)
