"""
Integração com a API ViaCEP (https://viacep.com.br).

Uso:
    dados = CepService.consultar('59100000')
    # {
    #   'cep': '59100000',
    #   'endereco': 'Rua X',
    #   'bairro': 'Centro',
    #   'cidade': 'Natal',
    #   'uf': 'RN',
    #   'codigo_municipio_ibge': '2408102',
    # }
"""
from __future__ import annotations

import logging

import requests
from django.conf import settings
from django.core.cache import cache

from apps.core.services.exceptions import DadosInvalidosError

logger = logging.getLogger(__name__)


class CepService:
    TIMEOUT = 5
    CACHE_TTL = 60 * 60 * 24 * 30  # 30 dias (CEPs mudam raramente)

    @classmethod
    def consultar(cls, cep: str) -> dict | None:
        """
        Consulta CEP. Retorna dict normalizado ou None se não encontrado.
        Levanta DadosInvalidosError se CEP malformado.
        """
        cep_limpo = cls._limpar(cep)
        if len(cep_limpo) != 8:
            raise DadosInvalidosError('CEP deve conter 8 dígitos.')

        cache_key = f'viacep:{cep_limpo}'
        cached = cache.get(cache_key)
        if cached is not None:
            return cached if cached else None

        url = settings.VIACEP_URL.format(cep=cep_limpo)
        try:
            response = requests.get(url, timeout=cls.TIMEOUT)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.warning('Falha ao consultar ViaCEP %s: %s', cep_limpo, e)
            return None
        except ValueError:
            logger.warning('Resposta inválida do ViaCEP para %s', cep_limpo)
            return None

        if data.get('erro'):
            cache.set(cache_key, {}, cls.CACHE_TTL)  # marca como inexistente
            return None

        resultado = {
            'cep': cep_limpo,
            'endereco': data.get('logradouro', ''),
            'complemento': data.get('complemento', ''),
            'bairro': data.get('bairro', ''),
            'cidade': data.get('localidade', ''),
            'uf': data.get('uf', ''),
            'codigo_municipio_ibge': data.get('ibge', ''),
        }
        cache.set(cache_key, resultado, cls.CACHE_TTL)
        return resultado

    @staticmethod
    def _limpar(cep: str) -> str:
        return ''.join(filter(str.isdigit, str(cep or '')))
