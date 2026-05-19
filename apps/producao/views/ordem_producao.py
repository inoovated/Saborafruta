"""Views de Ordem de Produção — ciclo de vida completo."""
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View

from apps.core.services.exceptions import DomainError
from apps.core.services.permissions import PermissaoRequiredMixin
from apps.producao.forms import (
    CancelarOrdemProducaoForm, CriarOrdemProducaoForm, EncerrarOrdemProducaoForm,
)
from apps.producao.models import OrdemProducao
from apps.producao.services.op_service import OrdemProducaoService


class OrdemProducaoListView(PermissaoRequiredMixin, View):
    permissao_modulo = 'producao'
    template_name = 'producao/ordem_producao/list.html'

    def get(self, request):
        qs = OrdemProducao.objects.for_filial(request.filial_ativa).select_related(
            'produto_acabado', 'ficha_tecnica', 'usuario_abertura',
        )

        busca = request.GET.get('q', '').strip()
        status = request.GET.get('status', '')
        if busca:
            qs = qs.filter(
                Q(numero__icontains=busca)
                | Q(produto_acabado__descricao__icontains=busca)
            )
        if status:
            qs = qs.filter(status=status)

        qs = qs.order_by('-created_at')
        page_obj = Paginator(qs, 25).get_page(request.GET.get('page'))

        return render(request, self.template_name, {
            'page_obj': page_obj,
            'ordens': page_obj.object_list,
            'busca': busca,
            'status': status,
            'status_choices': OrdemProducao.Status.choices,
        })


class OrdemProducaoDetailView(PermissaoRequiredMixin, View):
    permissao_modulo = 'producao'
    template_name = 'producao/ordem_producao/detail.html'

    def get(self, request, pk):
        op = get_object_or_404(
            OrdemProducao.objects.for_filial(request.filial_ativa)
            .select_related('produto_acabado', 'ficha_tecnica', 'lote_gerado',
                            'usuario_abertura', 'usuario_encerramento'),
            pk=pk,
        )
        itens_bom = op.ficha_tecnica.itens.select_related('materia_prima').all()
        perdas = op.perdas.select_related('produto', 'usuario').all()
        return render(request, self.template_name, {
            'op': op,
            'itens_bom': itens_bom,
            'perdas': perdas,
            'encerrar_form': EncerrarOrdemProducaoForm() if op.pode_encerrar else None,
            'cancelar_form': CancelarOrdemProducaoForm() if op.pode_cancelar else None,
        })


class CriarOrdemProducaoView(PermissaoRequiredMixin, View):
    permissao_modulo = 'producao'
    permissao_acao = 'criar'
    template_name = 'producao/ordem_producao/criar.html'

    def get(self, request):
        return render(request, self.template_name, {
            'form': CriarOrdemProducaoForm(filial=request.filial_ativa),
            'title': 'Nova Ordem de Produção',
            'cancel_url': reverse_lazy('producao:op-list'),
        })

    def post(self, request):
        form = CriarOrdemProducaoForm(request.POST, filial=request.filial_ativa)
        if form.is_valid():
            try:
                op = OrdemProducaoService.criar_op(
                    ficha_id=form.cleaned_data['ficha_tecnica'].pk,
                    quantidade_planejada=form.cleaned_data['quantidade_planejada'],
                    filial=request.filial_ativa,
                    usuario=request.user,
                    data_inicio_prevista=form.cleaned_data.get('data_inicio_prevista'),
                    observacao=form.cleaned_data.get('observacao', ''),
                )
                messages.success(request, f'OP {op.numero} criada em rascunho.')
                return redirect('producao:op-detail', pk=op.pk)
            except DomainError as e:
                messages.error(request, str(e))
        return render(request, self.template_name, {
            'form': form,
            'title': 'Nova Ordem de Produção',
            'cancel_url': reverse_lazy('producao:op-list'),
        })


class AbrirOrdemProducaoView(PermissaoRequiredMixin, View):
    permissao_modulo = 'producao'
    permissao_acao = 'aprovar'

    def post(self, request, pk):
        op = get_object_or_404(OrdemProducao.objects.for_filial(request.filial_ativa), pk=pk)
        try:
            OrdemProducaoService.abrir(op, request.user)
            messages.success(request, f'OP {op.numero} aberta. Matéria-prima validada.')
        except DomainError as e:
            messages.error(request, str(e))
        return redirect('producao:op-detail', pk=op.pk)


class IniciarOrdemProducaoView(PermissaoRequiredMixin, View):
    permissao_modulo = 'producao'
    permissao_acao = 'editar'

    def post(self, request, pk):
        op = get_object_or_404(OrdemProducao.objects.for_filial(request.filial_ativa), pk=pk)
        try:
            OrdemProducaoService.iniciar(op, request.user)
            messages.success(request, f'OP {op.numero} em produção.')
        except DomainError as e:
            messages.error(request, str(e))
        return redirect('producao:op-detail', pk=op.pk)


class EncerrarOrdemProducaoView(PermissaoRequiredMixin, View):
    permissao_modulo = 'producao'
    permissao_acao = 'editar'

    def post(self, request, pk):
        op = get_object_or_404(OrdemProducao.objects.for_filial(request.filial_ativa), pk=pk)
        form = EncerrarOrdemProducaoForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Preencha corretamente os dados de encerramento.')
            return redirect('producao:op-detail', pk=op.pk)

        try:
            OrdemProducaoService.encerrar(
                op=op,
                usuario=request.user,
                quantidade_produzida=form.cleaned_data['quantidade_produzida'],
                peso_saida=form.cleaned_data.get('peso_saida'),
                numero_lote_gerado=form.cleaned_data.get('numero_lote_gerado', ''),
                data_validade=form.cleaned_data.get('data_validade'),
            )
            messages.success(
                request,
                f'OP {op.numero} encerrada. Rendimento: {op.rendimento}%. '
                f'Lote gerado: {op.lote_gerado.numero_lote}.',
            )
            if op.rendimento < OrdemProducaoService.RENDIMENTO_MINIMO_ALERTA:
                messages.warning(
                    request,
                    f'⚠️ Rendimento ({op.rendimento}%) abaixo do mínimo esperado '
                    f'({OrdemProducaoService.RENDIMENTO_MINIMO_ALERTA}%).',
                )
        except DomainError as e:
            messages.error(request, str(e))
        return redirect('producao:op-detail', pk=op.pk)


class CancelarOrdemProducaoView(PermissaoRequiredMixin, View):
    permissao_modulo = 'producao'
    permissao_acao = 'cancelar'

    def post(self, request, pk):
        op = get_object_or_404(OrdemProducao.objects.for_filial(request.filial_ativa), pk=pk)
        form = CancelarOrdemProducaoForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Informe o motivo do cancelamento.')
            return redirect('producao:op-detail', pk=op.pk)

        try:
            OrdemProducaoService.cancelar(op, request.user, form.cleaned_data['motivo'])
            messages.success(request, f'OP {op.numero} cancelada.')
        except DomainError as e:
            messages.error(request, str(e))
        return redirect('producao:op-detail', pk=op.pk)
