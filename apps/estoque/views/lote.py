"""CRUD de lote."""
import csv
from decimal import Decimal

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View

from apps.core.services.exceptions import DomainError
from apps.core.services.permissions import PermissaoRequiredMixin
from apps.estoque.forms import LoteProdutoForm
from apps.estoque.models import LoteProduto, MovimentacaoEstoque
from apps.estoque.services.movimentacao_service import MovimentacaoService
from apps.estoque.views.permissoes import (
    bloquear_exportacao_sem_permissao,
    permissoes_estoque,
)


class LoteListView(PermissaoRequiredMixin, View):
    permissao_modulo = 'estoque'
    template_name = 'estoque/lote/list.html'

    def get(self, request):
        qs = LoteProduto.objects.for_filial(request.filial_ativa).select_related(
            'produto',
            'fornecedor',
        )

        busca = request.GET.get('q', '').strip()
        status = request.GET.get('status', '')
        vencendo = request.GET.get('vencendo', '')

        if busca:
            filtro_busca = (
                Q(numero_lote__icontains=busca)
                | Q(produto__codigo__icontains=busca)
                | Q(produto__codigo_barras__icontains=busca)
                | Q(produto__descricao__icontains=busca)
            )
            busca_codigo = busca.lstrip('0')
            if busca_codigo.isdigit():
                codigo_int = int(busca_codigo)
                filtro_busca |= Q(produto__pk=codigo_int) | Q(produto__id_externo=f'produto:{codigo_int}')
            qs = qs.filter(filtro_busca)
        if status:
            qs = qs.filter(status=status)

        if vencendo:
            from datetime import timedelta
            from django.utils import timezone
            hoje = timezone.now().date()
            dias = int(vencendo)
            qs = qs.filter(
                data_validade__isnull=False,
                data_validade__gte=hoje,
                data_validade__lte=hoje + timedelta(days=dias),
            )

        if request.GET.get('export') == 'csv':
            bloqueio = bloquear_exportacao_sem_permissao(request, 'estoque:lote-list')
            if bloqueio:
                return bloqueio
            return self._exportar_csv(qs.order_by('data_validade', 'numero_lote'))

        qs = qs.order_by('data_validade', 'numero_lote')
        page_obj = Paginator(qs, 30).get_page(request.GET.get('page'))
        querydict = request.GET.copy()
        querydict.pop('page', None)

        return render(request, self.template_name, {
            'page_obj': page_obj,
            'lotes': page_obj.object_list,
            'busca': busca,
            'status': status,
            'vencendo': vencendo,
            'status_choices': LoteProduto.Status.choices,
            'permissoes_estoque': permissoes_estoque(request),
            'page_querystring': querydict.urlencode(),
        })

    @staticmethod
    def _exportar_csv(qs):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="lotes_estoque.csv"'
        response.write('\ufeff')
        writer = csv.writer(response, delimiter=';')
        writer.writerow([
            'Numero lote',
            'Produto ID',
            'Produto',
            'Fornecedor',
            'Fabricacao',
            'Validade',
            'Dias para vencer',
            'Quantidade atual',
            'Custo unitario',
            'Status',
            'Motivo bloqueio',
        ])
        for lote in qs:
            writer.writerow([
                lote.numero_lote,
                lote.produto.codigo_replicacao,
                lote.produto.descricao,
                lote.fornecedor.razao_social if lote.fornecedor_id else '',
                lote.data_fabricacao.strftime('%d/%m/%Y') if lote.data_fabricacao else '',
                lote.data_validade.strftime('%d/%m/%Y') if lote.data_validade else '',
                lote.dias_para_vencer if lote.data_validade else '',
                lote.quantidade_atual,
                lote.custo_unitario,
                lote.get_status_display(),
                lote.motivo_bloqueio,
            ])
        return response


class LoteCreateView(PermissaoRequiredMixin, View):
    permissao_modulo = 'estoque'
    permissao_acao = 'criar'
    template_name = 'estoque/lote/form.html'

    def get(self, request):
        return render(request, self.template_name, {
            'form': LoteProdutoForm(filial=request.filial_ativa),
            'title': 'Novo lote',
            'cancel_url': reverse_lazy('estoque:lote-list'),
        })

    def post(self, request):
        form = LoteProdutoForm(request.POST, filial=request.filial_ativa)
        if form.is_valid():
            try:
                with transaction.atomic():
                    lote = form.save(commit=False)
                    lote.filial = request.filial_ativa
                    quantidade_inicial = lote.quantidade_inicial or Decimal('0')
                    lote.quantidade_atual = Decimal('0')
                    lote.save()
                    if quantidade_inicial > 0:
                        MovimentacaoService.registrar_movimentacao(
                            produto_id=lote.produto_id,
                            filial_id=request.filial_ativa.pk,
                            tipo_operacao=MovimentacaoEstoque.TipoOperacao.ENTRADA,
                            quantidade=quantidade_inicial,
                            usuario_id=request.user.pk,
                            lote_id=lote.pk,
                            valor_unitario=lote.custo_unitario,
                            documento_tipo=(
                                MovimentacaoEstoque.DocumentoTipo.NFE
                                if lote.numero_nota_entrada
                                else MovimentacaoEstoque.DocumentoTipo.OUTRAS
                            ),
                            documento_numero=lote.numero_nota_entrada,
                            observacao=f'Entrada inicial do lote {lote.numero_lote}.',
                        )
                messages.success(request, f'Lote "{lote.numero_lote}" criado.')
                return redirect('estoque:lote-list')
            except DomainError as e:
                messages.error(request, str(e))
        return render(request, self.template_name, {
            'form': form,
            'title': 'Novo lote',
            'cancel_url': reverse_lazy('estoque:lote-list'),
        })


class LoteUpdateView(PermissaoRequiredMixin, View):
    permissao_modulo = 'estoque'
    permissao_acao = 'editar'
    template_name = 'estoque/lote/form.html'

    def get(self, request, pk):
        lote = get_object_or_404(LoteProduto.objects.for_filial(request.filial_ativa), pk=pk)
        return render(request, self.template_name, {
            'form': LoteProdutoForm(instance=lote, filial=request.filial_ativa),
            'lote': lote,
            'title': f'Editar lote - {lote.numero_lote}',
            'cancel_url': reverse_lazy('estoque:lote-list'),
        })

    def post(self, request, pk):
        lote = get_object_or_404(LoteProduto.objects.for_filial(request.filial_ativa), pk=pk)
        form = LoteProdutoForm(request.POST, instance=lote, filial=request.filial_ativa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Lote atualizado.')
            return redirect('estoque:lote-list')
        return render(request, self.template_name, {
            'form': form,
            'lote': lote,
            'title': f'Editar lote - {lote.numero_lote}',
            'cancel_url': reverse_lazy('estoque:lote-list'),
        })


class LoteBaixaValidadeView(PermissaoRequiredMixin, View):
    permissao_modulo = 'estoque'
    permissao_acao = 'cancelar'

    def post(self, request, pk):
        lote = get_object_or_404(LoteProduto.objects.for_filial(request.filial_ativa), pk=pk)
        try:
            MovimentacaoService.baixar_lote_por_validade(
                lote_id=lote.pk,
                usuario_id=request.user.pk,
            )
            messages.success(request, f'Lote "{lote.numero_lote}" baixado por validade.')
        except DomainError as e:
            messages.error(request, str(e))
        return redirect('estoque:lote-list')
