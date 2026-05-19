"""CRUD de Unidade de Medida."""
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View

from apps.core.services.permissions import PermissaoRequiredMixin
from apps.produtos.forms import UnidadeMedidaForm
from apps.produtos.models import UnidadeMedida
from apps.produtos.services.replicacao_service import ReplicacaoProdutoService


class UnidadeListView(PermissaoRequiredMixin, View):
    permissao_modulo = 'produtos'
    template_name = 'produtos/unidade/list.html'

    def get(self, request):
        qs = UnidadeMedida.objects.for_filial(request.filial_ativa).filter(
            empresa=request.user.empresa,
        ).order_by('sigla')
        page_obj = Paginator(qs, 25).get_page(request.GET.get('page'))
        return render(request, self.template_name, {
            'page_obj': page_obj,
            'unidades': page_obj.object_list,
        })


class UnidadeCreateView(PermissaoRequiredMixin, View):
    permissao_modulo = 'produtos'
    permissao_acao = 'criar'
    template_name = 'produtos/unidade/form.html'

    def get(self, request):
        return render(request, self.template_name, {
            'form': UnidadeMedidaForm(),
            'title': 'Nova Unidade',
            'cancel_url': reverse_lazy('produtos:unidade-list'),
        })

    def post(self, request):
        form = UnidadeMedidaForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.empresa = request.user.empresa
            obj.save()
            ReplicacaoProdutoService.sincronizar_unidade(obj, request.filial_ativa)
            messages.success(request, f'Unidade "{obj}" criada.')
            return redirect('produtos:unidade-list')
        return render(request, self.template_name, {
            'form': form,
            'title': 'Nova Unidade',
            'cancel_url': reverse_lazy('produtos:unidade-list'),
        })


class UnidadeUpdateView(PermissaoRequiredMixin, View):
    permissao_modulo = 'produtos'
    permissao_acao = 'editar'
    template_name = 'produtos/unidade/form.html'

    def get(self, request, pk):
        obj = get_object_or_404(
            UnidadeMedida.objects.for_filial(request.filial_ativa),
            pk=pk,
            empresa=request.user.empresa,
        )
        return render(request, self.template_name, {
            'form': UnidadeMedidaForm(instance=obj),
            'title': f'Editar — {obj}',
            'cancel_url': reverse_lazy('produtos:unidade-list'),
        })

    def post(self, request, pk):
        obj = get_object_or_404(
            UnidadeMedida.objects.for_filial(request.filial_ativa),
            pk=pk,
            empresa=request.user.empresa,
        )
        form = UnidadeMedidaForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save()
            ReplicacaoProdutoService.sincronizar_unidade(obj, request.filial_ativa)
            messages.success(request, 'Unidade atualizada.')
            return redirect('produtos:unidade-list')
        return render(request, self.template_name, {
            'form': form,
            'title': f'Editar — {obj}',
            'cancel_url': reverse_lazy('produtos:unidade-list'),
        })
