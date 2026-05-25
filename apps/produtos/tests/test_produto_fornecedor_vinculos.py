from decimal import Decimal
from unittest.mock import patch

from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase
from django.utils import timezone

from apps.cadastros.models import Fornecedor, FornecedorFilial
from apps.compras.models import EntradaNF, ItemEntradaNF
from apps.compras.views.entrada import EntradaNFConferenciaView
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
        cls.fornecedor = Fornecedor.objects.create(
            filial=cls.filial,
            tipo_pessoa='J',
            razao_social='Fornecedor XML LTDA',
            nome_fantasia='Fornecedor XML',
            cpf_cnpj='12345678000199',
            uf='RN',
        )
        FornecedorFilial.objects.create(fornecedor=cls.fornecedor, filial=cls.filial)

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
            fornecedor=self.fornecedor,
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

    def criar_entrada_com_item_vinculado(self, produto):
        entrada = EntradaNF.objects.create(
            filial=self.filial,
            fornecedor=self.fornecedor,
            usuario=self.usuario,
            numero_nf='1001',
            serie_nf='1',
            chave_acesso_nf='',
            data_emissao_nf=timezone.now().date(),
            data_entrada=timezone.now(),
            status=EntradaNF.Status.AGUARDANDO_CONFERENCIA,
            valor_produtos=Decimal('39.08'),
            valor_total=Decimal('39.08'),
            emitente_cnpj_xml='12345678000199',
            emitente_razao_social_xml='Fornecedor XML LTDA',
        )
        return ItemEntradaNF.objects.create(
            entrada=entrada,
            produto=produto,
            numero_item=1,
            quantidade=Decimal('1.000'),
            quantidade_xml=Decimal('1.000'),
            quantidade_estoque=Decimal('12.000'),
            quantidade_recebida=Decimal('12.000'),
            unidade_xml='CX',
            unidade_estoque='UN',
            fator_conversao=Decimal('12.0000'),
            valor_unitario=Decimal('39.0800'),
            valor_bruto=Decimal('39.08'),
            valor_total=Decimal('39.08'),
            ean_xml='7891234567890',
            codigo_produto_fornecedor='ACER-01',
            descricao_xml='ACEROLA CONGELADA CX',
        )

    def test_cadastro_do_produto_exibe_vinculos_de_fornecedor(self):
        produto = self.criar_produto()
        vinculo = self.criar_vinculo(produto)

        response = ProdutoUpdateView.as_view()(self.request(), pk=produto.pk)

        html = response.content.decode()
        self.assertContains(response, 'Vinculos com fornecedores')
        self.assertContains(response, 'Fornecedor XML')
        self.assertContains(response, 'ACER-01')
        self.assertContains(response, 'ACEROLA CONGELADA CX')
        self.assertContains(response, '7891234567890')
        self.assertIn(f'produto-vinculo-delete-{vinculo.pk}', html)

    def test_cadastro_do_produto_abre_mesmo_se_vinculos_falharem(self):
        produto = self.criar_produto()

        with patch(
            'apps.produtos.views.produto.ProdutoFornecedorEquivalencia.objects.select_related',
            side_effect=Exception('schema parcial em producao'),
        ):
            response = ProdutoUpdateView.as_view()(self.request(), pk=produto.pk)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Editar -')
        self.assertContains(response, 'Nenhum vinculo de fornecedor salvo para este produto.')

    def test_produto_com_margem_extrema_salva_sem_estourar_decimal(self):
        produto = self.criar_produto()
        produto.preco_custo = Decimal('100000.00')
        produto.preco_venda = Decimal('1.00')

        produto.calcular_margem()
        produto.save()

        produto.refresh_from_db()
        self.assertEqual(produto.margem_lucro, Decimal('-999.99'))
        self.assertEqual(produto.markup, Decimal('-99.9990'))

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

    def test_remover_vinculo_libera_item_de_entrada_aberta_para_nova_vinculacao(self):
        produto = self.criar_produto()
        vinculo = self.criar_vinculo(produto)
        item = self.criar_entrada_com_item_vinculado(produto)

        ProdutoFornecedorVinculoDeleteView.as_view()(
            self.request(method='post'),
            pk=produto.pk,
            vinculo_pk=vinculo.pk,
        )

        item.refresh_from_db()
        item.entrada.refresh_from_db()
        self.assertIsNone(item.produto_id)
        self.assertEqual(item.entrada.status, EntradaNF.Status.AGUARDANDO_VINCULOS)

    def test_conferencia_libera_item_ainda_vinculado_a_equivalencia_removida(self):
        produto = self.criar_produto()
        vinculo = self.criar_vinculo(produto)
        vinculo.ativo = False
        vinculo.save(update_fields=['ativo', 'updated_at'])
        item = self.criar_entrada_com_item_vinculado(produto)

        response = EntradaNFConferenciaView.as_view()(self.request(), pk=item.entrada_id)

        item.refresh_from_db()
        item.entrada.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(item.produto_id)
        self.assertEqual(item.entrada.status, EntradaNF.Status.AGUARDANDO_VINCULOS)

    def test_conferencia_vincula_automaticamente_item_pendente_por_ean_do_produto(self):
        produto = self.criar_produto()
        item = self.criar_entrada_com_item_vinculado(produto)
        item.produto = None
        item.ean_xml = produto.codigo_barras
        item.fator_conversao = Decimal('1.0000')
        item.quantidade_estoque = Decimal('1.000')
        item.quantidade_recebida = Decimal('1.000')
        item.quantidade = Decimal('1.000')
        item.save(update_fields=[
            'produto',
            'ean_xml',
            'fator_conversao',
            'quantidade_estoque',
            'quantidade_recebida',
            'quantidade',
            'updated_at',
        ])

        response = EntradaNFConferenciaView.as_view()(self.request(), pk=item.entrada_id)

        item.refresh_from_db()
        item.entrada.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(item.produto, produto)
        self.assertEqual(item.fator_conversao, Decimal('1'))
        self.assertEqual(item.entrada.status, EntradaNF.Status.AGUARDANDO_CONFERENCIA)
