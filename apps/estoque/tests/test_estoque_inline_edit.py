import json
from decimal import Decimal

from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase

from apps.cadastros.models import Fornecedor, FornecedorFilial
from apps.core.models import Empresa, Filial, PerfilAcesso, Usuario
from apps.estoque.models import Estoque, MovimentacaoEstoque
from apps.estoque.views import EstoqueInlineEditView, EstoqueListView
from apps.produtos.models import (
    CategoriaProduto,
    CategoriaProdutoFilial,
    Produto,
    ProdutoFilial,
    UnidadeMedida,
    UnidadeMedidaFilial,
)


class EstoqueInlineEditTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa = Empresa.objects.create(
            razao_social='Empresa Estoque Inline LTDA',
            nome_fantasia='Empresa Estoque Inline',
            cnpj='82345678000191',
            regime_tributario=Empresa.RegimeTributario.SIMPLES_NACIONAL,
            codigo_regime_tributario=1,
        )
        cls.filial = Filial.objects.create(
            empresa=cls.empresa,
            razao_social='Filial Estoque Inline',
            nome_fantasia='Filial Estoque',
            cnpj='82345678000192',
            uf='RN',
        )
        cls.perfil = PerfilAcesso.objects.create(
            empresa=cls.empresa,
            nome='Administrador',
            is_admin=True,
        )
        cls.usuario = Usuario.objects.create_user(
            email='estoque-inline@inoovated.com',
            nome='Usuario Estoque Inline',
            password='teste1234',
            empresa=cls.empresa,
            filial=cls.filial,
            perfil=cls.perfil,
        )
        cls.unidade = UnidadeMedida.objects.create(
            empresa=cls.empresa,
            sigla='UN',
            descricao='Unidade',
            tipo=UnidadeMedida.Tipo.UNIDADE,
        )
        UnidadeMedidaFilial.objects.create(unidade=cls.unidade, filial=cls.filial)
        cls.categoria = cls.criar_categoria('Polpas')
        cls.nova_categoria = cls.criar_categoria('Sorvetes')
        cls.fornecedor = cls.criar_fornecedor('Fornecedor Antigo', '82345678000193')
        cls.novo_fornecedor = cls.criar_fornecedor('Fornecedor Novo', '82345678000194')

    @classmethod
    def criar_categoria(cls, nome):
        categoria = CategoriaProduto.objects.create(
            empresa=cls.empresa,
            filial=cls.filial,
            nome=nome,
        )
        CategoriaProdutoFilial.objects.create(categoria=categoria, filial=cls.filial)
        return categoria

    @classmethod
    def criar_fornecedor(cls, nome, cnpj):
        fornecedor = Fornecedor.objects.create(
            filial=cls.filial,
            tipo_pessoa='J',
            razao_social=nome,
            cpf_cnpj=cnpj,
            uf='RN',
        )
        FornecedorFilial.objects.create(fornecedor=fornecedor, filial=cls.filial)
        return fornecedor

    def setUp(self):
        self.factory = RequestFactory()

    def criar_produto(self, **kwargs):
        dados = {
            'filial': self.filial,
            'unidade_medida': self.unidade,
            'categoria': self.categoria,
            'fornecedor': self.fornecedor,
            'descricao': 'Polpa Acerola 300 ML',
            'ncm': '20089900',
            'preco_venda': Decimal('10.00'),
            'preco_custo': Decimal('4.00'),
            'estoque_minimo': Decimal('2.000'),
        }
        dados.update(kwargs)
        produto = Produto.objects.create(**dados)
        ProdutoFilial.objects.create(produto=produto, filial=self.filial)
        Estoque.objects.create(
            produto=produto,
            filial=self.filial,
            quantidade_atual=Decimal('5.000'),
            quantidade_disponivel=Decimal('5.000'),
            custo_medio=Decimal('4.0000'),
        )
        return produto

    def post_inline(self, produto, field, value):
        request = self.factory.post(
            f'/estoque/produtos/{produto.pk}/inline-edit/',
            {'field': field, 'value': value},
        )
        request.user = self.usuario
        request.filial_ativa = self.filial
        request.session = self.client.session
        request._messages = FallbackStorage(request)
        return EstoqueInlineEditView.as_view()(request, pk=produto.pk)

    def payload(self, response):
        return json.loads(response.content.decode('utf-8'))

    def test_edita_campos_do_produto_pela_listagem_de_estoque(self):
        produto = self.criar_produto()

        resposta_nome = self.post_inline(produto, 'descricao', 'Polpa Acerola Nova')
        resposta_categoria = self.post_inline(produto, 'categoria', str(self.nova_categoria.pk))
        resposta_fornecedor = self.post_inline(produto, 'fornecedor', str(self.novo_fornecedor.pk))
        resposta_minimo = self.post_inline(produto, 'estoque_minimo', '4,5')

        produto.refresh_from_db()
        self.assertEqual(resposta_nome.status_code, 200)
        self.assertEqual(resposta_categoria.status_code, 200)
        self.assertEqual(resposta_fornecedor.status_code, 200)
        self.assertEqual(resposta_minimo.status_code, 200)
        self.assertEqual(produto.descricao, 'Polpa Acerola Nova')
        self.assertEqual(produto.categoria, self.nova_categoria)
        self.assertEqual(produto.fornecedor, self.novo_fornecedor)
        self.assertEqual(produto.estoque_minimo, Decimal('4.5'))
        self.assertEqual(self.payload(resposta_minimo)['display'], '4,50')

    def test_edita_estoque_atual_com_movimentacao_auditada(self):
        produto = self.criar_produto()

        response = self.post_inline(produto, 'estoque_atual', '8')

        estoque = Estoque.objects.get(produto=produto, filial=self.filial)
        movimento = MovimentacaoEstoque.objects.get(produto=produto, filial=self.filial)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(estoque.quantidade_atual, Decimal('8.000'))
        self.assertEqual(estoque.quantidade_disponivel, Decimal('8.000'))
        self.assertEqual(movimento.tipo_operacao, MovimentacaoEstoque.TipoOperacao.AJUSTE_MAIS)
        self.assertEqual(movimento.quantidade, Decimal('3.000'))
        self.assertEqual(self.payload(response)['display'], '8')

    def test_rejeita_nome_vazio(self):
        produto = self.criar_produto()

        response = self.post_inline(produto, 'descricao', '')

        self.assertEqual(response.status_code, 400)
        self.assertIn('obrigatorio', self.payload(response)['error'])

    def test_listagem_de_estoque_mostra_preco_promocional(self):
        produto = self.criar_produto(
            preco_venda=Decimal('10.00'),
            preco_promocional=Decimal('8.00'),
            promocao_tipo_desconto='preco_final',
            promocao_valor_desconto=Decimal('8.00'),
        )

        request = self.factory.get('/estoque/')
        request.user = self.usuario
        request.filial_ativa = self.filial
        response = EstoqueListView.as_view()(request)
        content = response.content.decode('utf-8')

        self.assertIn(produto.descricao, content)
        self.assertIn('estoque-price-active', content)
        self.assertIn('R$ 8,00', content)
        self.assertIn('R$ 10,00', content)
