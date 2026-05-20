"""Views de consulta e operacoes de estoque."""
import csv
import json
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import (
    Case, Count, DecimalField, ExpressionWrapper, F, OuterRef, Q, Subquery, Sum, Value,
    When,
)
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.dateparse import parse_date
from django.views import View

from apps.core.services.exceptions import DomainError
from apps.core.services.permissions import PermissaoRequiredMixin
from apps.estoque.forms import AjusteEstoqueForm, MovimentacaoManualForm, TransferenciaForm
from apps.estoque.models import Estoque, MovimentacaoEstoque
from apps.estoque.services.movimentacao_service import MovimentacaoService
from apps.estoque.views.permissoes import (
    bloquear_exportacao_sem_permissao,
    permissoes_estoque,
)
from apps.cadastros.models import Fornecedor
from apps.produtos.models import CategoriaProduto, MarcaProduto, Produto


def produtos_estoque_queryset(filial):
    estoque_qs = Estoque.objects.filter(
        produto=OuterRef('pk'),
        filial=filial,
    )
    quantidade_field = DecimalField(max_digits=12, decimal_places=3)
    custo_field = DecimalField(max_digits=14, decimal_places=4)
    reposicao_field = DecimalField(max_digits=12, decimal_places=3)
    return Produto.objects.for_filial(filial).filter(
        ativo=True,
    ).select_related(
        'unidade_medida',
        'categoria',
        'fornecedor',
    ).annotate(
        estoque_quantidade_atual=Coalesce(
            Subquery(
                estoque_qs.values('quantidade_atual')[:1],
                output_field=quantidade_field,
            ),
            Value(Decimal('0'), output_field=quantidade_field),
            output_field=quantidade_field,
        ),
        estoque_quantidade_reservada=Coalesce(
            Subquery(
                estoque_qs.values('quantidade_reservada')[:1],
                output_field=quantidade_field,
            ),
            Value(Decimal('0'), output_field=quantidade_field),
            output_field=quantidade_field,
        ),
        estoque_quantidade_disponivel=Coalesce(
            Subquery(
                estoque_qs.values('quantidade_disponivel')[:1],
                output_field=quantidade_field,
            ),
            Value(Decimal('0'), output_field=quantidade_field),
            output_field=quantidade_field,
        ),
        estoque_custo_medio=Coalesce(
            Subquery(
                estoque_qs.values('custo_medio')[:1],
                output_field=custo_field,
            ),
            Value(Decimal('0'), output_field=custo_field),
            output_field=custo_field,
        ),
    ).annotate(
        estoque_valor_custo_total=ExpressionWrapper(
            F('estoque_quantidade_atual') * F('estoque_custo_medio'),
            output_field=DecimalField(max_digits=18, decimal_places=4),
        ),
        sugestao_reposicao=Case(
            When(
                ponto_reposicao__gt=0,
                estoque_quantidade_disponivel__lt=F('ponto_reposicao'),
                estoque_maximo__gt=F('estoque_quantidade_disponivel'),
                then=ExpressionWrapper(
                    F('estoque_maximo') - F('estoque_quantidade_disponivel'),
                    output_field=reposicao_field,
                ),
            ),
            When(
                Q(ponto_reposicao__gt=0)
                & Q(ponto_reposicao__gt=F('estoque_quantidade_disponivel')),
                then=ExpressionWrapper(
                    F('ponto_reposicao') - F('estoque_quantidade_disponivel'),
                    output_field=reposicao_field,
                ),
            ),
            When(
                estoque_minimo__gt=0,
                estoque_quantidade_disponivel__lt=F('estoque_minimo'),
                estoque_maximo__gt=F('estoque_quantidade_disponivel'),
                then=ExpressionWrapper(
                    F('estoque_maximo') - F('estoque_quantidade_disponivel'),
                    output_field=reposicao_field,
                ),
            ),
            When(
                Q(estoque_minimo__gt=0)
                & Q(estoque_minimo__gt=F('estoque_quantidade_disponivel')),
                then=ExpressionWrapper(
                    F('estoque_minimo') - F('estoque_quantidade_disponivel'),
                    output_field=reposicao_field,
                ),
            ),
            default=Value(Decimal('0'), output_field=reposicao_field),
            output_field=reposicao_field,
        ),
    )


class EstoqueListView(PermissaoRequiredMixin, View):
    """Lista consolidada de estoque por produto na filial ativa."""

    permissao_modulo = 'estoque'
    template_name = 'estoque/estoque/list.html'

    def get(self, request):
        base_qs = produtos_estoque_queryset(request.filial_ativa)
        qs = base_qs

        busca = request.GET.get('q', '').strip()
        categoria_id = request.GET.get('categoria', '')
        subcategoria_id = request.GET.get('subcategoria', '')
        marca_id = request.GET.get('marca', '')
        fornecedor_id = request.GET.get('fornecedor', '')
        status = request.GET.get('status') or 'todos'
        ordem = request.GET.get('ordem', 'id')

        if busca:
            filtro_busca = (
                Q(codigo__icontains=busca)
                | Q(descricao__icontains=busca)
                | Q(codigo_barras__icontains=busca)
                | Q(ncm__icontains=busca)
            )
            busca_codigo = busca.lstrip('0')
            if busca_codigo.isdigit():
                codigo_int = int(busca_codigo)
                filtro_busca |= Q(pk=codigo_int) | Q(id_externo=f'produto:{codigo_int}')
            qs = qs.filter(filtro_busca)

        if categoria_id:
            categoria = CategoriaProduto.objects.for_filial(request.filial_ativa).filter(
                pk=categoria_id,
                empresa=request.user.empresa,
            ).first()
            subcategoria = CategoriaProduto.objects.for_filial(request.filial_ativa).filter(
                pk=subcategoria_id,
                categoria_pai_id=categoria_id,
                empresa=request.user.empresa,
            ).first() if subcategoria_id else None
            if subcategoria:
                filtro_categoria = (
                    Q(subcategoria_id=subcategoria_id)
                    | Q(categoria_id=subcategoria_id)
                    | Q(categoria_id=subcategoria.categoria_pai_id, subcategoria__isnull=True)
                )
                if subcategoria.id_externo:
                    filtro_categoria |= Q(subcategoria__id_externo=subcategoria.id_externo)
                if subcategoria.categoria_pai and subcategoria.categoria_pai.id_externo:
                    filtro_categoria |= Q(
                        categoria__id_externo=subcategoria.categoria_pai.id_externo,
                        subcategoria__isnull=True,
                    )
                qs = qs.filter(filtro_categoria)
            else:
                filtro_categoria = (
                    Q(categoria_id=categoria_id)
                    | Q(categoria__categoria_pai_id=categoria_id)
                )
                if categoria and categoria.id_externo:
                    filtro_categoria |= (
                        Q(categoria__id_externo=categoria.id_externo)
                        | Q(categoria__categoria_pai__id_externo=categoria.id_externo)
                    )
                qs = qs.filter(filtro_categoria)
        elif subcategoria_id and (
            subcategoria := CategoriaProduto.objects.for_filial(request.filial_ativa).filter(
                pk=subcategoria_id,
                empresa=request.user.empresa,
                categoria_pai__isnull=False,
            ).first()
        ):
            filtro_categoria = (
                Q(subcategoria_id=subcategoria_id)
                | Q(categoria_id=subcategoria_id)
                | Q(categoria_id=subcategoria.categoria_pai_id, subcategoria__isnull=True)
            )
            if subcategoria.id_externo:
                filtro_categoria |= Q(subcategoria__id_externo=subcategoria.id_externo)
            if subcategoria.categoria_pai and subcategoria.categoria_pai.id_externo:
                filtro_categoria |= Q(
                    categoria__id_externo=subcategoria.categoria_pai.id_externo,
                    subcategoria__isnull=True,
                )
            qs = qs.filter(filtro_categoria)

        if marca_id:
            marca = MarcaProduto.objects.for_filial(request.filial_ativa).filter(
                pk=marca_id,
                empresa=request.user.empresa,
            ).first()
            if marca:
                filtro_marca = Q(marca_id=marca_id)
                if marca.id_externo:
                    filtro_marca |= Q(marca__id_externo=marca.id_externo)
                qs = qs.filter(filtro_marca)

        if fornecedor_id:
            fornecedor = Fornecedor.objects.for_filial(request.filial_ativa).filter(
                pk=fornecedor_id,
            ).first()
            if fornecedor:
                filtro_fornecedor = Q(fornecedor_id=fornecedor_id)
                if fornecedor.id_externo:
                    filtro_fornecedor |= Q(fornecedor__id_externo=fornecedor.id_externo)
                if getattr(fornecedor, 'grupo_replicacao', None):
                    filtro_fornecedor |= Q(fornecedor__grupo_replicacao=fornecedor.grupo_replicacao)
                qs = qs.filter(filtro_fornecedor)

        if status == 'critico':
            qs = qs.filter(
                estoque_minimo__gt=0,
                estoque_quantidade_disponivel__lt=F('estoque_minimo'),
            )
        elif status == 'zerado':
            qs = qs.filter(estoque_quantidade_disponivel__lte=0)
        elif status == 'ok':
            qs = qs.filter(estoque_quantidade_disponivel__gt=0).filter(
                Q(estoque_minimo__lte=0)
                | Q(estoque_quantidade_disponivel__gte=F('estoque_minimo'))
            )

        if request.GET.get('export') == 'csv':
            bloqueio = bloquear_exportacao_sem_permissao(request)
            if bloqueio:
                return bloqueio
            return self._exportar_csv(qs.order_by('descricao'))

        valor_expr = ExpressionWrapper(
            F('estoque_quantidade_atual') * F('estoque_custo_medio'),
            output_field=DecimalField(max_digits=18, decimal_places=4),
        )
        resumo = base_qs.aggregate(
            total_itens=Count('id'),
            valor_total=Sum(valor_expr),
        )
        resumo.update({
            'abaixo_minimo': base_qs.filter(
                estoque_minimo__gt=0,
                estoque_quantidade_disponivel__lt=F('estoque_minimo'),
            ).count(),
            'zerados': base_qs.filter(estoque_quantidade_disponivel__lte=0).count(),
        })

        ordenacoes = {
            'id': 'id',
            'id_desc': '-id',
            'referencia': 'codigo',
            'referencia_desc': '-codigo',
            'az': 'descricao',
            'za': '-descricao',
            'atual': 'estoque_quantidade_atual',
            'atual_desc': '-estoque_quantidade_atual',
            'disponivel': 'estoque_quantidade_disponivel',
            'disponivel_desc': '-estoque_quantidade_disponivel',
            'custo': 'estoque_custo_medio',
            'custo_desc': '-estoque_custo_medio',
            'custo_total': 'estoque_valor_custo_total',
            'custo_total_desc': '-estoque_valor_custo_total',
            'preco': 'preco_venda',
            'preco_desc': '-preco_venda',
        }
        qs = qs.order_by(ordenacoes.get(ordem, 'id'))
        page_obj = Paginator(qs, 30).get_page(request.GET.get('page'))
        querydict = request.GET.copy()
        querydict.pop('page', None)
        sort_urls = {}
        for key, value in {
            'id': 'id_desc' if ordem == 'id' else 'id',
            'referencia': 'referencia_desc' if ordem == 'referencia' else 'referencia',
            'nome': 'za' if ordem == 'az' else 'az',
            'atual': 'atual_desc' if ordem == 'atual' else 'atual',
            'disponivel': 'disponivel_desc' if ordem == 'disponivel' else 'disponivel',
            'custo': 'custo_desc' if ordem == 'custo' else 'custo',
            'custo_total': 'custo_total_desc' if ordem == 'custo_total' else 'custo_total',
            'preco': 'preco_desc' if ordem == 'preco' else 'preco',
        }.items():
            params = request.GET.copy()
            params.pop('page', None)
            params['ordem'] = value
            sort_urls[key] = params.urlencode()

        return render(request, self.template_name, {
            'page_obj': page_obj,
            'produtos_estoque': page_obj.object_list,
            'busca': busca,
            'categoria_id': categoria_id,
            'subcategoria_id': subcategoria_id,
            'marca_id': marca_id,
            'fornecedor_id': fornecedor_id,
            'status': status,
            'ordem': ordem,
            'sort_urls': sort_urls,
            'categorias': CategoriaProduto.objects.for_filial(request.filial_ativa).filter(
                empresa=request.user.empresa,
                ativo=True,
                categoria_pai__isnull=True,
            ).order_by('nome'),
            'subcategorias': CategoriaProduto.objects.for_filial(request.filial_ativa).filter(
                empresa=request.user.empresa,
                ativo=True,
                categoria_pai_id=categoria_id,
            ).order_by('nome') if categoria_id else CategoriaProduto.objects.for_filial(request.filial_ativa).filter(
                empresa=request.user.empresa,
                ativo=True,
                categoria_pai__isnull=False,
            ).order_by('categoria_pai__nome', 'nome'),
            'subcategorias_por_categoria_json': json.dumps({
                '': [
                    {'id': item.id, 'nome': item.nome}
                    for item in CategoriaProduto.objects.for_filial(request.filial_ativa).filter(
                        empresa=request.user.empresa,
                        ativo=True,
                        categoria_pai__isnull=False,
                    ).order_by('categoria_pai__nome', 'nome')
                ],
                **{
                    str(categoria_id): [
                        {'id': item.id, 'nome': item.nome}
                        for item in CategoriaProduto.objects.for_filial(request.filial_ativa).filter(
                            empresa=request.user.empresa,
                            ativo=True,
                            categoria_pai_id=categoria_id,
                        ).order_by('nome')
                    ]
                    for categoria_id in CategoriaProduto.objects.for_filial(request.filial_ativa).filter(
                        empresa=request.user.empresa,
                        ativo=True,
                        categoria_pai__isnull=True,
                    ).values_list('id', flat=True)
                },
            }),
            'marcas': MarcaProduto.objects.for_filial(request.filial_ativa).filter(
                empresa=request.user.empresa,
                ativo=True,
            ).order_by('nome'),
            'fornecedores': Fornecedor.objects.for_filial(request.filial_ativa).filter(
                ativo=True,
            ).order_by('nome_fantasia', 'razao_social'),
            'resumo': resumo,
            'permissoes_estoque': permissoes_estoque(request),
            'page_querystring': querydict.urlencode(),
        })

    @staticmethod
    def _exportar_csv(qs):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="estoque.csv"'
        response.write('\ufeff')
        writer = csv.writer(response, delimiter=';')
        writer.writerow([
            'Produto ID',
            'Codigo',
            'Codigo barras',
            'Descricao',
            'Unidade',
            'Atual',
            'Reservado',
            'Disponivel',
            'Minimo',
            'Reposicao sugerida',
            'Preco venda',
            'Custo unitario',
            'Custo total',
        ])
        for produto in qs:
            writer.writerow([
                produto.codigo_replicacao,
                produto.codigo,
                produto.codigo_barras,
                produto.descricao,
                produto.unidade_medida.sigla if produto.unidade_medida_id else '',
                produto.estoque_quantidade_atual,
                produto.estoque_quantidade_reservada,
                produto.estoque_quantidade_disponivel,
                produto.estoque_minimo,
                produto.sugestao_reposicao,
                produto.preco_atual,
                produto.estoque_custo_medio,
                produto.estoque_valor_custo_total,
            ])
        return response


class ReposicaoListView(PermissaoRequiredMixin, View):
    """Plano operacional de reposicao a partir dos pontos de estoque."""

    permissao_modulo = 'estoque'
    template_name = 'estoque/reposicao/list.html'

    def get_queryset(self, filial):
        return produtos_estoque_queryset(filial).filter(
            sugestao_reposicao__gt=0,
        ).order_by('descricao')

    def get(self, request):
        qs = self.get_queryset(request.filial_ativa)
        if request.GET.get('export') == 'csv':
            bloqueio = bloquear_exportacao_sem_permissao(request, 'estoque:reposicao-list')
            if bloqueio:
                return bloqueio
            return self._exportar_csv(qs)

        produtos = list(qs)
        resumo = {
            'total': len(produtos),
            'com_fornecedor': sum(1 for produto in produtos if produto.fornecedor_id),
            'sem_fornecedor': sum(1 for produto in produtos if not produto.fornecedor_id),
            'quantidade_total': sum((produto.sugestao_reposicao for produto in produtos), Decimal('0')),
        }
        return render(request, self.template_name, {
            'produtos': produtos,
            'resumo': resumo,
            'permissoes_estoque': permissoes_estoque(request),
            'pode_gerar_pedido': (
                request.user.tem_permissao('estoque', 'editar')
                and request.user.tem_permissao('compras', 'criar')
            ),
        })

    def post(self, request):
        if not request.user.tem_permissao('estoque', 'editar'):
            messages.error(request, 'Voce nao tem permissao para acionar reposicao.')
            return redirect('estoque:reposicao-list')
        if not request.user.tem_permissao('compras', 'criar'):
            messages.error(request, 'Voce nao tem permissao para criar pedidos de compra.')
            return redirect('estoque:reposicao-list')

        ids = request.POST.getlist('produto')
        if not ids:
            messages.error(request, 'Selecione ao menos um produto para gerar reposicao.')
            return redirect('estoque:reposicao-list')

        produtos = list(
            self.get_queryset(request.filial_ativa)
            .filter(pk__in=ids)
            .select_related('fornecedor')
        )
        try:
            self._aplicar_quantidades_post(request, produtos)
        except DomainError as e:
            messages.error(request, str(e))
            return redirect('estoque:reposicao-list')

        pedidos = self._gerar_pedidos_compra(request, produtos)
        sem_fornecedor = [produto for produto in produtos if not produto.fornecedor_id]

        if pedidos:
            numeros = ', '.join(pedido.numero_pedido for pedido in pedidos)
            messages.success(request, f'Pedidos de compra em rascunho gerados: {numeros}.')
        if sem_fornecedor:
            messages.warning(
                request,
                f'{len(sem_fornecedor)} produto(s) ficaram sem pedido por falta de fornecedor.',
            )
        if not pedidos:
            messages.error(request, 'Nenhum pedido foi gerado. Verifique fornecedores dos produtos.')
            return redirect('estoque:reposicao-list')
        return redirect('compras:pedido-list')

    @classmethod
    def _aplicar_quantidades_post(cls, request, produtos):
        for produto in produtos:
            quantidade = cls._quantidade_reposicao_from_request(request, produto)
            produto.quantidade_reposicao_acao = quantidade

    @classmethod
    def _quantidade_reposicao_from_request(cls, request, produto):
        default = produto.sugestao_reposicao
        mobile = cls._parse_quantidade_reposicao(
            request.POST.get(f'quantidade_mobile_{produto.pk}'),
            default,
            produto,
        )
        desktop = cls._parse_quantidade_reposicao(
            request.POST.get(f'quantidade_desktop_{produto.pk}'),
            default,
            produto,
        )
        if desktop != default:
            return desktop
        if mobile != default:
            return mobile
        return desktop

    @staticmethod
    def _parse_quantidade_reposicao(value, default, produto):
        if value is None or str(value).strip() == '':
            return default
        text = str(value).strip()
        if ',' in text and '.' in text:
            text = text.replace('.', '').replace(',', '.')
        elif ',' in text:
            text = text.replace(',', '.')
        try:
            quantidade = Decimal(text).quantize(Decimal('0.001'))
        except (InvalidOperation, ValueError):
            raise DomainError(f'Quantidade invalida para {produto.descricao}.')
        if quantidade <= 0:
            raise DomainError(f'Quantidade de reposicao deve ser positiva para {produto.descricao}.')
        return quantidade

    @staticmethod
    def _gerar_pedidos_compra(request, produtos):
        from collections import defaultdict

        from apps.compras.services.compra_service import CompraService

        grupos = defaultdict(list)
        for produto in produtos:
            if produto.fornecedor_id:
                grupos[produto.fornecedor].append(produto)

        pedidos = []
        for fornecedor, produtos_fornecedor in grupos.items():
            pedido = CompraService.criar_pedido(
                filial=request.filial_ativa,
                usuario=request.user,
                fornecedor=fornecedor,
                observacao='Gerado pelo plano de reposicao de estoque.',
            )
            for produto in produtos_fornecedor:
                valor_unitario = (
                    produto.preco_custo_medio
                    or produto.preco_custo
                    or produto.estoque_custo_medio
                    or Decimal('0')
                )
                CompraService.adicionar_item(
                    pedido=pedido,
                    produto=produto,
                    quantidade=getattr(produto, 'quantidade_reposicao_acao', produto.sugestao_reposicao),
                    valor_unitario=valor_unitario,
                )
            pedidos.append(pedido)
        return pedidos

    @staticmethod
    def _exportar_csv(qs):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="reposicao_estoque.csv"'
        response.write('\ufeff')
        writer = csv.writer(response, delimiter=';')
        writer.writerow([
            'Produto ID',
            'Codigo',
            'Produto',
            'Fornecedor',
            'Atual',
            'Disponivel',
            'Minimo',
            'Ponto reposicao',
            'Maximo',
            'Reposicao sugerida',
            'Custo base',
        ])
        for produto in qs:
            writer.writerow([
                produto.codigo_replicacao,
                produto.codigo,
                produto.descricao,
                produto.fornecedor.razao_social if produto.fornecedor_id else '',
                produto.estoque_quantidade_atual,
                produto.estoque_quantidade_disponivel,
                produto.estoque_minimo,
                produto.ponto_reposicao,
                produto.estoque_maximo,
                produto.sugestao_reposicao,
                produto.preco_custo_medio or produto.preco_custo or produto.estoque_custo_medio,
            ])
        return response


class MovimentacaoManualView(PermissaoRequiredMixin, View):
    permissao_modulo = 'estoque'
    permissao_acao = 'editar'
    template_name = 'estoque/movimentacao/operacao.html'

    def get(self, request):
        initial = {}
        produto_id = request.GET.get('produto')
        if produto_id:
            initial['produto'] = produto_id
        return render(request, self.template_name, {
            'form': MovimentacaoManualForm(initial=initial, filial=request.filial_ativa),
            'title': 'Nova movimentacao',
            'cancel_url': reverse_lazy('estoque:estoque-list'),
        })

    def post(self, request):
        form = MovimentacaoManualForm(request.POST, filial=request.filial_ativa)
        if form.is_valid():
            try:
                MovimentacaoService.registrar_movimentacao(
                    produto_id=form.cleaned_data['produto'].pk,
                    filial_id=request.filial_ativa.pk,
                    tipo_operacao=form.cleaned_data['tipo_operacao'],
                    quantidade=form.cleaned_data['quantidade'],
                    usuario_id=request.user.pk,
                    lote_id=form.cleaned_data['lote'].pk if form.cleaned_data.get('lote') else None,
                    valor_unitario=form.cleaned_data.get('valor_unitario'),
                    documento_tipo=MovimentacaoEstoque.DocumentoTipo.OUTRAS,
                    documento_numero=form.cleaned_data.get('documento_numero', ''),
                    observacao=form.cleaned_data.get('observacao', ''),
                )
                messages.success(request, 'Movimentacao registrada.')
                return redirect('estoque:movimentacao-list')
            except DomainError as e:
                messages.error(request, str(e))
        return render(request, self.template_name, {
            'form': form,
            'title': 'Nova movimentacao',
            'cancel_url': reverse_lazy('estoque:estoque-list'),
        })


class AjusteEstoqueView(PermissaoRequiredMixin, View):
    permissao_modulo = 'estoque'
    permissao_acao = 'editar'
    template_name = 'estoque/movimentacao/ajuste.html'

    def get(self, request):
        return render(request, self.template_name, {
            'form': AjusteEstoqueForm(filial=request.filial_ativa),
            'title': 'Ajuste manual de estoque',
            'cancel_url': reverse_lazy('estoque:estoque-list'),
        })

    def post(self, request):
        form = AjusteEstoqueForm(request.POST, filial=request.filial_ativa)
        if form.is_valid():
            try:
                MovimentacaoService.ajustar_manual(
                    produto_id=form.cleaned_data['produto'].pk,
                    filial_id=request.filial_ativa.pk,
                    quantidade_nova=form.cleaned_data['quantidade_nova'],
                    usuario_id=request.user.pk,
                    justificativa=form.cleaned_data['justificativa'],
                    lote_id=form.cleaned_data['lote'].pk if form.cleaned_data.get('lote') else None,
                )
                messages.success(request, 'Ajuste aplicado.')
                return redirect('estoque:estoque-list')
            except DomainError as e:
                messages.error(request, str(e))
        return render(request, self.template_name, {
            'form': form,
            'title': 'Ajuste manual de estoque',
            'cancel_url': reverse_lazy('estoque:estoque-list'),
        })


class TransferenciaView(PermissaoRequiredMixin, View):
    permissao_modulo = 'estoque'
    permissao_acao = 'editar'
    template_name = 'estoque/movimentacao/transferencia.html'

    def get(self, request):
        return render(request, self.template_name, {
            'form': TransferenciaForm(
                filial=request.filial_ativa,
                empresa=request.user.empresa,
            ),
            'title': 'Transferencia entre filiais',
            'cancel_url': reverse_lazy('estoque:estoque-list'),
        })

    def post(self, request):
        form = TransferenciaForm(
            request.POST,
            filial=request.filial_ativa,
            empresa=request.user.empresa,
        )
        if form.is_valid():
            try:
                mov_saida, mov_entrada = MovimentacaoService.transferir_entre_filiais(
                    produto_id=form.cleaned_data['produto'].pk,
                    filial_origem_id=request.filial_ativa.pk,
                    filial_destino_id=form.cleaned_data['filial_destino'].pk,
                    quantidade=form.cleaned_data['quantidade'],
                    usuario_id=request.user.pk,
                    lote_id=form.cleaned_data['lote'].pk if form.cleaned_data.get('lote') else None,
                    observacao=form.cleaned_data.get('observacao', ''),
                )
                messages.success(
                    request,
                    f'Transferencia efetuada. Saida #{mov_saida.pk} / Entrada #{mov_entrada.pk}.',
                )
                return redirect('estoque:movimentacao-list')
            except DomainError as e:
                messages.error(request, str(e))
        return render(request, self.template_name, {
            'form': form,
            'title': 'Transferencia entre filiais',
            'cancel_url': reverse_lazy('estoque:estoque-list'),
        })


class MovimentacaoListView(PermissaoRequiredMixin, View):
    permissao_modulo = 'estoque'
    template_name = 'estoque/movimentacao/list.html'

    def get(self, request):
        qs = MovimentacaoEstoque.objects.for_filial(request.filial_ativa).select_related(
            'filial',
            'filial_destino',
            'produto',
            'usuario',
            'lote',
        )

        busca = request.GET.get('q', '').strip()
        tipo = request.GET.get('tipo', '')
        data_inicio = request.GET.get('data_inicio', '').strip()
        data_fim = request.GET.get('data_fim', '').strip()
        produto_id = request.GET.get('produto', '').strip()
        produto_filtrado = None

        if busca:
            filtro_busca = (
                Q(produto__codigo__icontains=busca)
                | Q(produto__descricao__icontains=busca)
                | Q(produto__codigo_barras__icontains=busca)
                | Q(documento_numero__icontains=busca)
                | Q(observacao__icontains=busca)
                | Q(filial_destino__nome_fantasia__icontains=busca)
                | Q(filial_destino__razao_social__icontains=busca)
            )
            busca_codigo = busca.lstrip('0')
            if busca_codigo.isdigit():
                codigo_int = int(busca_codigo)
                filtro_busca |= (
                    Q(pk=codigo_int)
                    | Q(documento_id=codigo_int)
                    | Q(produto__pk=codigo_int)
                    | Q(produto__id_externo=f'produto:{codigo_int}')
                )
            qs = qs.filter(filtro_busca)
        if tipo:
            qs = qs.filter(tipo_operacao=tipo)
        data_inicio_parseada = parse_date(data_inicio) if data_inicio else None
        data_fim_parseada = parse_date(data_fim) if data_fim else None
        if data_inicio_parseada:
            qs = qs.filter(data_movimentacao__date__gte=data_inicio_parseada)
        if data_fim_parseada:
            qs = qs.filter(data_movimentacao__date__lte=data_fim_parseada)
        if produto_id:
            produto_filtrado = Produto.objects.for_filial(request.filial_ativa).filter(
                pk=produto_id,
            ).first()
            if produto_filtrado:
                qs = qs.filter(produto=produto_filtrado)
            else:
                qs = qs.none()

        if request.GET.get('export') == 'csv':
            bloqueio = bloquear_exportacao_sem_permissao(request, 'estoque:movimentacao-list')
            if bloqueio:
                return bloqueio
            return self._exportar_csv(qs.order_by('-data_movimentacao'))

        qs = qs.order_by('-data_movimentacao')
        page_obj = Paginator(qs, 50).get_page(request.GET.get('page'))
        movimentacoes = list(page_obj.object_list)
        ids_relacionados = [
            mov.documento_id
            for mov in movimentacoes
            if (
                mov.documento_tipo == MovimentacaoEstoque.DocumentoTipo.TRANSFERENCIA
                and mov.documento_id
            )
        ]
        relacionados = {
            mov.pk: mov
            for mov in MovimentacaoEstoque.objects.filter(pk__in=ids_relacionados).select_related(
                'filial',
                'filial_destino',
            )
        }
        for mov in movimentacoes:
            mov.movimento_relacionado = relacionados.get(mov.documento_id)

        querydict = request.GET.copy()
        querydict.pop('page', None)

        return render(request, self.template_name, {
            'page_obj': page_obj,
            'movimentacoes': movimentacoes,
            'busca': busca,
            'tipo': tipo,
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'produto_filtrado': produto_filtrado,
            'tipos': MovimentacaoEstoque.TipoOperacao.choices,
            'permissoes_estoque': permissoes_estoque(request),
            'page_querystring': querydict.urlencode(),
        })

    @staticmethod
    def _exportar_csv(qs):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="movimentacoes_estoque.csv"'
        response.write('\ufeff')
        writer = csv.writer(response, delimiter=';')
        writer.writerow([
            'Data',
            'Tipo',
            'Produto ID',
            'Produto',
            'Lote',
            'Quantidade',
            'Anterior',
            'Posterior',
            'Documento tipo',
            'Documento numero',
            'Documento ID',
            'Filial origem',
            'Filial destino',
            'Usuario',
            'Observacao',
        ])
        for mov in qs:
            filial_destino = ''
            if mov.filial_destino_id:
                filial_destino = mov.filial_destino.nome_fantasia or mov.filial_destino.razao_social
            writer.writerow([
                mov.data_movimentacao.strftime('%d/%m/%Y %H:%M') if mov.data_movimentacao else '',
                mov.get_tipo_operacao_display(),
                mov.produto.codigo_replicacao,
                mov.produto.descricao,
                mov.lote.numero_lote if mov.lote_id else '',
                mov.quantidade,
                mov.quantidade_anterior,
                mov.quantidade_posterior,
                mov.get_documento_tipo_display() if mov.documento_tipo else '',
                mov.documento_numero,
                mov.documento_id or '',
                mov.filial.nome_fantasia or mov.filial.razao_social,
                filial_destino,
                mov.usuario.nome if getattr(mov.usuario, 'nome', '') else str(mov.usuario),
                mov.observacao,
            ])
        return response
