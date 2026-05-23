from decimal import Decimal

from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase

from apps.core.models import Empresa, Filial, LogSistema, PerfilAcesso, Usuario
from apps.produtos.models import (
    CategoriaProduto,
    CategoriaProdutoFilial,
    Produto,
    ProdutoFilial,
    ProdutoFornecedorEquivalencia,
    UnidadeMedida,
    UnidadeMedidaFilial,
)
from apps.produtos.views.produto import ProdutoFornecedorVinculoDeleteView, ProdutoUpdateView


class ProdutoFornecedorVinculoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa = Empresa.objects.create(
            razao_social='Empresa Vinculo Produto LTDA',
            nome_fantasia='Empresa Vinculo Produto',
            cnpj='62345678000191',
            regime_tributario=Empresa.RegimeTributario.SIMPLES_NACIONAL,
            codigo_regime_tributario=1,
        )
        cls.filial = Filial.objects.create(
            empresa=cls.empresa,
            razao_social='Filial Vinculo Produto',
            nome_fantasia='Filial Vinculo',
            cnpj='62345678000192',
            uf='RN',
        )
        perfil = PerfilAcesso.objects.create(
            empresa=cls.empresa,
            nome='Administrador',
            is_admin=True,
        )
        cls.usuario = Usuario.objects.create_user(
            email='produto-vinculo@inoovated.com',
            nome='Usuario Produto Vinculo',
            password='teste1234',
            empresa=cls.empresa,
            filial=cls.filial,
            perfil=perfil,
        )
        cls.unidade = UnidadeMedida.objects.create(
            empresa=cls.empresa,
            sigla='UN',
            descricao='Unidade',
        )
        UnidadeMedidaFilial.objects.create(unidade=cls.unidade, filial=cls.filial)
        cls.categoria = CategoriaProduto.objects.create(
            empresa=cls.empresa,
            filial=cls.filial,
            nome='Polpas',
        )
        CategoriaProdutoFilial.objects.create(categoria=cls.categoria, filial=cls.filial)

    def setUp(self):
        self.factory = RequestFactory()

    def request(self, method='get', data=None):
        factory_method = self.factory.post if method == 'post' else self.factory.get
        request = factory_method('/produtos/vinculos/', data or {})
        request.user = self.usuario
        request.filial_ativa = self.filial
        request.session = self.client.session
        request._messages = FallbackStorage(request)
        return request

    def criar_produto(self):
        produto = Produto.objects.create(
            filial=self.filial,
            unidade_medida=self.unidade,
            categoria=self.categoria,
            descricao='Polpa Acerola 300 ML',
            codigo='PA300',
            codigo_barras='7891000000001',
            ncm='20089900',
            preco_venda=Decimal('10.00'),
            preco_custo=Decimal('4.00'),
            ativo=True,
        )
        ProdutoFilial.objects.create(produto=produto, filial=self.filial, ativo=True)
        return produto

    def criar_vinculo(self, produto):
        return ProdutoFornecedorEquivalencia.objects.create(
            produto=produto,
            fornecedor_cnpj_xml='12345678000199',
            fornecedor_razao_social_xml='Fornecedor XML LTDA',
            codigo_fornecedor='ACER-01',
            descricao_fornecedor='ACEROLA CONGELADA CX',
            ean_utilizado='7891234567890',
            unidade_compra='CX',
            unidade_estoque='UN',
            fator_conversao=Decimal('12.0000'),
            ultimo_custo=Decimal('39.0800'),
            ativo=True,
        )

    def test_cadastro_do_produto_exibe_vinculos_de_fornecedor(self):
        produto = self.criar_produto()
        vinculo = self.criar_vinculo(produto)

        response = ProdutoUpdateView.as_view()(self.request(), pk=produto.pk)

        html = response.content.decode()
        self.assertContains(response, 'Vinculos com fornecedores')
        self.assertContains(response, 'Fornecedor XML LTDA')
        self.assertContains(response, 'ACER-01')
        self.assertContains(response, 'ACEROLA CONGELADA CX')
        self.assertContains(response, '7891234567890')
        self.assertIn(f'produto-vinculo-delete-{vinculo.pk}', html)

    def test_remover_vinculo_desativa_equivalencia_sem_apagar_historico(self):
        produto = self.criar_produto()
        vinculo = self.criar_vinculo(produto)

        response = ProdutoFornecedorVinculoDeleteView.as_view()(
            self.request(method='post'),
            pk=produto.pk,
            vinculo_pk=vinculo.pk,
        )

        vinculo.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertFalse(vinculo.ativo)
        self.assertTrue(
            LogSistema.objects.filter(
                modulo='produtos',
                registro_id=produto.pk,
                dados_novos__evento='Vinculo de fornecedor removido',
            ).exists()
        )
