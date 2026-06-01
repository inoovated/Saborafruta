"""
NFSe — Nota Fiscal de Serviço Eletrônica (padrão municipal).
Cada município tem seu próprio webservice; a Focus NFe abstrai isso.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .._base import ResourceBase


class NFSeResource(ResourceBase):
    endpoint = "nfse"

    def autorizar(self, ref: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Emite NFSe. `ref` é seu identificador interno."""
        return self._http.post(f"/v2/{self.endpoint}", params={"ref": ref}, json_body=payload)

    def consultar(self, ref: str) -> Dict[str, Any]:
        return self._http.get(f"/v2/{self.endpoint}/{ref}")

    def cancelar(self, ref: str, justificativa: Optional[str] = None) -> Dict[str, Any]:
        body: Dict[str, Any] = {}
        if justificativa:
            body["justificativa"] = justificativa
        return self._http.delete(f"/v2/{self.endpoint}/{ref}", json_body=body or None)

    def baixar_xml(self, ref: str) -> bytes:
        return self._http.get(f"/v2/{self.endpoint}/{ref}.xml", binary=True)

    def baixar_pdf(self, ref: str) -> bytes:
        return self._http.get(f"/v2/{self.endpoint}/{ref}.pdf", binary=True)

    def enviar_email(self, ref: str, emails: List[str]) -> Dict[str, Any]:
        return self._http.post(f"/v2/{self.endpoint}/{ref}/email", json_body={"emails": list(emails)})
