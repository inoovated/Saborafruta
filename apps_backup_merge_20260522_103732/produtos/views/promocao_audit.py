import csv
import logging

from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views import View
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.cadastros.views.audit import (
    AUDIT_IGNORED_FIELDS,
    _audit_values_equal,
    _display_value,
    _is_numeric_model_field,
)
from apps.core.models import LogSistema
from apps.core.services.permissions import PermissaoRequiredMixin
from apps.produtos.models import (
    BrindeProduto,
    BrindeProdutoItem,
    KitCategoria,
    KitCategoriaRegra,
    KitProduto,
    KitProdutoItem,
    Produto,
    ProdutoFilial,
    PromocaoQuantidade,
    PromocaoQuantidadeFaixa,
)


logger = logging.getLogger(__name__)

PROMO_LOG_MODELS = {
    PromocaoQuantidade._meta.db_table: (PromocaoQuantidade, 'Combo'),
    PromocaoQuantidadeFaixa._meta.db_table: (PromocaoQuantidadeFaixa, 'Faixa do combo'),
    KitProduto._meta.db_table: (KitProduto, 'Kit'),
    KitProdutoItem._meta.db_table: (KitProdutoItem, 'Item do kit'),
    BrindeProduto._meta.db_table: (BrindeProduto, 'Brinde'),
    BrindeProdutoItem._meta.db_table: (BrindeProdutoItem, 'Item do brinde'),
    KitCategoria._meta.db_table: (KitCategoria, 'Desconto por categoria'),
    KitCategoriaRegra._meta.db_table: (KitCategoriaRegra, 'Regra de categoria'),
    Produto._meta.db_table: (Produto, 'Preco promocional'),
    ProdutoFilial._meta.db_table: (ProdutoFilial, 'Preco promocional'),
}

PROMO_PRODUCT_FIELDS = {
    'preco_venda',
    'preco_promocional',
    'promocao_tipo_desconto',
    'promocao_valor_desconto',
    'promocao_inicio',
    'promocao_fim',
    'promocao_dias_semana',
}

DIAS_SEMANA_LABELS = {
    '0': 'Seg',
    '1': 'Ter',
    '2': 'Qua',
    '3': 'Qui',
    '4': 'Sex',
    '5': 'Sab',
    '6': 'Dom',
}

FIELD_LABELS = {
    'produto': 'Produto',
    'produto_id': 'Produto',
    'produto_gatilho': 'Produto gatilho',
    'produto_gatilho_id': 'Produto gatilho',
    'nome': 'Nome',
    'descricao': 'Descricao',
    'data_inicio': 'Inicio',
    'data_fim': 'Fim',
    'dias_semana': 'Dias da semana',
    'usar_preco_promocional': 'Usar preco promocional',
    'permite_preco_promocional': 'Usar preco promocional',
    'replicar_filiais': 'Replicar para filiais',
    'ativo': 'Status ativo',
    'condicao_quantidade': 'Condicao',
    'quantidade_minima': 'Quantidade',
    'quantidade_gatilho': 'Quantidade gatilho',
    'tipo_desconto': 'Tipo de desconto',
    'valor': 'Valor',
    'valor_desconto': 'Valor do desconto',
    'kit': 'Kit',
    'kit_id': 'Kit',
    'brinde': 'Brinde',
    'brinde_id': 'Brinde',
    'categoria': 'Categoria',
    'categoria_id': 'Categoria',
    'subcategoria': 'Subcategoria',
    'subcategoria_id': 'Subcategoria',
    'quantidade': 'Quantidade',
    'preco_venda': 'Preco de venda',
    'preco_promocional': 'Preco promocional',
    'promocao_tipo_desconto': 'Tipo de desconto promocional',
    'promocao_valor_desconto': 'Valor do desconto promocional',
    'promocao_inicio': 'Inicio da promocao',
    'promocao_fim': 'Fim da promocao',
    'promocao_dias_semana': 'Dias da promocao',
}


def _log_queryset(request):
    return (
        LogSistema.objects.filter(
            filial=request.filial_ativa,
            modulo='produtos',
            tabela_afetada__in=PROMO_LOG_MODELS.keys(),
        )
        .select_related('usuario')
        .order_by('-data_hora')
    )


def _field_label(model, field):
    if field in FIELD_LABELS:
        return FIELD_LABELS[field]
    try:
        return model._meta.get_field(field).verbose_name.title()
    except Exception:
        return field.replace('_', ' ').title()


def _log_detail(changes, fallback):
    if not changes:
        return fallback
    campos = [change['campo'] for change in changes if change.get('campo')]
    if len(campos) == 1:
        return f'{campos[0]} alterado.'
    return f'{len(campos)} campos alterados: {", ".join(campos)}.'


def _registro_referencia(log, model):
    if model is ProdutoFilial:
        dados = log.dados_novos or log.dados_anteriores or {}
        produto = dados.get('produto') or dados.get('produto_id')
        if produto:
            return f'Produto {produto} (vinculo #{log.registro_id or "-"})'
    return f'Registro #{log.registro_id or "-"}'


def _dias_semana_display(value):
    if value in (None, ''):
        return 'Todos os dias'
    selected = [item.strip() for item in str(value).split(',') if item.strip() in DIAS_SEMANA_LABELS]
    if len(selected) == 7:
        return 'Todos os dias'
    return ', '.join(DIAS_SEMANA_LABELS[item] for item in selected) or 'Todos os dias'


def _display_field_value(model, field, value):
    if field in {'dias_semana', 'promocao_dias_semana'}:
        return _dias_semana_display(value)
    return _display_value(value, is_numeric=_is_numeric_model_field(model, field))


def _produto_tinha_preco_promocional(data):
    if not data:
        return False
    try:
        return float(str(data.get('preco_promocional') or '0').replace(',', '.')) > 0
    except (TypeError, ValueError):
        return False


def _changes_for_log(log, model):
    novos = log.dados_novos or {}
    anteriores = log.dados_anteriores or {}
    fields = set(novos.keys()) | set(anteriores.keys())
    if model in {Produto, ProdutoFilial}:
        fields &= PROMO_PRODUCT_FIELDS
    changes = []
    for field in sorted(fields):
        if field in AUDIT_IGNORED_FIELDS:
            continue
        before = anteriores.get(field)
        after = novos.get(field)
        if _audit_values_equal(model, field, before, after):
            continue
        changes.append({
            'campo': _field_label(model, field),
            'antes': _display_field_value(model, field, before),
            'depois': _display_field_value(model, field, after),
        })
    return changes


def _entry_from_log(log):
    model, label = PROMO_LOG_MODELS.get(log.tabela_afetada, (None, 'Promocao'))
    if not model:
        return None
    changes = _changes_for_log(log, model)
    if model in {Produto, ProdutoFilial} and not changes:
        return None
    if log.acao == LogSistema.Acao.CRIAR:
        acao = f'{label} criado'
        detalhe = _log_detail(changes, 'Registro inicial')
        quantidade = f'{len(changes)} campos' if changes else ''
        kind = 'created'
    elif log.acao == LogSistema.Acao.EXCLUIR:
        acao = f'{label} excluido'
        detalhe = 'Registro excluido ou removido da promocao'
        quantidade = ''
        kind = 'edit'
    elif log.acao == LogSistema.Acao.EDITAR:
        if not changes:
            return None
        if model in {Produto, ProdutoFilial} and not _produto_tinha_preco_promocional(log.dados_anteriores) and _produto_tinha_preco_promocional(log.dados_novos):
            acao = f'{label} criado'
            kind = 'created'
            if model is ProdutoFilial:
                detalhe = 'Preco promocional criado nesta filial.'
        elif model in {Produto, ProdutoFilial} and _produto_tinha_preco_promocional(log.dados_anteriores) and not _produto_tinha_preco_promocional(log.dados_novos):
            acao = f'{label} inativado'
            kind = 'edit'
            if model is ProdutoFilial:
                detalhe = 'Preco promocional inativado nesta filial.'
        else:
            acao = f'{label} editado'
            kind = 'edit'
        detalhe = locals().get('detalhe') or _log_detail(changes, 'Promocao alterada')
        quantidade = f'{len(changes)} campos'
    else:
        acao = log.get_acao_display()
        detalhe = 'Acao registrada'
        quantidade = ''
        kind = 'edit'
    return {
        'data': log.data_hora,
        'usuario': log.usuario.nome if log.usuario else 'Sistema',
        'acao': acao,
        'quantidade': quantidade,
        'detalhes': f'{detalhe} {_registro_referencia(log, model)}',
        'changes': changes,
        'kind': kind,
    }


def promocao_log_entries(request, limit=10, offset=0):
    entries = []
    try:
        queryset = _log_queryset(request)
        for log in queryset:
            try:
                entry = _entry_from_log(log)
            except Exception:
                logger.exception('Falha ao interpretar registro de log de promocao.')
                continue
            if entry:
                entries.append(entry)
    except Exception:
        logger.exception('Falha ao consultar registros de log de promocao.')
        return []
    return entries[offset:offset + limit] if limit is not None else entries


def promocao_log_context(request):
    logs = promocao_log_entries(request, limit=10)
    all_logs = promocao_log_entries(request, limit=None)
    return {
        'cadastro_log_tipo': 'promocoes',
        'cadastro_log_pk': 'tela',
        'cadastro_log_label': 'promocoes',
        'cadastro_log_button_label': 'Log',
        'cadastro_log_title': 'Log',
        'cadastro_log_items': logs,
        'cadastro_log_total': len(all_logs),
        'cadastro_log_next_offset': len(logs),
        'cadastro_log_items_url': reverse('produtos:combo-promocao-log-items'),
        'cadastro_log_export_csv_url': reverse('produtos:combo-promocao-log-export-csv'),
        'cadastro_log_export_pdf_url': reverse('produtos:combo-promocao-log-export-pdf'),
        'cadastro_log_usuarios': sorted({item['usuario'] for item in all_logs if item.get('usuario')}),
        'cadastro_log_campos': sorted({
            change['campo']
            for item in all_logs
            for change in item.get('changes', [])
            if change.get('campo')
        }),
    }


def _export_rows(request):
    rows = []
    for item in promocao_log_entries(request, limit=None):
        data = timezone.localtime(item['data']).strftime('%d/%m/%Y %H:%M') if item.get('data') else ''
        base = [data, item.get('usuario') or '', item.get('acao') or '', item.get('quantidade') or '', item.get('detalhes') or '']
        changes = item.get('changes') or []
        if not changes:
            rows.append(base + ['', '', ''])
            continue
        for change in changes:
            rows.append(base + [change.get('campo') or '', change.get('antes') or '', change.get('depois') or ''])
    return rows


class ComboPromocaoLogItemsView(PermissaoRequiredMixin, View):
    permissao_modulo = 'produtos'
    permissao_acao = 'ver'

    def get(self, request):
        offset = max(int(request.GET.get('offset', 0) or 0), 0)
        limit = min(max(int(request.GET.get('limit', 50) or 50), 1), 50)
        items = promocao_log_entries(request, limit=limit, offset=offset)
        total = len(promocao_log_entries(request, limit=None))
        html = ''.join(
            render_to_string('cadastros/partials/_cadastro_log_item.html', {'item': item}, request=request)
            for item in items
        )
        return JsonResponse({'html': html, 'next_offset': offset + len(items), 'total': total})


class ComboPromocaoLogExportCsvView(PermissaoRequiredMixin, View):
    permissao_modulo = 'produtos'
    permissao_acao = 'ver'

    def get(self, request):
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename="log_promocoes.csv"'
        response.write('\ufeff')
        writer = csv.writer(response, delimiter=';')
        writer.writerow(['Data e hora', 'Usuario', 'Acao', 'Quantidade', 'Detalhe', 'Campo', 'Antes', 'Depois'])
        writer.writerows(_export_rows(request))
        return response


class ComboPromocaoLogExportPdfView(PermissaoRequiredMixin, View):
    permissao_modulo = 'produtos'
    permissao_acao = 'ver'

    def get(self, request):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="log_promocoes.pdf"'
        doc = SimpleDocTemplate(response, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
        styles = getSampleStyleSheet()
        elementos = [
            Paragraph('Log', styles['Title']),
            Paragraph(f'Gerado em {timezone.localtime().strftime("%d/%m/%Y %H:%M")}', styles['Normal']),
            Spacer(1, 10),
        ]
        dados = [['Data/hora', 'Usuario', 'Acao', 'Qtd.', 'Detalhe', 'Campo', 'Antes', 'Depois']]
        dados.extend(_export_rows(request))
        table = Table(dados, repeatRows=1, colWidths=[62, 78, 96, 42, 150, 96, 124, 124])
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
