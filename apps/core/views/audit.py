"""Log reutilizavel para cadastros administrativos."""
import csv

from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views import View
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.cadastros.views.audit import _cadastro_entries
from apps.core.models import Empresa, Filial, PerfilAcesso, Permissao, Usuario
from apps.core.views._admin import admin_area_required, superuser_required


CORE_LOG_MODELS = {
    'empresas': (Empresa, 'Empresa', True),
    'filiais': (Filial, 'Filial', True),
    'usuarios': (Usuario, 'Usuario', False),
    'perfis': (PerfilAcesso, 'Perfil', False),
}


def _core_entries(obj, tipo, label, usuario_padrao=None, limit=10, offset=0):
    entries = _cadastro_entries(obj, label, usuario_padrao=usuario_padrao, limit=None)
    if tipo == 'perfis':
        for permissao in Permissao.objects.filter(perfil=obj):
            for item in _cadastro_entries(permissao, 'Permissao', usuario_padrao=usuario_padrao, limit=None):
                item = {**item}
                item['acao'] = item['acao'].replace('Permissao', 'Permissao do perfil')
                entries.append(item)
    entries = sorted(entries, key=lambda item: item['data'], reverse=True)
    return entries[offset:offset + limit] if limit is not None else entries


def _core_export_rows(obj, tipo, label, request):
    rows = []
    for item in _core_entries(obj, tipo, label, usuario_padrao=request.user, limit=None):
        data = timezone.localtime(item['data']).strftime('%d/%m/%Y %H:%M') if item.get('data') else ''
        base = [data, item.get('usuario') or '', item.get('acao') or '', item.get('quantidade') or '', item.get('detalhes') or '']
        changes = item.get('changes') or []
        if not changes:
            rows.append(base + ['', '', ''])
            continue
        for change in changes:
            rows.append(base + [change.get('campo') or '', change.get('antes') or '', change.get('depois') or ''])
    return rows


def _core_model(tipo):
    try:
        return CORE_LOG_MODELS[tipo]
    except KeyError as exc:
        raise Http404('Cadastro administrativo nao encontrado.') from exc


def core_log_context(obj, tipo, label, usuario_padrao=None):
    logs = _core_entries(obj, tipo, label, usuario_padrao=usuario_padrao, limit=10)
    all_logs = _core_entries(obj, tipo, label, usuario_padrao=usuario_padrao, limit=None)
    return {
        'cadastro_log_tipo': tipo,
        'cadastro_log_label': label.lower(),
        'cadastro_log_pk': obj.pk,
        'cadastro_log_items': logs,
        'cadastro_log_total': len(all_logs),
        'cadastro_log_next_offset': len(logs),
        'cadastro_log_items_url': reverse('core:admin-log-items', args=[tipo, obj.pk]),
        'cadastro_log_export_csv_url': reverse('core:admin-log-export-csv', args=[tipo, obj.pk]),
        'cadastro_log_export_pdf_url': reverse('core:admin-log-export-pdf', args=[tipo, obj.pk]),
        'cadastro_log_usuarios': sorted({item['usuario'] for item in all_logs if item.get('usuario')}),
        'cadastro_log_campos': sorted({
            change['campo']
            for item in all_logs
            for change in item.get('changes', [])
            if change.get('campo')
        }),
    }


def _get_obj(tipo, pk):
    model, label, _super_only = _core_model(tipo)
    return get_object_or_404(model, pk=pk), label


class CoreAdminLogItemsView(View):
    def dispatch(self, request, *args, **kwargs):
        _model, _label, super_only = _core_model(kwargs.get('tipo'))
        checker = superuser_required if super_only else admin_area_required
        return checker(lambda req, *a, **kw: View.dispatch(self, req, *a, **kw))(request, *args, **kwargs)

    def get(self, request, tipo, pk):
        model, _label, super_only = _core_model(tipo)
        obj = get_object_or_404(model, pk=pk)
        label = _core_model(tipo)[1]
        offset = max(int(request.GET.get('offset', 0) or 0), 0)
        limit = min(max(int(request.GET.get('limit', 50) or 50), 1), 50)
        items = _core_entries(obj, tipo, label, usuario_padrao=request.user, limit=limit, offset=offset)
        total = len(_core_entries(obj, tipo, label, usuario_padrao=request.user, limit=None))
        html = ''.join(
            render_to_string('cadastros/partials/_cadastro_log_item.html', {'item': item}, request=request)
            for item in items
        )
        return JsonResponse({'html': html, 'next_offset': offset + len(items), 'total': total})


class CoreAdminLogExportCsvView(View):
    def dispatch(self, request, *args, **kwargs):
        _model, _label, super_only = _core_model(kwargs.get('tipo'))
        checker = superuser_required if super_only else admin_area_required
        return checker(lambda req, *a, **kw: View.dispatch(self, req, *a, **kw))(request, *args, **kwargs)

    def get(self, request, tipo, pk):
        obj, label = _get_obj(tipo, pk)
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="log_{tipo}_{pk}.csv"'
        response.write('\ufeff')
        writer = csv.writer(response, delimiter=';')
        writer.writerow(['Data e hora', 'Usuario', 'Acao', 'Quantidade', 'Detalhe', 'Campo', 'Antes', 'Depois'])
        writer.writerows(_core_export_rows(obj, tipo, label, request))
        return response


class CoreAdminLogExportPdfView(View):
    def dispatch(self, request, *args, **kwargs):
        _model, _label, super_only = _core_model(kwargs.get('tipo'))
        checker = superuser_required if super_only else admin_area_required
        return checker(lambda req, *a, **kw: View.dispatch(self, req, *a, **kw))(request, *args, **kwargs)

    def get(self, request, tipo, pk):
        obj, label = _get_obj(tipo, pk)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="log_{tipo}_{pk}.pdf"'
        doc = SimpleDocTemplate(response, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
        styles = getSampleStyleSheet()
        elementos = [
            Paragraph(f'Log de {label.lower()} #{pk} - {obj}', styles['Title']),
            Paragraph(f'Gerado em {timezone.localtime().strftime("%d/%m/%Y %H:%M")}', styles['Normal']),
            Spacer(1, 10),
        ]
        dados = [['Data/hora', 'Usuario', 'Acao', 'Qtd.', 'Detalhe', 'Campo', 'Antes', 'Depois']]
        dados.extend(_core_export_rows(obj, tipo, label, request))
        table = Table(dados, repeatRows=1, colWidths=[62, 78, 78, 42, 130, 84, 130, 130])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#d1d5db')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elementos.append(table)
        doc.build(elementos)
        return response
