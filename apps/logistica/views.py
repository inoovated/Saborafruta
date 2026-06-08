import json

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from apps.cadastros.models import Cliente, Fornecedor, Motorista, Veiculo
from apps.core.services.permissions import PermissaoRequiredMixin
from apps.financeiro.models.fiscal import DocumentoFiscal
from apps.logistica.forms import (
    CTeForm,
    DocumentoCTeForm,
    DocumentoManifestoCargaForm,
    ItemOrdemColetaForm,
    ItemRomaneioCargaForm,
    ManifestoCargaForm,
    OrdemColetaForm,
    RomaneioCargaForm,
)
from apps.logistica.models import (
    CTe,
    DocumentoCTe,
    DocumentoManifestoCarga,
    ItemOrdemColeta,
    ItemRomaneioCarga,
    ManifestoCarga,
    OrdemColeta,
    RomaneioCarga,
)


def _filial(request):
    return request.filial_ativa


def _clientes_fornecedores_json(filial):
    """Retorna JSON com clientes e fornecedores ativos da filial para autocomplete."""
    clientes = list(
        Cliente.objects.for_filial(filial).filter(ativo=True)
        .values('id', 'razao_social', 'nome_fantasia', 'cpf_cnpj')
        .order_by('razao_social')
    )
    fornecedores = list(
        Fornecedor.objects.for_filial(filial).filter(ativo=True)
        .values('id', 'razao_social', 'nome_fantasia', 'cpf_cnpj')
        .order_by('razao_social')
    )
    return json.dumps(clientes, ensure_ascii=False), json.dumps(fornecedores, ensure_ascii=False)


def _motoristas_veiculos_json(filial):
    """Retorna JSON com motoristas e veículos ativos da filial para os forms."""
    motoristas = list(
        Motorista.objects.for_filial(filial).filter(ativo=True)
        .values('id', 'nome', 'cpf', 'cnh')
        .order_by('nome')
    )
    veiculos = list(
        Veiculo.objects.for_filial(filial).filter(ativo=True)
        .values('id', 'placa', 'descricao', 'marca', 'modelo')
        .order_by('placa')
    )
    return json.dumps(motoristas), json.dumps(veiculos)


def _proximo_numero(filial):
    ultimo = (
        RomaneioCarga.objects.for_filial(filial)
        .order_by("-numero")
        .values_list("numero", flat=True)
        .first()
    )
    return (ultimo or 0) + 1


def _proximo_numero_ordem_coleta(filial):
    ultimo = (
        OrdemColeta.objects.for_filial(filial)
        .order_by("-numero")
        .values_list("numero", flat=True)
        .first()
    )
    return (ultimo or 0) + 1


def _proximo_numero_manifesto(filial):
    ultimo = (
        ManifestoCarga.objects.for_filial(filial)
        .order_by("-numero")
        .values_list("numero", flat=True)
        .first()
    )
    return (ultimo or 0) + 1


def _proximo_numero_cte(filial):
    ultimo = (
        CTe.objects.for_filial(filial)
        .order_by("-numero")
        .values_list("numero", flat=True)
        .first()
    )
    return (ultimo or 0) + 1


class RomaneioCargaListView(PermissaoRequiredMixin, View):
    permissao_modulo = "logistica"
    template_name = "logistica/romaneio/list.html"

    def get(self, request):
        filial = _filial(request)
        qs = (
            RomaneioCarga.objects.for_filial(filial)
            .select_related("transportadora", "responsavel")
            .annotate(qtd_itens=Count("itens"))
        )

        status = request.GET.get("status", "")
        q = request.GET.get("q", "").strip()
        data_ini = request.GET.get("data_ini", "")
        data_fim = request.GET.get("data_fim", "")

        if status:
            qs = qs.filter(status=status)
        if q:
            qs = qs.filter(
                Q(numero__icontains=q)
                | Q(motorista_nome__icontains=q)
                | Q(veiculo_placa__icontains=q)
                | Q(destino_rota__icontains=q)
                | Q(transportadora__razao_social__icontains=q)
                | Q(transportadora__nome_fantasia__icontains=q)
            )
        if data_ini:
            qs = qs.filter(data__gte=data_ini)
        if data_fim:
            qs = qs.filter(data__lte=data_fim)

        kpis = qs.aggregate(
            total=Count("id"),
            itens=Count("itens"),
            peso=Sum("peso_total_kg"),
            valor=Sum("valor_total"),
        )

        page_obj = Paginator(qs, 30).get_page(request.GET.get("page"))
        return render(request, self.template_name, {
            "title": "Romaneio de Carga",
            "romaneios": page_obj.object_list,
            "page_obj": page_obj,
            "status_choices": RomaneioCarga.Status.choices,
            "status_filtro": status,
            "q": q,
            "data_ini": data_ini,
            "data_fim": data_fim,
            "kpis": kpis,
        })


class RomaneioCargaCreateView(PermissaoRequiredMixin, View):
    permissao_modulo = "logistica"
    permissao_acao = "criar"
    template_name = "logistica/romaneio/form.html"

    def get(self, request):
        filial = _filial(request)
        form = RomaneioCargaForm(filial=filial, initial={
            "numero": _proximo_numero(filial),
            "data": timezone.localdate(),
        })
        motoristas_json, veiculos_json = _motoristas_veiculos_json(filial)
        return render(request, self.template_name, {
            "title": "Novo Romaneio de Carga",
            "form": form,
            "cancel_url": reverse("logistica:romaneio-list"),
            "motoristas_json": motoristas_json,
            "veiculos_json": veiculos_json,
        })

    def post(self, request):
        filial = _filial(request)
        form = RomaneioCargaForm(request.POST, filial=filial)
        if form.is_valid():
            romaneio = form.save(commit=False)
            romaneio.filial = filial
            romaneio.responsavel = request.user
            romaneio.save()
            messages.success(request, f"Romaneio #{romaneio.numero:06d} criado.")
            return redirect("logistica:romaneio-detail", pk=romaneio.pk)
        motoristas_json, veiculos_json = _motoristas_veiculos_json(filial)
        return render(request, self.template_name, {
            "title": "Novo Romaneio de Carga",
            "form": form,
            "cancel_url": reverse("logistica:romaneio-list"),
            "motoristas_json": motoristas_json,
            "veiculos_json": veiculos_json,
        })


class RomaneioCargaUpdateView(PermissaoRequiredMixin, View):
    permissao_modulo = "logistica"
    permissao_acao = "editar"
    template_name = "logistica/romaneio/form.html"

    def get(self, request, pk):
        filial = _filial(request)
        romaneio = get_object_or_404(RomaneioCarga.objects.for_filial(filial), pk=pk)
        form = RomaneioCargaForm(instance=romaneio, filial=filial)
        motoristas_json, veiculos_json = _motoristas_veiculos_json(filial)
        return render(request, self.template_name, {
            "title": f"Editar Romaneio #{romaneio.numero:06d}",
            "form": form,
            "romaneio": romaneio,
            "cancel_url": reverse("logistica:romaneio-detail", kwargs={"pk": romaneio.pk}),
            "motoristas_json": motoristas_json,
            "veiculos_json": veiculos_json,
        })

    def post(self, request, pk):
        romaneio = get_object_or_404(RomaneioCarga.objects.for_filial(_filial(request)), pk=pk)
        form = RomaneioCargaForm(request.POST, instance=romaneio, filial=_filial(request))
        if form.is_valid():
            form.save()
            messages.success(request, f"Romaneio #{romaneio.numero:06d} atualizado.")
            return redirect("logistica:romaneio-detail", pk=romaneio.pk)
        return render(request, self.template_name, {
            "title": f"Editar Romaneio #{romaneio.numero:06d}",
            "form": form,
            "romaneio": romaneio,
            "cancel_url": reverse("logistica:romaneio-detail", kwargs={"pk": romaneio.pk}),
        })


class RomaneioCargaDetailView(PermissaoRequiredMixin, View):
    permissao_modulo = "logistica"
    template_name = "logistica/romaneio/detail.html"

    def get(self, request, pk):
        romaneio = get_object_or_404(
            RomaneioCarga.objects.for_filial(_filial(request)).select_related("transportadora", "responsavel"),
            pk=pk,
        )
        itens = romaneio.itens.all()
        item_form = ItemRomaneioCargaForm(initial={"ordem": itens.count() + 1})
        return render(request, self.template_name, {
            "title": f"Romaneio #{romaneio.numero:06d}",
            "romaneio": romaneio,
            "itens": itens,
            "item_form": item_form,
        })


class ItemRomaneioCreateView(PermissaoRequiredMixin, View):
    permissao_modulo = "logistica"
    permissao_acao = "editar"

    def post(self, request, pk):
        romaneio = get_object_or_404(RomaneioCarga.objects.for_filial(_filial(request)), pk=pk)
        form = ItemRomaneioCargaForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.romaneio = romaneio
            item.save()
            romaneio.recalcular_totais()
            messages.success(request, "Entrega adicionada ao romaneio.")
        else:
            messages.error(request, "Revise os dados da entrega do romaneio.")
        return redirect("logistica:romaneio-detail", pk=romaneio.pk)


class ItemRomaneioDeleteView(PermissaoRequiredMixin, View):
    permissao_modulo = "logistica"
    permissao_acao = "editar"

    def post(self, request, pk, item_pk):
        romaneio = get_object_or_404(RomaneioCarga.objects.for_filial(_filial(request)), pk=pk)
        item = get_object_or_404(ItemRomaneioCarga.objects.filter(romaneio=romaneio), pk=item_pk)
        item.delete()
        romaneio.recalcular_totais()
        messages.success(request, "Entrega removida do romaneio.")
        return redirect("logistica:romaneio-detail", pk=romaneio.pk)


class OrdemColetaListView(PermissaoRequiredMixin, View):
    permissao_modulo = "logistica"
    template_name = "logistica/ordem_coleta/list.html"

    def get(self, request):
        filial = _filial(request)
        qs = (
            OrdemColeta.objects.for_filial(filial)
            .select_related("cliente", "fornecedor", "transportadora", "romaneio", "responsavel")
            .annotate(qtd_itens=Count("itens"))
        )

        status = request.GET.get("status", "")
        q = request.GET.get("q", "").strip()
        data_ini = request.GET.get("data_ini", "")
        data_fim = request.GET.get("data_fim", "")

        if status:
            qs = qs.filter(status=status)
        if q:
            qs = qs.filter(
                Q(numero__icontains=q)
                | Q(solicitante_nome__icontains=q)
                | Q(contato_nome__icontains=q)
                | Q(contato_telefone__icontains=q)
                | Q(cliente__razao_social__icontains=q)
                | Q(fornecedor__razao_social__icontains=q)
                | Q(transportadora__razao_social__icontains=q)
            )
        if data_ini:
            qs = qs.filter(data_solicitacao__gte=data_ini)
        if data_fim:
            qs = qs.filter(data_solicitacao__lte=data_fim)

        kpis = qs.aggregate(
            total=Count("id"),
            itens=Count("itens"),
            peso=Sum("peso_total_kg"),
            valor=Sum("valor_estimado"),
        )
        page_obj = Paginator(qs, 30).get_page(request.GET.get("page"))
        return render(request, self.template_name, {
            "title": "Ordens de Coleta",
            "ordens": page_obj.object_list,
            "page_obj": page_obj,
            "status_choices": OrdemColeta.Status.choices,
            "status_filtro": status,
            "q": q,
            "data_ini": data_ini,
            "data_fim": data_fim,
            "kpis": kpis,
        })


class OrdemColetaCreateView(PermissaoRequiredMixin, View):
    permissao_modulo = "logistica"
    permissao_acao = "criar"
    template_name = "logistica/ordem_coleta/form.html"

    def get(self, request):
        filial = _filial(request)
        form = OrdemColetaForm(filial=filial, initial={
            "numero": _proximo_numero_ordem_coleta(filial),
            "data_solicitacao": timezone.localdate(),
        })
        clientes_json, fornecedores_json = _clientes_fornecedores_json(filial)
        return render(request, self.template_name, {
            "title": "Nova Ordem de Coleta",
            "form": form,
            "cancel_url": reverse("logistica:ordem-coleta-list"),
            "clientes_json": clientes_json,
            "fornecedores_json": fornecedores_json,
        })

    def post(self, request):
        filial = _filial(request)
        form = OrdemColetaForm(request.POST, filial=filial)
        if form.is_valid():
            ordem = form.save(commit=False)
            ordem.filial = filial
            ordem.responsavel = request.user
            ordem.save()
            messages.success(request, f"Ordem de Coleta #{ordem.numero:06d} criada.")
            return redirect("logistica:ordem-coleta-detail", pk=ordem.pk)
        clientes_json, fornecedores_json = _clientes_fornecedores_json(filial)
        return render(request, self.template_name, {
            "title": "Nova Ordem de Coleta",
            "form": form,
            "cancel_url": reverse("logistica:ordem-coleta-list"),
            "clientes_json": clientes_json,
            "fornecedores_json": fornecedores_json,
        })


class OrdemColetaUpdateView(PermissaoRequiredMixin, View):
    permissao_modulo = "logistica"
    permissao_acao = "editar"
    template_name = "logistica/ordem_coleta/form.html"

    def get(self, request, pk):
        filial = _filial(request)
        ordem = get_object_or_404(OrdemColeta.objects.for_filial(filial), pk=pk)
        form = OrdemColetaForm(instance=ordem, filial=filial)
        clientes_json, fornecedores_json = _clientes_fornecedores_json(filial)
        return render(request, self.template_name, {
            "title": f"Editar Ordem #{ordem.numero:06d}",
            "form": form,
            "ordem": ordem,
            "cancel_url": reverse("logistica:ordem-coleta-detail", kwargs={"pk": ordem.pk}),
            "clientes_json": clientes_json,
            "fornecedores_json": fornecedores_json,
        })

    def post(self, request, pk):
        filial = _filial(request)
        ordem = get_object_or_404(OrdemColeta.objects.for_filial(filial), pk=pk)
        form = OrdemColetaForm(request.POST, instance=ordem, filial=filial)
        if form.is_valid():
            form.save()
            messages.success(request, f"Ordem de Coleta #{ordem.numero:06d} atualizada.")
            return redirect("logistica:ordem-coleta-detail", pk=ordem.pk)
        clientes_json, fornecedores_json = _clientes_fornecedores_json(filial)
        return render(request, self.template_name, {
            "title": f"Editar Ordem #{ordem.numero:06d}",
            "form": form,
            "ordem": ordem,
            "cancel_url": reverse("logistica:ordem-coleta-detail", kwargs={"pk": ordem.pk}),
            "clientes_json": clientes_json,
            "fornecedores_json": fornecedores_json,
        })


class OrdemColetaDetailView(PermissaoRequiredMixin, View):
    permissao_modulo = "logistica"
    template_name = "logistica/ordem_coleta/detail.html"

    def get(self, request, pk):
        ordem = get_object_or_404(
            OrdemColeta.objects.for_filial(_filial(request)).select_related(
                "cliente", "fornecedor", "transportadora", "romaneio", "responsavel"
            ),
            pk=pk,
        )
        itens = ordem.itens.all()
        item_form = ItemOrdemColetaForm(initial={"quantidade": 1, "unidade": "UN"})
        return render(request, self.template_name, {
            "title": f"Ordem de Coleta #{ordem.numero:06d}",
            "ordem": ordem,
            "itens": itens,
            "item_form": item_form,
        })


class ItemOrdemColetaCreateView(PermissaoRequiredMixin, View):
    permissao_modulo = "logistica"
    permissao_acao = "editar"

    def post(self, request, pk):
        ordem = get_object_or_404(OrdemColeta.objects.for_filial(_filial(request)), pk=pk)
        form = ItemOrdemColetaForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.ordem = ordem
            item.save()
            ordem.recalcular_totais()
            messages.success(request, "Item adicionado a ordem de coleta.")
        else:
            messages.error(request, "Revise os dados do item da coleta.")
        return redirect("logistica:ordem-coleta-detail", pk=ordem.pk)


class ItemOrdemColetaDeleteView(PermissaoRequiredMixin, View):
    permissao_modulo = "logistica"
    permissao_acao = "editar"

    def post(self, request, pk, item_pk):
        ordem = get_object_or_404(OrdemColeta.objects.for_filial(_filial(request)), pk=pk)
        item = get_object_or_404(ItemOrdemColeta.objects.filter(ordem=ordem), pk=item_pk)
        item.delete()
        ordem.recalcular_totais()
        messages.success(request, "Item removido da ordem de coleta.")
        return redirect("logistica:ordem-coleta-detail", pk=ordem.pk)


class ManifestoCargaListView(PermissaoRequiredMixin, View):
    permissao_modulo = "logistica"
    template_name = "logistica/manifesto/list.html"

    def get(self, request):
        filial = _filial(request)
        qs = (
            ManifestoCarga.objects.for_filial(filial)
            .select_related("transportadora", "romaneio", "responsavel")
            .annotate(documentos_count=Count("documentos"))
        )
        status = request.GET.get("status", "")
        q = request.GET.get("q", "").strip()
        data_ini = request.GET.get("data_ini", "")
        data_fim = request.GET.get("data_fim", "")

        if status:
            qs = qs.filter(status=status)
        if q:
            qs = qs.filter(
                Q(numero__icontains=q)
                | Q(motorista_nome__icontains=q)
                | Q(veiculo_placa__icontains=q)
                | Q(cidade_origem__icontains=q)
                | Q(cidade_destino__icontains=q)
                | Q(transportadora__razao_social__icontains=q)
                | Q(transportadora__nome_fantasia__icontains=q)
            )
        if data_ini:
            qs = qs.filter(data_emissao__gte=data_ini)
        if data_fim:
            qs = qs.filter(data_emissao__lte=data_fim)

        kpis = qs.aggregate(
            total=Count("id"),
            documentos=Count("documentos"),
            peso=Sum("peso_total_kg"),
            valor=Sum("valor_total"),
        )
        page_obj = Paginator(qs, 30).get_page(request.GET.get("page"))
        return render(request, self.template_name, {
            "title": "Manifestos de Carga",
            "manifestos": page_obj.object_list,
            "page_obj": page_obj,
            "status_choices": ManifestoCarga.Status.choices,
            "status_filtro": status,
            "q": q,
            "data_ini": data_ini,
            "data_fim": data_fim,
            "kpis": kpis,
        })


class ManifestoCargaCreateView(PermissaoRequiredMixin, View):
    permissao_modulo = "logistica"
    permissao_acao = "criar"
    template_name = "logistica/manifesto/form.html"

    def get(self, request):
        filial = _filial(request)
        form = ManifestoCargaForm(filial=filial, initial={
            "numero": _proximo_numero_manifesto(filial),
            "data_emissao": timezone.localdate(),
        })
        return render(request, self.template_name, {
            "title": "Novo Manifesto de Carga",
            "form": form,
            "cancel_url": reverse("logistica:manifesto-list"),
        })

    def post(self, request):
        filial = _filial(request)
        form = ManifestoCargaForm(request.POST, filial=filial)
        if form.is_valid():
            manifesto = form.save(commit=False)
            manifesto.filial = filial
            manifesto.responsavel = request.user
            manifesto.save()
            messages.success(request, f"Manifesto #{manifesto.numero:06d} criado.")
            return redirect("logistica:manifesto-detail", pk=manifesto.pk)
        return render(request, self.template_name, {
            "title": "Novo Manifesto de Carga",
            "form": form,
            "cancel_url": reverse("logistica:manifesto-list"),
        })


class ManifestoCargaUpdateView(PermissaoRequiredMixin, View):
    permissao_modulo = "logistica"
    permissao_acao = "editar"
    template_name = "logistica/manifesto/form.html"

    def get(self, request, pk):
        manifesto = get_object_or_404(ManifestoCarga.objects.for_filial(_filial(request)), pk=pk)
        form = ManifestoCargaForm(instance=manifesto, filial=_filial(request))
        return render(request, self.template_name, {
            "title": f"Editar Manifesto #{manifesto.numero:06d}",
            "form": form,
            "manifesto": manifesto,
            "cancel_url": reverse("logistica:manifesto-detail", kwargs={"pk": manifesto.pk}),
        })

    def post(self, request, pk):
        manifesto = get_object_or_404(ManifestoCarga.objects.for_filial(_filial(request)), pk=pk)
        form = ManifestoCargaForm(request.POST, instance=manifesto, filial=_filial(request))
        if form.is_valid():
            form.save()
            messages.success(request, f"Manifesto #{manifesto.numero:06d} atualizado.")
            return redirect("logistica:manifesto-detail", pk=manifesto.pk)
        return render(request, self.template_name, {
            "title": f"Editar Manifesto #{manifesto.numero:06d}",
            "form": form,
            "manifesto": manifesto,
            "cancel_url": reverse("logistica:manifesto-detail", kwargs={"pk": manifesto.pk}),
        })


class ManifestoCargaDetailView(PermissaoRequiredMixin, View):
    permissao_modulo = "logistica"
    template_name = "logistica/manifesto/detail.html"

    def get(self, request, pk):
        manifesto = get_object_or_404(
            ManifestoCarga.objects.for_filial(_filial(request)).select_related(
                "transportadora", "romaneio", "responsavel"
            ),
            pk=pk,
        )
        documentos = manifesto.documentos.all()
        documento_form = DocumentoManifestoCargaForm()
        return render(request, self.template_name, {
            "title": f"Manifesto #{manifesto.numero:06d}",
            "manifesto": manifesto,
            "documentos": documentos,
            "documento_form": documento_form,
        })


class DocumentoManifestoCreateView(PermissaoRequiredMixin, View):
    permissao_modulo = "logistica"
    permissao_acao = "editar"

    def post(self, request, pk):
        manifesto = get_object_or_404(ManifestoCarga.objects.for_filial(_filial(request)), pk=pk)
        form = DocumentoManifestoCargaForm(request.POST)
        if form.is_valid():
            documento = form.save(commit=False)
            documento.manifesto = manifesto
            documento.save()
            manifesto.recalcular_totais()
            messages.success(request, "Documento adicionado ao manifesto.")
        else:
            messages.error(request, "Revise os dados do documento do manifesto.")
        return redirect("logistica:manifesto-detail", pk=manifesto.pk)


class DocumentoManifestoDeleteView(PermissaoRequiredMixin, View):
    permissao_modulo = "logistica"
    permissao_acao = "editar"

    def post(self, request, pk, documento_pk):
        manifesto = get_object_or_404(ManifestoCarga.objects.for_filial(_filial(request)), pk=pk)
        documento = get_object_or_404(DocumentoManifestoCarga.objects.filter(manifesto=manifesto), pk=documento_pk)
        documento.delete()
        manifesto.recalcular_totais()
        messages.success(request, "Documento removido do manifesto.")
        return redirect("logistica:manifesto-detail", pk=manifesto.pk)


class CTeListView(PermissaoRequiredMixin, View):
    permissao_modulo = "logistica"
    template_name = "logistica/cte/list.html"

    def get(self, request):
        filial = _filial(request)
        qs = (
            CTe.objects.for_filial(filial)
            .select_related("transportadora", "responsavel")
            .annotate(qtd_documentos=Count("documentos"))
        )

        status = request.GET.get("status", "")
        q = request.GET.get("q", "").strip()
        data_ini = request.GET.get("data_ini", "")
        data_fim = request.GET.get("data_fim", "")

        if status:
            qs = qs.filter(status=status)
        if q:
            qs = qs.filter(
                Q(numero__icontains=q)
                | Q(numero_cte__icontains=q)
                | Q(chave_acesso__icontains=q)
                | Q(remetente_nome__icontains=q)
                | Q(destinatario_nome__icontains=q)
                | Q(veiculo_placa__icontains=q)
                | Q(transportadora__razao_social__icontains=q)
                | Q(transportadora__nome_fantasia__icontains=q)
            )
        if data_ini:
            qs = qs.filter(data_emissao__gte=data_ini)
        if data_fim:
            qs = qs.filter(data_emissao__lte=data_fim)

        kpis = qs.aggregate(
            total=Count("id"),
            documentos=Count("documentos"),
            peso=Sum("peso_total_kg"),
            valor=Sum("valor_frete"),
        )
        page_obj = Paginator(qs, 30).get_page(request.GET.get("page"))
        return render(request, self.template_name, {
            "title": "CT-e",
            "ctes": page_obj.object_list,
            "page_obj": page_obj,
            "status_choices": CTe.Status.choices,
            "status_filtro": status,
            "q": q,
            "data_ini": data_ini,
            "data_fim": data_fim,
            "kpis": kpis,
        })


class CTeCreateView(PermissaoRequiredMixin, View):
    permissao_modulo = "logistica"
    permissao_acao = "criar"
    template_name = "logistica/cte/form.html"

    def get(self, request):
        filial = _filial(request)
        form = CTeForm(filial=filial, initial={
            "numero": _proximo_numero_cte(filial),
            "data_emissao": timezone.localdate(),
        })
        return render(request, self.template_name, {
            "title": "Novo CT-e",
            "form": form,
            "cancel_url": reverse("logistica:cte-list"),
        })

    def post(self, request):
        filial = _filial(request)
        form = CTeForm(request.POST, filial=filial)
        if form.is_valid():
            cte = form.save(commit=False)
            cte.filial = filial
            cte.responsavel = request.user
            cte.valor_total = (
                (cte.valor_frete or 0) + (cte.valor_pedagio or 0) + (cte.valor_outros or 0)
            )
            cte.save()
            messages.success(request, f"CT-e #{cte.numero:06d} criado.")
            return redirect("logistica:cte-detail", pk=cte.pk)
        return render(request, self.template_name, {
            "title": "Novo CT-e",
            "form": form,
            "cancel_url": reverse("logistica:cte-list"),
        })


class CTeUpdateView(PermissaoRequiredMixin, View):
    permissao_modulo = "logistica"
    permissao_acao = "editar"
    template_name = "logistica/cte/form.html"

    def get(self, request, pk):
        cte = get_object_or_404(CTe.objects.for_filial(_filial(request)), pk=pk)
        form = CTeForm(instance=cte, filial=_filial(request))
        return render(request, self.template_name, {
            "title": f"Editar CT-e #{cte.numero:06d}",
            "form": form,
            "cte": cte,
            "cancel_url": reverse("logistica:cte-detail", kwargs={"pk": cte.pk}),
        })

    def post(self, request, pk):
        cte = get_object_or_404(CTe.objects.for_filial(_filial(request)), pk=pk)
        form = CTeForm(request.POST, instance=cte, filial=_filial(request))
        if form.is_valid():
            obj = form.save(commit=False)
            obj.valor_total = (
                (obj.valor_frete or 0) + (obj.valor_pedagio or 0) + (obj.valor_outros or 0)
            )
            obj.save()
            messages.success(request, f"CT-e #{cte.numero:06d} atualizado.")
            return redirect("logistica:cte-detail", pk=cte.pk)
        return render(request, self.template_name, {
            "title": f"Editar CT-e #{cte.numero:06d}",
            "form": form,
            "cte": cte,
            "cancel_url": reverse("logistica:cte-detail", kwargs={"pk": cte.pk}),
        })


class CTeDetailView(PermissaoRequiredMixin, View):
    permissao_modulo = "logistica"
    template_name = "logistica/cte/detail.html"

    def get(self, request, pk):
        cte = get_object_or_404(
            CTe.objects.for_filial(_filial(request)).select_related("transportadora", "responsavel"),
            pk=pk,
        )
        documentos = cte.documentos.all()
        documento_form = DocumentoCTeForm()
        doc_fiscal = DocumentoFiscal.objects.filter(origem_tipo="cte", origem_id=cte.pk).first()
        return render(request, self.template_name, {
            "title": f"CT-e #{cte.numero:06d}",
            "cte": cte,
            "documentos": documentos,
            "documento_form": documento_form,
            "doc_fiscal": doc_fiscal,
        })


class DocumentoCTeCreateView(PermissaoRequiredMixin, View):
    permissao_modulo = "logistica"
    permissao_acao = "editar"

    def post(self, request, pk):
        cte = get_object_or_404(CTe.objects.for_filial(_filial(request)), pk=pk)
        form = DocumentoCTeForm(request.POST)
        if form.is_valid():
            documento = form.save(commit=False)
            documento.cte = cte
            documento.save()
            cte.recalcular_totais()
            messages.success(request, "Documento adicionado ao CT-e.")
        else:
            messages.error(request, "Revise os dados do documento do CT-e.")
        return redirect("logistica:cte-detail", pk=cte.pk)


class DocumentoCTeDeleteView(PermissaoRequiredMixin, View):
    permissao_modulo = "logistica"
    permissao_acao = "editar"

    def post(self, request, pk, documento_pk):
        cte = get_object_or_404(CTe.objects.for_filial(_filial(request)), pk=pk)
        documento = get_object_or_404(DocumentoCTe.objects.filter(cte=cte), pk=documento_pk)
        documento.delete()
        cte.recalcular_totais()
        messages.success(request, "Documento removido do CT-e.")
        return redirect("logistica:cte-detail", pk=cte.pk)


# --------------------------------------------------------------------------
# CT-e Focus NFe — Emissao Fiscal
# --------------------------------------------------------------------------

class CTeEmitirView(PermissaoRequiredMixin, View):
    permissao_modulo = "logistica"
    permissao_acao = "editar"

    def post(self, request, pk):
        from apps.logistica.services.cte_focusnfe import emitir_cte
        cte = get_object_or_404(CTe.objects.for_filial(_filial(request)), pk=pk)
        doc, erro = emitir_cte(cte, request.user)
        if erro:
            messages.error(request, f"Erro ao emitir CT-e: {erro}")
        else:
            messages.success(request, "CT-e enviado para autorizacao na SEFAZ.")
        return redirect("logistica:cte-detail", pk=cte.pk)


class CTeConsultarView(PermissaoRequiredMixin, View):
    permissao_modulo = "logistica"
    permissao_acao = "editar"

    def post(self, request, pk):
        from apps.logistica.services.cte_focusnfe import consultar_cte
        cte = get_object_or_404(CTe.objects.for_filial(_filial(request)), pk=pk)
        doc, erro = consultar_cte(cte)
        if erro:
            messages.error(request, f"Erro ao consultar CT-e: {erro}")
        else:
            messages.success(request, f"Status atualizado: {doc.get_status_display() if doc else ''}.")
        return redirect("logistica:cte-detail", pk=cte.pk)


class CteCancelarView(PermissaoRequiredMixin, View):
    permissao_modulo = "logistica"
    permissao_acao = "editar"

    def post(self, request, pk):
        from apps.logistica.services.cte_focusnfe import cancelar_cte
        cte = get_object_or_404(CTe.objects.for_filial(_filial(request)), pk=pk)
        justificativa = request.POST.get("justificativa", "").strip()
        if len(justificativa) < 15:
            messages.error(request, "Justificativa deve ter no minimo 15 caracteres.")
            return redirect("logistica:cte-detail", pk=cte.pk)
        doc, erro = cancelar_cte(cte, justificativa)
        if erro:
            messages.error(request, f"Erro ao cancelar CT-e: {erro}")
        else:
            messages.success(request, "CT-e cancelado com sucesso.")
        return redirect("logistica:cte-detail", pk=cte.pk)


class CteDACTEView(PermissaoRequiredMixin, View):
    permissao_modulo = "logistica"

    def get(self, request, pk):
        from apps.logistica.services.cte_focusnfe import dacte_pdf
        cte = get_object_or_404(CTe.objects.for_filial(_filial(request)), pk=pk)
        try:
            pdf_bytes = dacte_pdf(cte)
        except Exception as exc:
            messages.error(request, f"Erro ao baixar DACTE: {exc}")
            return redirect("logistica:cte-detail", pk=cte.pk)
        resp = HttpResponse(pdf_bytes, content_type="application/pdf")
        resp["Content-Disposition"] = f'inline; filename="dacte-{cte.numero:06d}.pdf"'
        return resp
