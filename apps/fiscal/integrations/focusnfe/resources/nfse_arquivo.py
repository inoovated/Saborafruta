"""
NFSe por arquivo — envio de XML já assinado/pronto para municípios
que exigem esse formato.
"""
from __future__ import annotations

from typing import Any, Dict, Union

from .._base import ResourceBase


class NFSeArquivoResource(ResourceBase):
    endpoint = "nfse_arquivo"

    def enviar(
        self,
        ref: str,
        cnpj_emitente: str,
        xml: Union[str, bytes],
    ) -> Dict[str, Any]:
        """
        Envia um XML pronto (string ou bytes) para emissão.

        Args:
            ref: identificador interno
            cnpj_emitente: CNPJ que está emitindo
            xml: conteúdo do XML (RPS/lote do município)
        """
        if isinstance(xml, str):
            xml = xml.encode("utf-8")
        return self._http.post(
            f"/v2/{self.endpoint}",
            params={"ref": ref, "cnpj_emitente": cnpj_emitente},
            data=xml,
            extra_headers={"Content-Type": "application/xml"},
        )

    def consultar(self, ref: str) -> Dict[str, Any]:
        return self._http.get(f"/v2/{self.endpoint}/{ref}")
