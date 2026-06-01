"""
APIs de consulta da Focus NFe:

  - NCM   (Nomenclatura Comum do Mercosul)
  - CFOP  (Código Fiscal de Operações e Prestações)
  - CNAE  (Classificação Nacional de Atividades Econômicas)
  - CNPJ  (Cadastro Nacional da Pessoa Jurídica)
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional

from .._base import ResourceBase


def _so_digitos(s: str) -> str:
    return re.sub(r"\D", "", s or "")


class NCMResource(ResourceBase):
    def consultar(self, codigo: str) -> Dict[str, Any]:
        """Consulta um NCM (8 dígitos, ponto opcional)."""
        return self._http.get(f"/v2/ncms/{_so_digitos(codigo)}")

    def listar(
        self,
        *,
        descricao: Optional[str] = None,
        pagina: Optional[int] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if descricao:
            params["descricao"] = descricao
        if pagina is not None:
            params["pagina"] = pagina
        return self._http.get("/v2/ncms", params=params)


class CFOPResource(ResourceBase):
    def consultar(self, codigo: str) -> Dict[str, Any]:
        """Consulta um CFOP (4 dígitos)."""
        return self._http.get(f"/v2/cfops/{_so_digitos(codigo)}")

    def listar(self, *, pagina: Optional[int] = None) -> Dict[str, Any]:
        params = {"pagina": pagina} if pagina is not None else None
        return self._http.get("/v2/cfops", params=params)


class CNAEResource(ResourceBase):
    def consultar(self, codigo: str) -> Dict[str, Any]:
        """Consulta um CNAE (7 dígitos no formato 0000-0/00 — pontos/barras opcionais)."""
        return self._http.get(f"/v2/cnaes/{_so_digitos(codigo)}")

    def listar(self, *, descricao: Optional[str] = None, pagina: Optional[int] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if descricao:
            params["descricao"] = descricao
        if pagina is not None:
            params["pagina"] = pagina
        return self._http.get("/v2/cnaes", params=params)


class CNPJResource(ResourceBase):
    def consultar(self, cnpj: str) -> Dict[str, Any]:
        """Consulta dados cadastrais de um CNPJ."""
        return self._http.get(f"/v2/cnpjs/{_so_digitos(cnpj)}")


class MunicipiosResource(ResourceBase):
    def consultar(self, codigo_ibge: str) -> Dict[str, Any]:
        """Consulta um municipio pelo codigo IBGE."""
        return self._http.get(f"/v2/municipios/{_so_digitos(codigo_ibge)}")

    def listar(
        self,
        *,
        uf: Optional[str] = None,
        nome: Optional[str] = None,
        pagina: Optional[int] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if uf:
            params["uf"] = uf.upper()
        if nome:
            params["nome"] = nome
        if pagina is not None:
            params["pagina"] = pagina
        return self._http.get("/v2/municipios", params=params)
