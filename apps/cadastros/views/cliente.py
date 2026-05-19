"""CRUD de Cliente + endpoint de consulta CEP."""
import csv

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import IntegerField, OuterRef, Q, Subquery
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views import View
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from apps.cadastros.forms import ClienteForm
from apps.cadastros.models import Cliente
from apps.cadastros.services.cep_service import CepService
from apps.cadastros.services.cliente_service import ClienteService
from apps.cadastros.services.replicacao_service import ReplicacaoCadastrosService
from apps.cadastros.views.audit import cadastro_log_context
from apps.core.services.exceptions import DomainError
from apps.core.services.permissions import PermissaoRequiredMixin


def _usuario_pode_exportar(request):
    perfil = getattr(request.user, '_perfil_ativo', None) or getattr(request.user, 'perfil', None)
    return bool(request.user.is_superuser or getattr(perfil, 'is_admin', False))


def _cliente_queryset_filtrado(request, incluir_inativos_por_padrao=False):
    mostrar_inativos = incluir_inativos_por_padrao or request.GET.get('inativos') == '1'
    codigo_global = Cliente.objects.filter(
        grupo_replicacao=OuterRef('grupo_replicacao'),
        filial__empresa_id=request.filial_ativa.empresa_id,
    ).order_by('pk').values('pk')[:1]
    qs = Cliente.objects.for_filial(request.filial_ativa).annotate(
        codigo_global=Subquery(codigo_global, output_field=IntegerField()),
    )
    if not mostrar_inativos:
        qs = qs.filter(ativo=True)

    busca = request.GET.get('q', '').strip()
    tipo = request.GET.get('tipo', '')
    ordem = request.GET.get('ordem', 'id')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')

    if busca:
        filtro_busca = (
            Q(razao_social__icontains=busca)
            | Q(nome_fantasia__icontains=busca)
            | Q(cpf_cnpj__icontains=busca)
            | Q(email__icontains=busca)
        )
        busca_codigo = busca.lstrip('0')
        if busca_codigo.isdigit():
            grupos_codigo = Cliente.objects.filter(
                filial__empresa_id=request.filial_ativa.empresa_id,
                pk=int(busca_codigo),
            ).values('grupo_replicacao')
            filtro_busca |= Q(pk=int(busca_codigo)) | Q(grupo_replicacao__in=grupos_codigo)
        qs = qs.filter(filtro_busca)
    if tipo:
        qs = qs.filter(tipo=tipo)

    data_inicio_valida = parse_date(data_inicio) if data_inicio else None
    data_fim_valida = parse_date(data_fim) if data_fim else None
    if data_inicio_valida:
        qs = qs.filter(created_at__date__gte=data_inicio_valida)
    if data_fim_valida:
        qs = qs.filter(created_at__date__lte=data_fim_valida)

    ordenacoes = {
        'id': 'codigo_global',
        'id_desc': '-codigo_global',
        'az': 'razao_social',
        'za': '-razao_social',
        'criado_desc': '-created_at',
        'criado_asc': 'created_at',
    }
    return qs.order_by(ordenacoes.get(ordem, 'id'))


def _codigo(pk):
    return f'{pk:02d}'


def _codigo_cadastro(obj):
    return _codigo(getattr(obj, 'codigo_global', None) or obj.pk)


def _cliente_csv_response(qs, filename):
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write('\ufeff')
    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'Codigo', 'Nome', 'Razao Social', 'CPF/CNPJ', 'Cidade', 'UF', 'Tipo',
        'Criado em', 'Ativo', 'Limite de credito',
    ])
    for c in qs:
        writer.writerow([
            _codigo_cadastro(c),
            c.nome_display,
            c.razao_social,
            c.cpf_cnpj,
            c.cidade,
            c.uf,
            c.get_tipo_display(),
            timezone.localtime(c.created_at).strftime('%d/%m/%Y %H:%M') if c.created_at else '',
            'Sim' if c.ativo else 'Nao',
            c.limite_credito,
        ])
    return response


def _cliente_pdf_response(qs):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="clientes_filtrados.pdf"'
    doc = SimpleDocTemplate(response, pagesize=landscape(A4), rightMargin=24, leftMargin=24, topMargin=24, bottomMargin=24)
    styles = getSampleStyleSheet()
    elementos = [
        Paragraph('Clientes filtrados', styles['Title']),
        Paragraph(f'Gerado em {timezone.localtime().strftime("%d/%m/%Y %H:%M")}', styles['Normal']),
        Spacer(1, 12),
    ]
    dados = [['Cod.', 'Nome', 'CPF/CNPJ', 'Cidade/UF', 'Tipo', 'Criado em', 'Ativo']]
    for c in qs:
        dados.append([
            _codigo_cadastro(c),
            c.nome_display,
            c.cpf_cnpj or '-',
            f'{c.cidade}/{c.uf}' if c.uf else c.cidade or '-',
            c.get_tipo_display(),
            timezone.localtime(c.created_at).strftime('%d/%m/%Y %H:%M') if c.created_at else '-',
            'Sim' if c.ativo else 'Nao',
        ])
    table = Table(dados, repeatRows=1, colWidths=[42, 170, 100, 110, 90, 92, 48])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8824a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#d1d5db')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elementos.append(table)
    doc.build(elementos)
    return response


class ClienteListView(PermissaoRequiredMixin, View):
    permissao_modulo = 'cadastros'
    permissao_acao = 'ver'
    template_name = 'cadastros/cliente/list.html'

    def get(self, request):
        mostrar_inativos = request.GET.get('inativos') == '1'
        qs = _cliente_queryset_filtrado(request)
        busca = request.GET.get('q', '').strip()
        tipo = request.GET.get('tipo', '')
        ordem = request.GET.get('ordem', 'id')
        data_inicio = request.GET.get('data_inicio', '')
        data_fim = request.GET.get('data_fim', '')

        page_obj = Paginator(qs, 50).get_page(request.GET.get('page'))
        query_params = request.GET.copy()
        query_params.pop('page', None)
        sort_urls = {}
        for key, value in {
            'codigo': 'id_desc' if ordem == 'id' else 'id',
            'nome': 'za' if ordem == 'az' else 'az',
            'criado': 'criado_asc' if ordem == 'criado_desc' else 'criado_desc',
        }.items():
            params = request.GET.copy()
            params.pop('page', None)
            params['ordem'] = value
            sort_urls[key] = params.urlencode()

        return render(request, self.template_name, {
            'page_obj': page_obj,
            'page_querystring': query_params.urlencode(),
            'sort_urls': sort_urls,
            'clientes': page_obj.object_list,
            'busca': busca,
            'tipo': tipo,
            'tipos': Cliente.Tipo.choices,
            'ordem': ordem,
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'mostrar_inativos': mostrar_inativos,
            'pode_exportar': _usuario_pode_exportar(request),
        })


class ClienteCreateView(PermissaoRequiredMixin, View):
    permissao_modulo = 'cadastros'
    permissao_acao = 'criar'
    template_name = 'cadastros/cliente/form.html'

    def get(self, request):
        return render(request, self.template_name, {
            'form': ClienteForm(),
            'title': 'Novo Cliente',
            'cancel_url': reverse_lazy('cadastros:cliente-list'),
        })

    def post(self, request):
        form = ClienteForm(request.POST)
        if form.is_valid():
            try:
                cliente = ClienteService.criar(
                    form.cleaned_data, request.user, request.filial_ativa,
                )
                messages.success(request, f'Cliente "{cliente.nome_display}" criado.')
                return redirect('cadastros:cliente-list')
            except DomainError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f'Nao foi possivel criar o cliente: {e}')
        else:
            erros = []
            for campo, lista_erros in form.errors.items():
                erros.append(f'{campo}: {", ".join(lista_erros)}')
            messages.error(request, f'Corrija os erros antes de salvar: {" | ".join(erros) or "sem erros de campo"}')

        return render(request, self.template_name, {
            'form': form,
            'title': 'Novo Cliente',
            'cancel_url': reverse_lazy('cadastros:cliente-list'),
        })


class ClienteUpdateView(PermissaoRequiredMixin, View):
    permissao_modulo = 'cadastros'
    permissao_acao = 'editar'
    template_name = 'cadastros/cliente/form.html'

    def get_object(self, request, pk):
        return get_object_or_404(
            Cliente.objects.for_filial(request.filial_ativa), pk=pk,
        )

    def get(self, request, pk):
        cliente = self.get_object(request, pk)
        return render(request, self.template_name, {
            'form': ClienteForm(instance=cliente),
            'cliente': cliente,
            'cadastro_log_pk': cliente.pk,
            **cadastro_log_context(cliente, 'clientes', 'Cliente', request.user),
            'title': f'Editar Cliente — {cliente.nome_display}',
            'cancel_url': reverse_lazy('cadastros:cliente-list'),
        })

    def post(self, request, pk):
        cliente = self.get_object(request, pk)
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            try:
                ClienteService.atualizar(cliente, form.cleaned_data)
                messages.success(request, 'Cliente atualizado.')
                return redirect('cadastros:cliente-list')
            except DomainError as e:
                messages.error(request, str(e))
        return render(request, self.template_name, {
            'form': form,
            'cliente': cliente,
            'cadastro_log_pk': cliente.pk,
            **cadastro_log_context(cliente, 'clientes', 'Cliente', request.user),
            'title': f'Editar Cliente — {cliente.nome_display}',
            'cancel_url': reverse_lazy('cadastros:cliente-list'),
        })


class ClienteDeleteView(PermissaoRequiredMixin, View):
    permissao_modulo = 'cadastros'
    permissao_acao = 'excluir'

    def post(self, request, pk):
        cliente = get_object_or_404(
            Cliente.objects.for_filial(request.filial_ativa), pk=pk,
        )
        cliente.ativo = False
        cliente.save(update_fields=['ativo', 'updated_at'])
        messages.success(request, f'Cliente "{cliente.nome_display}" desativado.')
        return redirect('cadastros:cliente-list')


class ClienteToggleAtivoView(PermissaoRequiredMixin, View):
    permissao_modulo = 'cadastros'
    permissao_acao = 'editar'

    def post(self, request, pk):
        cliente = get_object_or_404(
            Cliente.objects.for_filial(request.filial_ativa), pk=pk,
        )
        with transaction.atomic():
            cliente.ativo = not cliente.ativo
            cliente.save(update_fields=['ativo', 'updated_at'])
            ReplicacaoCadastrosService.sincronizar_cliente(cliente)
        status = 'ativado' if cliente.ativo else 'desativado'
        messages.success(request, f'Cliente "{cliente.nome_display}" {status}.')
        return redirect(request.META.get('HTTP_REFERER', 'cadastros:cliente-list'))


class ClienteExportCsvView(PermissaoRequiredMixin, View):
    permissao_modulo = 'cadastros'
    permissao_acao = 'ver'

    def get(self, request):
        if not _usuario_pode_exportar(request):
            messages.error(request, 'Apenas administradores podem exportar clientes.')
            return redirect('cadastros:cliente-list')
        return _cliente_csv_response(_cliente_queryset_filtrado(request), 'clientes_filtrados.csv')


class ClienteExportTodosCsvView(PermissaoRequiredMixin, View):
    permissao_modulo = 'cadastros'
    permissao_acao = 'ver'

    def get(self, request):
        if not _usuario_pode_exportar(request):
            messages.error(request, 'Apenas administradores podem exportar clientes.')
            return redirect('cadastros:cliente-list')
        qs = Cliente.objects.for_filial(request.filial_ativa).order_by('id')
        return _cliente_csv_response(qs, 'clientes_todos.csv')


class ClienteExportPdfView(PermissaoRequiredMixin, View):
    permissao_modulo = 'cadastros'
    permissao_acao = 'ver'

    def get(self, request):
        if not _usuario_pode_exportar(request):
            messages.error(request, 'Apenas administradores podem exportar clientes.')
            return redirect('cadastros:cliente-list')
        return _cliente_pdf_response(_cliente_queryset_filtrado(request))


def consultar_cep_ajax(request):
    cep = request.GET.get('cep', '')
    try:
        dados = CepService.consultar(cep)
    except DomainError as e:
        return JsonResponse({'erro': str(e)}, status=400)

    if not dados:
        return JsonResponse({'erro': 'CEP não encontrado.'}, status=404)
    return JsonResponse(dados)
