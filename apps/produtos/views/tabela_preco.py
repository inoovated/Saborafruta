"""CRUD de Tabela de Preço."""
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View

from apps.core.services.permissions import PermissaoRequiredMixin
from apps.produtos.forms import TabelaPrecoForm
from apps.produtos.models import TabelaPreco
from apps.produtos.services.replicacao_service import ReplicacaoProdutoService


class TabelaPrecoListView(PermissaoRequiredMixin, View):
    permissao_modulo = 'produtos'
    template_name = 'produtos/tabela_preco/list.html'

    def get(self, request):
        qs = TabelaPreco.objects.for_filial(request.filial_ativa).filter(ativo=True)
        page_obj = Paginator(qs.order_by('descricao'), 25).get_page(request.GET.get('page'))
        return render(request, self.template_name, {
            'page_obj': page_obj,
            'tabelas': page_obj.object_list,
        })


class TabelaPrecoCreateView(PermissaoRequiredMixin, View):
    permissao_modulo = 'produtos'
    permissao_acao = 'criar'
    template_name = 'produtos/tabela_preco/form.html'

    def get(self, request):
        return render(request, self.template_name, {
            'form': TabelaPrecoForm(),
            'title': 'Nova Tabela de Preço',
            'cancel_url': reverse_lazy('produtos:tabela-list'),
        })

    def post(self, request):
        form = TabelaPrecoForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.filial = request.filial_ativa
            obj.save()
            ReplicacaoProdutoService._vincular_tabela_preco(obj, obj.filial)
            ReplicacaoProdutoService.sincronizar_tabela_preco(obj)
            messages.success(request, 'Tabela de preço criada.')
            return redirect('produtos:tabela-update', pk=obj.pk)
        return render(request, self.template_name, {
            'form': form,
            'title': 'Nova Tabela de Preço',
            'cancel_url': reverse_lazy('produtos:tabela-list'),
        })


class TabelaPrecoUpdateView(PermissaoRequiredMixin, View):
    permissao_modulo = 'produtos'
    permissao_acao = 'editar'
    template_name = 'produtos/tabela_preco/form.html'

    def get(self, request, pk):
        obj = get_object_or_404(TabelaPreco.objects.for_filial(request.filial_ativa), pk=pk)
        return render(request, self.template_name, {
            'form': TabelaPrecoForm(instance=obj),
            'tabela': obj,
            'title': f'Editar — {obj}',
            'cancel_url': reverse_lazy('produtos:tabela-list'),
        })

    def post(self, request, pk):
        obj = get_object_or_404(TabelaPreco.objects.for_filial(request.filial_ativa), pk=pk)
        form = TabelaPrecoForm(request.POST, instance=obj)
        if form.is_valid():
            tabela = form.save()
            ReplicacaoProdutoService._vincular_tabela_preco(tabela, tabela.filial)
            ReplicacaoProdutoService.sincronizar_tabela_preco(tabela)
            messages.success(request, 'Tabela atualizada.')
            return redirect('produtos:tabela-list')
        return render(request, self.template_name, {
            'form': form,
            'tabela': obj,
            'title': f'Editar — {obj}',
            'cancel_url': reverse_lazy('produtos:tabela-list'),
        })
