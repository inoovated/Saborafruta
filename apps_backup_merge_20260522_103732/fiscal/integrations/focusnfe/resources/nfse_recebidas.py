"""
NFSes recebidas pelo CNPJ tomador.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from .._base import ResourceBase


class NFSeRecebidasResource(ResourceBase):
    endpoint = "nfses_recebidas"

    def listar(
        self,
        cnpj: str,
        *,
        data_emissao_inicial: Optional[str] = None,
        data_emissao_final: Optional[str] = None,
        pagina: Optional[int] = None,
        por_pagina: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Lista NFSes recebidas para o CNPJ no período."""
        params: Dict[str, Any] = {"cnpj": cnpj}
        if data_emissao_inicial:
            params["data_emissao_inicial"] = data_emissao_inicial
        if data_emissao_final:
            params["data_emissao_final"] = data_emissao_final
        if pagina is not None:
            params["pagina"] = pagina
        if por_pagina is not None:
            params["por_pagina"] = por_pagina
        return self._http.get(f"/v2/{self.endpoint}", params=params)

    def consultar(self, identificador: str) -> Dict[str, Any]:
        return self._http.get(f"/v2/{self.endpoint}/{identificador}")
