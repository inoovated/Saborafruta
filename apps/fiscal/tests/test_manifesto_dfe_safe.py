import base64
import gzip
from datetime import date, datetime, timedelta, timezone as dt_timezone
from decimal import Decimal
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.core.models import Empresa, Filial, PerfilAcesso, Usuario
from apps.core.services.exceptions import DadosInvalidosError
from apps.fiscal.integrations.dfe_client import (
    DFeConsultaResultado, DFeDocumentoResumo, LocalDFeClient,
)
from apps.fiscal.models import ManifestoFiscalConfig, ManifestoFiscalDocumento, ManifestoFiscalLog
from apps.fiscal.services.manifesto_service import ManifestoFiscalService
from apps.fiscal.views import ManifestoFiscalConfigView, ManifestoFiscalListView


class FakeDFeClient:
    def __init__(self, documentos):
        self.documentos = documentos

    def consultar_documentos(self, config):
        return DFeConsultaResultado(
            documentos=self.documentos,
            ultimo_nsu='99',
            mensagem='Consulta fake concluida.',
            modo='fake',
        )


class FakeHttpResponse:
    def __init__(self, text):
        self.text = text
        self.status_code = 200

    def raise_for_status(self):
        return None


class ManifestoDFeSafeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa = Empresa.objects.create(
            razao_social='Empresa DFe LTDA',
            nome_fantasia='DFe',
            cnpj='61234567000191',
            regime_tributario=Empresa.RegimeTributario.SIMPLES_NACIONAL,
            codigo_regime_tributario=1,
        )
        cls.filial = Filial.objects.create(
            empresa=cls.empresa,
            razao_social='Filial DFe',
            nome_fantasia='DFe RN',
            cnpj='61234567000192',
            uf='RN',
        )
        cls.perfil = PerfilAcesso.objects.create(
            empresa=cls.empresa,
            nome='Admin DFe',
            is_admin=True,
        )
        cls.usuario = Usuario.objects.create_user(
            email='dfe-test@inoovated.com',
            nome='Usuario DFe',
            password='teste1234',
            empresa=cls.empresa,
            filial=cls.filial,
            perfil=cls.perfil,
        )

    def setUp(self):
        self.factory = RequestFactory()

    def request(self, method, path, data=None):
        if method == 'post':
            request = self.factory.post(path, data or {})
        else:
            request = self.factory.get(path, data or {})
        request.user = self.usuario
        request.filial_ativa = self.filial
        request.session = {}
        request._messages = FallbackStorage(request)
        return request

    def criar_config(self):
        return ManifestoFiscalConfig.objects.create(
            filial=self.filial,
            cnpj=self.filial.cnpj,
            uf=self.filial.uf,
            ambiente=ManifestoFiscalConfig.Ambiente.HOMOLOGACAO,
            ativo=True,
        )

    def pfx_teste(self, cnpj=None, senha='senha-controlada'):
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives.serialization import pkcs12
        from cryptography.x509.oid import NameOID

        cnpj = cnpj or self.filial.cnpj
        chave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, 'BR'),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'ICP-Brasil Teste'),
            x509.NameAttribute(NameOID.COMMON_NAME, f'EMPRESA TESTE:{cnpj}'),
        ])
        agora = datetime.now(dt_timezone.utc)
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(chave.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(agora - timedelta(days=1))
            .not_valid_after(agora + timedelta(days=365))
            .sign(chave, hashes.SHA256())
        )
        return pkcs12.serialize_key_and_certificates(
            name=b'teste-a1',
            key=chave,
            cert=cert,
            cas=None,
            encryption_algorithm=serialization.BestAvailableEncryption(senha.encode('utf-8')),
        )

    def salvar_certificado_config(self, config, cnpj=None, senha='senha-controlada'):
        conteudo = self.pfx_teste(cnpj=cnpj, senha=senha)
        config.certificado_digital.save('teste.pfx', ContentFile(conteudo), save=False)
        config.certificado_nome = 'teste.pfx'
        config.save(update_fields=['certificado_digital', 'certificado_nome', 'updated_at'])
        return conteudo

    def chave(self, numero='000000123', cnpj='11222333000144'):
        return f'242605{cnpj}55001{numero}1123456789'

    def xml_nfe_resposta(self, chave=None):
        chave = chave or self.chave(numero='000000401')
        return f'''<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
  <NFe>
    <infNFe Id="NFe{chave}" versao="4.00">
      <ide><dhEmi>2026-05-18T10:30:00-03:00</dhEmi></ide>
      <emit><CNPJ>11222333000144</CNPJ><xNome>Fornecedor SEFAZ LTDA</xNome></emit>
      <total><ICMSTot><vNF>321.45</vNF></ICMSTot></total>
    </infNFe>
  </NFe>
</nfeProc>'''

    def soap_dist_dfe(self, cstat='138', motivo='Documento localizado', ultimo='000000000000401', maximo='000000000000450', docs=None):
        docs_xml = ''
        for nsu, schema, xml_texto in docs or []:
            compactado = base64.b64encode(gzip.compress(xml_texto.encode('utf-8'))).decode('ascii')
            docs_xml += f'<docZip NSU="{nsu}" schema="{schema}">{compactado}</docZip>'
        lote = f'<loteDistDFeInt>{docs_xml}</loteDistDFeInt>' if docs_xml else ''
        return f'''<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
  <soap:Body>
    <nfeDistDFeInteresseResponse xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe">
      <nfeDistDFeInteresseResult>
        <retDistDFeInt xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.01">
          <tpAmb>2</tpAmb><verAplic>AN_1.0</verAplic><cStat>{cstat}</cStat>
          <xMotivo>{motivo}</xMotivo><dhResp>2026-05-19T10:00:00-03:00</dhResp>
          <ultNSU>{ultimo}</ultNSU><maxNSU>{maximo}</maxNSU>{lote}
        </retDistDFeInt>
      </nfeDistDFeInteresseResult>
    </nfeDistDFeInteresseResponse>
  </soap:Body>
</soap:Envelope>'''

    @override_settings(
        FISCAL_DFE_MODE='local',
        FISCAL_DFE_ENABLE_REAL_CONSULTA=False,
        FISCAL_DFE_ENABLE_REAL_EVENTS=False,
    )
    def test_consulta_local_nao_acessa_sefaz_nem_cria_documento_fake(self):
        self.criar_config()

        resultado = ManifestoFiscalService.sincronizar_documentos(self.filial, self.usuario)

        log = ManifestoFiscalLog.objects.get()
        self.assertEqual(resultado.modo, 'local')
        self.assertEqual(resultado.total_documentos, 0)
        self.assertFalse(ManifestoFiscalDocumento.objects.exists())
        self.assertEqual(log.tipo_evento, 'consulta_dfe_local')
        self.assertEqual(log.codigo_status, 'ERP-LOCAL')
        self.assertNotIn('senha', str(log.requisicao_resumo).lower())
        self.assertNotIn('certificado', str(log.retorno_resumo).lower())

    @override_settings(
        FISCAL_DFE_MODE='sefaz',
        FISCAL_DFE_ENABLE_REAL_CONSULTA=False,
        FISCAL_DFE_ENABLE_REAL_EVENTS=False,
    )
    def test_consulta_sefaz_real_fica_bloqueada_por_padrao(self):
        self.criar_config()

        with self.assertRaisesMessage(DadosInvalidosError, 'bloqueada'):
            ManifestoFiscalService.sincronizar_documentos(self.filial, self.usuario)

        self.assertFalse(ManifestoFiscalDocumento.objects.exists())
        self.assertFalse(ManifestoFiscalLog.objects.exists())

    @override_settings(
        FISCAL_DFE_MODE='sefaz',
        FISCAL_DFE_ENABLE_REAL_CONSULTA=True,
        FISCAL_DFE_ENABLE_REAL_EVENTS=False,
        FISCAL_DFE_CERT_PASSWORD='',
    )
    def test_consulta_sefaz_real_exige_certificado_a1(self):
        self.criar_config()

        with self.assertRaisesMessage(DadosInvalidosError, 'certificado A1'):
            ManifestoFiscalService.sincronizar_documentos(self.filial, self.usuario)

        self.assertFalse(ManifestoFiscalDocumento.objects.exists())
        self.assertFalse(ManifestoFiscalLog.objects.exists())

    @override_settings(
        FISCAL_DFE_MODE='sefaz',
        FISCAL_DFE_ENABLE_REAL_CONSULTA=True,
        FISCAL_DFE_ENABLE_REAL_EVENTS=False,
        FISCAL_DFE_CERT_PASSWORD='',
    )
    def test_consulta_sefaz_real_exige_senha_fora_do_banco(self):
        config = self.criar_config()
        config.certificado_digital.name = 'fiscal/certificados/teste.pfx'
        config.certificado_nome = 'teste.pfx'
        config.save(update_fields=['certificado_digital', 'certificado_nome', 'updated_at'])

        with self.assertRaisesMessage(DadosInvalidosError, 'FISCAL_DFE_CERT_PASSWORD'):
            ManifestoFiscalService.sincronizar_documentos(self.filial, self.usuario)

        self.assertFalse(ManifestoFiscalDocumento.objects.exists())
        self.assertFalse(ManifestoFiscalLog.objects.exists())

    def test_consulta_sefaz_real_em_homologacao_importa_doczip_mockado(self):
        with TemporaryDirectory() as media_root, self.settings(
            MEDIA_ROOT=media_root,
            FISCAL_DFE_MODE='sefaz',
            FISCAL_DFE_ENABLE_REAL_CONSULTA=True,
            FISCAL_DFE_ENABLE_REAL_EVENTS=False,
            FISCAL_DFE_CERT_PASSWORD='senha-controlada',
        ):
            config = self.criar_config()
            self.salvar_certificado_config(config)
            chave = self.chave(numero='000000401')
            resposta = self.soap_dist_dfe(
                docs=[('000000000000401', 'procNFe_v4.00.xsd', self.xml_nfe_resposta(chave))],
            )

            with patch('apps.fiscal.integrations.dfe_client.requests.post') as post:
                post.return_value = FakeHttpResponse(resposta)
                resultado = ManifestoFiscalService.sincronizar_documentos(self.filial, self.usuario)

            config.refresh_from_db()
            documento = ManifestoFiscalDocumento.objects.get(chave_acesso=chave)
            chamada = post.call_args.kwargs
            self.assertIn('hom1.nfe.fazenda.gov.br', post.call_args.args[0])
            self.assertIn(b'<tpAmb>2</tpAmb>', chamada['data'])
            self.assertEqual(resultado.modo, 'sefaz')
            self.assertEqual(resultado.total_documentos, 1)
            self.assertEqual(resultado.criados, 1)
            self.assertEqual(config.ultimo_nsu, '000000000000401')
            self.assertEqual(config.max_nsu, '000000000000450')
            self.assertEqual(documento.status_download_xml, ManifestoFiscalDocumento.StatusDownload.XML_BAIXADO)
            self.assertIn('<nfeProc', documento.xml_completo)
            self.assertEqual(ManifestoFiscalLog.objects.get().codigo_status, '138')

    def test_consulta_sefaz_real_em_homologacao_sem_documentos_mockado(self):
        with TemporaryDirectory() as media_root, self.settings(
            MEDIA_ROOT=media_root,
            FISCAL_DFE_MODE='sefaz',
            FISCAL_DFE_ENABLE_REAL_CONSULTA=True,
            FISCAL_DFE_ENABLE_REAL_EVENTS=False,
            FISCAL_DFE_CERT_PASSWORD='senha-controlada',
        ):
            config = self.criar_config()
            self.salvar_certificado_config(config)
            resposta = self.soap_dist_dfe(
                cstat='137',
                motivo='Nenhum documento localizado',
                ultimo='000000000000010',
                maximo='000000000000010',
            )

            with patch('apps.fiscal.integrations.dfe_client.requests.post') as post:
                post.return_value = FakeHttpResponse(resposta)
                resultado = ManifestoFiscalService.sincronizar_documentos(self.filial, self.usuario)

            config.refresh_from_db()
            self.assertEqual(resultado.total_documentos, 0)
            self.assertEqual(config.ultimo_nsu, '000000000000010')
            self.assertEqual(config.max_nsu, '000000000000010')
            self.assertEqual(ManifestoFiscalLog.objects.get().codigo_status, '137')
            self.assertFalse(ManifestoFiscalDocumento.objects.exists())

    def test_consulta_sefaz_real_respeita_cooldown_quando_nsu_no_limite(self):
        with TemporaryDirectory() as media_root, self.settings(
            MEDIA_ROOT=media_root,
            FISCAL_DFE_MODE='sefaz',
            FISCAL_DFE_ENABLE_REAL_CONSULTA=True,
            FISCAL_DFE_ENABLE_REAL_EVENTS=False,
            FISCAL_DFE_CERT_PASSWORD='senha-controlada',
        ):
            config = self.criar_config()
            self.salvar_certificado_config(config)
            config.ultimo_nsu = '000000000000010'
            config.max_nsu = '000000000000010'
            config.data_ultima_consulta = timezone.now()
            config.save(update_fields=['ultimo_nsu', 'max_nsu', 'data_ultima_consulta', 'updated_at'])

            with patch('apps.fiscal.integrations.dfe_client.requests.post') as post:
                with self.assertRaisesMessage(DadosInvalidosError, 'consumo indevido'):
                    ManifestoFiscalService.sincronizar_documentos(self.filial, self.usuario)

            post.assert_not_called()
            self.assertFalse(ManifestoFiscalLog.objects.exists())

    def test_evento_fiscal_real_fica_bloqueado_no_client(self):
        with self.assertRaisesMessage(DadosInvalidosError, 'Eventos fiscais reais estao bloqueados'):
            LocalDFeClient().manifestar(None, 'ciencia')

    def test_sync_com_client_fake_cria_documento_sem_tocar_estoque(self):
        config = self.criar_config()
        resumo = DFeDocumentoResumo(
            chave_acesso=self.chave(numero='000000301'),
            nsu='301',
            cnpj_emitente='11222333000144',
            razao_social_emitente='Fornecedor DFe LTDA',
            data_emissao=date(2026, 5, 18),
            valor_total=Decimal('125.50'),
            xml_resumo='<resNFe />',
        )

        resultado = ManifestoFiscalService.sincronizar_documentos(
            self.filial,
            self.usuario,
            client=FakeDFeClient([resumo]),
        )

        config.refresh_from_db()
        documento = ManifestoFiscalDocumento.objects.get(chave_acesso=resumo.chave_acesso)
        log = ManifestoFiscalLog.objects.get()
        self.assertEqual(resultado.total_documentos, 1)
        self.assertEqual(resultado.criados, 1)
        self.assertEqual(config.ultimo_nsu, '99')
        self.assertEqual(documento.nsu, '301')
        self.assertEqual(documento.razao_social_emitente, 'Fornecedor DFe LTDA')
        self.assertEqual(documento.status_download_xml, ManifestoFiscalDocumento.StatusDownload.RESUMO)
        self.assertIsNone(documento.entrada_nf)
        self.assertEqual(log.retorno_resumo['criados'], 1)

    def test_sync_nao_rebaixa_documento_ja_importado(self):
        self.criar_config()
        documento = ManifestoFiscalDocumento.objects.create(
            filial=self.filial,
            chave_acesso=self.chave(numero='000000302'),
            status_download_xml=ManifestoFiscalDocumento.StatusDownload.IMPORTADA,
        )
        resumo = DFeDocumentoResumo(
            chave_acesso=documento.chave_acesso,
            nsu='302',
            xml_resumo='<resNFe />',
        )

        resultado = ManifestoFiscalService.sincronizar_documentos(
            self.filial,
            self.usuario,
            client=FakeDFeClient([resumo]),
        )

        documento.refresh_from_db()
        self.assertEqual(resultado.atualizados, 1)
        self.assertEqual(documento.status_download_xml, ManifestoFiscalDocumento.StatusDownload.IMPORTADA)
        self.assertEqual(ManifestoFiscalDocumento.objects.count(), 1)

    def test_view_consultar_usa_modo_local_seguro(self):
        self.criar_config()

        request = self.request('post', reverse('fiscal:manifesto-list'))
        response = ManifestoFiscalListView.as_view()(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('fiscal:manifesto-list'))
        self.assertEqual(ManifestoFiscalLog.objects.get().tipo_evento, 'consulta_dfe_local')

    def test_config_view_exibe_prontidao_segura_sem_certificado(self):
        self.criar_config()

        request = self.request('get', reverse('fiscal:manifesto-config'))
        response = ManifestoFiscalConfigView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Prontidao da integracao')
        self.assertContains(response, 'Modo local seguro')
        self.assertContains(response, 'Certificado A1 ausente')
        self.assertContains(response, 'Eventos reais bloqueados')

    def test_config_rejeita_certificado_com_extensao_invalida(self):
        arquivo = SimpleUploadedFile('certificado.txt', b'conteudo', content_type='text/plain')
        request = self.request('post', reverse('fiscal:manifesto-config'), {
            'cnpj': self.filial.cnpj,
            'uf': self.filial.uf,
            'ambiente': ManifestoFiscalConfig.Ambiente.HOMOLOGACAO,
            'ultimo_nsu': '',
            'certificado_digital': arquivo,
        })

        response = ManifestoFiscalConfigView.as_view()(request)

        config = ManifestoFiscalConfig.objects.get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(config.certificado_nome, '')

    def test_config_bloqueia_ambiente_producao_por_padrao(self):
        request = self.request('post', reverse('fiscal:manifesto-config'), {
            'cnpj': self.filial.cnpj,
            'uf': self.filial.uf,
            'ambiente': ManifestoFiscalConfig.Ambiente.PRODUCAO,
            'ultimo_nsu': '',
        })

        response = ManifestoFiscalConfigView.as_view()(request)

        config = ManifestoFiscalConfig.objects.get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(config.ambiente, ManifestoFiscalConfig.Ambiente.HOMOLOGACAO)

    def test_config_valida_certificado_a1_e_salva_metadados(self):
        with TemporaryDirectory() as media_root, self.settings(
            MEDIA_ROOT=media_root,
            FISCAL_DFE_CERT_PASSWORD='senha-controlada',
        ):
            arquivo = SimpleUploadedFile(
                'certificado.pfx',
                self.pfx_teste(),
                content_type='application/x-pkcs12',
            )
            request = self.request('post', reverse('fiscal:manifesto-config'), {
                'cnpj': self.filial.cnpj,
                'uf': self.filial.uf,
                'ambiente': ManifestoFiscalConfig.Ambiente.HOMOLOGACAO,
                'ultimo_nsu': '',
                'certificado_digital': arquivo,
            })

            response = ManifestoFiscalConfigView.as_view()(request)

            config = ManifestoFiscalConfig.objects.get()
            self.assertEqual(response.status_code, 302)
            self.assertEqual(config.certificado_nome, 'certificado.pfx')
            self.assertEqual(config.certificado_cnpj, self.filial.cnpj)
            self.assertTrue(config.certificado_thumbprint)
            self.assertIsNotNone(config.certificado_validade_fim)

    def test_config_recusa_certificado_de_outro_cnpj_quando_tem_senha(self):
        with TemporaryDirectory() as media_root, self.settings(
            MEDIA_ROOT=media_root,
            FISCAL_DFE_CERT_PASSWORD='senha-controlada',
        ):
            arquivo = SimpleUploadedFile(
                'certificado.pfx',
                self.pfx_teste(cnpj='11222333000144'),
                content_type='application/x-pkcs12',
            )
            request = self.request('post', reverse('fiscal:manifesto-config'), {
                'cnpj': self.filial.cnpj,
                'uf': self.filial.uf,
                'ambiente': ManifestoFiscalConfig.Ambiente.HOMOLOGACAO,
                'ultimo_nsu': '',
                'certificado_digital': arquivo,
            })

            response = ManifestoFiscalConfigView.as_view()(request)

            config = ManifestoFiscalConfig.objects.get()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(config.certificado_nome, '')
