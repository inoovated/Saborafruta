"""Views do Pedido de Compra."""
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View

from apps.core.services.exceptions import DomainError
from apps.core.services.permissions import PermissaoRequiredMixin
from apps.compras.forms import (
    AdicionarItemCompraForm, CancelarPedidoCompraForm, PedidoCompraForm,
)
from apps.compras.models import EntradaNF, PedidoCompra
from apps.core.services.auditoria import auditoria_para_objeto
from apps.compras.services.compra_service import CompraService


class PedidoCompraListView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    template_name = 'compras/pedido/list.html'

    def get(self, request):
        qs = PedidoCompra.objects.for_filial(request.filial_ativa).select_related(
            'fornecedor', 'usuario',
        )
        busca = request.GET.get('q', '').strip()
        status = request.GET.get('status', '')
        if busca:
            qs = qs.filter(
                Q(numero_pedido__icontains=busca)
                | Q(fornecedor__razao_social__icontains=busca)
            )
        if status:
            qs = qs.filter(status=status)

        qs = qs.order_by('-data_emissao')
        page_obj = Paginator(qs, 25).get_page(request.GET.get('page'))
        return render(request, self.template_name, {
            'page_obj': page_obj,
            'pedidos': page_obj.object_list,
            'busca': busca,
            'status': status,
            'status_choices': PedidoCompra.Status.choices,
        })


class PedidoCompraCreateView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'criar'
    template_name = 'compras/pedido/criar.html'

    def get(self, request):
        return render(request, self.template_name, {
            'form': PedidoCompraForm(filial=request.filial_ativa),
            'title': 'Novo Pedido de Compra',
            'cancel_url': reverse_lazy('compras:pedido-list'),
        })

    def post(self, request):
        form = PedidoCompraForm(request.POST, filial=request.filial_ativa)
        if form.is_valid():
            try:
                pedido = CompraService.criar_pedido(
                    filial=request.filial_ativa,
                    usuario=request.user,
                    fornecedor=form.cleaned_data['fornecedor'],
                    data_entrega_prevista=form.cleaned_data.get('data_entrega_prevista'),
                    observacao=form.cleaned_data.get('observacao', ''),
                )
                # Atualizar campos restantes
                for campo in ('modalidade_frete', 'valor_frete', 'valor_outras_despesas'):
                    setattr(pedido, campo, form.cleaned_data.get(campo))
                pedido.save()
                messages.success(request, f'Pedido {pedido.numero_pedido} criado. Adicione itens.')
                return redirect('compras:pedido-detail', pk=pedido.pk)
            except DomainError as e:
                messages.error(request, str(e))
        return render(request, self.template_name, {
            'form': form,
            'title': 'Novo Pedido de Compra',
            'cancel_url': reverse_lazy('compras:pedido-list'),
        })


class PedidoCompraDetailView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    template_name = 'compras/pedido/detail.html'

    def get(self, request, pk):
        pedido = get_object_or_404(
            PedidoCompra.objects.for_filial(request.filial_ativa)
            .select_related('fornecedor', 'usuario', 'aprovado_por'),
            pk=pk,
        )
        itens = pedido.itens.select_related('produto', 'produto__unidade_medida').all()
        entradas = EntradaNF.objects.for_filial(request.filial_ativa).filter(
            pedido_compra=pedido,
        ).select_related('usuario_efetivacao').order_by('-data_entrada')
        return render(request, self.template_name, {
            'pedido': pedido,
            'itens': itens,
            'entradas_pedido': entradas,
            'auditoria_pedido': list(auditoria_para_objeto(pedido, limit=8)),
            'adicionar_item_form': AdicionarItemCompraForm(filial=request.filial_ativa) if pedido.status == 'rascunho' else None,
            'cancelar_form': CancelarPedidoCompraForm() if pedido.pode_cancelar else None,
        })


class AdicionarItemCompraView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'editar'

    def post(self, request, pk):
        pedido = get_object_or_404(PedidoCompra.objects.for_filial(request.filial_ativa), pk=pk)
        form = AdicionarItemCompraForm(request.POST, filial=request.filial_ativa)
        if form.is_valid():
            try:
                CompraService.adicionar_item(
                    pedido=pedido,
                    produto=form.cleaned_data['produto'],
                    quantidade=form.cleaned_data['quantidade'],
                    valor_unitario=form.cleaned_data['valor_unitario'],
                    valor_ipi=form.cleaned_data.get('valor_ipi') or 0,
                )
                messages.success(request, 'Item adicionado.')
            except DomainError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, 'Preencha corretamente os dados do item.')
        return redirect('compras:pedido-detail', pk=pk)


class RemoverItemCompraView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'editar'

    def post(self, request, pk, item_id):
        pedido = get_object_or_404(PedidoCompra.objects.for_filial(request.filial_ativa), pk=pk)
        try:
            CompraService.remover_item(pedido, item_id)
            messages.success(request, 'Item removido.')
        except DomainError as e:
            messages.error(request, str(e))
        return redirect('compras:pedido-detail', pk=pk)


class AprovarPedidoCompraView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'aprovar'

    def post(self, request, pk):
        pedido = get_object_or_404(PedidoCompra.objects.for_filial(request.filial_ativa), pk=pk)
        try:
            CompraService.aprovar_pedido(pedido, request.user)
            messages.success(request, f'Pedido {pedido.numero_pedido} aprovado.')
        except DomainError as e:
            messages.error(request, str(e))
        return redirect('compras:pedido-detail', pk=pk)


class EnviarPedidoCompraView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'editar'

    def post(self, request, pk):
        pedido = get_object_or_404(PedidoCompra.objects.for_filial(request.filial_ativa), pk=pk)
        try:
            CompraService.enviar_fornecedor(pedido, request.user)
            messages.success(request, f'Pedido enviado ao fornecedor.')
        except DomainError as e:
            messages.error(request, str(e))
        return redirect('compras:pedido-detail', pk=pk)


class CancelarPedidoCompraView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'cancelar'

    def post(self, request, pk):
        pedido = get_object_or_404(PedidoCompra.objects.for_filial(request.filial_ativa), pk=pk)
        form = CancelarPedidoCompraForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Informe o motivo do cancelamento.')
            return redirect('compras:pedido-detail', pk=pk)
        try:
            CompraService.cancelar_pedido(pedido, request.user, form.cleaned_data['motivo'])
            messages.success(request, f'Pedido cancelado.')
        except DomainError as e:
            messages.error(request, str(e))
        return redirect('compras:pedido-detail', pk=pk)
