"""CRUD de Transportadora, Motorista e Representante."""
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View

from apps.cadastros.forms import MotoristaForm, RepresentanteForm, TransportadoraForm, VeiculoForm
from apps.cadastros.models import Motorista, Representante, Transportadora, Veiculo
from apps.cadastros.services.compartilhamento_service import CompartilhamentoCadastrosService
from apps.cadastros.views.audit import cadastro_log_context
from apps.core.services.permissions import PermissaoRequiredMixin


class TransportadoraListView(PermissaoRequiredMixin, View):
    permissao_modulo = 'cadastros'
    template_name = 'cadastros/transportadora/list.html'

    def get(self, request):
        qs = Transportadora.objects.for_filial(request.filial_ativa)
        ativo = request.GET.get('ativo', '1')
        busca = request.GET.get('q', '').strip()
        if ativo == '0':
            qs = qs.filter(ativo=False)
        else:
            qs = qs.filter(ativo=True)
        if busca:
            qs = qs.filter(
                Q(razao_social__icontains=busca)
                | Q(nome_fantasia__icontains=busca)
                | Q(cnpj__icontains=busca)
                | Q(rntrc__icontains=busca)
            )
        page_obj = Paginator(qs.order_by('razao_social'), 25).get_page(request.GET.get('page'))
        return render(request, self.template_name, {
            'page_obj': page_obj,
            'transportadoras': page_obj.object_list,
            'busca': busca,
            'ativo': ativo,
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


class MotoristaListView(PermissaoRequiredMixin, View):
    permissao_modulo = 'cadastros'
    template_name = 'cadastros/motorista/list.html'

    def get(self, request):
        filial = request.filial_ativa
        qs = Motorista.objects.for_filial(filial)
        ativo = request.GET.get('ativo', '1')
        busca = request.GET.get('q', '').strip()
        if ativo == '0':
            qs = qs.filter(ativo=False)
        else:
            qs = qs.filter(ativo=True)
        if busca:
            qs = qs.filter(
                Q(nome__icontains=busca)
                | Q(cpf__icontains=busca)
                | Q(cnh__icontains=busca)
            )
        page_obj = Paginator(qs.select_related('transportadora'), 25).get_page(request.GET.get('page'))
        return render(request, self.template_name, {
            'motoristas': page_obj.object_list,
            'page_obj': page_obj,
            'busca': busca,
            'ativo': ativo,
        })


class MotoristaCreateView(PermissaoRequiredMixin, View):
    permissao_modulo = 'cadastros'
    permissao_acao = 'criar'
    template_name = 'cadastros/motorista/form.html'

    def get(self, request):
        return render(request, self.template_name, {
            'form': MotoristaForm(filial=request.filial_ativa),
            'title': 'Novo Motorista',
            'cancel_url': reverse_lazy('cadastros:motorista-list'),
        })

    def post(self, request):
        form = MotoristaForm(request.POST, filial=request.filial_ativa)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.filial = request.filial_ativa
            obj.save()
            messages.success(request, f'Motorista {obj.nome} cadastrado.')
            return redirect('cadastros:motorista-list')
        return render(request, self.template_name, {
            'form': form,
            'title': 'Novo Motorista',
            'cancel_url': reverse_lazy('cadastros:motorista-list'),
        })


class MotoristaUpdateView(PermissaoRequiredMixin, View):
    permissao_modulo = 'cadastros'
    permissao_acao = 'editar'
    template_name = 'cadastros/motorista/form.html'

    def get(self, request, pk):
        obj = get_object_or_404(Motorista.objects.for_filial(request.filial_ativa), pk=pk)
        return render(request, self.template_name, {
            'form': MotoristaForm(instance=obj, filial=request.filial_ativa),
            'motorista': obj,
            'title': f'Editar — {obj.nome}',
            'cancel_url': reverse_lazy('cadastros:motorista-list'),
        })

    def post(self, request, pk):
        obj = get_object_or_404(Motorista.objects.for_filial(request.filial_ativa), pk=pk)
        form = MotoristaForm(request.POST, instance=obj, filial=request.filial_ativa)
        if form.is_valid():
            form.save()
            messages.success(request, f'Motorista {obj.nome} atualizado.')
            return redirect('cadastros:motorista-list')
        return render(request, self.template_name, {
            'form': form,
            'motorista': obj,
            'title': f'Editar — {obj.nome}',
            'cancel_url': reverse_lazy('cadastros:motorista-list'),
        })


class MotoristaToggleAtivoView(PermissaoRequiredMixin, View):
    permissao_modulo = 'cadastros'
    permissao_acao = 'editar'

    def post(self, request, pk):
        obj = get_object_or_404(Motorista.objects.for_filial(request.filial_ativa), pk=pk)
        obj.ativo = not obj.ativo
        obj.save(update_fields=['ativo', 'updated_at'])
        status = 'ativado' if obj.ativo else 'desativado'
        messages.success(request, f'Motorista {obj.nome} {status}.')
        return redirect('cadastros:motorista-list')


class TransportadoraToggleAtivoView(PermissaoRequiredMixin, View):
    permissao_modulo = 'cadastros'
    permissao_acao = 'editar'

    def post(self, request, pk):
        obj = get_object_or_404(Transportadora.objects.for_filial(request.filial_ativa), pk=pk)
        obj.ativo = not obj.ativo
        obj.save(update_fields=['ativo', 'updated_at'])
        status = 'ativada' if obj.ativo else 'desativada'
        messages.success(request, f'Transportadora {obj} {status}.')
        return redirect('cadastros:transportadora-list')


class VeiculoListView(PermissaoRequiredMixin, View):
    permissao_modulo = 'cadastros'
    template_name = 'cadastros/veiculo/list.html'

    def get(self, request):
        filial = request.filial_ativa
        qs = Veiculo.objects.for_filial(filial)
        ativo = request.GET.get('ativo', '1')
        busca = request.GET.get('q', '').strip()
        if ativo == '0':
            qs = qs.filter(ativo=False)
        else:
            qs = qs.filter(ativo=True)
        if busca:
            qs = qs.filter(
                Q(placa__icontains=busca)
                | Q(descricao__icontains=busca)
                | Q(marca__icontains=busca)
                | Q(modelo__icontains=busca)
                | Q(renavam__icontains=busca)
                | Q(chassi__icontains=busca)
            )
        page_obj = Paginator(qs.select_related('transportadora'), 25).get_page(request.GET.get('page'))
        return render(request, self.template_name, {
            'veiculos': page_obj.object_list,
            'page_obj': page_obj,
            'busca': busca,
            'ativo': ativo,
        })


class VeiculoCreateView(PermissaoRequiredMixin, View):
    permissao_modulo = 'cadastros'
    permissao_acao = 'criar'
    template_name = 'cadastros/veiculo/form.html'

    def get(self, request):
        return render(request, self.template_name, {
            'form': VeiculoForm(filial=request.filial_ativa),
            'title': 'Novo Veículo',
            'cancel_url': reverse_lazy('cadastros:veiculo-list'),
        })

    def post(self, request):
        form = VeiculoForm(request.POST, filial=request.filial_ativa)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.filial = request.filial_ativa
            obj.placa = obj.placa.upper()
            obj.save()
            messages.success(request, f'Veículo {obj.placa} cadastrado.')
            return redirect('cadastros:veiculo-list')
        return render(request, self.template_name, {
            'form': form,
            'title': 'Novo Veículo',
            'cancel_url': reverse_lazy('cadastros:veiculo-list'),
        })


class VeiculoUpdateView(PermissaoRequiredMixin, View):
    permissao_modulo = 'cadastros'
    permissao_acao = 'editar'
    template_name = 'cadastros/veiculo/form.html'

    def get(self, request, pk):
        obj = get_object_or_404(Veiculo.objects.for_filial(request.filial_ativa), pk=pk)
        return render(request, self.template_name, {
            'form': VeiculoForm(instance=obj, filial=request.filial_ativa),
            'veiculo': obj,
            'title': f'Editar — {obj.placa}',
            'cancel_url': reverse_lazy('cadastros:veiculo-list'),
        })

    def post(self, request, pk):
        obj = get_object_or_404(Veiculo.objects.for_filial(request.filial_ativa), pk=pk)
        form = VeiculoForm(request.POST, instance=obj, filial=request.filial_ativa)
        if form.is_valid():
            saved = form.save(commit=False)
            saved.placa = saved.placa.upper()
            saved.save()
            messages.success(request, f'Veículo {obj.placa} atualizado.')
            return redirect('cadastros:veiculo-list')
        return render(request, self.template_name, {
            'form': form,
            'veiculo': obj,
            'title': f'Editar — {obj.placa}',
            'cancel_url': reverse_lazy('cadastros:veiculo-list'),
        })


class VeiculoToggleAtivoView(PermissaoRequiredMixin, View):
    permissao_modulo = 'cadastros'
    permissao_acao = 'editar'

    def post(self, request, pk):
        obj = get_object_or_404(Veiculo.objects.for_filial(request.filial_ativa), pk=pk)
        obj.ativo = not obj.ativo
        obj.save(update_fields=['ativo', 'updated_at'])
        status = 'ativado' if obj.ativo else 'desativado'
        messages.success(request, f'Veículo {obj.placa} {status}.')
        return redirect('cadastros:veiculo-list')


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
