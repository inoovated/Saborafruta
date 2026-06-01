"""
Recurso NFe (Nota Fiscal Eletrônica modelo 55).
Endpoints documentados em https://focusnfe.com.br/doc/#nota_fiscal_eletronica
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from ._authorized_doc import AuthorizedDocResource


class NFeResource(AuthorizedDocResource):
    endpoint = "nfe"
    supports_carta_correcao = True
    supports_inutilizacao = True

    def inutilizar(
        self,
        cnpj: str,
        serie: int,
        numero_inicial: int,
        numero_final: int,
        justificativa: str,
        ano: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Inutiliza uma faixa de numeração."""
        if not justificativa or len(justificativa) < 15:
            raise ValueError("Justificativa de inutilização exige no mínimo 15 caracteres.")
        body: Dict[str, Any] = {
            "cnpj": cnpj,
            "serie": serie,
            "numero_inicial": numero_inicial,
            "numero_final": numero_final,
            "justificativa": justificativa,
        }
        if ano is not None:
            body["ano"] = ano
        return self._http.post("/v2/nfe_inutilizacao", json_body=body)

    def baixar_danfe(self, ref: str) -> bytes:
        """Alias para baixar_pdf — DANFE é o PDF da NFe."""
        return self.baixar_pdf(ref)

    def duplicatas(self, ref: str) -> Dict[str, Any]:
        return self._http.get(f"/v2/nfe/{ref}/duplicatas")

    def prorrogar_duplicata(self, ref: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._http.post(f"/v2/nfe/{ref}/prorrogar_duplicata", json_body=payload)
