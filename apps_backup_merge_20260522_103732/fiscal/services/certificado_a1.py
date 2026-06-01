"""Validacao offline de certificado digital A1.

Este modulo nunca chama SEFAZ. Ele apenas abre o PFX/P12 com a senha informada
em memoria para validar metadados publicos e a presenca da chave privada.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone as dt_timezone
from pathlib import Path
from re import sub

from django.utils import timezone

from apps.core.services.exceptions import DadosInvalidosError


ICP_BRASIL_CNPJ_OID = '2.16.76.1.3.3'


@dataclass(frozen=True)
class CertificadoA1Info:
    subject: str
    issuer: str
    serial_number: str
    thumbprint: str
    cnpj: str
    not_before: datetime
    not_after: datetime
    has_private_key: bool

    @property
    def valido_agora(self) -> bool:
        agora = timezone.now()
        return self.not_before <= agora <= self.not_after


@dataclass(frozen=True)
class CertificadoA1Pem:
    certificado_path: str
    chave_path: str


def somente_digitos(valor: str | None) -> str:
    return sub(r'\D+', '', valor or '')


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=dt_timezone.utc)
    return dt


def _validade_certificado(certificado, attr_utc: str, attr_legacy: str) -> datetime:
    valor = getattr(certificado, attr_utc, None)
    if valor is None:
        valor = getattr(certificado, attr_legacy)
    return _aware(valor)


def _decode_asn1_string(raw: bytes) -> str:
    if not raw:
        return ''
    tag = raw[0]
    if tag not in {0x0c, 0x13, 0x16}:  # UTF8String, PrintableString, IA5String
        try:
            return raw.decode('utf-8', errors='ignore')
        except Exception:
            return ''
    if len(raw) < 2:
        return ''
    length = raw[1]
    start = 2
    if length & 0x80:
        len_bytes = length & 0x7F
        if len(raw) < 2 + len_bytes:
            return ''
        length = int.from_bytes(raw[2:2 + len_bytes], 'big')
        start = 2 + len_bytes
    return raw[start:start + length].decode('utf-8', errors='ignore')


def _cnpj_subject_alternative_name(cert) -> str:
    from cryptography import x509
    from cryptography.x509.oid import ExtensionOID, ObjectIdentifier

    try:
        san = cert.extensions.get_extension_for_oid(
            ExtensionOID.SUBJECT_ALTERNATIVE_NAME,
        ).value
    except x509.ExtensionNotFound:
        return ''

    cnpj_oid = ObjectIdentifier(ICP_BRASIL_CNPJ_OID)
    for item in san:
        if isinstance(item, x509.OtherName) and item.type_id == cnpj_oid:
            cnpj = somente_digitos(_decode_asn1_string(item.value))
            if len(cnpj) == 14:
                return cnpj
    return ''


def _cnpj_subject_cn(cert) -> str:
    from cryptography.x509.oid import NameOID

    for attr in cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME):
        valor = attr.value or ''
        if ':' in valor:
            cnpj = somente_digitos(valor.rsplit(':', 1)[-1])
            if len(cnpj) == 14:
                return cnpj
    return ''


def inspecionar_certificado_a1(conteudo: bytes, senha: str) -> CertificadoA1Info:
    if not senha:
        raise DadosInvalidosError('Senha do certificado A1 nao informada para validacao offline.')
    if not conteudo:
        raise DadosInvalidosError('Arquivo de certificado A1 vazio.')

    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.serialization import pkcs12
    except ImportError as exc:
        raise DadosInvalidosError(
            'Dependencia cryptography ausente para validar certificado A1.',
        ) from exc

    try:
        chave_privada, certificado, _ = pkcs12.load_key_and_certificates(
            conteudo,
            senha.encode('utf-8'),
        )
    except Exception as exc:
        raise DadosInvalidosError(
            'Nao foi possivel abrir o certificado A1 com a senha configurada.',
        ) from exc

    if certificado is None:
        raise DadosInvalidosError('Certificado A1 nao encontrado dentro do arquivo informado.')

    cnpj = _cnpj_subject_alternative_name(certificado) or _cnpj_subject_cn(certificado)
    return CertificadoA1Info(
        subject=certificado.subject.rfc4514_string(),
        issuer=certificado.issuer.rfc4514_string(),
        serial_number=format(certificado.serial_number, 'X'),
        thumbprint=certificado.fingerprint(hashes.SHA1()).hex().upper(),
        cnpj=cnpj,
        not_before=_validade_certificado(
            certificado,
            'not_valid_before_utc',
            'not_valid_before',
        ),
        not_after=_validade_certificado(
            certificado,
            'not_valid_after_utc',
            'not_valid_after',
        ),
        has_private_key=chave_privada is not None,
    )


def exportar_certificado_a1_pem(conteudo: bytes, senha: str, diretorio: str | Path) -> CertificadoA1Pem:
    """Materializa certificado/chave em PEM temporario para clientes mTLS.

    O arquivo deve ser criado em um diretorio temporario e descartado logo apos a
    requisicao. A senha nunca e gravada; a chave privada fica sem criptografia
    apenas nesse arquivo efemero porque a biblioteca HTTP precisa le-la.
    """
    if not senha:
        raise DadosInvalidosError('Senha do certificado A1 nao informada para exportacao mTLS.')
    if not conteudo:
        raise DadosInvalidosError('Arquivo de certificado A1 vazio.')

    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.serialization import pkcs12
    except ImportError as exc:
        raise DadosInvalidosError(
            'Dependencia cryptography ausente para preparar certificado A1.',
        ) from exc

    try:
        chave_privada, certificado, cadeia = pkcs12.load_key_and_certificates(
            conteudo,
            senha.encode('utf-8'),
        )
    except Exception as exc:
        raise DadosInvalidosError(
            'Nao foi possivel abrir o certificado A1 com a senha configurada.',
        ) from exc

    if certificado is None or chave_privada is None:
        raise DadosInvalidosError('Certificado A1 precisa conter certificado e chave privada.')

    pasta = Path(diretorio)
    pasta.mkdir(parents=True, exist_ok=True)
    cert_path = pasta / 'certificado.pem'
    key_path = pasta / 'chave.pem'

    cert_bytes = certificado.public_bytes(serialization.Encoding.PEM)
    for cert_cadeia in cadeia or []:
        cert_bytes += cert_cadeia.public_bytes(serialization.Encoding.PEM)

    key_bytes = chave_privada.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    cert_path.write_bytes(cert_bytes)
    key_path.write_bytes(key_bytes)
    key_path.chmod(0o600)
    return CertificadoA1Pem(str(cert_path), str(key_path))


def validar_certificado_a1_para_config(
    conteudo: bytes,
    senha: str,
    cnpj_esperado: str = '',
) -> CertificadoA1Info:
    info = inspecionar_certificado_a1(conteudo, senha)
    bloqueios: list[str] = []
    hoje = timezone.now()
    esperado = somente_digitos(cnpj_esperado)

    if not info.has_private_key:
        bloqueios.append('arquivo sem chave privada')
    if info.not_after < hoje:
        bloqueios.append('certificado vencido')
    if info.not_before > hoje:
        bloqueios.append('certificado ainda nao vigente')
    if esperado and info.cnpj and info.cnpj != esperado:
        bloqueios.append('CNPJ do certificado diferente do CNPJ configurado')
    if esperado and not info.cnpj:
        bloqueios.append('CNPJ do certificado nao identificado')

    if bloqueios:
        raise DadosInvalidosError(f'Certificado A1 invalido: {", ".join(bloqueios)}.')
    return info
