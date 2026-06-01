"""
NFSe Nacional — padrão nacional unificado da Receita Federal.
Endpoint base: /v2/nfsen_nacional
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .._base import ResourceBase


class NFSeNacionalResource(ResourceBase):
    endpoint = "nfsen_nacional"

    def autorizar(self, ref: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._http.post(f"/v2/{self.endpoint}", params={"ref": ref}, json_body=payload)

    def consultar(self, ref: str) -> Dict[str, Any]:
        return self._http.get(f"/v2/{self.endpoint}/{ref}")

    def cancelar(self, ref: str, justificativa: str, codigo_motivo: Optional[str] = None) -> Dict[str, Any]:
        body: Dict[str, Any] = {"justificativa": justificativa}
        if codigo_motivo:
            body["codigo_motivo"] = codigo_motivo
        return self._http.delete(f"/v2/{self.endpoint}/{ref}", json_body=body)

    def baixar_xml(self, ref: str) -> bytes:
        return self._http.get(f"/v2/{self.endpoint}/{ref}.xml", binary=True)

    def baixar_pdf(self, ref: str) -> bytes:
        return self._http.get(f"/v2/{self.endpoint}/{ref}.pdf", binary=True)

    def enviar_email(self, ref: str, emails: List[str]) -> Dict[str, Any]:
        return self._http.post(f"/v2/{self.endpoint}/{ref}/email", json_body={"emails": list(emails)})
