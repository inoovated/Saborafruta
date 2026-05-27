from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.core.paginator import Paginator
from django.db.models import Sum
from apps.core.services.permissions import requer_permissao
from apps.financeiro.forms import CentroCustoForm, PlanoContasDespesaForm
from apps.financeiro.models import (
    CentroCusto, ContaReceber, ContaPagar, DocumentoFiscal, DREConsolidado, PlanoContas,
)


def _filial_ativa(request):
    return getattr(request, 'filial_ativa', None) or getattr(request, 'filial', None)


@requer_permissao('financeiro', 'ver')
def receber_list(request):
    qs = ContaReceber.objects.for_filial(_filial_ativa(request)).select_related(
        "cliente"
    ).order_by("data_vencimento")
    status = request.GET.get("status")
    if status:
        qs = qs.filter(status=status)
    paginator = Paginator(qs, 50)
    page = paginator.get_page(request.GET.get("page", 1))

    totais = qs.aggregate(
        total=Sum("valor_final"),
        saldo=Sum("valor_saldo"),
    )
    return render(request, "financeiro/receber_list.html", {
        "title": "Contas a receber", "page": page, "totais": totais,
    })


@requer_permissao('financeiro', 'ver')
def pagar_list(request):
    qs = ContaPagar.objects.for_filial(_filial_ativa(request)).select_related(
        "fornecedor"
    ).order_by("data_vencimento")
    paginator = Paginator(qs, 50)
    page = paginator.get_page(request.GET.get("page", 1))
    return render(request, "financeiro/pagar_list.html", {
        "title": "Contas a pagar", "page": page,
    })


def _empresa_ativa(request):
    filial = _filial_ativa(request)
    return getattr(filial, "empresa", None) or getattr(request.user, "empresa", None)


def _pode_alterar_cadastros_financeiros(request):
    return (
        request.user.tem_permissao('financeiro', 'criar')
        or request.user.tem_permissao('financeiro', 'editar')
    )


@requer_permissao('financeiro', 'ver')
def centros_custo(request):
    empresa = _empresa_ativa(request)
    instance = None
    editar_id = request.GET.get("editar")
    if editar_id:
        instance = get_object_or_404(CentroCusto.objects.filter(empresa=empresa), pk=editar_id)

    if request.method == "POST":
        if not _pode_alterar_cadastros_financeiros(request):
            messages.error(request, "Usuario sem permissao para alterar cadastros financeiros.")
            return redirect("financeiro:centros_custo")
        acao = request.POST.get("acao")
        if acao == "excluir":
            obj = get_object_or_404(CentroCusto.objects.filter(empresa=empresa), pk=request.POST.get("id"))
            obj.ativo = False
            obj.save(update_fields=["ativo", "updated_at"])
            messages.success(request, "Centro de custo inativado.")
            return redirect("financeiro:centros_custo")
        if acao == "salvar":
            obj = None
            if request.POST.get("id"):
                obj = get_object_or_404(CentroCusto.objects.filter(empresa=empresa), pk=request.POST.get("id"))
            form = CentroCustoForm(request.POST, instance=obj, empresa=empresa)
            if form.is_valid():
                centro = form.save(commit=False)
                centro.empresa = empresa
                centro.save()
                messages.success(request, "Centro de custo salvo.")
                return redirect("financeiro:centros_custo")
            instance = obj
        else:
            form = CentroCustoForm(empresa=empresa)
    else:
        form = CentroCustoForm(instance=instance, empresa=empresa)

    centros = CentroCusto.objects.filter(empresa=empresa).order_by("codigo", "nome")
    return render(request, "financeiro/centros_custo.html", {
        "title": "Centros de custo",
        "form": form,
        "centros": centros,
        "instance": instance,
    })


@requer_permissao('financeiro', 'ver')
def plano_contas_despesas(request):
    empresa = _empresa_ativa(request)
    instance = None
    editar_id = request.GET.get("editar")
    if editar_id:
        instance = get_object_or_404(PlanoContas.objects.filter(empresa=empresa, tipo="D"), pk=editar_id)

    if request.method == "POST":
        if not _pode_alterar_cadastros_financeiros(request):
            messages.error(request, "Usuario sem permissao para alterar cadastros financeiros.")
            return redirect("financeiro:plano_contas_despesas")
        acao = request.POST.get("acao")
        if acao == "excluir":
            obj = get_object_or_404(PlanoContas.objects.filter(empresa=empresa, tipo="D"), pk=request.POST.get("id"))
            obj.ativo = False
            obj.save(update_fields=["ativo"])
            messages.success(request, "Despesa inativada.")
            return redirect("financeiro:plano_contas_despesas")
        if acao == "salvar":
            obj = None
            if request.POST.get("id"):
                obj = get_object_or_404(PlanoContas.objects.filter(empresa=empresa, tipo="D"), pk=request.POST.get("id"))
            form = PlanoContasDespesaForm(request.POST, instance=obj, empresa=empresa)
            if form.is_valid():
                form.save()
                messages.success(request, "Plano de contas de despesas salvo.")
                return redirect("financeiro:plano_contas_despesas")
            instance = obj
        else:
            form = PlanoContasDespesaForm(empresa=empresa)
    else:
        form = PlanoContasDespesaForm(instance=instance, empresa=empresa)

    contas = list(
        PlanoContas.objects.filter(empresa=empresa, tipo="D").select_related("conta_pai").order_by("codigo")
    )
    return render(request, "financeiro/plano_contas_despesas.html", {
        "title": "Plano de contas de despesas",
        "form": form,
        "contas": contas,
        "instance": instance,
    })


@requer_permissao('fiscal', 'ver')
def documentos_fiscais_list(request):
    qs = DocumentoFiscal.objects.for_filial(_filial_ativa(request)).order_by("-data_emissao")
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get("page", 1))
    return render(request, "financeiro/documentos_fiscais.html", {
        "title": "Documentos fiscais", "page": page,
    })


@requer_permissao('financeiro', 'ver')
def dre_view(request):
    qs = DREConsolidado.objects.for_filial(_filial_ativa(request)).order_by(
        "-competencia", "linha_producao",
    )[:36]
    return render(request, "financeiro/dre.html", {
        "title": "DRE Consolidado", "dres": qs,
    })
