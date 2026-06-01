"""CRUD de Transportadora e Representante."""
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View

from apps.cadastros.forms import RepresentanteForm, TransportadoraForm
from apps.cadastros.models import Representante, Transportadora
from apps.cadastros.services.compartilhamento_service import CompartilhamentoCadastrosService
from apps.cadastros.views.audit import cadastro_log_context
from apps.core.services.permissions import PermissaoRequiredMixin


class TransportadoraListView(PermissaoRequiredMixin, View):
    permissao_modulo = 'cadastros'
    template_name = 'cadastros/transportadora/list.html'

    def get(self, request):
        qs = Transportadora.objects.for_filial(request.filial_ativa).filter(ativo=True)
        busca = request.GET.get('q', '').strip()
        if busca:
            qs = qs.filter(Q(razao_social__icontains=busca) | Q(cnpj__icontains=busca))
        page_obj = Paginator(qs.order_by('razao_social'), 25).get_page(request.GET.get('page'))
        return render(request, self.template_name, {
            'page_obj': page_obj,
            'transportadoras': page_obj.object_list,
            'busca': busca,
        })


class TransportadoraCreateView(PermissaoRequiredMixin, View):
    permissao_modulo = 'cadastros'
    permissao_acao = 'criar'
    template_name = 'cadastros/transportadora/form.html'

    def get(self, request):
        return render(request, self.template_name, {
            'form': TransportadoraForm(),
            'title': 'Nova Transportadora',
            'cancel_url': reverse_lazy('cadastros:transportadora-list'),
        })

    def post(self, request):
        form = TransportadoraForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.filial = request.filial_ativa
            obj.save()
            CompartilhamentoCadastrosService.sincronizar_transportadora(obj)
            messages.success(request, 'Transportadora criada.')
            return redirect('cadastros:transportadora-list')
        return render(request, self.template_name, {
            'form': form,
            'title': 'Nova Transportadora',
            'cancel_url': reverse_lazy('cadastros:transportadora-list'),
        })


class TransportadoraUpdateView(PermissaoRequiredMixin, View):
    permissao_modulo = 'cadastros'
    permissao_acao = 'editar'
    template_name = 'cadastros/transportadora/form.html'

    def get(self, request, pk):
        obj = get_object_or_404(Transportadora.objects.for_filial(request.filial_ativa), pk=pk)
        return render(request, self.template_name, {
            'form': TransportadoraForm(instance=obj),
            'transportadora': obj,
            'cadastro_log_pk': obj.pk,
            **cadastro_log_context(obj, 'transportadoras', 'Transportadora', request.user),
            'title': f'Editar — {obj}',
            'cancel_url': reverse_lazy('cadastros:transportadora-list'),
        })

    def post(self, request, pk):
        obj = get_object_or_404(Transportadora.objects.for_filial(request.filial_ativa), pk=pk)
        form = TransportadoraForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save()
            CompartilhamentoCadastrosService.sincronizar_transportadora(obj)
            messages.success(request, 'Transportadora atualizada.')
            return redirect('cadastros:transportadora-list')
        return render(request, self.template_name, {
            'form': form,
            'transportadora': obj,
            'cadastro_log_pk': obj.pk,
            **cadastro_log_context(obj, 'transportadoras', 'Transportadora', request.user),
            'title': f'Editar — {obj}',
            'cancel_url': reverse_lazy('cadastros:transportadora-list'),
        })


class RepresentanteListView(PermissaoRequiredMixin, View):
    permissao_modulo = 'cadastros'
    template_name = 'cadastros/representante/list.html'

    def get(self, request):
        qs = Representante.objects.for_filial(request.filial_ativa).filter(ativo=True)
        busca = request.GET.get('q', '').strip()
        if busca:
            qs = qs.filter(Q(nome__icontains=busca) | Q(cpf__icontains=busca))
        page_obj = Paginator(qs.order_by('nome'), 25).get_page(request.GET.get('page'))
        return render(request, self.template_name, {
            'page_obj': page_obj,
            'representantes': page_obj.object_list,
            'busca': busca,
        })


class RepresentanteCreateView(PermissaoRequiredMixin, View):
    permissao_modulo = 'cadastros'
    permissao_acao = 'criar'
    template_name = 'cadastros/representante/form.html'

    def get(self, request):
        return render(request, self.template_name, {
            'form': RepresentanteForm(),
            'title': 'Novo Representante',
            'cancel_url': reverse_lazy('cadastros:representante-list'),
        })

    def post(self, request):
        form = RepresentanteForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.filial = request.filial_ativa
            obj.save()
            CompartilhamentoCadastrosService.sincronizar_representante(obj)
            messages.success(request, 'Representante criado.')
            return redirect('cadastros:representante-list')
        return render(request, self.template_name, {
            'form': form,
            'title': 'Novo Representante',
            'cancel_url': reverse_lazy('cadastros:representante-list'),
        })


class RepresentanteUpdateView(PermissaoRequiredMixin, View):
    permissao_modulo = 'cadastros'
    permissao_acao = 'editar'
    template_name = 'cadastros/representante/form.html'

    def get(self, request, pk):
        obj = get_object_or_404(Representante.objects.for_filial(request.filial_ativa), pk=pk)
        return render(request, self.template_name, {
            'form': RepresentanteForm(instance=obj),
            'representante': obj,
            'cadastro_log_pk': obj.pk,
            **cadastro_log_context(obj, 'representantes', 'Representante', request.user),
            'title': f'Editar — {obj}',
            'cancel_url': reverse_lazy('cadastros:representante-list'),
        })

    def post(self, request, pk):
        obj = get_object_or_404(Representante.objects.for_filial(request.filial_ativa), pk=pk)
        form = RepresentanteForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save()
            CompartilhamentoCadastrosService.sincronizar_representante(obj)
            messages.success(request, 'Representante atualizado.')
            return redirect('cadastros:representante-list')
        return render(request, self.template_name, {
            'form': form,
            'representante': obj,
            'cadastro_log_pk': obj.pk,
            **cadastro_log_context(obj, 'representantes', 'Representante', request.user),
            'title': f'Editar — {obj}',
            'cancel_url': reverse_lazy('cadastros:representante-list'),
        })
