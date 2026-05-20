import json

from django.test import RequestFactory, TestCase

from apps.cadastros.models import Fornecedor, FornecedorFilial
from apps.cadastros.views.fornecedor import FornecedorInlineEditView
from apps.core.models import Empresa, Filial, PerfilAcesso, Usuario


class FornecedorInlineEditTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa = Empresa.objects.create(
            razao_social='Empresa Fornecedor LTDA',
            nome_fantasia='Empresa Fornecedor',
            cnpj='72345678000191',
            regime_tributario=Empresa.RegimeTributario.SIMPLES_NACIONAL,
            codigo_regime_tributario=1,
        )
        cls.filial = Filial.objects.create(
            empresa=cls.empresa,
            razao_social='Filial Fornecedor',
            nome_fantasia='Filial Fornecedor',
            cnpj='72345678000192',
            uf='RN',
        )
        cls.perfil = PerfilAcesso.objects.create(
            empresa=cls.empresa,
            nome='Administrador',
            is_admin=True,
        )
        cls.usuario = Usuario.objects.create_user(
            email='fornecedor-inline@inoovated.com',
            nome='Usuario Fornecedor',
            password='teste1234',
            empresa=cls.empresa,
            filial=cls.filial,
            perfil=cls.perfil,
        )

    def setUp(self):
        self.factory = RequestFactory()

    def criar_fornecedor(self, **kwargs):
        dados = {
            'filial': self.filial,
            'tipo_pessoa': 'J',
            'razao_social': 'Fornecedor Teste',
            'cpf_cnpj': '12345678000190',
            'cidade': 'Mossoro',
            'uf': 'RN',
            'telefone': '84999990000',
        }
        dados.update(kwargs)
        fornecedor = Fornecedor.objects.create(**dados)
        FornecedorFilial.objects.create(fornecedor=fornecedor, filial=self.filial)
        return fornecedor

    def post_inline(self, fornecedor, field, value):
        request = self.factory.post(
            f'/cadastros/fornecedores/{fornecedor.pk}/inline-edit/',
            {'field': field, 'value': value},
        )
        request.user = self.usuario
        request.filial_ativa = self.filial
        return FornecedorInlineEditView.as_view()(request, pk=fornecedor.pk)

    def payload(self, response):
        return json.loads(response.content.decode('utf-8'))

    def test_edita_nome_documento_cidade_e_contato(self):
        fornecedor = self.criar_fornecedor()

        resposta_nome = self.post_inline(fornecedor, 'nome', 'Fornecedor Novo')
        resposta_doc = self.post_inline(fornecedor, 'cpf_cnpj', '11.222.333/0001-44')
        resposta_cidade = self.post_inline(fornecedor, 'cidade', 'Natal')
        resposta_contato = self.post_inline(fornecedor, 'telefone', '(84) 98888-7777')

        fornecedor.refresh_from_db()
        self.assertEqual(resposta_nome.status_code, 200)
        self.assertEqual(resposta_doc.status_code, 200)
        self.assertEqual(resposta_cidade.status_code, 200)
        self.assertEqual(resposta_contato.status_code, 200)
        self.assertEqual(fornecedor.razao_social, 'Fornecedor Novo')
        self.assertEqual(fornecedor.cpf_cnpj, '11222333000144')
        self.assertEqual(fornecedor.cidade, 'Natal')
        self.assertEqual(fornecedor.telefone, '84988887777')
        self.assertEqual(self.payload(resposta_contato)['display'], '(84) 98888-7777')

    def test_rejeita_cpf_cnpj_invalido(self):
        fornecedor = self.criar_fornecedor()

        response = self.post_inline(fornecedor, 'cpf_cnpj', '123')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.payload(response)['error'], 'CPF/CNPJ invalido.')

    def test_rejeita_documento_duplicado_na_filial(self):
        fornecedor = self.criar_fornecedor(cpf_cnpj='12345678000190')
        self.criar_fornecedor(razao_social='Fornecedor Duplicado', cpf_cnpj='11222333000144')

        response = self.post_inline(fornecedor, 'cpf_cnpj', '11.222.333/0001-44')

        self.assertEqual(response.status_code, 400)
        self.assertIn('CPF/CNPJ', self.payload(response)['error'])

    def test_percentual_no_prazo_fica_disponivel_para_listagem(self):
        fornecedor = self.criar_fornecedor(total_entregas=4, entregas_no_prazo=3)

        self.assertEqual(fornecedor.percentual_no_prazo, 75)
