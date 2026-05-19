"""Cliente seguro para consulta DF-e recebida.

O modo padrao e local e nao conversa com SEFAZ. O modo SEFAZ consulta somente o
web service NFeDistribuicaoDFe quando as travas explicitas estiverem ligadas,
mantendo eventos fiscais reais e ambiente de producao bloqueados por padrao.
"""
from __future__ import annotations

import base64
import gzip
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from tempfile import TemporaryDirectory
from xml.etree import ElementTree

import requests
from django.conf import settings
from django.utils import timezone

from apps.core.services.exceptions import DadosInvalidosError
from apps.fiscal.services.certificado_a1 import (
    CertificadoA1Info, exportar_certificado_a1_pem, validar_certificado_a1_para_config,
)


NFE_NS = 'http://www.portalfiscal.inf.br/nfe'
NFE_DFE_WSDL_NS = 'http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe'
SOAP12_NS = 'http://www.w3.org/2003/05/soap-envelope'
UF_CODIGOS = {
    'RO': '11', 'AC': '12', 'AM': '13', 'RR': '14', 'PA': '15', 'AP': '16', 'TO': '17',
    'MA': '21', 'PI': '22', 'CE': '23', 'RN': '24', 'PB': '25', 'PE': '26', 'AL': '27',
    'SE': '28', 'BA': '29', 'MG': '31', 'ES': '32', 'RJ': '33', 'SP': '35', 'PR': '41',
    'SC': '42', 'RS': '43', 'MS': '50', 'MT': '51', 'GO': '52', 'DF': '53',
}
SEFAZ_DFE_ENDPOINTS = {
    'homologacao': 'https://hom1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx',
    'producao': 'https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx',
}


@dataclass(frozen=True)
class DFeDocumentoResumo:
    chave_acesso: str
    nsu: str = ''
    cnpj_emitente: str = ''
    razao_social_emitente: str = ''
    data_emissao: date | None = None
    valor_total: Decimal = Decimal('0')
    xml_resumo: str = ''
    xml_completo: str = ''


@dataclass(frozen=True)
class DFeConsultaResultado:
    documentos: list[DFeDocumentoResumo] = field(default_factory=list)
    ultimo_nsu: str = ''
    max_nsu: str = ''
    codigo_status: str = ''
    mensagem: str = ''
    modo: str = 'local'


@dataclass(frozen=True)
class DFeProntidaoItem:
    codigo: str
    titulo: str
    mensagem: str
    status: str = 'info'


@dataclass(frozen=True)
class DFeProntidaoResultado:
    modo: str
    consulta_real_habilitada: bool
    eventos_reais_habilitados: bool
    certificado_configurado: bool
    senha_configurada: bool
    certificado_valido: bool
    pronto_consulta_real: bool
    certificado_info: CertificadoA1Info | None = None
    itens: list[DFeProntidaoItem] = field(default_factory=list)

    @property
    def bloqueios(self) -> list[DFeProntidaoItem]:
        return [item for item in self.itens if item.status == 'bloqueio']


def _modo_configurado() -> str:
    return str(getattr(settings, 'FISCAL_DFE_MODE', 'local') or 'local').strip().lower()


def _senha_certificado_configurada() -> bool:
    return bool(getattr(settings, 'FISCAL_DFE_CERT_PASSWORD', ''))


def _certificado_configurado(config) -> bool:
    return bool(config and config.certificado_digital and config.certificado_nome)


def _ambiente_producao_permitido() -> bool:
    return bool(getattr(settings, 'FISCAL_ALLOW_PRODUCTION_ENVIRONMENT', False))


def _ler_certificado_config(config) -> CertificadoA1Info:
    try:
        with config.certificado_digital.open('rb') as arquivo:
            conteudo = arquivo.read()
    except Exception as exc:
        raise DadosInvalidosError('Certificado A1 nao pode ser lido do armazenamento.') from exc
    return validar_certificado_a1_para_config(
        conteudo,
        getattr(settings, 'FISCAL_DFE_CERT_PASSWORD', ''),
        cnpj_esperado=getattr(config, 'cnpj', ''),
    )


def _ler_bytes_certificado_config(config) -> bytes:
    try:
        with config.certificado_digital.open('rb') as arquivo:
            return arquivo.read()
    except Exception as exc:
        raise DadosInvalidosError('Certificado A1 nao pode ser lido do armazenamento.') from exc


def _somente_digitos(valor: str | None) -> str:
    return ''.join(ch for ch in str(valor or '') if ch.isdigit())


def _codigo_uf(uf: str | None) -> str:
    codigo = UF_CODIGOS.get((uf or '').strip().upper())
    if not codigo:
        raise DadosInvalidosError('UF invalida para consulta DF-e.')
    return codigo


def _tp_ambiente(ambiente: str) -> str:
    return '1' if ambiente == 'producao' else '2'


def _endpoint_sefaz(ambiente: str) -> str:
    if ambiente == 'producao':
        return (
            getattr(settings, 'FISCAL_DFE_SEFAZ_ENDPOINT_PRODUCAO', '')
            or SEFAZ_DFE_ENDPOINTS['producao']
        )
    return (
        getattr(settings, 'FISCAL_DFE_SEFAZ_ENDPOINT_HOMOLOGACAO', '')
        or SEFAZ_DFE_ENDPOINTS['homologacao']
    )


def _normalizar_nsu(nsu: str | None) -> str:
    digitos = _somente_digitos(nsu)
    if not digitos:
        digitos = '0'
    return digitos[-15:].zfill(15)


def _consulta_em_cooldown(config) -> bool:
    minutos = int(getattr(settings, 'FISCAL_DFE_EMPTY_COOLDOWN_MINUTES', 60) or 0)
    if minutos <= 0 or not getattr(config, 'data_ultima_consulta', None):
        return False
    ultimo = _normalizar_nsu(getattr(config, 'ultimo_nsu', ''))
    maximo = _normalizar_nsu(getattr(config, 'max_nsu', ''))
    if ultimo != maximo:
        return False
    return config.data_ultima_consulta > timezone.now() - timedelta(minutes=minutos)


def _montar_dist_dfe(config) -> str:
    documento = _somente_digitos(getattr(config, 'cnpj', ''))
    if len(documento) == 14:
        doc_tag = 'CNPJ'
    elif len(documento) == 11:
        doc_tag = 'CPF'
    else:
        raise DadosInvalidosError('Informe um CNPJ ou CPF valido para consultar DF-e.')

    versao = getattr(settings, 'FISCAL_DFE_DIST_VERSION', '1.01') or '1.01'
    return (
        f'<distDFeInt xmlns="{NFE_NS}" versao="{versao}">'
        f'<tpAmb>{_tp_ambiente(config.ambiente)}</tpAmb>'
        f'<cUFAutor>{_codigo_uf(config.uf)}</cUFAutor>'
        f'<{doc_tag}>{documento}</{doc_tag}>'
        f'<distNSU><ultNSU>{_normalizar_nsu(config.ultimo_nsu)}</ultNSU></distNSU>'
        '</distDFeInt>'
    )


def _montar_envelope_soap(config) -> str:
    dist_dfe = _montar_dist_dfe(config)
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        f'<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        f'xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="{SOAP12_NS}">'
        '<soap12:Body>'
        f'<nfeDistDFeInteresse xmlns="{NFE_DFE_WSDL_NS}">'
        f'<nfeDadosMsg>{dist_dfe}</nfeDadosMsg>'
        '</nfeDistDFeInteresse>'
        '</soap12:Body>'
        '</soap12:Envelope>'
    )


def _local_name(tag: str) -> str:
    return tag.rsplit('}', 1)[-1] if '}' in tag else tag


def _first(root, nome: str):
    return next((el for el in root.iter() if _local_name(el.tag) == nome), None)


def _text(root, nome: str, default: str = '') -> str:
    el = _first(root, nome)
    return (el.text or '').strip() if el is not None and el.text else default


def _decimal_xml(valor: str | None) -> Decimal:
    try:
        return Decimal(str(valor or '0').strip() or '0')
    except Exception:
        return Decimal('0')


def _data_xml(valor: str | None) -> date | None:
    raw = (valor or '').strip()
    if not raw:
        return None
    try:
        return timezone.datetime.fromisoformat(raw[:10]).date()
    except ValueError:
        return None


def _decode_xml_bytes(conteudo: bytes) -> str:
    for encoding in ('utf-8', 'latin1'):
        try:
            return conteudo.decode(encoding)
        except UnicodeDecodeError:
            continue
    return conteudo.decode('utf-8', errors='ignore')


def _parse_doc_zip(doc_zip) -> DFeDocumentoResumo | None:
    conteudo_base64 = (doc_zip.text or '').strip()
    if not conteudo_base64:
        return None
    try:
        xml_texto = _decode_xml_bytes(gzip.decompress(base64.b64decode(conteudo_base64)))
        root = ElementTree.fromstring(xml_texto)
    except Exception as exc:
        raise DadosInvalidosError('Retorno SEFAZ trouxe docZip invalido.') from exc

    nsu = doc_zip.attrib.get('NSU', '')
    schema = (doc_zip.attrib.get('schema', '') or '').lower()
    chave = (
        _text(root, 'chNFe')
        or _somente_digitos((_first(root, 'infNFe').attrib.get('Id', '') if _first(root, 'infNFe') is not None else ''))
    ).replace('NFe', '')
    chave = _somente_digitos(chave)
    if len(chave) != 44:
        return None

    documento = _text(root, 'CNPJ') or _text(root, 'CPF')
    resumo = DFeDocumentoResumo(
        chave_acesso=chave,
        nsu=nsu,
        cnpj_emitente=_somente_digitos(documento),
        razao_social_emitente=_text(root, 'xNome'),
        data_emissao=_data_xml(_text(root, 'dhEmi') or _text(root, 'dEmi') or _text(root, 'dhEvento')),
        valor_total=_decimal_xml(_text(root, 'vNF')),
        xml_resumo=xml_texto,
        xml_completo='',
    )
    if 'procnfe' in schema or _first(root, 'nfeProc') is not None or _first(root, 'NFe') is not None:
        return DFeDocumentoResumo(
            chave_acesso=resumo.chave_acesso,
            nsu=resumo.nsu,
            cnpj_emitente=resumo.cnpj_emitente,
            razao_social_emitente=resumo.razao_social_emitente,
            data_emissao=resumo.data_emissao,
            valor_total=resumo.valor_total,
            xml_resumo='',
            xml_completo=xml_texto,
        )
    return resumo


def _extrair_ret_dist_dfe(xml_resposta: str):
    try:
        root = ElementTree.fromstring(xml_resposta)
    except ElementTree.ParseError as exc:
        raise DadosInvalidosError('Retorno SEFAZ nao e um XML valido.') from exc
    ret = _first(root, 'retDistDFeInt')
    if ret is None:
        raise DadosInvalidosError('Retorno SEFAZ nao trouxe retDistDFeInt.')
    return ret


def _parse_resposta_sefaz(xml_resposta: str) -> DFeConsultaResultado:
    ret = _extrair_ret_dist_dfe(xml_resposta)
    cstat = _text(ret, 'cStat')
    motivo = _text(ret, 'xMotivo')
    ultimo_nsu = _text(ret, 'ultNSU')
    max_nsu = _text(ret, 'maxNSU')

    documentos: list[DFeDocumentoResumo] = []
    if cstat == '138':
        for doc_zip in [el for el in ret.iter() if _local_name(el.tag) == 'docZip']:
            resumo = _parse_doc_zip(doc_zip)
            if resumo:
                documentos.append(resumo)
    elif cstat != '137':
        raise DadosInvalidosError(f'Consulta DF-e rejeitada pela SEFAZ ({cstat}): {motivo}')

    return DFeConsultaResultado(
        documentos=documentos,
        ultimo_nsu=ultimo_nsu,
        max_nsu=max_nsu,
        codigo_status=cstat,
        mensagem=motivo,
        modo='sefaz',
    )


@contextmanager
def _certificado_temporario_pem(config):
    conteudo = _ler_bytes_certificado_config(config)
    senha = getattr(settings, 'FISCAL_DFE_CERT_PASSWORD', '')
    with TemporaryDirectory() as tmpdir:
        pem = exportar_certificado_a1_pem(conteudo, senha, tmpdir)
        yield pem


def avaliar_prontidao_dfe(config) -> DFeProntidaoResultado:
    modo = _modo_configurado()
    consulta_real = bool(getattr(settings, 'FISCAL_DFE_ENABLE_REAL_CONSULTA', False))
    eventos_reais = bool(getattr(settings, 'FISCAL_DFE_ENABLE_REAL_EVENTS', False))
    certificado_ok = _certificado_configurado(config)
    senha_ok = _senha_certificado_configurada()
    modo_real = modo == 'sefaz'
    certificado_info: CertificadoA1Info | None = None
    certificado_valido = False
    itens: list[DFeProntidaoItem] = []

    if modo in {'local', 'fake', 'dry-run', 'dryrun'}:
        itens.append(DFeProntidaoItem(
            codigo='modo_local',
            titulo='Modo local seguro',
            mensagem='Nenhuma consulta externa sera feita enquanto FISCAL_DFE_MODE estiver local.',
            status='ok',
        ))
    elif modo_real:
        itens.append(DFeProntidaoItem(
            codigo='modo_sefaz',
            titulo='Modo SEFAZ selecionado',
            mensagem='Consulta real continua bloqueada ate todas as travas ficarem verdes.',
            status='aviso',
        ))
    else:
        itens.append(DFeProntidaoItem(
            codigo='modo_invalido',
            titulo='Modo DF-e invalido',
            mensagem=f'Modo configurado: {modo}. Use local ou sefaz.',
            status='bloqueio',
        ))

    if consulta_real:
        itens.append(DFeProntidaoItem(
            codigo='consulta_real',
            titulo='Flag de consulta real ligada',
            mensagem='FISCAL_DFE_ENABLE_REAL_CONSULTA esta ativa.',
            status='ok' if modo_real else 'aviso',
        ))
    else:
        itens.append(DFeProntidaoItem(
            codigo='consulta_real_bloqueada',
            titulo='Consulta real bloqueada',
            mensagem='FISCAL_DFE_ENABLE_REAL_CONSULTA esta desligada.',
            status='bloqueio' if modo_real else 'ok',
        ))

    if certificado_ok:
        itens.append(DFeProntidaoItem(
            codigo='certificado_ok',
            titulo='Certificado A1 anexado',
            mensagem='O ERP tem um arquivo de certificado configurado para esta filial.',
            status='ok',
        ))
    else:
        itens.append(DFeProntidaoItem(
            codigo='certificado_ausente',
            titulo='Certificado A1 ausente',
            mensagem='Anexe um .pfx ou .p12 apenas quando formos testar a consulta real.',
            status='bloqueio' if modo_real else 'aviso',
        ))

    if senha_ok:
        itens.append(DFeProntidaoItem(
            codigo='senha_ok',
            titulo='Senha em variavel de ambiente',
            mensagem='FISCAL_DFE_CERT_PASSWORD esta configurada sem ser salva no banco.',
            status='ok',
        ))
    else:
        itens.append(DFeProntidaoItem(
            codigo='senha_ausente',
            titulo='Senha fora do banco',
            mensagem='Quando chegar o teste real, informe a senha via FISCAL_DFE_CERT_PASSWORD.',
            status='bloqueio' if modo_real else 'aviso',
        ))

    if certificado_ok and senha_ok:
        try:
            certificado_info = _ler_certificado_config(config)
            certificado_valido = True
            itens.append(DFeProntidaoItem(
                codigo='certificado_validado',
                titulo='Certificado A1 validado offline',
                mensagem=(
                    f'CNPJ {certificado_info.cnpj or "nao identificado"}; '
                    f'validade ate {certificado_info.not_after:%d/%m/%Y}.'
                ),
                status='ok',
            ))
        except DadosInvalidosError as exc:
            itens.append(DFeProntidaoItem(
                codigo='certificado_invalido',
                titulo='Certificado A1 nao validado',
                mensagem=str(exc),
                status='bloqueio',
            ))

    if eventos_reais:
        itens.append(DFeProntidaoItem(
            codigo='eventos_reais',
            titulo='Eventos reais habilitados',
            mensagem='Acoes reais de manifestacao exigem autorizacao explicita antes de uso.',
            status='aviso',
        ))
    else:
        itens.append(DFeProntidaoItem(
            codigo='eventos_reais_bloqueados',
            titulo='Eventos reais bloqueados',
            mensagem='Ciencia, desconhecimento e operacao nao realizada seguem apenas locais.',
            status='ok',
        ))

    if config and config.ambiente == 'producao':
        itens.append(DFeProntidaoItem(
            codigo='ambiente_producao',
            titulo='Ambiente producao',
            mensagem=(
                'Ambiente producao bloqueado por padrao. '
                'Use homologacao ate liberar FISCAL_ALLOW_PRODUCTION_ENVIRONMENT.'
            ),
            status='ok' if _ambiente_producao_permitido() else 'bloqueio',
        ))

    pronto = (
        modo_real and consulta_real and certificado_ok and senha_ok
        and certificado_valido
        and (not config or config.ambiente != 'producao' or _ambiente_producao_permitido())
    )
    return DFeProntidaoResultado(
        modo=modo,
        consulta_real_habilitada=consulta_real,
        eventos_reais_habilitados=eventos_reais,
        certificado_configurado=certificado_ok,
        senha_configurada=senha_ok,
        certificado_valido=certificado_valido,
        pronto_consulta_real=pronto,
        certificado_info=certificado_info,
        itens=itens,
    )


class DFeClientBase:
    modo = 'base'

    def consultar_documentos(self, config) -> DFeConsultaResultado:
        raise NotImplementedError

    def manifestar(self, documento, evento: str):
        raise DadosInvalidosError(
            'Eventos fiscais reais estao bloqueados nesta etapa. '
            'A manifestacao registrada no ERP e apenas local.'
        )


class LocalDFeClient(DFeClientBase):
    modo = 'local'

    def consultar_documentos(self, config) -> DFeConsultaResultado:
        return DFeConsultaResultado(
            documentos=[],
            ultimo_nsu=config.ultimo_nsu,
            mensagem='Consulta DF-e executada em modo local seguro; nenhum acesso a SEFAZ foi feito.',
            modo=self.modo,
        )


class SefazDFeClient(DFeClientBase):
    modo = 'sefaz'

    def consultar_documentos(self, config) -> DFeConsultaResultado:
        prontidao = avaliar_prontidao_dfe(config)
        if not prontidao.consulta_real_habilitada:
            raise DadosInvalidosError(
                'Consulta real SEFAZ bloqueada por seguranca. '
                'Ative apenas depois de configurar certificado em ambiente controlado.'
            )
        if not prontidao.certificado_configurado:
            raise DadosInvalidosError('Consulta real SEFAZ bloqueada: certificado A1 nao configurado.')
        if not prontidao.senha_configurada:
            raise DadosInvalidosError(
                'Consulta real SEFAZ bloqueada: senha do certificado nao configurada '
                'em FISCAL_DFE_CERT_PASSWORD.'
            )
        if not prontidao.certificado_valido:
            raise DadosInvalidosError(
                'Consulta real SEFAZ bloqueada: certificado A1 nao validado offline.'
            )
        if config.ambiente == 'producao' and not _ambiente_producao_permitido():
            raise DadosInvalidosError(
                'Consulta real SEFAZ em producao bloqueada por seguranca. '
                'Use homologacao ou libere explicitamente FISCAL_ALLOW_PRODUCTION_ENVIRONMENT.'
            )
        if _consulta_em_cooldown(config):
            raise DadosInvalidosError(
                'Consulta DF-e bloqueada temporariamente: ultimo NSU ja alcancou o maxNSU. '
                'Aguarde antes de consultar novamente para evitar consumo indevido na SEFAZ.'
            )

        envelope = _montar_envelope_soap(config)
        timeout = int(getattr(settings, 'FISCAL_DFE_SEFAZ_TIMEOUT', 30) or 30)
        headers = {
            'Content-Type': (
                'application/soap+xml; charset=utf-8; '
                f'action="{NFE_DFE_WSDL_NS}/nfeDistDFeInteresse"'
            ),
        }
        try:
            with _certificado_temporario_pem(config) as pem:
                resposta = requests.post(
                    _endpoint_sefaz(config.ambiente),
                    data=envelope.encode('utf-8'),
                    headers=headers,
                    cert=(pem.certificado_path, pem.chave_path),
                    timeout=timeout,
                )
            resposta.raise_for_status()
        except requests.RequestException as exc:
            raise DadosInvalidosError(f'Falha de comunicacao com a SEFAZ DF-e: {exc}') from exc

        return _parse_resposta_sefaz(resposta.text)


def get_dfe_client() -> DFeClientBase:
    modo = _modo_configurado()
    if modo in {'local', 'fake', 'dry-run', 'dryrun'}:
        return LocalDFeClient()
    if modo == 'sefaz':
        return SefazDFeClient()
    raise DadosInvalidosError(f'Modo DF-e invalido: {modo}.')
