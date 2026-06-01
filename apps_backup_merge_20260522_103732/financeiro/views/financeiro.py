from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Sum
from apps.core.services.permissions import requer_permissao
from apps.financeiro.models import (
    ContaReceber, ContaPagar, DocumentoFiscal, DREConsolidado,
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
