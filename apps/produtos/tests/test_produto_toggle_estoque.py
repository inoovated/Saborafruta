from decimal import Decimal

from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase

from apps.core.models import Empresa, Filial, PerfilAcesso, Usuario
from apps.estoque.models import Estoque, MovimentacaoEstoque
from apps.produtos.models import Produto, ProdutoFilial, UnidadeMedida, UnidadeMedidaFilial
from apps.produtos.views.produto import ProdutoToggleAtivoView


class ProdutoToggleEstoqueTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            razao_social='Empresa Produto LTDA',
            nome_fantasia='Empresa Produto',
            cnpj='52345678000191',
            regime_tributario=Empresa.RegimeTributario.SIMPLES_NACIONAL,
            codigo_regime_tributario=1,
        )
        self.filial = Filial.objects.create(
            empresa=self.empresa,
            razao_social='Filial Produto',
            nome_fantasia='Filial Produto',
            cnpj='52345678000192',
            uf='RN',
        )
        perfil = PerfilAcesso.objects.create(
            empresa=self.empresa,
            nome='Administrador',
            is_admin=True,
        )
        self.usuario = Usuario.objects.create_user(
            email='produto-toggle@inoovated.com',
            nome='Usuario Produto',
            password='teste1234',
            empresa=self.empresa,
            filial=self.filial,
            perfil=perfil,
        )
        self.unidade = UnidadeMedida.objects.create(
            empresa=self.empresa,
            sigla='UN',
            descricao='Unidade',
        )
        UnidadeMedidaFilial.objects.create(unidade=self.unidade, filial=self.filial)
        self.factory = RequestFactory()

    def criar_produto(self, ativo=True):
        produto = Produto.objects.create(
            filial=self.filial,
            unidade_medida=self.unidade,
            descricao='Produto com estoque',
            ncm='20089900',
            preco_venda=Decimal('10.00'),
            preco_custo=Decimal('4.00'),
            ativo=ativo,
        )
        ProdutoFilial.objects.create(produto=produto, filial=self.filial)
        Estoque.objects.create(
            produto=produto,
            filial=self.filial,
            quantidade_atual=Decimal('5.000'),
            quantidade_disponivel=Decimal('5.000'),
        )
        return produto

    def request(self, data):
        request = self.factory.post('/produtos/toggle/', data)
        request.user = self.usuario
        request.filial_ativa = self.filial
        request.session = self.client.session
        request._messages = FallbackStorage(request)
        return request

    def test_inativar_produto_zera_estoque_quando_solicitado(self):
        produto = self.criar_produto()

        response = ProdutoToggleAtivoView.as_view()(self.request({'zerar_estoque': '1'}), pk=produto.pk)

        produto.refresh_from_db()
        estoque = Estoque.objects.get(produto=produto, filial=self.filial)
        movimento = MovimentacaoEstoque.objects.get(produto=produto, filial=self.filial)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(produto.ativo)
        self.assertEqual(estoque.quantidade_atual, Decimal('0.000'))
        self.assertEqual(movimento.tipo_operacao, MovimentacaoEstoque.TipoOperacao.AJUSTE_MENOS)
        self.assertEqual(movimento.quantidade, Decimal('5.000'))

    def test_inativar_produto_sem_confirmar_mantem_estoque(self):
        produto = self.criar_produto()

        ProdutoToggleAtivoView.as_view()(self.request({'zerar_estoque': '0'}), pk=produto.pk)

        produto.refresh_from_db()
        estoque = Estoque.objects.get(produto=produto, filial=self.filial)
        self.assertFalse(produto.ativo)
        self.assertEqual(estoque.quantidade_atual, Decimal('5.000'))
        self.assertFalse(MovimentacaoEstoque.objects.filter(produto=produto).exists())

    def test_ativar_produto_nao_zera_estoque_mesmo_com_flag(self):
        produto = self.criar_produto(ativo=False)

        ProdutoToggleAtivoView.as_view()(self.request({'zerar_estoque': '1'}), pk=produto.pk)

        produto.refresh_from_db()
        estoque = Estoque.objects.get(produto=produto, filial=self.filial)
        self.assertTrue(produto.ativo)
        self.assertEqual(estoque.quantidade_atual, Decimal('5.000'))
        self.assertFalse(MovimentacaoEstoque.objects.filter(produto=produto).exists())
