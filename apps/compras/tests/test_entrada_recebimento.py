from datetime import date, timedelta
from decimal import Decimal

from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.cadastros.models import Fornecedor, FornecedorFilial
from apps.compras.models import EntradaNF, EntradaNFParcela
from apps.compras.services.compra_service import CompraService
from apps.compras.services.entrada_xml_service import get_fornecedor_padrao, importar_xml_para_entrada
from apps.compras.views import (
    EntradaNFConferenciaView, EntradaNFCriarProdutoItemView, EntradaNFFornecedorPendenteView,
    EntradaNFDiferencasView, EntradaNFFinalizacaoView, EntradaNFFinanceiroView,
    EntradaNFGerarContasPagarView, EntradaNFImportarXMLView, EntradaNFLocalizarNotaView,
    EntradaNFVincularItemView, EntradaNFVincularSugestoesView,
)
from apps.core.models import Empresa, Filial, PerfilAcesso, Usuario
from apps.core.services.exceptions import DadosInvalidosError
from apps.estoque.models import Estoque, LoteProduto, MovimentacaoEstoque
from apps.financeiro.constants.enums import StatusContaPagar
from apps.financeiro.models import ContaPagar
from apps.produtos.models import (
    Produto, ProdutoCodigoBarras, ProdutoFilial, ProdutoFornecedorEquivalencia,
    UnidadeMedida, UnidadeMedidaFilial,
)


class EntradaRecebimentoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa = Empresa.objects.create(
            razao_social='Empresa Entrada LTDA',
            nome_fantasia='Entrada',
            cnpj='41234567000191',
            regime_tributario=Empresa.RegimeTributario.SIMPLES_NACIONAL,
            codigo_regime_tributario=1,
        )
        cls.filial = Filial.objects.create(
            empresa=cls.empresa,
            razao_social='Filial Entrada',
            nome_fantasia='Entrada RN',
            cnpj='41234567000192',
            uf='RN',
        )
        cls.perfil = PerfilAcesso.objects.create(
            empresa=cls.empresa,
            nome='Admin Entrada',
            is_admin=True,
        )
        cls.usuario = Usuario.objects.create_user(
            email='entrada-test@inoovated.com',
            nome='Usuario Entrada',
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

    def setUp(self):
        self.factory = RequestFactory()

    def request(self, method, path, data=None, files=None):
        if method == 'post':
            payload = data or {}
            if files:
                payload.update(files)
            request = self.factory.post(path, payload)
        else:
            request = self.factory.get(path, data or {})
        request.user = self.usuario
        request.filial_ativa = self.filial
        request.session = {}
        request._messages = FallbackStorage(request)
        return request

    def criar_fornecedor(self, documento='11222333000144'):
        fornecedor = Fornecedor.objects.create(
            filial=self.filial,
            tipo_pessoa='J',
            razao_social='Fornecedor XML',
            cpf_cnpj=documento,
            uf='RN',
        )
        FornecedorFilial.objects.create(fornecedor=fornecedor, filial=self.filial)
        return fornecedor

    def criar_produto(
        self,
        descricao='Produto XML',
        controla_lote=False,
        controla_validade=False,
        dias_aviso_vencimento=30,
    ):
        produto = Produto.objects.create(
            filial=self.filial,
            unidade_medida=self.unidade,
            descricao=descricao,
            ncm='20089900',
            controla_lote=controla_lote,
            controla_validade=controla_validade,
            dias_aviso_vencimento=dias_aviso_vencimento,
            permite_venda_sem_estoque=False,
            preco_custo=Decimal('0'),
            preco_venda=Decimal('10.00'),
        )
        ProdutoFilial.objects.create(produto=produto, filial=self.filial)
        return produto

    def chave(self, numero='000000123', cnpj='11222333000144'):
        return f'242605{cnpj}55001{numero}1123456789'

    def xml_nfe(
        self,
        chave,
        emit_doc='11222333000144',
        dest_doc='99988877000166',
        ean='7891000000001',
        codigo='FORN-001',
        quantidade='2.0000',
        valor_unitario='30.0000',
        valor_produto='60.00',
        rastro_xml='',
        cobr_xml='',
    ):
        emit_tag = 'CPF' if len(emit_doc) == 11 else 'CNPJ'
        dest_tag = 'CPF' if len(dest_doc) == 11 else 'CNPJ'
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
  <NFe>
    <infNFe Id="NFe{chave}" versao="4.00">
      <ide>
        <cUF>24</cUF>
        <serie>1</serie>
        <nNF>123</nNF>
        <dhEmi>2026-05-18T10:00:00-03:00</dhEmi>
      </ide>
      <emit>
        <{emit_tag}>{emit_doc}</{emit_tag}>
        <xNome>Fornecedor XML LTDA</xNome>
        <enderEmit>
          <xLgr>Rua Teste</xLgr>
          <nro>10</nro>
          <xMun>Natal</xMun>
          <UF>RN</UF>
          <CEP>59000000</CEP>
        </enderEmit>
      </emit>
      <dest>
        <{dest_tag}>{dest_doc}</{dest_tag}>
        <xNome>Outro Documento Operacional</xNome>
      </dest>
      <det nItem="1">
        <prod>
          <cProd>{codigo}</cProd>
          <cEAN>{ean}</cEAN>
          <xProd>Produto de fornecedor</xProd>
          <NCM>20089900</NCM>
          <uCom>CX</uCom>
          <qCom>{quantidade}</qCom>
          <vUnCom>{valor_unitario}</vUnCom>
          <vProd>{valor_produto}</vProd>
          {rastro_xml}
        </prod>
      </det>
      {cobr_xml}
      <total>
        <ICMSTot>
          <vProd>{valor_produto}</vProd>
          <vFrete>0.00</vFrete>
          <vSeg>0.00</vSeg>
          <vDesc>0.00</vDesc>
          <vOutro>0.00</vOutro>
          <vIPI>0.00</vIPI>
          <vICMS>0.00</vICMS>
          <vNF>{valor_produto}</vNF>
        </ICMSTot>
      </total>
    </infNFe>
  </NFe>
</nfeProc>'''

    def test_xml_com_destinatario_de_qualquer_documento_nao_bloqueia(self):
        entrada = importar_xml_para_entrada(
            self.xml_nfe(self.chave(), dest_doc='12345678901'),
            filial=self.filial,
            usuario=self.usuario,
            nome_arquivo='nota.xml',
        )

        item = entrada.itens.get()
        self.assertTrue(entrada.destinatario_documento_diferente)
        self.assertEqual(entrada.destinatario_documento_xml, '12345678901')
        self.assertFalse(entrada.fornecedor_pendente)
        self.assertEqual(entrada.fornecedor.cpf_cnpj, '11222333000144')
        self.assertEqual(entrada.fornecedor.razao_social, 'Fornecedor XML LTDA')
        self.assertEqual(entrada.status, EntradaNF.Status.AGUARDANDO_VINCULOS)
        self.assertIsNone(item.produto)
        self.assertTrue(item.diferenca_bloqueante)
        self.assertEqual(item.ncm_xml, '20089900')

    def test_xml_duplicado_na_mesma_filial_e_bloqueado(self):
        chave = self.chave(numero='000000124')
        importar_xml_para_entrada(
            self.xml_nfe(chave),
            filial=self.filial,
            usuario=self.usuario,
        )

        with self.assertRaisesMessage(DadosInvalidosError, 'ja foi importada'):
            importar_xml_para_entrada(
                self.xml_nfe(chave),
                filial=self.filial,
                usuario=self.usuario,
            )

    def test_xml_resolve_ean_converte_quantidade_e_movimenta_estoque(self):
        self.criar_fornecedor()
        produto = self.criar_produto()
        ProdutoCodigoBarras.objects.create(
            produto=produto,
            ean='7891000000001',
            tipo=ProdutoCodigoBarras.Tipo.FORNECEDOR,
            quantidade_conversao=Decimal('12'),
        )

        entrada = importar_xml_para_entrada(
            self.xml_nfe(self.chave(numero='000000125')),
            filial=self.filial,
            usuario=self.usuario,
        )
        item = entrada.itens.get()

        self.assertEqual(entrada.status, EntradaNF.Status.AGUARDANDO_CONFERENCIA)
        self.assertEqual(item.produto, produto)
        self.assertEqual(item.quantidade_xml, Decimal('2.000'))
        self.assertEqual(item.quantidade_estoque, Decimal('24.000'))
        self.assertEqual(item.valor_unitario, Decimal('2.5000'))

        CompraService.efetivar_entrada(entrada, self.usuario)

        entrada.refresh_from_db()
        estoque = Estoque.objects.get(produto=produto, filial=self.filial)
        self.assertEqual(entrada.status, EntradaNF.Status.EFETIVADA)
        self.assertEqual(estoque.quantidade_atual, Decimal('24.000'))
        self.assertEqual(estoque.quantidade_disponivel, Decimal('24.000'))

    def test_xml_importa_rastro_lote_validade_e_efetiva_com_lote_rastreavel(self):
        self.criar_fornecedor()
        validade = timezone.localdate() + timedelta(days=90)
        fabricacao = timezone.localdate() - timedelta(days=10)
        produto = self.criar_produto(
            'Produto rastreado XML',
            controla_lote=True,
            controla_validade=True,
        )
        ProdutoCodigoBarras.objects.create(
            produto=produto,
            ean='7891000000001',
            tipo=ProdutoCodigoBarras.Tipo.FORNECEDOR,
            quantidade_conversao=Decimal('1'),
        )

        entrada = importar_xml_para_entrada(
            self.xml_nfe(
                self.chave(numero='000000135'),
                quantidade='2.0000',
                valor_unitario='30.0000',
                valor_produto='60.00',
                rastro_xml=f'''
          <rastro>
            <nLote>XML-LOTE-01</nLote>
            <qLote>2.0000</qLote>
            <dFab>{fabricacao:%Y-%m-%d}</dFab>
            <dVal>{validade:%Y-%m-%d}</dVal>
          </rastro>''',
            ),
            filial=self.filial,
            usuario=self.usuario,
        )
        item = entrada.itens.get()

        self.assertEqual(entrada.status, EntradaNF.Status.AGUARDANDO_CONFERENCIA)
        self.assertEqual(item.numero_lote, 'XML-LOTE-01')
        self.assertEqual(item.data_fabricacao, fabricacao)
        self.assertEqual(item.data_validade, validade)
        self.assertFalse(item.diferenca_bloqueante)

        CompraService.efetivar_entrada(entrada, self.usuario)
        item.refresh_from_db()
        lote = LoteProduto.objects.get(produto=produto, filial=self.filial)
        movimento = MovimentacaoEstoque.objects.get(
            produto=produto,
            filial=self.filial,
            documento_id=entrada.pk,
        )

        self.assertEqual(item.lote_gerado, lote)
        self.assertEqual(movimento.lote, lote)
        self.assertEqual(lote.numero_lote, 'XML-LOTE-01')
        self.assertEqual(lote.data_validade, validade)
        self.assertEqual(lote.quantidade_atual, Decimal('2.000'))

    def test_xml_sem_rastro_bloqueia_produto_que_controla_lote_validade(self):
        self.criar_fornecedor()
        produto = self.criar_produto(
            'Produto lote obrigatorio XML',
            controla_lote=True,
            controla_validade=True,
        )
        ProdutoCodigoBarras.objects.create(
            produto=produto,
            ean='7891000000001',
            tipo=ProdutoCodigoBarras.Tipo.FORNECEDOR,
            quantidade_conversao=Decimal('1'),
        )

        entrada = importar_xml_para_entrada(
            self.xml_nfe(self.chave(numero='000000136')),
            filial=self.filial,
            usuario=self.usuario,
        )
        item = entrada.itens.get()

        self.assertEqual(entrada.status, EntradaNF.Status.AGUARDANDO_VINCULOS)
        self.assertEqual(item.diferenca_tipo, 'lote_obrigatorio')
        self.assertTrue(item.diferenca_bloqueante)
        entrada.status = EntradaNF.Status.CONFERIDA
        entrada.save(update_fields=['status', 'updated_at'])
        with self.assertRaisesMessage(DadosInvalidosError, 'lote obrigatorio'):
            CompraService.efetivar_entrada(entrada, self.usuario)

    def test_xml_com_validade_vencida_bloqueia_finalizacao(self):
        self.criar_fornecedor()
        vencida = timezone.localdate() - timedelta(days=1)
        produto = self.criar_produto(
            'Produto validade vencida XML',
            controla_lote=True,
            controla_validade=True,
        )
        ProdutoCodigoBarras.objects.create(
            produto=produto,
            ean='7891000000001',
            tipo=ProdutoCodigoBarras.Tipo.FORNECEDOR,
            quantidade_conversao=Decimal('1'),
        )

        entrada = importar_xml_para_entrada(
            self.xml_nfe(
                self.chave(numero='000000137'),
                rastro_xml=f'''
          <rastro>
            <nLote>XML-VENCIDO</nLote>
            <qLote>2.0000</qLote>
            <dVal>{vencida:%Y-%m-%d}</dVal>
          </rastro>''',
            ),
            filial=self.filial,
            usuario=self.usuario,
        )
        item = entrada.itens.get()

        self.assertEqual(entrada.status, EntradaNF.Status.AGUARDANDO_VINCULOS)
        self.assertEqual(item.diferenca_tipo, 'validade_vencida')
        self.assertTrue(item.diferenca_bloqueante)
        entrada.status = EntradaNF.Status.CONFERIDA
        entrada.save(update_fields=['status', 'updated_at'])
        with self.assertRaisesMessage(DadosInvalidosError, 'validade vencida'):
            CompraService.efetivar_entrada(entrada, self.usuario)

        path = reverse('compras:entrada-finalizacao', args=[entrada.pk])
        request = self.request('get', path)
        response = EntradaNFFinalizacaoView.as_view()(request, pk=entrada.pk)
        self.assertContains(response, 'validade vencida')

    def test_xml_com_validade_proxima_vira_alerta_sem_bloquear_estoque(self):
        self.criar_fornecedor()
        validade = timezone.localdate() + timedelta(days=5)
        produto = self.criar_produto(
            'Produto validade proxima XML',
            controla_lote=True,
            controla_validade=True,
            dias_aviso_vencimento=30,
        )
        ProdutoCodigoBarras.objects.create(
            produto=produto,
            ean='7891000000001',
            tipo=ProdutoCodigoBarras.Tipo.FORNECEDOR,
            quantidade_conversao=Decimal('1'),
        )

        entrada = importar_xml_para_entrada(
            self.xml_nfe(
                self.chave(numero='000000138'),
                rastro_xml=f'''
          <rastro>
            <nLote>XML-PROXIMO</nLote>
            <qLote>2.0000</qLote>
            <dVal>{validade:%Y-%m-%d}</dVal>
          </rastro>''',
            ),
            filial=self.filial,
            usuario=self.usuario,
        )
        item = entrada.itens.get()

        self.assertEqual(entrada.status, EntradaNF.Status.COM_DIFERENCAS)
        self.assertEqual(item.diferenca_tipo, 'validade_proxima')
        self.assertFalse(item.diferenca_bloqueante)
        CompraService.efetivar_entrada(entrada, self.usuario)
        self.assertTrue(LoteProduto.objects.filter(numero_lote='XML-PROXIMO').exists())

    def test_xml_com_multiplos_rastros_separa_itens_por_lote(self):
        self.criar_fornecedor()
        validade = timezone.localdate() + timedelta(days=90)
        produto = self.criar_produto(
            'Produto multi lote XML',
            controla_lote=True,
            controla_validade=True,
        )
        ProdutoCodigoBarras.objects.create(
            produto=produto,
            ean='7891000000001',
            tipo=ProdutoCodigoBarras.Tipo.FORNECEDOR,
            quantidade_conversao=Decimal('1'),
        )

        entrada = importar_xml_para_entrada(
            self.xml_nfe(
                self.chave(numero='000000139'),
                quantidade='3.0000',
                valor_unitario='20.0000',
                valor_produto='60.00',
                rastro_xml=f'''
          <rastro>
            <nLote>XML-LOTE-A</nLote>
            <qLote>1.0000</qLote>
            <dVal>{validade:%Y-%m-%d}</dVal>
          </rastro>
          <rastro>
            <nLote>XML-LOTE-B</nLote>
            <qLote>2.0000</qLote>
            <dVal>{validade:%Y-%m-%d}</dVal>
          </rastro>''',
            ),
            filial=self.filial,
            usuario=self.usuario,
        )

        itens = list(entrada.itens.order_by('numero_lote'))
        self.assertEqual(len(itens), 2)
        self.assertEqual(itens[0].numero_lote, 'XML-LOTE-A')
        self.assertEqual(itens[0].quantidade_xml, Decimal('1.000'))
        self.assertEqual(itens[0].valor_total, Decimal('20.00'))
        self.assertEqual(itens[1].numero_lote, 'XML-LOTE-B')
        self.assertEqual(itens[1].quantidade_xml, Decimal('2.000'))
        self.assertEqual(itens[1].valor_total, Decimal('40.00'))

    def test_finalizacao_bloqueia_item_sem_produto_vinculado(self):
        fornecedor = self.criar_fornecedor(documento='22333444000155')
        entrada = CompraService.criar_entrada_nf(
            filial=self.filial,
            usuario=self.usuario,
            fornecedor=fornecedor,
            numero_nf='NF-SEMVINC',
            serie_nf='1',
            data_emissao_nf=timezone.localdate(),
        )
        entrada.itens.create(
            numero_item=1,
            quantidade=Decimal('1'),
            quantidade_xml=Decimal('1'),
            quantidade_estoque=Decimal('1'),
            quantidade_recebida=Decimal('1'),
            valor_unitario=Decimal('5'),
            valor_bruto=Decimal('5'),
            valor_total=Decimal('5'),
            diferenca_bloqueante=True,
            diferenca_descricao='Produto sem equivalencia interna.',
        )

        with self.assertRaisesMessage(DadosInvalidosError, 'produto sem vinculo'):
            CompraService.efetivar_entrada(entrada, self.usuario)

    def test_tela_localizar_entrada_renderiza_caminhos(self):
        path = reverse('compras:entrada-localizar')
        request = self.request('get', path)
        response = EntradaNFLocalizarNotaView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'XML')
        self.assertContains(response, 'Chave')
        self.assertContains(response, 'Manual')

    def test_view_importar_xml_cria_entrada_e_abre_conferencia(self):
        arquivo = SimpleUploadedFile(
            'nota.xml',
            self.xml_nfe(self.chave(numero='000000126')).encode('utf-8'),
            content_type='text/xml',
        )

        path = reverse('compras:entrada-importar-xml')
        request = self.request('post', path, {'arquivo_xml': arquivo})
        response = EntradaNFImportarXMLView.as_view()(request)

        entrada = EntradaNF.objects.get(numero_nf='123')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('compras:entrada-conferencia', args=[entrada.pk]))

        request = self.request('get', response.url)
        conferencia = EntradaNFConferenciaView.as_view()(request, pk=entrada.pk)
        self.assertEqual(conferencia.status_code, 200)
        self.assertContains(conferencia, 'Produto de fornecedor')

    def test_conferencia_sugere_produtos_por_nome_e_ncm(self):
        self.criar_produto(descricao='Produto fornecedor estoque interno')
        entrada = importar_xml_para_entrada(
            self.xml_nfe(self.chave(numero='000000127')),
            filial=self.filial,
            usuario=self.usuario,
        )

        path = reverse('compras:entrada-conferencia', args=[entrada.pk])
        request = self.request('get', path)
        response = EntradaNFConferenciaView.as_view()(request, pk=entrada.pk)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sugestoes')
        self.assertContains(response, 'Produto fornecedor estoque interno')
        item = entrada.itens.get()
        self.assertContains(response, f'name="produto_{item.pk}"')
        self.assertContains(response, f'name="fator_conversao_{item.pk}"')
        self.assertContains(response, 'Cadastrar pelo XML')

    def test_conferencia_confirma_sugestoes_em_lote(self):
        produto = self.criar_produto(descricao='Produto fornecedor estoque interno')
        entrada = importar_xml_para_entrada(
            self.xml_nfe(self.chave(numero='000000132')),
            filial=self.filial,
            usuario=self.usuario,
        )
        item = entrada.itens.get()

        path = reverse('compras:entrada-vincular-sugestoes', args=[entrada.pk])
        request = self.request('post', path, {
            'item': [str(item.pk)],
            f'produto_{item.pk}': str(produto.pk),
            f'fator_conversao_{item.pk}': '3',
            f'unidade_estoque_{item.pk}': 'UN',
            f'numero_lote_{item.pk}': 'LOTE-132',
            f'data_validade_{item.pk}': '2026-12-31',
        })
        response = EntradaNFVincularSugestoesView.as_view()(request, pk=entrada.pk)

        item.refresh_from_db()
        entrada.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(item.produto, produto)
        self.assertEqual(item.fator_conversao, Decimal('3'))
        self.assertEqual(item.quantidade_recebida, Decimal('6.0000'))
        self.assertEqual(item.unidade_estoque, 'UN')
        self.assertEqual(item.numero_lote, 'LOTE-132')
        self.assertEqual(item.data_validade, date(2026, 12, 31))
        self.assertEqual(entrada.status, EntradaNF.Status.AGUARDANDO_CONFERENCIA)
        self.assertTrue(
            ProdutoFornecedorEquivalencia.objects.filter(
                produto=produto,
                fornecedor=entrada.fornecedor,
                codigo_fornecedor='FORN-001',
            ).exists()
        )

    def test_conferencia_lote_aceita_segunda_sugestao_recalculada(self):
        self.criar_produto(descricao='Produto fornecedor estoque interno')
        produto_alternativo = self.criar_produto(descricao='Produto fornecedor alternativa interna')
        entrada = importar_xml_para_entrada(
            self.xml_nfe(self.chave(numero='000000137')),
            filial=self.filial,
            usuario=self.usuario,
        )
        item = entrada.itens.get()

        path = reverse('compras:entrada-vincular-sugestoes', args=[entrada.pk])
        request = self.request('post', path, {
            'item': [str(item.pk)],
            f'produto_{item.pk}': str(produto_alternativo.pk),
            f'fator_conversao_{item.pk}': '1',
            f'unidade_estoque_{item.pk}': 'UN',
        })
        response = EntradaNFVincularSugestoesView.as_view()(request, pk=entrada.pk)

        item.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(item.produto, produto_alternativo)

    def test_conferencia_lote_ignora_sugestao_trocada(self):
        produto_sugerido = self.criar_produto(descricao='Produto fornecedor estoque interno')
        produto_trocado = self.criar_produto(descricao='Outro produto interno')
        produto_trocado.descricao = 'Sem relacao operacional'
        produto_trocado.ncm = '00000000'
        produto_trocado.save()
        entrada = importar_xml_para_entrada(
            self.xml_nfe(self.chave(numero='000000133')),
            filial=self.filial,
            usuario=self.usuario,
        )
        item = entrada.itens.get()

        path = reverse('compras:entrada-vincular-sugestoes', args=[entrada.pk])
        request = self.request('post', path, {
            'item': [str(item.pk)],
            f'produto_{item.pk}': str(produto_trocado.pk),
            f'fator_conversao_{item.pk}': '1',
            f'unidade_estoque_{item.pk}': 'UN',
        })
        response = EntradaNFVincularSugestoesView.as_view()(request, pk=entrada.pk)

        item.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(item.produto)
        self.assertFalse(
            ProdutoFornecedorEquivalencia.objects.filter(produto=produto_sugerido).exists()
        )

    def test_criar_produto_pelo_item_xml_cadastra_e_vincula_item(self):
        entrada = importar_xml_para_entrada(
            self.xml_nfe(self.chave(numero='000000128')),
            filial=self.filial,
            usuario=self.usuario,
        )
        item = entrada.itens.get()

        path = reverse('compras:entrada-criar-produto-item', args=[entrada.pk, item.pk])
        request = self.request('post', path)
        response = EntradaNFCriarProdutoItemView.as_view()(request, pk=entrada.pk, item_id=item.pk)

        item.refresh_from_db()
        produto = item.produto
        self.assertEqual(response.status_code, 302)
        self.assertIsNotNone(produto)
        self.assertEqual(produto.descricao, 'Produto de fornecedor')
        self.assertEqual(produto.ncm, '20089900')
        self.assertEqual(produto.codigo_barras, '7891000000001')
        self.assertFalse(produto.permite_venda_sem_estoque)
        self.assertTrue(ProdutoFilial.objects.filter(produto=produto, filial=self.filial).exists())
        self.assertTrue(ProdutoCodigoBarras.objects.filter(produto=produto, ean='7891000000001').exists())
        self.assertTrue(
            ProdutoFornecedorEquivalencia.objects.filter(
                produto=produto,
                fornecedor=entrada.fornecedor,
                codigo_fornecedor='FORN-001',
            ).exists()
        )

    def test_criar_produto_pelo_xml_com_rastro_habilita_lote_validade(self):
        validade = timezone.localdate() + timedelta(days=90)
        fabricacao = timezone.localdate() - timedelta(days=5)
        entrada = importar_xml_para_entrada(
            self.xml_nfe(
                self.chave(numero='000000140'),
                rastro_xml=f'''
          <rastro>
            <nLote>XML-CAD-LOTE</nLote>
            <qLote>2.0000</qLote>
            <dFab>{fabricacao:%Y-%m-%d}</dFab>
            <dVal>{validade:%Y-%m-%d}</dVal>
          </rastro>''',
            ),
            filial=self.filial,
            usuario=self.usuario,
        )
        item = entrada.itens.get()

        path = reverse('compras:entrada-criar-produto-item', args=[entrada.pk, item.pk])
        request = self.request('post', path)
        response = EntradaNFCriarProdutoItemView.as_view()(request, pk=entrada.pk, item_id=item.pk)

        item.refresh_from_db()
        entrada.refresh_from_db()
        produto = item.produto
        self.assertEqual(response.status_code, 302)
        self.assertIsNotNone(produto)
        self.assertTrue(produto.controla_lote)
        self.assertTrue(produto.controla_validade)
        self.assertEqual(item.numero_lote, 'XML-CAD-LOTE')
        self.assertEqual(item.data_fabricacao, fabricacao)
        self.assertEqual(item.data_validade, validade)
        self.assertEqual(entrada.status, EntradaNF.Status.AGUARDANDO_CONFERENCIA)

        CompraService.efetivar_entrada(entrada, self.usuario)
        self.assertTrue(
            LoteProduto.objects.filter(
                produto=produto,
                filial=self.filial,
                numero_lote='XML-CAD-LOTE',
            ).exists()
        )

    def test_criar_produto_pelo_xml_reaproveita_produto_de_outro_lote(self):
        validade = timezone.localdate() + timedelta(days=90)
        entrada = importar_xml_para_entrada(
            self.xml_nfe(
                self.chave(numero='000000141'),
                quantidade='3.0000',
                valor_unitario='20.0000',
                valor_produto='60.00',
                rastro_xml=f'''
          <rastro>
            <nLote>XML-CAD-A</nLote>
            <qLote>1.0000</qLote>
            <dVal>{validade:%Y-%m-%d}</dVal>
          </rastro>
          <rastro>
            <nLote>XML-CAD-B</nLote>
            <qLote>2.0000</qLote>
            <dVal>{validade:%Y-%m-%d}</dVal>
          </rastro>''',
            ),
            filial=self.filial,
            usuario=self.usuario,
        )
        item_a, item_b = list(entrada.itens.order_by('numero_lote'))

        path_a = reverse('compras:entrada-criar-produto-item', args=[entrada.pk, item_a.pk])
        request_a = self.request('post', path_a)
        EntradaNFCriarProdutoItemView.as_view()(request_a, pk=entrada.pk, item_id=item_a.pk)
        item_a.refresh_from_db()
        produto = item_a.produto

        path_b = reverse('compras:entrada-criar-produto-item', args=[entrada.pk, item_b.pk])
        request_b = self.request('post', path_b)
        response = EntradaNFCriarProdutoItemView.as_view()(request_b, pk=entrada.pk, item_id=item_b.pk)

        item_b.refresh_from_db()
        entrada.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(item_b.produto, produto)
        self.assertEqual(
            Produto.objects.filter(filial=self.filial, codigo_barras='7891000000001').count(),
            1,
        )
        self.assertEqual(entrada.status, EntradaNF.Status.AGUARDANDO_CONFERENCIA)

    def test_vincular_item_aceita_fator_decimal_localizado_da_tela(self):
        produto = self.criar_produto('Produto interno localizado')
        entrada = importar_xml_para_entrada(
            self.xml_nfe(self.chave(numero='000000129')),
            filial=self.filial,
            usuario=self.usuario,
        )
        item = entrada.itens.get()

        path = reverse('compras:entrada-vincular-item', args=[entrada.pk, item.pk])
        request = self.request('post', path, {
            'produto': str(produto.pk),
            'fator_conversao': '1,0000',
            'unidade_estoque': 'UN',
        })
        response = EntradaNFVincularItemView.as_view()(request, pk=entrada.pk, item_id=item.pk)

        item.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(item.produto, produto)
        self.assertEqual(item.fator_conversao, Decimal('1.0000'))
        self.assertTrue(
            ProdutoFornecedorEquivalencia.objects.filter(
                produto=produto,
                fornecedor=entrada.fornecedor,
                codigo_fornecedor='FORN-001',
            ).exists()
        )

    def test_xml_importa_duplicatas_como_pre_financeiro(self):
        cobr_xml = '''
      <cobr>
        <fat>
          <nFat>123</nFat>
          <vOrig>60.00</vOrig>
          <vLiq>60.00</vLiq>
        </fat>
        <dup>
          <nDup>001</nDup>
          <dVenc>2026-06-20</dVenc>
          <vDup>30.00</vDup>
        </dup>
        <dup>
          <nDup>002</nDup>
          <dVenc>2026-07-20</dVenc>
          <vDup>30.00</vDup>
        </dup>
      </cobr>'''
        entrada = importar_xml_para_entrada(
            self.xml_nfe(self.chave(numero='000000130'), cobr_xml=cobr_xml),
            filial=self.filial,
            usuario=self.usuario,
        )

        parcelas = list(entrada.parcelas_financeiras.order_by('numero'))
        self.assertEqual(len(parcelas), 2)
        self.assertEqual(parcelas[0].numero, '001')
        self.assertEqual(parcelas[0].valor, Decimal('30.00'))
        self.assertEqual(parcelas[0].origem, EntradaNFParcela.Origem.XML)
        self.assertEqual(parcelas[0].status, EntradaNFParcela.Status.PENDENTE)
        self.assertEqual(parcelas[0].emitente_documento_xml, '11222333000144')

    def test_financeiro_permite_parcela_manual_sem_gerar_conta_pagar(self):
        entrada = importar_xml_para_entrada(
            self.xml_nfe(self.chave(numero='000000131')),
            filial=self.filial,
            usuario=self.usuario,
        )

        path = reverse('compras:entrada-financeiro', args=[entrada.pk])
        request = self.request('post', path, {
            'numero': '',
            'data_vencimento': '2026-06-25',
            'valor': '60.00',
            'forma_pagamento': 'Boleto',
            'observacao': 'Parcela manual',
        })
        response = EntradaNFFinanceiroView.as_view()(request, pk=entrada.pk)

        parcela = entrada.parcelas_financeiras.get()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(parcela.numero, '001')
        self.assertEqual(parcela.origem, EntradaNFParcela.Origem.MANUAL)
        self.assertEqual(parcela.conta_pagar_id, None)

        request = self.request('get', path)
        tela = EntradaNFFinanceiroView.as_view()(request, pk=entrada.pk)
        self.assertEqual(tela.status_code, 200)
        self.assertContains(tela, 'Boleto')
        self.assertContains(tela, 'Revise as parcelas')

    def test_financeiro_gera_conta_pagar_apenas_apos_entrada_efetivada(self):
        fornecedor = self.criar_fornecedor(documento='66777888000199')
        produto = self.criar_produto('Produto financeiro entrada')
        entrada = CompraService.criar_entrada_nf(
            filial=self.filial,
            usuario=self.usuario,
            fornecedor=fornecedor,
            numero_nf='NF-FIN-GERAR',
            serie_nf='1',
            data_emissao_nf=timezone.localdate(),
        )
        CompraService.adicionar_item_entrada(
            entrada=entrada,
            produto=produto,
            quantidade=Decimal('2'),
            valor_unitario=Decimal('30'),
            unidade_xml='UN',
            fator_conversao=Decimal('1'),
        )
        EntradaNFParcela.objects.create(
            entrada=entrada,
            numero='001',
            data_vencimento=timezone.localdate(),
            valor=Decimal('60.00'),
            forma_pagamento='Boleto',
            origem=EntradaNFParcela.Origem.MANUAL,
        )

        path = reverse('compras:entrada-gerar-contas-pagar', args=[entrada.pk])
        request = self.request('post', path)
        response = EntradaNFGerarContasPagarView.as_view()(request, pk=entrada.pk)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ContaPagar.objects.exists())

        CompraService.efetivar_entrada(entrada, self.usuario)
        request = self.request('post', path)
        response = EntradaNFGerarContasPagarView.as_view()(request, pk=entrada.pk)

        parcela = entrada.parcelas_financeiras.get()
        conta = ContaPagar.objects.get()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(conta.filial, self.filial)
        self.assertEqual(conta.fornecedor, fornecedor)
        self.assertEqual(conta.documento_tipo, 'entrada_nf')
        self.assertEqual(conta.documento_id, entrada.pk)
        self.assertEqual(conta.documento_numero, 'NF-FIN-GERAR')
        self.assertEqual(conta.nota_fiscal_fornecedor, 'NF-FIN-GERAR')
        self.assertEqual(conta.parcela, 1)
        self.assertEqual(conta.total_parcelas, 1)
        self.assertEqual(conta.valor_original, Decimal('60.00'))
        self.assertEqual(conta.valor_final, Decimal('60.00'))
        self.assertEqual(conta.valor_saldo, Decimal('60.00'))
        self.assertEqual(conta.status, StatusContaPagar.ABERTO)
        self.assertEqual(parcela.status, EntradaNFParcela.Status.GERADA)
        self.assertEqual(parcela.conta_pagar_id, conta.pk)

        request = self.request('post', path)
        EntradaNFGerarContasPagarView.as_view()(request, pk=entrada.pk)
        self.assertEqual(ContaPagar.objects.count(), 1)

    def test_financeiro_nao_gera_conta_pagar_com_fornecedor_pendente(self):
        entrada = importar_xml_para_entrada(
            self.xml_nfe(
                self.chave(numero='000000134', cnpj='12312312000155'),
                emit_doc='12312312000155',
                cobr_xml='''
      <cobr>
        <dup>
          <nDup>001</nDup>
          <dVenc>2026-06-20</dVenc>
          <vDup>60.00</vDup>
        </dup>
      </cobr>''',
            ),
            filial=self.filial,
            usuario=self.usuario,
        )
        entrada.fornecedor_pendente = True
        entrada.status = EntradaNF.Status.EFETIVADA
        entrada.save(update_fields=['fornecedor_pendente', 'status', 'updated_at'])

        path = reverse('compras:entrada-gerar-contas-pagar', args=[entrada.pk])
        request = self.request('post', path)
        response = EntradaNFGerarContasPagarView.as_view()(request, pk=entrada.pk)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(ContaPagar.objects.exists())
        self.assertEqual(entrada.parcelas_financeiras.get().status, EntradaNFParcela.Status.PENDENTE)

    def test_tela_financeiro_exibe_acao_de_geracao_para_entrada_efetivada(self):
        fornecedor = self.criar_fornecedor(documento='77888999000100')
        entrada = CompraService.criar_entrada_nf(
            filial=self.filial,
            usuario=self.usuario,
            fornecedor=fornecedor,
            numero_nf='NF-FIN-TELA',
            serie_nf='1',
            data_emissao_nf=timezone.localdate(),
        )
        entrada.valor_total = Decimal('25.00')
        entrada.status = EntradaNF.Status.EFETIVADA
        entrada.save(update_fields=['valor_total', 'status', 'updated_at'])
        EntradaNFParcela.objects.create(
            entrada=entrada,
            numero='001',
            data_vencimento=timezone.localdate(),
            valor=Decimal('25.00'),
            origem=EntradaNFParcela.Origem.MANUAL,
        )

        path = reverse('compras:entrada-financeiro', args=[entrada.pk])
        request = self.request('get', path)
        response = EntradaNFFinanceiroView.as_view()(request, pk=entrada.pk)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Gerar contas a pagar')
        self.assertContains(response, '1 parcela(s) pronta(s) para gerar')

    def test_diferencas_justifica_quantidade_recebida_e_libera_bloqueio(self):
        fornecedor = self.criar_fornecedor(documento='33444555000166')
        produto = self.criar_produto('Produto com recebimento parcial')
        entrada = CompraService.criar_entrada_nf(
            filial=self.filial,
            usuario=self.usuario,
            fornecedor=fornecedor,
            numero_nf='NF-DIFF-QTD',
            serie_nf='1',
            data_emissao_nf=timezone.localdate(),
        )
        item = CompraService.adicionar_item_entrada(
            entrada=entrada,
            produto=produto,
            quantidade=Decimal('2'),
            valor_unitario=Decimal('10'),
            unidade_xml='UN',
            fator_conversao=Decimal('1'),
        )

        path = reverse('compras:entrada-diferencas', args=[entrada.pk])
        request = self.request('post', path, {
            'item_id': str(item.pk),
            'quantidade_recebida': '1,000',
            'numero_lote': '',
            'data_validade': '',
            'justificativa_diferenca': 'Recebimento parcial conferido na doca.',
        })
        response = EntradaNFDiferencasView.as_view()(request, pk=entrada.pk)

        item.refresh_from_db()
        entrada.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(item.quantidade_recebida, Decimal('1.000'))
        self.assertEqual(item.diferenca_tipo, 'quantidade_recebida')
        self.assertFalse(item.diferenca_bloqueante)
        self.assertEqual(entrada.status, EntradaNF.Status.COM_DIFERENCAS)
        CompraService._validar_itens_para_efetivar(entrada)

    def test_diferencas_lote_obrigatorio_permanece_bloqueante_ate_informar_lote(self):
        fornecedor = self.criar_fornecedor(documento='44555666000177')
        produto = self.criar_produto('Produto rastreado')
        produto.controla_lote = True
        produto.save(update_fields=['controla_lote', 'updated_at'])
        entrada = CompraService.criar_entrada_nf(
            filial=self.filial,
            usuario=self.usuario,
            fornecedor=fornecedor,
            numero_nf='NF-DIFF-LOTE',
            serie_nf='1',
            data_emissao_nf=timezone.localdate(),
        )
        item = entrada.itens.create(
            produto=produto,
            numero_item=1,
            quantidade=Decimal('2'),
            quantidade_xml=Decimal('2'),
            quantidade_estoque=Decimal('2'),
            quantidade_recebida=Decimal('2'),
            unidade_xml='UN',
            unidade_estoque='UN',
            fator_conversao=Decimal('1'),
            valor_unitario=Decimal('10'),
            valor_bruto=Decimal('20'),
            valor_total=Decimal('20'),
        )

        path = reverse('compras:entrada-diferencas', args=[entrada.pk])
        request = self.request('post', path, {
            'item_id': str(item.pk),
            'quantidade_recebida': '2,000',
            'numero_lote': '',
            'data_validade': '',
            'justificativa_diferenca': '',
        })
        response = EntradaNFDiferencasView.as_view()(request, pk=entrada.pk)
        item.refresh_from_db()
        entrada.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(item.diferenca_tipo, 'lote_obrigatorio')
        self.assertTrue(item.diferenca_bloqueante)
        self.assertEqual(entrada.status, EntradaNF.Status.AGUARDANDO_VINCULOS)

        request = self.request('post', path, {
            'item_id': str(item.pk),
            'quantidade_recebida': '2,000',
            'numero_lote': 'LOTE-01',
            'data_validade': '',
            'justificativa_diferenca': '',
        })
        EntradaNFDiferencasView.as_view()(request, pk=entrada.pk)
        item.refresh_from_db()
        entrada.refresh_from_db()
        self.assertEqual(item.numero_lote, 'LOTE-01')
        self.assertEqual(item.diferenca_tipo, '')
        self.assertFalse(item.diferenca_bloqueante)
        self.assertEqual(entrada.status, EntradaNF.Status.AGUARDANDO_CONFERENCIA)

    def test_tela_diferencas_renderiza_edicao_da_conferencia(self):
        fornecedor = self.criar_fornecedor(documento='55666777000188')
        produto = self.criar_produto('Produto com diferenca visual')
        entrada = CompraService.criar_entrada_nf(
            filial=self.filial,
            usuario=self.usuario,
            fornecedor=fornecedor,
            numero_nf='NF-DIFF-TELA',
            serie_nf='1',
            data_emissao_nf=timezone.localdate(),
        )
        item = CompraService.adicionar_item_entrada(
            entrada=entrada,
            produto=produto,
            quantidade=Decimal('3'),
            valor_unitario=Decimal('10'),
            unidade_xml='UN',
            fator_conversao=Decimal('1'),
        )
        item.quantidade_recebida = Decimal('2')
        item.diferenca_tipo = 'quantidade_recebida'
        item.diferenca_descricao = 'Quantidade recebida diferente da nota.'
        item.diferenca_bloqueante = True
        item.save(update_fields=[
            'quantidade_recebida', 'diferenca_tipo', 'diferenca_descricao',
            'diferenca_bloqueante', 'updated_at',
        ])

        path = reverse('compras:entrada-diferencas', args=[entrada.pk])
        request = self.request('get', path)
        response = EntradaNFDiferencasView.as_view()(request, pk=entrada.pk)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Quantidade recebida')
        self.assertContains(response, 'Justificativa')
        self.assertContains(response, 'Salvar diferenca')

    def test_tela_diferencas_recalcula_lote_obrigatorio_para_exibicao(self):
        fornecedor = self.criar_fornecedor(documento='66777888000199')
        produto = self.criar_produto('Produto rastreio visual')
        entrada = CompraService.criar_entrada_nf(
            filial=self.filial,
            usuario=self.usuario,
            fornecedor=fornecedor,
            numero_nf='NF-DIFF-STALE',
            serie_nf='1',
            data_emissao_nf=timezone.localdate(),
        )
        item = CompraService.adicionar_item_entrada(
            entrada=entrada,
            produto=produto,
            quantidade=Decimal('2'),
            valor_unitario=Decimal('10'),
            unidade_xml='UN',
            fator_conversao=Decimal('1'),
        )
        produto.controla_lote = True
        produto.save(update_fields=['controla_lote', 'updated_at'])
        item.diferenca_tipo = ''
        item.diferenca_descricao = ''
        item.diferenca_bloqueante = False
        item.save(update_fields=[
            'diferenca_tipo', 'diferenca_descricao', 'diferenca_bloqueante', 'updated_at',
        ])

        path = reverse('compras:entrada-diferencas', args=[entrada.pk])
        request = self.request('get', path)
        response = EntradaNFDiferencasView.as_view()(request, pk=entrada.pk)

        item.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Produto exige lote para movimentar estoque')
        self.assertContains(response, 'lote obrigatorio')
        self.assertEqual(item.diferenca_tipo, '')

    def test_finalizacao_recalcula_bloqueios_antes_de_liberar_botao(self):
        fornecedor = self.criar_fornecedor(documento='77888999000100')
        produto = self.criar_produto('Produto finalizacao rastreavel')
        entrada = CompraService.criar_entrada_nf(
            filial=self.filial,
            usuario=self.usuario,
            fornecedor=fornecedor,
            numero_nf='NF-FINAL-STALE',
            serie_nf='1',
            data_emissao_nf=timezone.localdate(),
        )
        item = CompraService.adicionar_item_entrada(
            entrada=entrada,
            produto=produto,
            quantidade=Decimal('2'),
            valor_unitario=Decimal('10'),
            unidade_xml='UN',
            fator_conversao=Decimal('1'),
        )
        produto.controla_lote = True
        produto.save(update_fields=['controla_lote', 'updated_at'])
        item.diferenca_tipo = ''
        item.diferenca_descricao = ''
        item.diferenca_bloqueante = False
        item.save(update_fields=[
            'diferenca_tipo', 'diferenca_descricao', 'diferenca_bloqueante', 'updated_at',
        ])

        path = reverse('compras:entrada-finalizacao', args=[entrada.pk])
        request = self.request('get', path)
        response = EntradaNFFinalizacaoView.as_view()(request, pk=entrada.pk)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1 diferenca(s) bloqueante(s) pendente(s)')
        self.assertContains(response, '1 item(ns) com lote obrigatorio pendente')
        self.assertContains(response, 'Resolver diferencas')
        self.assertNotContains(response, reverse('compras:entrada-efetivar', args=[entrada.pk]))

    def test_fornecedor_pendente_cria_fornecedor_pelo_xml_e_atualiza_equivalencias(self):
        produto = self.criar_produto()
        entrada = CompraService.criar_entrada_nf(
            filial=self.filial,
            usuario=self.usuario,
            fornecedor=get_fornecedor_padrao(self.filial),
            numero_nf='NF-FORNPEND',
            serie_nf='1',
            data_emissao_nf=timezone.localdate(),
            origem_entrada=EntradaNF.OrigemEntrada.XML,
            fornecedor_pendente=True,
            dados_emitente_xml={
                'documento': '11222333000144',
                'razao_social': 'Fornecedor XML LTDA',
                'nome_fantasia': 'Fornecedor XML',
                'ie': '200000000',
                'endereco': 'Rua Teste 10',
                'municipio': 'Natal',
                'uf': 'RN',
                'cep': '59000000',
                'telefone': '84999990000',
            },
        )
        equivalencia = ProdutoFornecedorEquivalencia.objects.create(
            fornecedor=None,
            fornecedor_cnpj_xml='11222333000144',
            fornecedor_razao_social_xml='Fornecedor XML LTDA',
            produto=produto,
            codigo_fornecedor='FORN-001',
            ean_utilizado='7891000000001',
            unidade_compra='CX',
            unidade_estoque='UN',
            fator_conversao=Decimal('12'),
            ultimo_custo=Decimal('2.5000'),
            data_ultima_compra=entrada.data_emissao_nf,
        )

        path = reverse('compras:entrada-fornecedor-pendente', args=[entrada.pk])
        request = self.request('post', path, {'acao': 'criar_xml'})
        response = EntradaNFFornecedorPendenteView.as_view()(request, pk=entrada.pk)

        entrada.refresh_from_db()
        equivalencia.refresh_from_db()
        fornecedor = Fornecedor.objects.get(cpf_cnpj='11222333000144')
        self.assertEqual(response.status_code, 302)
        self.assertFalse(entrada.fornecedor_pendente)
        self.assertEqual(entrada.fornecedor, fornecedor)
        self.assertEqual(fornecedor.razao_social, 'Fornecedor XML LTDA')
        self.assertTrue(FornecedorFilial.objects.filter(fornecedor=fornecedor, filial=self.filial).exists())
        self.assertEqual(equivalencia.fornecedor, fornecedor)
