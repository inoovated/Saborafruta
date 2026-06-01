"""
NFe recebidas — consulta de NFes emitidas contra um CNPJ destinatário,
captura de XML e operações de manifestação do destinatário.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from .._base import ResourceBase


# Códigos de manifestação do destinatário
MANIFESTO_CIENCIA = "ciencia_operacao"
MANIFESTO_CONFIRMACAO = "confirmacao_operacao"
MANIFESTO_DESCONHECIMENTO = "desconhecimento_operacao"
MANIFESTO_OPERACAO_NAO_REALIZADA = "operacao_nao_realizada"


class NFeRecebidasResource(ResourceBase):
    endpoint = "nfes_recebidas"

    def listar(
        self,
        cnpj: str,
        *,
        nsu: Optional[int] = None,
        pagina: Optional[int] = None,
        por_pagina: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Lista NFes recebidas. Use `nsu` para resgatar a partir de um número de sequência."""
        params: Dict[str, Any] = {"cnpj": cnpj}
        if nsu is not None:
            params["nsu"] = nsu
        if pagina is not None:
            params["pagina"] = pagina
        if por_pagina is not None:
            params["por_pagina"] = por_pagina
        return self._http.get(f"/v2/{self.endpoint}", params=params)

    def consultar(self, chave_nfe: str) -> Dict[str, Any]:
        """Consulta uma NFe específica pela chave de 44 dígitos."""
        return self._http.get(f"/v2/{self.endpoint}/{chave_nfe}")

    def baixar_xml(self, chave_nfe: str) -> bytes:
        return self._http.get(f"/v2/{self.endpoint}/{chave_nfe}.xml", binary=True)

    def manifestar(
        self,
        chave_nfe: str,
        tipo: str,
        justificativa: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Manifesta-se sobre uma NFe recebida.

        Args:
            chave_nfe: chave de 44 dígitos.
            tipo: um dos MANIFESTO_*. 'desconhecimento_operacao' e
                  'operacao_nao_realizada' não exigem justificativa,
                  mas pode ser informada.
        """
        body: Dict[str, Any] = {"tipo": tipo}
        if justificativa:
            body["justificativa"] = justificativa
        return self._http.post(
            f"/v2/{self.endpoint}/{chave_nfe}/manifestacao",
            json_body=body,
        )
