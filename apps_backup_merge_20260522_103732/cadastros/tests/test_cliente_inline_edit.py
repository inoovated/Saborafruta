import json

from django.test import RequestFactory, TestCase

from apps.cadastros.models import Cliente, ClienteFilial
from apps.cadastros.views.cliente import ClienteInlineEditView
from apps.core.models import Empresa, Filial, PerfilAcesso, Usuario


class ClienteInlineEditTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa = Empresa.objects.create(
            razao_social='Empresa Cliente LTDA',
            nome_fantasia='Empresa Cliente',
            cnpj='62345678000191',
            regime_tributario=Empresa.RegimeTributario.SIMPLES_NACIONAL,
            codigo_regime_tributario=1,
        )
        cls.filial = Filial.objects.create(
            empresa=cls.empresa,
            razao_social='Filial Cliente',
            nome_fantasia='Filial Cliente',
            cnpj='62345678000192',
            uf='RN',
        )
        cls.perfil = PerfilAcesso.objects.create(
            empresa=cls.empresa,
            nome='Administrador',
            is_admin=True,
        )
        cls.usuario = Usuario.objects.create_user(
            email='cliente-inline@inoovated.com',
            nome='Usuario Cliente',
            password='teste1234',
            empresa=cls.empresa,
            filial=cls.filial,
            perfil=cls.perfil,
        )

    def setUp(self):
        self.factory = RequestFactory()

    def criar_cliente(self, **kwargs):
        dados = {
            'filial': self.filial,
            'tipo_pessoa': 'F',
            'razao_social': 'Cliente Teste',
            'cpf_cnpj': '12345678901',
            'cidade': 'Mossoro',
            'uf': 'RN',
            'telefone': '84999990000',
        }
        dados.update(kwargs)
        cliente = Cliente.objects.create(**dados)
        ClienteFilial.objects.create(cliente=cliente, filial=self.filial)
        return cliente

    def post_inline(self, cliente, field, value):
        request = self.factory.post(
            f'/cadastros/clientes/{cliente.pk}/inline-edit/',
            {'field': field, 'value': value},
        )
        request.user = self.usuario
        request.filial_ativa = self.filial
        return ClienteInlineEditView.as_view()(request, pk=cliente.pk)

    def payload(self, response):
        return json.loads(response.content.decode('utf-8'))

    def test_edita_nome_documento_cidade_e_contato(self):
        cliente = self.criar_cliente()

        resposta_nome = self.post_inline(cliente, 'nome', 'Cliente Novo')
        resposta_doc = self.post_inline(cliente, 'cpf_cnpj', '11.222.333/0001-44')
        resposta_cidade = self.post_inline(cliente, 'cidade', 'Natal')
        resposta_contato = self.post_inline(cliente, 'telefone', '(84) 98888-7777')

        cliente.refresh_from_db()
        self.assertEqual(resposta_nome.status_code, 200)
        self.assertEqual(resposta_doc.status_code, 200)
        self.assertEqual(resposta_cidade.status_code, 200)
        self.assertEqual(resposta_contato.status_code, 200)
        self.assertEqual(cliente.razao_social, 'Cliente Novo')
        self.assertEqual(cliente.cpf_cnpj, '11222333000144')
        self.assertEqual(cliente.cidade, 'Natal')
        self.assertEqual(cliente.telefone, '84988887777')
        self.assertEqual(self.payload(resposta_contato)['display'], '(84) 98888-7777')

    def test_rejeita_cpf_cnpj_invalido(self):
        cliente = self.criar_cliente()

        response = self.post_inline(cliente, 'cpf_cnpj', '123')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.payload(response)['error'], 'CPF/CNPJ invalido.')

    def test_rejeita_documento_duplicado_na_filial(self):
        cliente = self.criar_cliente(cpf_cnpj='12345678901')
        self.criar_cliente(razao_social='Cliente Duplicado', cpf_cnpj='11222333000144')

        response = self.post_inline(cliente, 'cpf_cnpj', '11.222.333/0001-44')

        self.assertEqual(response.status_code, 400)
        self.assertIn('CPF/CNPJ', self.payload(response)['error'])
