from decimal import Decimal

from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.cadastros.models import Fornecedor, FornecedorFilial
from apps.core.models import Empresa, Filial, PerfilAcesso, Usuario
from apps.estoque.models import MovimentacaoEstoque
from apps.estoque.services.movimentacao_service import MovimentacaoService
from apps.produtos.models import Produto, ProdutoFilial, UnidadeMedida, UnidadeMedidaFilial


class SugestaoComprasViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa = Empresa.objects.create(
            razao_social="Empresa Sugestao LTDA",
            nome_fantasia="Empresa Sugestao",
            cnpj="72345678000191",
            regime_tributario=Empresa.RegimeTributario.SIMPLES_NACIONAL,
            codigo_regime_tributario=1,
        )
        cls.filial = Filial.objects.create(
            empresa=cls.empresa,
            razao_social="Filial Sugestao",
            nome_fantasia="Matriz",
            cnpj="72345678000192",
            uf="RN",
        )
        cls.perfil = PerfilAcesso.objects.create(
            empresa=cls.empresa,
            nome="Estoque Admin",
            is_admin=True,
        )
        cls.usuario = Usuario.objects.create_user(
            email="sugestao-compras@inoovated.com",
            nome="Usuario Sugestao",
            password="teste1234",
            empresa=cls.empresa,
            filial=cls.filial,
            perfil=cls.perfil,
        )
        cls.unidade = UnidadeMedida.objects.create(
            empresa=cls.empresa,
            sigla="UN",
            descricao="Unidade",
            tipo=UnidadeMedida.Tipo.UNIDADE,
        )
        UnidadeMedidaFilial.objects.create(unidade=cls.unidade, filial=cls.filial)
        cls.fornecedor = Fornecedor.objects.create(
            filial=cls.filial,
            tipo_pessoa="J",
            razao_social="Fornecedor Sugestao",
            cpf_cnpj="72345678000193",
            uf="RN",
        )
        FornecedorFilial.objects.create(fornecedor=cls.fornecedor, filial=cls.filial)

    def setUp(self):
        self.factory = RequestFactory()

    def request_get(self, params=None):
        from apps.estoque.views.sugestao_compras import SugestaoComprasView

        request = self.factory.get(reverse("estoque:sugestao-compras"), params or {})
        request.user = self.usuario
        request.filial_ativa = self.filial
        request.session = {"filial_ativa_id": self.filial.pk}
        return SugestaoComprasView.as_view()(request)

    def criar_produto(self):
        produto = Produto.objects.create(
            filial=self.filial,
            unidade_medida=self.unidade,
            fornecedor=self.fornecedor,
            descricao="Produto Sugestão Compra",
            ncm="20089900",
            controla_lote=False,
            permite_venda_sem_estoque=False,
            preco_venda=Decimal("10.00"),
            preco_custo=Decimal("4.00"),
        )
        ProdutoFilial.objects.create(produto=produto, filial=self.filial)
        return produto

    def movimentar(self, produto, tipo, quantidade):
        return MovimentacaoService.registrar_movimentacao(
            produto_id=produto.pk,
            filial_id=self.filial.pk,
            tipo_operacao=tipo,
            quantidade=Decimal(quantidade),
            usuario_id=self.usuario.pk,
            valor_unitario=Decimal("4.00"),
        )

    def test_tela_inicial_orienta_busca(self):
        response = self.request_get()

        self.assertEqual(response.status_code, 200)
        self.assertIn("Sugestão de Compras".encode(), response.content)
        self.assertIn("Configure os filtros e clique em Buscar".encode(), response.content)
        self.assertIn("Análise de giro".encode(), response.content)

    def test_busca_calcula_sugestao_por_giro(self):
        produto = self.criar_produto()
        self.movimentar(produto, MovimentacaoEstoque.TipoOperacao.ENTRADA, "8")
        self.movimentar(produto, MovimentacaoEstoque.TipoOperacao.SAIDA, "6")

        response = self.request_get(
            {"buscar": "1", "periodo": "60", "manter_dias": "45"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Produto Sugestão Compra".encode(), response.content)
        self.assertIn("Giro".encode(), response.content)
        self.assertIn("Sugestão".encode(), response.content)
