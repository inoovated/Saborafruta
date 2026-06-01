"""Log reutilizavel para cadastros."""
import csv
from decimal import Decimal, InvalidOperation

from django.http import Http404, HttpResponse, JsonResponse
from django.db import models
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views import View
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet

from apps.cadastros.models import Cliente, Fornecedor, Representante, Transportadora
from apps.core.models import LogSistema
from apps.core.services.permissions import PermissaoRequiredMixin


CADASTRO_LOG_MODELS = {
    'clientes': (Cliente, 'Cliente'),
    'fornecedores': (Fornecedor, 'Fornecedor'),
    'transportadoras': (Transportadora, 'Transportadora'),
    'representantes': (Representante, 'Representante'),
}

AUDIT_IGNORED_FIELDS = {
    'id',
    'password',
    'last_login',
    'is_staff',
    'is_active',
    'is_superuser',
    'created_at',
    'updated_at',
    'id_externo',
    'grupo_replicacao',
    'filial',
    'filial_id',
    'empresa',
    'empresa_id',
}

FIELD_LABEL_OVERRIDES = {
    'tipo_pessoa': 'Tipo de pessoa',
    'razao_social': 'Razão social',
    'nome_fantasia': 'Nome fantasia',
    'cpf_cnpj': 'CPF/CNPJ',
    'rg_ie': 'RG/IE',
    'inscricao_municipal': 'Inscricao municipal',
    'inscricao_estadual': 'Inscricao estadual',
    'data_nascimento': 'Data de nascimento',
    'endereco': 'Endereço',
    'numero': 'Número',
    'codigo_municipio_ibge': 'Codigo IBGE',
    'codigo_pais_bacen': 'Codigo BACEN',
    'email_nfe': 'Email NFe',
    'contato_nome': 'Contato',
    'limite_credito': 'Limite de crédito',
    'saldo_devedor': 'Saldo devedor',
    'prazo_pagamento_dias': 'Prazo de pagamento',
    'grupo_desconto': 'Grupo de desconto',
    'consumidor_final': 'Consumidor final',
    'contribuinte_icms': 'Contribuinte ICMS',
    'optante_simples': 'Optante Simples',
    'pontos_fidelidade': 'Pontos fidelidade',
    'prazo_entrega_dias': 'Prazo de entrega',
    'nota_qualidade': 'Nota qualidade',
    'total_entregas': 'Total de entregas',
    'entregas_no_prazo': 'Entregas no prazo',
    'ativo': 'Status ativo',
    'cnpj': 'CNPJ',
    'cpf': 'CPF',
    'nome': 'Nome',
    'email': 'Email',
    'perfil': 'Perfil',
    'bloqueado_ate': 'Bloqueado até',
    'tentativas_login_falhas': 'Tentativas falhas de login',
    'ip_ultimo_acesso': 'IP ultimo acesso',
    'ultimo_acesso': 'Último acesso',
    'permissao': 'Permissão',
    'modulo': 'Módulo',
}


def _cadastro_model(tipo):
    try:
        return CADASTRO_LOG_MODELS[tipo]
    except KeyError as exc:
        raise Http404('Cadastro nao encontrado.') from exc


def _display_value(value, is_numeric=False):
    if value in (None, ''):
        return '-'
    if isinstance(value, bool):
        return 'Sim' if value else 'Não'
    if is_numeric:
        decimal_value = _decimal_value(value)
        if decimal_value is not None:
            return _format_decimal(decimal_value)
    return str(value)


def _format_decimal(value):
    text = format(value, 'f')
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    return text or '0'


def _decimal_value(value):
    if isinstance(value, bool) or value in (None, ''):
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace('R$', '').replace('%', '').replace(' ', '')
    if ',' in text and '.' in text:
        text = text.replace('.', '').replace(',', '.')
    elif ',' in text:
        text = text.replace(',', '.')
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def _is_numeric_model_field(model, field_name):
    try:
        field = model._meta.get_field(field_name)
    except Exception:
        return False
    return isinstance(
        field,
        (
            models.DecimalField,
            models.FloatField,
            models.IntegerField,
            models.PositiveIntegerField,
            models.PositiveSmallIntegerField,
            models.SmallIntegerField,
            models.BigIntegerField,
            models.PositiveBigIntegerField,
        ),
    )


def _audit_values_equal(model, field_name, before, after):
    if before == after:
        return True
    if _is_numeric_model_field(model, field_name):
        before_decimal = _decimal_value(before)
        after_decimal = _decimal_value(after)
        if before_decimal is not None and after_decimal is not None:
            return before_decimal == after_decimal
    return False


def _field_labels(model):
    return {
        field.name: FIELD_LABEL_OVERRIDES.get(field.name, field.verbose_name.title())
        for field in model._meta.concrete_fields
    }


def _log_detail(changes, fallback):
    if not changes:
        return fallback
    nomes = [change.get('campo') for change in changes if change.get('campo')]
    if len(nomes) == 1:
        return f'{nomes[0]} alterado.'
    return f'{len(nomes)} campos alterados: {", ".join(nomes)}.'


def _cadastro_entries(obj, label, usuario_padrao=None, limit=10, offset=0):
    model = obj.__class__
    labels = _field_labels(model)
    qs = list(LogSistema.objects.filter(
        tabela_afetada=model._meta.db_table,
        registro_id=obj.pk,
    ).select_related('usuario').order_by('data_hora'))
    entries = []
    previous = {}
    fallback_usuario = getattr(usuario_padrao, 'nome', '') or 'Sistema'

    for log in qs:
        novos = log.dados_novos or {}
        anteriores = log.dados_anteriores or previous or {}
        changes = []
        if log.acao == LogSistema.Acao.EDITAR:
            for field, after in novos.items():
                if field in AUDIT_IGNORED_FIELDS:
                    continue
                before = anteriores.get(field)
                if not _audit_values_equal(model, field, before, after):
                    is_numeric = _is_numeric_model_field(model, field)
                    changes.append({
                        'campo': labels.get(field, field.replace('_', ' ').title()),
                        'antes': _display_value(before, is_numeric=is_numeric),
                        'depois': _display_value(after, is_numeric=is_numeric),
                    })
            if not changes:
                previous = novos or previous
                continue
            acao = f'{label} editado'
            detalhe = _log_detail(changes, 'Cadastro alterado')
            quantidade = f'{len(changes)} campos'
            kind = 'edit'
        elif log.acao == LogSistema.Acao.CRIAR:
            acao = f'{label} criado'
            detalhe = 'Registro inicial'
            quantidade = ''
            kind = 'created'
        elif log.acao == LogSistema.Acao.EXCLUIR:
            acao = f'{label} excluido'
            detalhe = 'Cadastro excluido ou inativado'
            quantidade = ''
            kind = 'edit'
        else:
            acao = log.get_acao_display()
            detalhe = 'Acao registrada'
            quantidade = ''
            kind = 'edit'

        if log.usuario:
            fallback_usuario = log.usuario.nome
        entries.append({
            'data': log.data_hora,
            'usuario': log.usuario.nome if log.usuario else fallback_usuario,
            'acao': acao,
            'quantidade': quantidade,
            'detalhes': detalhe,
            'changes': changes,
            'kind': kind,
        })
        if novos:
            previous = novos

    if getattr(obj, 'created_at', None) and not any(item['kind'] == 'created' for item in entries):
        entries.append({
            'data': obj.created_at,
            'usuario': fallback_usuario,
            'acao': f'{label} criado',
            'quantidade': '',
            'detalhes': 'Registro inicial',
            'changes': [],
            'kind': 'created',
        })

    entries = sorted(entries, key=lambda item: item['data'], reverse=True)
    return entries[offset:offset + limit] if limit is not None else entries


def cadastro_log_context(obj, tipo, label, usuario_padrao=None):
    logs = _cadastro_entries(obj, label, usuario_padrao=usuario_padrao, limit=10)
    all_logs = _cadastro_entries(obj, label, usuario_padrao=usuario_padrao, limit=None)
    return {
        'cadastro_log_tipo': tipo,
        'cadastro_log_label': label.lower(),
        'cadastro_log_items': logs,
        'cadastro_log_total': len(all_logs),
        'cadastro_log_next_offset': len(logs),
        'cadastro_log_items_url': reverse('cadastros:cadastro-log-items', args=[tipo, obj.pk]),
        'cadastro_log_export_csv_url': reverse('cadastros:cadastro-log-export-csv', args=[tipo, obj.pk]),
        'cadastro_log_export_pdf_url': reverse('cadastros:cadastro-log-export-pdf', args=[tipo, obj.pk]),
        'cadastro_log_usuarios': sorted({item['usuario'] for item in all_logs if item.get('usuario')}),
        'cadastro_log_campos': sorted({
            change['campo']
            for item in all_logs
            for change in item.get('changes', [])
            if change.get('campo')
        }),
    }


def _get_obj(request, tipo, pk):
    model, label = _cadastro_model(tipo)
    return get_object_or_404(model.objects.for_filial(request.filial_ativa), pk=pk), label


def _export_rows(obj, label, request):
    rows = []
    for item in _cadastro_entries(obj, label, usuario_padrao=request.user, limit=None):
        data = timezone.localtime(item['data']).strftime('%d/%m/%Y %H:%M') if item.get('data') else ''
        base = [data, item.get('usuario') or '', item.get('acao') or '', item.get('quantidade') or '', item.get('detalhes') or '']
        changes = item.get('changes') or []
        if not changes:
            rows.append(base + ['', '', ''])
            continue
        for change in changes:
            rows.append(base + [change.get('campo') or '', change.get('antes') or '', change.get('depois') or ''])
    return rows


class CadastroLogItemsView(PermissaoRequiredMixin, View):
    permissao_modulo = 'cadastros'
    permissao_acao = 'ver'

    def get(self, request, tipo, pk):
        obj, label = _get_obj(request, tipo, pk)
        offset = max(int(request.GET.get('offset', 0) or 0), 0)
        limit = min(max(int(request.GET.get('limit', 50) or 50), 1), 50)
        items = _cadastro_entries(obj, label, usuario_padrao=request.user, limit=limit, offset=offset)
        total = len(_cadastro_entries(obj, label, usuario_padrao=request.user, limit=None))
        html = ''.join(
            render_to_string('cadastros/partials/_cadastro_log_item.html', {'item': item}, request=request)
            for item in items
        )
        return JsonResponse({'html': html, 'next_offset': offset + len(items), 'total': total})


class CadastroLogExportCsvView(PermissaoRequiredMixin, View):
    permissao_modulo = 'cadastros'
    permissao_acao = 'ver'

    def get(self, request, tipo, pk):
        obj, label = _get_obj(request, tipo, pk)
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="log_{tipo}_{pk}.csv"'
        response.write('\ufeff')
        writer = csv.writer(response, delimiter=';')
        writer.writerow(['Data e hora', 'Usuario', 'Acao', 'Quantidade', 'Detalhe', 'Campo', 'Antes', 'Depois'])
        writer.writerows(_export_rows(obj, label, request))
        return response


class CadastroLogExportPdfView(PermissaoRequiredMixin, View):
    permissao_modulo = 'cadastros'
    permissao_acao = 'ver'

    def get(self, request, tipo, pk):
        obj, label = _get_obj(request, tipo, pk)
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
        dados.extend(_export_rows(obj, label, request))
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
