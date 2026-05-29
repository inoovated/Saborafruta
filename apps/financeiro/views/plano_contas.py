"""Views de Plano de Contas."""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from apps.core.services.permissions import PermissaoRequiredMixin
from apps.financeiro.forms.plano_contas import PlanoContasForm
from apps.financeiro.models.conta_bancaria import PlanoContas


class PlanoContasListView(PermissaoRequiredMixin, View):
    permissao_modulo = 'financeiro'
    permissao_acao = 'ver'

    def get(self, request):
        filial = request.filial_ativa
        empresa = filial.empresa if filial else None

        contas = (
            PlanoContas.objects
            .filter(empresa=empresa)
            .select_related("conta_pai")
            .order_by("codigo")
        ) if empresa else PlanoContas.objects.none()

        receitas = [c for c in contas if c.tipo == "R"]
        despesas = [c for c in contas if c.tipo == "D"]

        return render(request, "financeiro/plano_contas/list.html", {
            "title": "Plano de Contas",
            "contas": contas,
            "receitas": receitas,
            "despesas": despesas,
            "total": contas.count() if empresa else 0,
            "pode_editar": True,
        })


class PlanoContasCreateView(PermissaoRequiredMixin, View):
    permissao_modulo = 'financeiro'
    permissao_acao = 'criar'

    def _get_empresa(self, request):
        filial = request.filial_ativa
        return filial.empresa if filial else None

    def get(self, request):
        empresa = self._get_empresa(request)
        form = PlanoContasForm(empresa=empresa)
        return render(request, "financeiro/plano_contas/form.html", {
            "title": "Nova conta",
            "form": form,
            "cancel_url": reverse("financeiro:plano_contas_list"),
        })

    def post(self, request):
        empresa = self._get_empresa(request)
        form = PlanoContasForm(request.POST, empresa=empresa)
        if form.is_valid():
            conta = form.save(commit=False)
            conta.empresa = empresa
            conta.save()
            messages.success(
                request,
                f"Conta '{conta.codigo} - {conta.descricao}' criada com sucesso.",
            )
            return redirect("financeiro:plano_contas_list")
        return render(request, "financeiro/plano_contas/form.html", {
            "title": "Nova conta",
            "form": form,
            "cancel_url": reverse("financeiro:plano_contas_list"),
        })


class PlanoContasEditView(PermissaoRequiredMixin, View):
    permissao_modulo = 'financeiro'
    permissao_acao = 'editar'

    def _get_conta(self, request, pk):
        filial = request.filial_ativa
        empresa = filial.empresa if filial else None
        return get_object_or_404(PlanoContas, pk=pk, empresa=empresa)

    def get(self, request, pk):
        conta = self._get_conta(request, pk)
        empresa = conta.empresa
        form = PlanoContasForm(instance=conta, empresa=empresa)
        return render(request, "financeiro/plano_contas/form.html", {
            "title": f"Editar - {conta.codigo}",
            "form": form,
            "conta": conta,
            "cancel_url": reverse("financeiro:plano_contas_list"),
        })

    def post(self, request, pk):
        conta = self._get_conta(request, pk)
        empresa = conta.empresa
        form = PlanoContasForm(request.POST, instance=conta, empresa=empresa)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f"Conta '{conta.codigo} - {conta.descricao}' atualizada.",
            )
            return redirect("financeiro:plano_contas_list")
        return render(request, "financeiro/plano_contas/form.html", {
            "title": f"Editar - {conta.codigo}",
            "form": form,
            "conta": conta,
            "cancel_url": reverse("financeiro:plano_contas_list"),
        })


class PlanoContasToggleAtivoView(PermissaoRequiredMixin, View):
    permissao_modulo = 'financeiro'
    permissao_acao = 'editar'

    def post(self, request, pk):
        filial = request.filial_ativa
        empresa = filial.empresa if filial else None
        conta = get_object_or_404(PlanoContas, pk=pk, empresa=empresa)
        conta.ativo = not conta.ativo
        conta.save(update_fields=["ativo"])
        estado = "ativada" if conta.ativo else "desativada"
        messages.success(request, f"Conta '{conta.codigo}' {estado}.")
        return redirect("financeiro:plano_contas_list")
