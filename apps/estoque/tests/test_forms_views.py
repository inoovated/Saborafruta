from decimal import Decimal

from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.cadastros.models import Fornecedor, FornecedorFilial
from apps.compras.models import PedidoCompra
from apps.core.models import Empresa, Filial, PerfilAcesso, Permissao, Usuario
from apps.estoque.forms import MovimentacaoManualForm, TransferenciaForm
from apps.estoque.models import Estoque, Inventario, ItemInventario, LoteProduto, MovimentacaoEstoque
from apps.estoque.services.movimentacao_service import MovimentacaoService
from apps.estoque.views import InventarioDivergenciasView, ReposicaoListView
from apps.produtos.models import Produto, ProdutoFilial, UnidadeMedida, UnidadeMedidaFilial


class EstoqueFormsViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa = Empresa.objects.create(
            razao_social='Empresa Teste LTDA',
            nome_fantasia='Empresa Teste',
            cnpj='22345678000191',
            regime_tributario=Empresa.RegimeTributario.SIMPLES_NACIONAL,
            codigo_regime_tributario=1,
        )
        cls.filial = Filial.objects.create(
            empresa=cls.empresa,
            razao_social='Filial Teste',
            nome_fantasia='Matriz',
            cnpj='22345678000192',
            uf='RN',
        )
        cls.filial_destino = Filial.objects.create(
            empresa=cls.empresa,
            razao_social='Filial Destino',
            nome_fantasia='Destino',
            cnpj='22345678000193',
            uf='RN',
        )
        cls.perfil = PerfilAcesso.objects.create(
            empresa=cls.empresa,
            nome='Estoque',
        )
        cls.usuario = Usuario.objects.create_user(
            email='forms-views@inoovated.com',
            nome='Usuario Estoque',
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
        UnidadeMedidaFilial.objects.create(unidade=cls.unidade, filial=cls.filial_destino)
        cls.fornecedor = Fornecedor.objects.create(
            filial=cls.filial,
            tipo_pessoa='J',
            razao_social='Fornecedor Teste',
            cpf_cnpj='22345678000194',
            uf='RN',
        )
        FornecedorFilial.objects.create(fornecedor=cls.fornecedor, filial=cls.filial)

    def setUp(self):
        self.factory = RequestFactory()
        self.client.force_login(self.usuario)
        session = self.client.session
        session['filial_ativa_id'] = self.filial.pk
        session.save()

    def conceder(self, modulo='estoque', **permissoes):
        defaults = {
            'pode_ver': False,
            'pode_criar': False,
            'pode_editar': False,
            'pode_excluir': False,
            'pode_cancelar': False,
            'pode_aprovar': False,
            'pode_exportar': False,
        }
        defaults.update(permissoes)
        Permissao.objects.update_or_create(
            perfil=self.perfil,
            modulo=modulo,
            defaults=defaults,
        )

    def criar_produto(self, descricao='Produto Teste', controla_lote=False, fornecedor=None):
        produto = Produto.objects.create(
            filial=self.filial,
            unidade_medida=self.unidade,
            fornecedor=fornecedor,
            descricao=descricao,
            ncm='20089900',
            controla_lote=controla_lote,
            controla_validade=controla_lote,
            permite_venda_sem_estoque=False,
        )
        ProdutoFilial.objects.create(produto=produto, filial=self.filial)
        return produto

    def criar_lote(self, produto):
        return LoteProduto.objects.create(
            produto=produto,
            filial=self.filial,
            numero_lote='LT-FORM',
            quantidade_inicial=Decimal('0'),
            quantidade_atual=Decimal('0'),
        )

    def test_movimentacao_manual_exige_lote_para_produto_controlado(self):
        self.conceder(pode_ver=True, pode_editar=True)
        produto = self.criar_produto(controla_lote=True)

        form = MovimentacaoManualForm(
            data={
                'produto': produto.pk,
                'tipo_operacao': MovimentacaoEstoque.TipoOperacao.ENTRADA,
                'quantidade': '1',
                'valor_unitario': '2',
            },
            filial=self.filial,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('Informe o lote', str(form.errors))

    def test_transferencia_rejeita_lote_de_outro_produto_no_form(self):
        self.conceder(pode_ver=True, pode_editar=True)
        produto = self.criar_produto(descricao='Produto A', controla_lote=True)
        outro = self.criar_produto(descricao='Produto B', controla_lote=True)
        lote = self.criar_lote(outro)

        form = TransferenciaForm(
            data={
                'produto': produto.pk,
                'lote': lote.pk,
                'filial_destino': self.filial_destino.pk,
                'quantidade': '1',
            },
            filial=self.filial,
            empresa=self.empresa,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('nao pertence ao produto', str(form.errors))

    def test_exportacao_estoque_exige_permissao_exportar(self):
        self.conceder(pode_ver=True)

        response = self.client.get(reverse('estoque:estoque-list'), {'export': 'csv'})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('estoque:estoque-list'))

    def test_exportacao_estoque_com_permissao_retorna_csv(self):
        self.conceder(pode_ver=True, pode_exportar=True)

        response = self.client.get(reverse('estoque:estoque-list'), {'export': 'csv'})

        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])

    def test_reposicao_gera_pedido_compra_em_rascunho(self):
        self.conceder(pode_ver=True, pode_editar=True)
        self.conceder('compras', pode_ver=True, pode_criar=True)
        produto = self.criar_produto(fornecedor=self.fornecedor)
        produto.estoque_minimo = Decimal('5')
        produto.estoque_maximo = Decimal('10')
        produto.preco_custo = Decimal('3.50')
        produto.save(update_fields=['estoque_minimo', 'estoque_maximo', 'preco_custo', 'updated_at'])
        MovimentacaoService.registrar_movimentacao(
            produto_id=produto.pk,
            filial_id=self.filial.pk,
            tipo_operacao=MovimentacaoEstoque.TipoOperacao.ENTRADA,
            quantidade=Decimal('2'),
            usuario_id=self.usuario.pk,
            valor_unitario=Decimal('3.50'),
        )

        response = self.client.post(
            reverse('estoque:reposicao-list'),
            {'produto': [str(produto.pk)]},
        )

        self.assertEqual(response.status_code, 302)
        pedido = PedidoCompra.objects.get(filial=self.filial, fornecedor=self.fornecedor)
        self.assertEqual(pedido.status, PedidoCompra.Status.RASCUNHO)
        item = pedido.itens.get(produto=produto)
        self.assertEqual(item.quantidade, Decimal('8.000'))

    def test_tela_reposicao_renderiza_sugestoes(self):
        self.conceder(pode_ver=True)
        produto = self.criar_produto(descricao='Produto Repor', fornecedor=self.fornecedor)
        produto.estoque_minimo = Decimal('5')
        produto.estoque_maximo = Decimal('10')
        produto.save(update_fields=['estoque_minimo', 'estoque_maximo', 'updated_at'])

        path = reverse('estoque:reposicao-list')
        request = self.factory.get(path)
        request.user = self.usuario
        request.filial_ativa = self.filial
        response = ReposicaoListView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Produto Repor', response.content)

    def test_relatorio_divergencias_inventario_abre_com_permissao_ver(self):
        self.conceder(pode_ver=True)
        produto = self.criar_produto()
        inventario = Inventario.objects.create(
            filial=self.filial,
            descricao='Inventario fechado',
            status=Inventario.Status.FECHADO,
            data_inicio=timezone.now(),
            usuario_inicio=self.usuario,
        )
        ItemInventario.objects.create(
            inventario=inventario,
            produto=produto,
            quantidade_sistema=Decimal('10'),
            quantidade_contada=Decimal('8'),
            diferenca=Decimal('-2'),
            valor_unitario=Decimal('3.50'),
            valor_diferenca=Decimal('-7.00'),
        )

        path = reverse('estoque:inventario-divergencias', args=[inventario.pk])
        request = self.factory.get(path)
        request.user = self.usuario
        request.filial_ativa = self.filial
        response = InventarioDivergenciasView.as_view()(request, pk=inventario.pk)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Produto Teste', response.content)
