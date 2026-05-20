"""Views de Entrada de Mercadoria."""
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.dateparse import parse_date
from django.utils import timezone
from django.views import View

from apps.cadastros.models import Fornecedor
from apps.compras.forms import (
    AdicionarItemEntradaForm, ConsultarChaveForm, EntradaNFForm, EntradaNFParcelaForm,
    ImportarXMLForm,
)
from apps.compras.models import EntradaNF, EntradaNFParcela
from apps.compras.services.compra_service import CompraService
from apps.compras.services.entrada_financeiro_service import (
    gerar_contas_pagar_da_entrada, validar_geracao_contas_pagar,
)
from apps.compras.services.entrada_produto_service import (
    criar_produto_e_vincular_item, reprocessar_vinculos_automaticos,
    sugerir_produtos_para_item, vincular_item_a_produto,
)
from apps.compras.services.entrada_xml_service import (
    atualizar_equivalencias_fornecedor_xml, criar_fornecedor_por_emitente_xml,
    get_fornecedor_padrao, importar_xml_para_entrada, localizar_fornecedor,
)
from apps.core.services.exceptions import DomainError
from apps.core.services.permissions import PermissaoRequiredMixin
from apps.produtos.models import Produto


STATUS_KPI = {
    'rascunho': [EntradaNF.Status.RASCUNHO],
    'aguardando': [
        EntradaNF.Status.AGUARDANDO_VINCULOS,
        EntradaNF.Status.AGUARDANDO_CONFERENCIA,
    ],
    'diferencas': [EntradaNF.Status.COM_DIFERENCAS],
    'efetivadas': [EntradaNF.Status.EFETIVADA],
}


def _decimal_localizado(valor, padrao=Decimal('1')) -> Decimal:
    if valor in (None, ''):
        return padrao
    texto = str(valor).strip().replace(' ', '')
    if ',' in texto:
        texto = texto.replace('.', '').replace(',', '.')
    return Decimal(texto)


def _entrada_aberta(entrada):
    return entrada.status in {
        EntradaNF.Status.RASCUNHO,
        EntradaNF.Status.AGUARDANDO_VINCULOS,
        EntradaNF.Status.AGUARDANDO_CONFERENCIA,
        EntradaNF.Status.COM_DIFERENCAS,
        EntradaNF.Status.CONFERIDA,
    }


def _atualizar_equivalencias_fornecedor(entrada):
    return atualizar_equivalencias_fornecedor_xml(
        entrada.filial,
        entrada.fornecedor,
        entrada.emitente_cnpj_xml,
    )


def _criar_fornecedor_do_xml(entrada) -> Fornecedor:
    return criar_fornecedor_por_emitente_xml(
        entrada.filial,
        {
            'documento': entrada.emitente_cnpj_xml,
            'razao_social': entrada.emitente_razao_social_xml,
            'nome_fantasia': entrada.emitente_nome_fantasia_xml,
            'ie': entrada.emitente_ie_xml,
            'endereco': entrada.emitente_endereco_xml,
            'municipio': entrada.emitente_municipio_xml,
            'uf': entrada.emitente_uf_xml,
            'cep': entrada.emitente_cep_xml,
            'telefone': entrada.emitente_telefone_xml,
        },
        exigir_dados=True,
    )


def _atualizar_diferenca_item(item):
    return CompraService.atualizar_diferenca_item(item)


def _avaliar_diferenca_item_para_tela(item):
    tipo, descricao, bloqueante = CompraService.avaliar_diferenca_item(item)
    item.diferenca_tipo = tipo
    item.diferenca_descricao = descricao
    item.diferenca_bloqueante = bloqueante
    return item


class EntradaNFListView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    template_name = 'compras/entrada/list.html'

    def get(self, request):
        base_qs = EntradaNF.objects.for_filial(request.filial_ativa).select_related(
            'fornecedor', 'pedido_compra', 'usuario',
        )
        qs = base_qs
        busca = request.GET.get('q', '').strip()
        status = request.GET.get('status', '')
        origem = request.GET.get('origem', '')
        if busca:
            qs = qs.filter(
                Q(numero_nf__icontains=busca)
                | Q(chave_acesso_nf__icontains=busca)
                | Q(fornecedor__razao_social__icontains=busca)
                | Q(emitente_razao_social_xml__icontains=busca)
                | Q(emitente_cnpj_xml__icontains=busca)
            )
        if status:
            qs = qs.filter(status=status)
        if origem:
            qs = qs.filter(origem_entrada=origem)

        agregados = base_qs.values('status').annotate(total=Count('id'))
        totais_status = {item['status']: item['total'] for item in agregados}
        kpis = {
            chave: sum(totais_status.get(status_item, 0) for status_item in status_list)
            for chave, status_list in STATUS_KPI.items()
        }

        page_obj = Paginator(qs.order_by('-data_entrada'), 25).get_page(request.GET.get('page'))
        return render(request, self.template_name, {
            'page_obj': page_obj,
            'entradas': page_obj.object_list,
            'busca': busca,
            'status': status,
            'origem': origem,
            'status_choices': EntradaNF.Status.choices,
            'origem_choices': EntradaNF.OrigemEntrada.choices,
            'kpis': kpis,
        })


class EntradaNFLocalizarNotaView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    template_name = 'compras/entrada/localizar_nota.html'

    def get(self, request):
        return render(request, self.template_name)


class EntradaNFImportarXMLView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'criar'
    template_name = 'compras/entrada/importar_xml.html'

    def get(self, request):
        return render(request, self.template_name, {'form': ImportarXMLForm()})

    def post(self, request):
        form = ImportarXMLForm(request.POST, request.FILES)
        if form.is_valid():
            arquivo = form.cleaned_data['arquivo_xml']
            raw = arquivo.read()
            try:
                xml_texto = raw.decode('utf-8')
            except UnicodeDecodeError:
                xml_texto = raw.decode('latin1')
            try:
                entrada = importar_xml_para_entrada(
                    xml_texto=xml_texto,
                    filial=request.filial_ativa,
                    usuario=request.user,
                    nome_arquivo=arquivo.name,
                )
                messages.success(request, f'XML importado. NF {entrada.numero_nf} pronta para conferencia.')
                return redirect('compras:entrada-conferencia', pk=entrada.pk)
            except DomainError as exc:
                messages.error(request, str(exc))
        return render(request, self.template_name, {'form': form})


class EntradaNFConsultarChaveView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'criar'
    template_name = 'compras/entrada/consultar_chave.html'

    def get(self, request):
        return render(request, self.template_name, {'form': ConsultarChaveForm()})

    def post(self, request):
        form = ConsultarChaveForm(request.POST)
        if form.is_valid():
            chave = form.cleaned_data['chave_acesso']
            if EntradaNF.objects.for_filial(request.filial_ativa).filter(chave_acesso_nf=chave).exists():
                messages.error(request, 'Esta chave de acesso ja existe nesta filial.')
                return render(request, self.template_name, {'form': form})
            cnpj_emitente = chave[6:20]
            fornecedor, fornecedor_pendente = localizar_fornecedor(request.filial_ativa, cnpj_emitente)
            entrada = CompraService.criar_entrada_nf(
                filial=request.filial_ativa,
                usuario=request.user,
                fornecedor=fornecedor,
                numero_nf=chave[25:34].lstrip('0') or chave[25:34],
                serie_nf=chave[22:25].lstrip('0') or '1',
                data_emissao_nf=timezone.localdate(),
                chave_acesso_nf=chave,
                origem_entrada=EntradaNF.OrigemEntrada.CHAVE,
                fornecedor_pendente=fornecedor_pendente,
                dados_emitente_xml={'documento': cnpj_emitente},
                observacao='Criada pela chave de acesso. Consulta DF-e real ainda pendente.',
            )
            messages.warning(
                request,
                'Chave registrada. Como a consulta SEFAZ real ainda esta em preparacao, confira ou preencha os itens manualmente.',
            )
            return redirect('compras:entrada-detail', pk=entrada.pk)
        return render(request, self.template_name, {'form': form})


class EntradaNFCreateView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'criar'
    template_name = 'compras/entrada/criar.html'

    def get(self, request):
        initial = {}
        if request.GET.get('chave'):
            initial['chave_acesso_nf'] = request.GET['chave']
        return render(request, self.template_name, {
            'form': EntradaNFForm(initial=initial, filial=request.filial_ativa),
            'title': 'Entrada manual',
            'cancel_url': reverse_lazy('compras:entrada-list'),
        })

    def post(self, request):
        form = EntradaNFForm(request.POST, filial=request.filial_ativa)
        if form.is_valid():
            try:
                fornecedor = form.cleaned_data.get('fornecedor')
                fornecedor_pendente = False
                if not fornecedor:
                    fornecedor = get_fornecedor_padrao(request.filial_ativa)
                    fornecedor_pendente = True
                entrada = CompraService.criar_entrada_nf(
                    filial=request.filial_ativa,
                    usuario=request.user,
                    fornecedor=fornecedor,
                    numero_nf=form.cleaned_data['numero_nf'],
                    serie_nf=form.cleaned_data.get('serie_nf') or '1',
                    data_emissao_nf=form.cleaned_data['data_emissao_nf'],
                    chave_acesso_nf=form.cleaned_data.get('chave_acesso_nf', ''),
                    pedido_compra=form.cleaned_data.get('pedido_compra'),
                    observacao=form.cleaned_data.get('observacao', ''),
                    origem_entrada=EntradaNF.OrigemEntrada.MANUAL,
                    fornecedor_pendente=fornecedor_pendente,
                )
                for campo in ('tipo', 'valor_frete', 'valor_seguro', 'valor_outras_despesas'):
                    setattr(entrada, campo, form.cleaned_data.get(campo) or 0)
                entrada.save()
                messages.success(request, f'Entrada NF {entrada.numero_nf} criada. Adicione os itens.')
                return redirect('compras:entrada-detail', pk=entrada.pk)
            except DomainError as e:
                messages.error(request, str(e))
        return render(request, self.template_name, {
            'form': form,
            'title': 'Entrada manual',
            'cancel_url': reverse_lazy('compras:entrada-list'),
        })


class EntradaNFDetailView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    template_name = 'compras/entrada/detail.html'

    def get_entrada(self, request, pk):
        return get_object_or_404(
            EntradaNF.objects.for_filial(request.filial_ativa)
            .select_related('fornecedor', 'pedido_compra', 'usuario', 'usuario_efetivacao'),
            pk=pk,
        )

    def get(self, request, pk):
        entrada = self.get_entrada(request, pk)
        itens = entrada.itens.select_related('produto', 'produto__unidade_medida', 'lote_gerado').all()
        return render(request, self.template_name, {
            'entrada': entrada,
            'itens': itens,
            'adicionar_item_form': (
                AdicionarItemEntradaForm(filial=request.filial_ativa)
                if _entrada_aberta(entrada)
                else None
            ),
        })


class EntradaNFConferenciaView(EntradaNFDetailView):
    template_name = 'compras/entrada/conferencia.html'

    def get(self, request, pk):
        entrada = self.get_entrada(request, pk)
        itens = entrada.itens.select_related('produto', 'produto__unidade_medida').all()
        sugestoes_em_lote = []
        for item in itens:
            item.sugestoes_produto = (
                sugerir_produtos_para_item(item, request.filial_ativa)
                if not item.produto_id
                else []
            )
            item.sugestao_principal = item.sugestoes_produto[0] if item.sugestoes_produto else None
            if item.sugestao_principal:
                sugestoes_em_lote.append(item)
        produtos = Produto.objects.for_filial(request.filial_ativa).filter(ativo=True).order_by('descricao')
        return render(request, self.template_name, {
            'entrada': entrada,
            'itens': itens,
            'produtos': produtos,
            'sugestoes_em_lote': sugestoes_em_lote,
        })


class EntradaNFVincularItemView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'editar'

    def post(self, request, pk, item_id):
        entrada = get_object_or_404(EntradaNF.objects.for_filial(request.filial_ativa), pk=pk)
        item = get_object_or_404(entrada.itens.all(), pk=item_id)
        produto = get_object_or_404(
            Produto.objects.for_filial(request.filial_ativa).filter(ativo=True),
            pk=request.POST.get('produto'),
        )
        fator = _decimal_localizado(request.POST.get('fator_conversao'), item.fator_conversao or Decimal('1'))
        unidade_estoque = request.POST.get('unidade_estoque') or produto.unidade_medida.sigla
        validade = parse_date(request.POST.get('data_validade') or '')
        vincular_item_a_produto(
            entrada=entrada,
            item=item,
            produto=produto,
            fator_conversao=fator,
            unidade_estoque=unidade_estoque,
            numero_lote=request.POST.get('numero_lote', item.numero_lote),
            data_validade=validade,
        )
        CompraService._atualizar_status_conferencia(entrada)
        messages.success(request, 'Produto vinculado e equivalencia salva para proximas entradas.')
        return redirect('compras:entrada-conferencia', pk=pk)


class EntradaNFVincularSugestoesView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'editar'

    def post(self, request, pk):
        entrada = get_object_or_404(EntradaNF.objects.for_filial(request.filial_ativa), pk=pk)
        if not _entrada_aberta(entrada):
            messages.error(request, 'Entrada fechada nao permite alterar vinculos.')
            return redirect('compras:entrada-conferencia', pk=entrada.pk)

        item_ids = request.POST.getlist('item')
        if not item_ids:
            messages.warning(request, 'Selecione ao menos uma sugestao para confirmar.')
            return redirect('compras:entrada-conferencia', pk=entrada.pk)

        vinculados = 0
        ignorados = 0
        with transaction.atomic():
            itens = (
                entrada.itens
                .filter(pk__in=item_ids, produto__isnull=True)
                .select_related('produto')
            )
            for item in itens:
                produto_id = request.POST.get(f'produto_{item.pk}')
                sugestoes = sugerir_produtos_para_item(item, request.filial_ativa)
                sugestao = next(
                    (
                        item_sugestao
                        for item_sugestao in sugestoes
                        if str(item_sugestao.produto.pk) == str(produto_id)
                    ),
                    None,
                )
                if not sugestao:
                    ignorados += 1
                    continue

                try:
                    fator = _decimal_localizado(
                        request.POST.get(f'fator_conversao_{item.pk}'),
                        item.fator_conversao or Decimal('1'),
                    )
                except (InvalidOperation, ValueError):
                    ignorados += 1
                    continue

                if fator <= 0:
                    ignorados += 1
                    continue

                unidade_estoque = (
                    request.POST.get(f'unidade_estoque_{item.pk}')
                    or sugestao.produto.unidade_medida.sigla
                )
                validade = (
                    parse_date(request.POST.get(f'data_validade_{item.pk}') or '')
                    or item.data_validade
                )
                vincular_item_a_produto(
                    entrada=entrada,
                    item=item,
                    produto=sugestao.produto,
                    fator_conversao=fator,
                    unidade_estoque=unidade_estoque.strip()[:6],
                    numero_lote=request.POST.get(f'numero_lote_{item.pk}', item.numero_lote),
                    data_validade=validade,
                )
                vinculados += 1
            CompraService._atualizar_status_conferencia(entrada)

        if vinculados:
            messages.success(request, f'{vinculados} sugestao(oes) vinculada(s).')
        if ignorados:
            messages.warning(request, f'{ignorados} sugestao(oes) foram ignorada(s) por seguranca.')
        if not vinculados and not ignorados:
            messages.warning(request, 'Nenhum item pendente foi encontrado para confirmar.')
        return redirect('compras:entrada-conferencia', pk=entrada.pk)


class EntradaNFReprocessarVinculosView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'editar'

    def post(self, request, pk):
        entrada = get_object_or_404(
            EntradaNF.objects.for_filial(request.filial_ativa).select_related('fornecedor'),
            pk=pk,
        )
        if not _entrada_aberta(entrada):
            messages.error(request, 'Entrada fechada nao permite reprocessar vinculos.')
            return redirect('compras:entrada-conferencia', pk=entrada.pk)

        resultado = reprocessar_vinculos_automaticos(entrada)
        vinculados = resultado['vinculados']
        pendentes = resultado['pendentes']
        if vinculados:
            messages.success(
                request,
                f'{vinculados} item(ns) vinculado(s) automaticamente por EAN ou equivalencia segura.',
            )
        elif pendentes:
            messages.warning(
                request,
                'Nenhum novo vinculo seguro foi encontrado. Revise as sugestoes por nome ou cadastre pelo XML.',
            )
        else:
            messages.info(request, 'Nao havia itens pendentes para reprocessar.')
        return redirect('compras:entrada-conferencia', pk=entrada.pk)


class EntradaNFCriarProdutoItemView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'editar'

    def post(self, request, pk, item_id):
        entrada = get_object_or_404(EntradaNF.objects.for_filial(request.filial_ativa), pk=pk)
        item = get_object_or_404(entrada.itens.all(), pk=item_id)
        try:
            produto = criar_produto_e_vincular_item(entrada, item)
            CompraService._atualizar_status_conferencia(entrada)
            messages.success(request, f'Produto "{produto.descricao}" cadastrado e vinculado ao item.')
        except Exception as exc:
            messages.error(request, f'Nao foi possivel cadastrar o produto: {exc}')
        return redirect('compras:entrada-conferencia', pk=pk)


class EntradaNFFornecedorPendenteView(EntradaNFDetailView):
    template_name = 'compras/entrada/fornecedor_pendente.html'

    def get(self, request, pk):
        entrada = self.get_entrada(request, pk)
        fornecedores = Fornecedor.objects.for_filial(request.filial_ativa).filter(ativo=True).order_by('razao_social')
        return render(request, self.template_name, {
            'entrada': entrada,
            'fornecedores': fornecedores,
        })

    def post(self, request, pk):
        entrada = self.get_entrada(request, pk)
        acao = request.POST.get('acao', 'vincular')
        if acao == 'criar_xml':
            try:
                with transaction.atomic():
                    fornecedor = _criar_fornecedor_do_xml(entrada)
                    entrada.fornecedor = fornecedor
                    entrada.fornecedor_pendente = False
                    entrada.save(update_fields=['fornecedor', 'fornecedor_pendente', 'updated_at'])
                    atualizadas = _atualizar_equivalencias_fornecedor(entrada)
                mensagem = 'Fornecedor criado a partir do XML e vinculado a entrada.'
                if atualizadas:
                    mensagem += f' {atualizadas} equivalencia(s) pendente(s) foram atualizadas.'
                messages.success(request, mensagem)
            except DomainError as exc:
                messages.error(request, str(exc))
            return redirect('compras:entrada-detail', pk=entrada.pk)

        fornecedor_id = request.POST.get('fornecedor')
        if fornecedor_id:
            fornecedor = get_object_or_404(
                Fornecedor.objects.for_filial(request.filial_ativa).filter(ativo=True),
                pk=fornecedor_id,
            )
            with transaction.atomic():
                entrada.fornecedor = fornecedor
                entrada.fornecedor_pendente = False
                entrada.save(update_fields=['fornecedor', 'fornecedor_pendente', 'updated_at'])
                atualizadas = _atualizar_equivalencias_fornecedor(entrada)
            mensagem = 'Fornecedor vinculado a entrada.'
            if atualizadas:
                mensagem += f' {atualizadas} equivalencia(s) pendente(s) foram atualizadas.'
            messages.success(request, mensagem)
        return redirect('compras:entrada-detail', pk=entrada.pk)


class EntradaNFDiferencasView(EntradaNFDetailView):
    template_name = 'compras/entrada/diferencas.html'

    def get_context(self, entrada):
        todos_itens = list(
            entrada.itens
            .select_related('produto')
            .order_by('numero_item', 'pk')
        )
        itens = []
        for item in todos_itens:
            _avaliar_diferenca_item_para_tela(item)
            if item.diferenca_tipo or item.diferenca_bloqueante or not item.produto_id:
                itens.append(item)
        return {
            'entrada': entrada,
            'itens': itens,
            'total_itens': len(todos_itens),
            'total_diferencas': len(itens),
            'total_bloqueantes': sum(1 for item in itens if item.diferenca_bloqueante or not item.produto_id),
            'total_alertas': sum(1 for item in itens if item.diferenca_tipo and not item.diferenca_bloqueante),
            'pode_editar_diferencas': _entrada_aberta(entrada),
        }

    def get(self, request, pk):
        entrada = self.get_entrada(request, pk)
        return render(request, self.template_name, self.get_context(entrada))

    def post(self, request, pk):
        entrada = self.get_entrada(request, pk)
        if not _entrada_aberta(entrada):
            messages.error(request, 'Entrada fechada nao permite alterar diferencas.')
            return redirect('compras:entrada-diferencas', pk=entrada.pk)

        item = get_object_or_404(
            entrada.itens.select_related('produto'),
            pk=request.POST.get('item_id'),
        )
        try:
            item.quantidade_recebida = _decimal_localizado(
                request.POST.get('quantidade_recebida'),
                item.quantidade_recebida or item.quantidade_estoque,
            )
        except (InvalidOperation, ValueError):
            messages.error(request, 'Quantidade recebida invalida.')
            return redirect('compras:entrada-diferencas', pk=entrada.pk)

        item.numero_lote = (request.POST.get('numero_lote') or '').strip()
        item.data_validade = parse_date(request.POST.get('data_validade') or '')
        item.justificativa_diferenca = (request.POST.get('justificativa_diferenca') or '').strip()
        _atualizar_diferenca_item(item)
        CompraService._atualizar_status_conferencia(entrada)

        if item.diferenca_bloqueante:
            messages.warning(request, 'Diferenca salva, mas ainda bloqueia a finalizacao.')
        elif item.diferenca_tipo:
            messages.success(request, 'Diferenca justificada. A entrada segue como alerta operacional.')
        else:
            messages.success(request, 'Diferenca resolvida.')
        return redirect('compras:entrada-diferencas', pk=entrada.pk)



class EntradaNFFinanceiroView(EntradaNFDetailView):
    template_name = 'compras/entrada/financeiro.html'

    def get_context(self, entrada, usuario=None):
        parcelas = list(entrada.parcelas_financeiras.all())
        total_parcelas = sum((parcela.valor for parcela in parcelas), Decimal('0'))
        diferenca_total = entrada.valor_total - total_parcelas
        pendentes_geracao = [
            parcela for parcela in parcelas
            if parcela.status == EntradaNFParcela.Status.PENDENTE and not parcela.conta_pagar_id
        ]
        bloqueios_geracao = validar_geracao_contas_pagar(entrada)
        pode_criar_contas = (
            usuario.tem_permissao('financeiro', 'criar')
            if usuario and usuario.is_authenticated
            else False
        )
        if not pode_criar_contas:
            bloqueios_geracao.append('Usuario sem permissao para criar contas a pagar.')
        return {
            'entrada': entrada,
            'parcelas': parcelas,
            'form': EntradaNFParcelaForm(),
            'total_parcelas': total_parcelas,
            'diferenca_total': diferenca_total,
            'pode_editar_financeiro': _entrada_aberta(entrada),
            'parcelas_pendentes_geracao': pendentes_geracao,
            'contas_geradas_count': sum(1 for parcela in parcelas if parcela.conta_pagar_id),
            'bloqueios_geracao': bloqueios_geracao,
            'pode_gerar_contas': bool(pendentes_geracao) and not bloqueios_geracao,
        }

    def get(self, request, pk):
        entrada = self.get_entrada(request, pk)
        return render(request, self.template_name, self.get_context(entrada, request.user))

    def post(self, request, pk):
        entrada = self.get_entrada(request, pk)
        if not _entrada_aberta(entrada):
            messages.error(request, 'Entrada fechada nao permite alterar parcelas.')
            return redirect('compras:entrada-financeiro', pk=entrada.pk)

        form = EntradaNFParcelaForm(request.POST)
        if form.is_valid():
            parcela = form.save(commit=False)
            parcela.entrada = entrada
            parcela.origem = EntradaNFParcela.Origem.MANUAL
            parcela.status = EntradaNFParcela.Status.PENDENTE
            parcela.fornecedor_pendente = entrada.fornecedor_pendente
            parcela.emitente_documento_xml = entrada.emitente_cnpj_xml
            parcela.emitente_nome_xml = entrada.emitente_razao_social_xml
            if not parcela.numero:
                proximo = entrada.parcelas_financeiras.count() + 1
                parcela.numero = str(proximo).zfill(3)
            parcela.save()
            messages.success(request, 'Parcela adicionada para revisao financeira.')
            return redirect('compras:entrada-financeiro', pk=entrada.pk)

        contexto = self.get_context(entrada, request.user)
        contexto['form'] = form
        messages.error(request, 'Verifique os dados da parcela.')
        return render(request, self.template_name, contexto)


class EntradaNFGerarContasPagarView(PermissaoRequiredMixin, View):
    permissao_modulo = 'financeiro'
    permissao_acao = 'criar'

    def post(self, request, pk):
        entrada = get_object_or_404(
            EntradaNF.objects.for_filial(request.filial_ativa),
            pk=pk,
        )
        try:
            resultado = gerar_contas_pagar_da_entrada(entrada, request.user)
            if resultado.criadas:
                messages.success(request, f'{resultado.criadas} conta(s) a pagar gerada(s).')
            if resultado.existentes:
                messages.info(request, f'{resultado.existentes} conta(s) ja existiam e foram vinculada(s).')
            if resultado.ignoradas:
                messages.warning(request, f'{resultado.ignoradas} parcela(s) ja estavam geradas.')
        except DomainError as exc:
            messages.error(request, str(exc))
        return redirect('compras:entrada-financeiro', pk=entrada.pk)


class EntradaNFFinalizacaoView(EntradaNFDetailView):
    template_name = 'compras/entrada/finalizacao.html'

    def get(self, request, pk):
        entrada = self.get_entrada(request, pk)
        itens = list(
            entrada.itens
            .select_related('produto', 'produto__unidade_medida', 'lote_gerado')
            .order_by('numero_item', 'pk')
        )
        for item in itens:
            _avaliar_diferenca_item_para_tela(item)
        hoje = timezone.localdate()
        bloqueios = []
        avisos = []
        if not itens:
            bloqueios.append('Entrada sem itens.')
        sem_produto = [item for item in itens if not item.produto_id]
        if sem_produto:
            bloqueios.append(f'{len(sem_produto)} item(ns) sem produto interno vinculado.')
        diferencas_bloqueantes = [item for item in itens if item.diferenca_bloqueante]
        if diferencas_bloqueantes:
            bloqueios.append(f'{len(diferencas_bloqueantes)} diferenca(s) bloqueante(s) pendente(s).')
        lotes_pendentes = [
            item for item in itens
            if item.produto_id and item.produto.controla_lote and not item.numero_lote
        ]
        if lotes_pendentes:
            bloqueios.append(f'{len(lotes_pendentes)} item(ns) com lote obrigatorio pendente.')
        validades_pendentes = [
            item for item in itens
            if item.produto_id and item.produto.controla_validade and not item.data_validade
        ]
        if validades_pendentes:
            bloqueios.append(f'{len(validades_pendentes)} item(ns) com validade obrigatoria pendente.')
        validades_vencidas = [
            item for item in itens
            if item.produto_id and item.produto.controla_validade
            and item.data_validade and item.data_validade < hoje
        ]
        if validades_vencidas:
            bloqueios.append(f'{len(validades_vencidas)} item(ns) com validade vencida.')
        validades_proximas = [
            item for item in itens
            if item.produto_id and item.produto.controla_validade
            and item.data_validade and item.data_validade >= hoje
            and item.produto.dias_aviso_vencimento is not None
            and (item.data_validade - hoje).days <= item.produto.dias_aviso_vencimento
        ]
        if validades_proximas:
            avisos.append(f'{len(validades_proximas)} item(ns) com validade proxima do vencimento.')
        if entrada.fornecedor_pendente:
            avisos.append('Fornecedor ainda pendente. Pode continuar, mas fica marcado para revisao.')
        if entrada.destinatario_documento_diferente:
            avisos.append('Documento destinatario diferente da filial. E apenas alerta operacional.')
        total_parcelas = sum(
            (parcela.valor for parcela in entrada.parcelas_financeiras.all()),
            Decimal('0'),
        )
        if not total_parcelas:
            avisos.append('Nenhuma parcela financeira informada. Finaliza estoque, mas o contas a pagar fica para revisao manual.')
        elif total_parcelas != entrada.valor_total:
            avisos.append('Total das parcelas financeiras diferente do total da nota. Revise antes de gerar contas a pagar.')

        return render(request, self.template_name, {
            'entrada': entrada,
            'itens': itens,
            'bloqueios': bloqueios,
            'avisos': avisos,
            'total_parcelas': total_parcelas,
            'pode_finalizar_visualmente': entrada.pode_efetivar and not bloqueios,
        })


class AdicionarItemEntradaView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'editar'

    def post(self, request, pk):
        entrada = get_object_or_404(EntradaNF.objects.for_filial(request.filial_ativa), pk=pk)
        form = AdicionarItemEntradaForm(request.POST, filial=request.filial_ativa)
        if form.is_valid():
            try:
                CompraService.adicionar_item_entrada(
                    entrada=entrada,
                    produto=form.cleaned_data['produto'],
                    quantidade=form.cleaned_data['quantidade'],
                    valor_unitario=form.cleaned_data['valor_unitario'],
                    valor_ipi=form.cleaned_data.get('valor_ipi') or 0,
                    valor_icms=form.cleaned_data.get('valor_icms') or 0,
                    numero_lote=form.cleaned_data.get('numero_lote', ''),
                    data_fabricacao=form.cleaned_data.get('data_fabricacao'),
                    data_validade=form.cleaned_data.get('data_validade'),
                    ean_xml=form.cleaned_data.get('ean_xml', ''),
                    codigo_produto_fornecedor=form.cleaned_data.get('codigo_produto_fornecedor', ''),
                    descricao_xml=form.cleaned_data.get('descricao_xml', ''),
                    unidade_xml=form.cleaned_data.get('unidade_xml', ''),
                    fator_conversao=form.cleaned_data.get('fator_conversao') or Decimal('1'),
                    quantidade_recebida=form.cleaned_data.get('quantidade_recebida'),
                )
                messages.success(request, 'Item adicionado.')
            except DomainError as e:
                messages.error(request, str(e))
        else:
            for erro in form.non_field_errors():
                messages.error(request, erro)
            messages.error(request, 'Verifique os dados do item.')
        return redirect('compras:entrada-detail', pk=pk)


class EfetivarEntradaView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'aprovar'

    def post(self, request, pk):
        entrada = get_object_or_404(EntradaNF.objects.for_filial(request.filial_ativa), pk=pk)
        try:
            CompraService.efetivar_entrada(entrada, request.user)
            messages.success(request, f'Entrada {entrada.numero_nf} finalizada. Estoque atualizado.')
        except DomainError as e:
            messages.error(request, str(e))
        return redirect('compras:entrada-detail', pk=pk)


class CancelarEntradaView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'cancelar'

    def post(self, request, pk):
        entrada = get_object_or_404(EntradaNF.objects.for_filial(request.filial_ativa), pk=pk)
        motivo = request.POST.get('motivo', '').strip() or 'Cancelamento manual'
        try:
            CompraService.cancelar_entrada(entrada, request.user, motivo)
            messages.success(request, 'Entrada cancelada.')
        except DomainError as e:
            messages.error(request, str(e))
        return redirect('compras:entrada-detail', pk=pk)
