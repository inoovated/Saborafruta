from decimal import Decimal

from django.test import RequestFactory, TestCase

from apps.core.models import Empresa, Filial, LogSistema, PoliticaReplicacaoFilial
from apps.produtos.models import (
    CategoriaProduto,
    KitCategoria,
    KitCategoriaRegra,
    Produto,
    ProdutoFilial,
    UnidadeMedida,
    UnidadeMedidaFilial,
)
from apps.produtos.services.preco_service import PrecoService
from apps.produtos.views.promocao_audit import _entry_from_log
from apps.produtos.views.promocao import (
    ComboPromocaoListView,
    DIAS_SEMANA_TODOS,
    _filiais_replicacao_context,
    _atualizar_preco_promocional,
    _registrar_ignorada,
    _registrar_replicada,
)


class PromocaoReplicacaoContextTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            razao_social='Empresa Promocao LTDA',
            nome_fantasia='Empresa Promocao',
            cnpj='42345678000191',
            regime_tributario=Empresa.RegimeTributario.SIMPLES_NACIONAL,
            codigo_regime_tributario=1,
        )
        self.origem = Filial.objects.create(
            empresa=self.empresa,
            razao_social='Origem Promocao',
            nome_fantasia='Origem',
            cnpj='42345678000192',
            uf='RN',
            participa_replicacao=True,
        )
        self.destino = Filial.objects.create(
            empresa=self.empresa,
            razao_social='Destino Promocao',
            nome_fantasia='Destino',
            cnpj='42345678000193',
            uf='RN',
            participa_replicacao=True,
        )
        PoliticaReplicacaoFilial.objects.create(
            filial=self.origem,
            replicar_produtos_basicos=True,
        )
        PoliticaReplicacaoFilial.objects.create(
            filial=self.destino,
            replicar_produtos_basicos=True,
        )
        self.unidade = UnidadeMedida.objects.create(
            empresa=self.empresa,
            sigla='UN',
            descricao='Unidade',
        )
        UnidadeMedidaFilial.objects.create(unidade=self.unidade, filial=self.origem)
        self.factory = RequestFactory()

    def test_contexto_replicacao_usa_nome_fantasia_da_filial(self):
        contexto = _filiais_replicacao_context(self.origem)

        self.assertEqual(contexto, [{
            'id': self.destino.pk,
            'nome': 'Destino',
            'habilitada': True,
            'motivo': '',
        }])

    def test_relatorio_replicacao_usa_nome_exibivel_da_filial(self):
        relatorio = {'replicadas': [], 'ignoradas': []}

        _registrar_replicada(relatorio, self.destino)
        _registrar_ignorada(relatorio, self.destino, 'Sem politica')

        self.assertEqual(relatorio['replicadas'], ['Destino'])
        self.assertEqual(relatorio['ignoradas'], ['Destino: Sem politica'])

    def test_preco_promocional_individual_fica_na_filial_atual(self):
        produto = Produto.objects.create(
            filial=self.origem,
            unidade_medida=self.unidade,
            descricao='Polpa compartilhada',
            ncm='20089900',
            preco_venda=Decimal('10.00'),
            preco_custo=Decimal('4.00'),
        )
        ProdutoFilial.objects.create(produto=produto, filial=self.origem)
        ProdutoFilial.objects.create(produto=produto, filial=self.destino)

        _atualizar_preco_promocional(
            produto,
            {
                'preco_promocional': Decimal('7.99'),
                'promocao_tipo_desconto': 'preco_final',
                'promocao_valor_desconto': Decimal('7.99'),
                'promocao_dias_semana': DIAS_SEMANA_TODOS,
                'ativo': True,
            },
            self.origem,
        )

        self.assertEqual(
            PrecoService.preco_promocional_vigente(produto, filial=self.origem),
            Decimal('7.99'),
        )
        self.assertIsNone(PrecoService.preco_promocional_vigente(produto, filial=self.destino))

    def test_flag_replicar_preco_promocional_fica_salva_na_filial(self):
        produto = Produto.objects.create(
            filial=self.origem,
            unidade_medida=self.unidade,
            descricao='Polpa replica flag',
            ncm='20089900',
            preco_venda=Decimal('10.00'),
            preco_custo=Decimal('4.00'),
        )
        ProdutoFilial.objects.create(produto=produto, filial=self.origem)

        _atualizar_preco_promocional(
            produto,
            {
                'preco_promocional': Decimal('7.99'),
                'promocao_tipo_desconto': 'preco_final',
                'promocao_valor_desconto': Decimal('7.99'),
                'promocao_dias_semana': DIAS_SEMANA_TODOS,
                'ativo': True,
            },
            self.origem,
            replicar_filiais=True,
        )

        vinculo = ProdutoFilial.objects.get(produto=produto, filial=self.origem)
        self.assertTrue(vinculo.preco_promocional_replicar_filiais)

    def test_inativar_preco_promocional_preserva_outra_filial(self):
        produto = Produto.objects.create(
            filial=self.origem,
            unidade_medida=self.unidade,
            descricao='Polpa com promocao por filial',
            ncm='20089900',
            preco_venda=Decimal('10.00'),
            preco_custo=Decimal('4.00'),
        )
        ProdutoFilial.objects.create(produto=produto, filial=self.origem)
        ProdutoFilial.objects.create(produto=produto, filial=self.destino)
        linha_base = {
            'preco_promocional': Decimal('7.99'),
            'promocao_tipo_desconto': 'preco_final',
            'promocao_valor_desconto': Decimal('7.99'),
            'promocao_dias_semana': DIAS_SEMANA_TODOS,
            'ativo': True,
        }
        _atualizar_preco_promocional(produto, linha_base, self.origem)
        _atualizar_preco_promocional(produto, {**linha_base, 'preco_promocional': Decimal('8.99'), 'promocao_valor_desconto': Decimal('8.99')}, self.destino)

        _atualizar_preco_promocional(produto, {**linha_base, 'ativo': False}, self.origem)

        vinculo_origem = ProdutoFilial.objects.get(produto=produto, filial=self.origem)
        self.assertFalse(vinculo_origem.preco_promocional_ativo)
        self.assertEqual(vinculo_origem.preco_promocional, Decimal('7.99'))
        self.assertIsNone(PrecoService.preco_promocional_vigente(produto, filial=self.origem))
        self.assertEqual(
            PrecoService.preco_promocional_vigente(produto, filial=self.destino),
            Decimal('8.99'),
        )

    def test_vinculo_da_filial_zerado_nao_usa_preco_promocional_legado_do_produto(self):
        produto = Produto.objects.create(
            filial=self.origem,
            unidade_medida=self.unidade,
            descricao='Polpa legado promocional',
            ncm='20089900',
            preco_venda=Decimal('10.00'),
            preco_custo=Decimal('4.00'),
            preco_promocional=Decimal('7.99'),
            promocao_tipo_desconto='preco_final',
            promocao_valor_desconto=Decimal('7.99'),
        )
        ProdutoFilial.objects.create(
            produto=produto,
            filial=self.origem,
            preco_promocional=Decimal('0'),
            promocao_tipo_desconto='preco_final',
            promocao_valor_desconto=Decimal('0'),
        )

        contexto = PrecoService.promocao_produto_contexto(produto, self.origem)

        self.assertIsInstance(contexto, ProdutoFilial)
        self.assertIsNone(PrecoService.preco_promocional_vigente(produto, filial=self.origem))

    def test_preco_promocional_inativo_fica_na_listagem_com_status_inativo(self):
        produto = Produto.objects.create(
            filial=self.origem,
            unidade_medida=self.unidade,
            descricao='Polpa inativa na tela',
            ncm='20089900',
            preco_venda=Decimal('10.00'),
            preco_custo=Decimal('4.00'),
        )
        ProdutoFilial.objects.create(
            produto=produto,
            filial=self.origem,
            preco_promocional=Decimal('7.99'),
            preco_promocional_ativo=False,
            promocao_tipo_desconto='preco_final',
            promocao_valor_desconto=Decimal('7.99'),
        )
        request = self.factory.get('/produtos/combos-promocoes/?aba=precos')
        request.filial_ativa = self.origem

        contexto = ComboPromocaoListView()._context(request)

        self.assertEqual(len(contexto['produtos_promocionais']), 1)
        produto_tela = contexto['produtos_promocionais'][0]
        self.assertEqual(produto_tela.status_info['texto'], 'Inativo')
        self.assertEqual(produto_tela.active_state, 'inativas')
        self.assertFalse(produto_tela.preco_promocional_ativo)
        self.assertNotIn(produto_tela, contexto['produtos_promocionais_ativos'])

    def test_preco_promocional_de_produto_inativo_segue_status_da_promocao(self):
        produto = Produto.objects.create(
            filial=self.origem,
            unidade_medida=self.unidade,
            descricao='Polpa produto desativado',
            ncm='20089900',
            preco_venda=Decimal('10.00'),
            preco_custo=Decimal('4.00'),
            ativo=False,
        )
        ProdutoFilial.objects.create(
            produto=produto,
            filial=self.origem,
            preco_promocional=Decimal('7.99'),
            preco_promocional_ativo=True,
            promocao_tipo_desconto='preco_final',
            promocao_valor_desconto=Decimal('7.99'),
        )
        request = self.factory.get('/produtos/combos-promocoes/?aba=precos')
        request.filial_ativa = self.origem

        contexto = ComboPromocaoListView()._context(request)

        self.assertEqual(len(contexto['produtos_promocionais']), 1)
        produto_tela = contexto['produtos_promocionais'][0]
        self.assertEqual(produto_tela.status_info['texto'], 'Ativo')
        self.assertEqual(produto_tela.active_state, 'ativas')
        self.assertTrue(produto_tela.preco_promocional_ativo)
        self.assertIn(produto_tela, contexto['produtos_promocionais_ativos'])

    def test_categoria_nao_marca_utiliza_preco_promocional_quando_promocao_individual_inativa(self):
        categoria = CategoriaProduto.objects.create(
            empresa=self.empresa,
            filial=self.origem,
            nome='Polpas',
        )
        produto = Produto.objects.create(
            filial=self.origem,
            unidade_medida=self.unidade,
            categoria=categoria,
            descricao='Polpa sem promo ativa',
            ncm='20089900',
            preco_venda=Decimal('10.00'),
            preco_custo=Decimal('4.00'),
        )
        ProdutoFilial.objects.create(
            produto=produto,
            filial=self.origem,
            preco_promocional=Decimal('7.99'),
            preco_promocional_ativo=False,
            promocao_tipo_desconto='preco_final',
            promocao_valor_desconto=Decimal('7.99'),
        )
        kit = KitCategoria.objects.create(
            filial=self.origem,
            nome='Desconto polpas',
            permite_preco_promocional=True,
            tipo_desconto='percentual',
            valor_desconto=Decimal('10.00'),
        )
        KitCategoriaRegra.objects.create(
            kit=kit,
            categoria=categoria,
            quantidade_minima=Decimal('1'),
            tipo_desconto='percentual',
            valor_desconto=Decimal('10.00'),
        )
        request = self.factory.get('/produtos/combos-promocoes/?aba=categorias')
        request.filial_ativa = self.origem

        contexto = ComboPromocaoListView()._context(request)

        kit_tela = contexto['kits_categorias'][0]
        self.assertTrue(kit_tela.permite_preco_promocional)
        self.assertFalse(kit_tela.tem_preco_promocional_vivo)

    def test_categoria_marca_utiliza_preco_promocional_quando_promocao_individual_ativa(self):
        categoria = CategoriaProduto.objects.create(
            empresa=self.empresa,
            filial=self.origem,
            nome='Polpas',
        )
        produto = Produto.objects.create(
            filial=self.origem,
            unidade_medida=self.unidade,
            categoria=categoria,
            descricao='Polpa com promo ativa',
            ncm='20089900',
            preco_venda=Decimal('10.00'),
            preco_custo=Decimal('4.00'),
            ativo=False,
        )
        ProdutoFilial.objects.create(
            produto=produto,
            filial=self.origem,
            preco_promocional=Decimal('7.99'),
            preco_promocional_ativo=True,
            promocao_tipo_desconto='preco_final',
            promocao_valor_desconto=Decimal('7.99'),
        )
        kit = KitCategoria.objects.create(
            filial=self.origem,
            nome='Desconto polpas',
            permite_preco_promocional=True,
            tipo_desconto='percentual',
            valor_desconto=Decimal('10.00'),
        )
        KitCategoriaRegra.objects.create(
            kit=kit,
            categoria=categoria,
            quantidade_minima=Decimal('1'),
            tipo_desconto='percentual',
            valor_desconto=Decimal('10.00'),
        )
        request = self.factory.get('/produtos/combos-promocoes/?aba=categorias')
        request.filial_ativa = self.origem

        contexto = ComboPromocaoListView()._context(request)

        kit_tela = contexto['kits_categorias'][0]
        self.assertTrue(kit_tela.permite_preco_promocional)
        self.assertTrue(kit_tela.tem_preco_promocional_vivo)

    def test_log_preco_promocional_inativado_mostra_filial_e_produto(self):
        produto = Produto.objects.create(
            filial=self.origem,
            unidade_medida=self.unidade,
            descricao='Polpa log promocao',
            ncm='20089900',
            preco_venda=Decimal('10.00'),
            preco_custo=Decimal('4.00'),
        )
        vinculo = ProdutoFilial.objects.create(produto=produto, filial=self.origem)
        log = LogSistema.objects.create(
            filial=self.origem,
            modulo='produtos',
            acao=LogSistema.Acao.EDITAR,
            tabela_afetada=ProdutoFilial._meta.db_table,
            registro_id=vinculo.pk,
            dados_anteriores={
                'produto': str(produto),
                'preco_promocional': '7.99',
                'promocao_tipo_desconto': 'preco_final',
                'promocao_valor_desconto': '7.99',
            },
            dados_novos={
                'produto': str(produto),
                'preco_promocional': '0',
                'promocao_tipo_desconto': 'preco_final',
                'promocao_valor_desconto': '0',
            },
        )

        entry = _entry_from_log(log)

        self.assertEqual(entry['acao'], 'Preco promocional inativado')
        self.assertIn('nesta filial', entry['detalhes'])
        self.assertIn('Polpa log promocao', entry['detalhes'])
