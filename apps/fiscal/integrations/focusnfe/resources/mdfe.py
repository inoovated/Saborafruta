"""
MDFe — Manifesto Eletrônico de Documentos Fiscais (modelo 58).
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from ._authorized_doc import AuthorizedDocResource


class MDFeResource(AuthorizedDocResource):
    endpoint = "mdfe"
    supports_carta_correcao = False

    def encerrar(
        self,
        ref: str,
        *,
        codigo_municipio: str,
        uf: str,
        data_encerramento: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Encerra um MDFe quando o transporte chega ao destino."""
        body: Dict[str, Any] = {
            "codigo_municipio": codigo_municipio,
            "uf": uf,
        }
        if data_encerramento:
            body["data_encerramento"] = data_encerramento
        return self._http.post(f"/v2/mdfe/{ref}/encerrar", json_body=body)

    def incluir_condutor(self, ref: str, nome: str, cpf: str) -> Dict[str, Any]:
        """Inclui um condutor adicional no MDFe."""
        return self._http.post(
            f"/v2/mdfe/{ref}/incluir_condutor",
            json_body={"nome": nome, "cpf": cpf},
        )

    def incluir_dfe(self, ref: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Inclui DF-e (NFe/CTe) em MDFe já autorizado."""
        return self._http.post(f"/v2/mdfe/{ref}/incluir_dfe", json_body=payload)

    def baixar_damdfe(self, ref: str) -> bytes:
        return self.baixar_pdf(ref)
