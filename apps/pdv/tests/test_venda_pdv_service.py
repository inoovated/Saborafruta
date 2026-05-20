from decimal import Decimal

from django.test import TestCase

from apps.core.models import Empresa, Filial, PerfilAcesso, Usuario
from apps.core.services.exceptions import EstoqueInsuficienteError
from apps.estoque.models import Estoque, MovimentacaoEstoque
from apps.estoque.services.movimentacao_service import MovimentacaoService
from apps.financeiro.constants.enums import TipoFormaPagamento
from apps.financeiro.models import FormaPagamento
from apps.pdv.models import Caixa, ItemVendaPDV, SessaoPDV, VendaPDV
from apps.pdv.services.venda_pdv_service import VendaPDVService
from apps.produtos.models import (
    KitCategoria, KitCategoriaRegra, Produto, ProdutoFilial, TipoDesconto,
    UnidadeMedida, UnidadeMedidaFilial,
)


class VendaPDVServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa = Empresa.objects.create(
            razao_social="Empresa PDV LTDA",
            nome_fantasia="Empresa PDV",
            cnpj="52345678000191",
            regime_tributario=Empresa.RegimeTributario.SIMPLES_NACIONAL,
            codigo_regime_tributario=1,
        )
        cls.filial = Filial.objects.create(
            empresa=cls.empresa,
            razao_social="Filial PDV",
            nome_fantasia="Matriz",
            cnpj="52345678000192",
            uf="RN",
        )
        cls.perfil = PerfilAcesso.objects.create(
            empresa=cls.empresa,
            nome="Operador PDV",
            is_admin=True,
        )
        cls.usuario = Usuario.objects.create_user(
            email="pdv-estoque@inoovated.com",
            nome="Usuario PDV",
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
        cls.caixa = Caixa.objects.create(filial=cls.filial, numero=1, descricao="Caixa 1")
        cls.forma = FormaPagamento.objects.create(
            empresa=cls.empresa,
            descricao="Dinheiro",
            tipo=TipoFormaPagamento.DINHEIRO,
        )

    def setUp(self):
        self.sessao = SessaoPDV.objects.create(
            filial=self.filial,
            caixa=self.caixa,
            usuario=self.usuario,
            valor_abertura=Decimal("0.00"),
            status="aberto",
        )

    def criar_produto(self, descricao="Polpa PDV"):
        produto = Produto.objects.create(
            filial=self.filial,
            unidade_medida=self.unidade,
            descricao=descricao,
            ncm="20089900",
            controla_lote=False,
            permite_venda_sem_estoque=False,
            preco_venda=Decimal("10.00"),
            preco_custo=Decimal("4.00"),
        )
        ProdutoFilial.objects.create(produto=produto, filial=self.filial)
        return produto

    def abastecer(self, produto, quantidade="10"):
        return MovimentacaoService.registrar_movimentacao(
            produto_id=produto.pk,
            filial_id=self.filial.pk,
            tipo_operacao=MovimentacaoEstoque.TipoOperacao.ENTRADA,
            quantidade=Decimal(quantidade),
            usuario_id=self.usuario.pk,
            valor_unitario=Decimal("4.00"),
        )

    def aplicar_promocoes(self, produto):
        ProdutoFilial.objects.filter(produto=produto, filial=self.filial).update(
            preco_promocional=Decimal("7.00"),
            preco_promocional_ativo=True,
            promocao_tipo_desconto="preco_final",
            promocao_valor_desconto=Decimal("7.00"),
            promocao_dias_semana="0,1,2,3,4,5,6",
        )
        kit = KitCategoria.objects.create(
            filial=self.filial,
            nome="Desconto geral PDV",
            permite_preco_promocional=False,
        )
        KitCategoriaRegra.objects.create(
            kit=kit,
            quantidade_minima=Decimal("1"),
            tipo_desconto=TipoDesconto.PERCENTUAL,
            valor_desconto=Decimal("50.00"),
        )

    def test_finalizar_venda_usa_preco_vivo_e_baixa_estoque(self):
        produto = self.criar_produto()
        self.abastecer(produto, "10")
        self.aplicar_promocoes(produto)

        venda = VendaPDVService.finalizar_venda(
            sessao=self.sessao,
            filial=self.filial,
            usuario=self.usuario,
            itens=[{
                "produto_id": produto.pk,
                "quantidade": "2",
                "valor_unitario": "99.00",
            }],
            pagamentos=[{"forma_id": self.forma.pk, "valor": "10.00"}],
        )

        item = ItemVendaPDV.objects.get(venda_pdv=venda)
        estoque = Estoque.objects.get(produto=produto, filial=self.filial)
        movimento = MovimentacaoEstoque.objects.get(pk=item.movimentacoes_estoque_ids[0])

        self.assertEqual(venda.valor_total, Decimal("10.00"))
        self.assertEqual(item.valor_unitario, Decimal("5.0000"))
        self.assertEqual(item.valor_unitario_tabela, Decimal("10.0000"))
        self.assertEqual(item.custo_unitario_snapshot, Decimal("4.0000"))
        self.assertEqual(item.preco_origem, "categoria")
        self.assertTrue(item.estoque_baixado)
        self.assertEqual(estoque.quantidade_atual, Decimal("8.000"))
        self.assertEqual(estoque.quantidade_disponivel, Decimal("8.000"))
        self.assertEqual(movimento.documento_tipo, MovimentacaoEstoque.DocumentoTipo.NFCE)
        self.assertEqual(movimento.documento_id, venda.pk)

    def test_finalizar_venda_sem_estoque_faz_rollback(self):
        produto = self.criar_produto("Produto sem saldo")
        self.abastecer(produto, "1")

        with self.assertRaises(EstoqueInsuficienteError):
            VendaPDVService.finalizar_venda(
                sessao=self.sessao,
                filial=self.filial,
                usuario=self.usuario,
                itens=[{"produto_id": produto.pk, "quantidade": "2"}],
                pagamentos=[{"forma_id": self.forma.pk, "valor": "20.00"}],
            )

        estoque = Estoque.objects.get(produto=produto, filial=self.filial)
        self.assertEqual(estoque.quantidade_atual, Decimal("1.000"))
        self.assertEqual(VendaPDV.objects.count(), 0)
        self.assertEqual(ItemVendaPDV.objects.count(), 0)
