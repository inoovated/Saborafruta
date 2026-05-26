"""Views de Entrada de Mercadoria."""
from datetime import datetime
import logging
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.db import transaction
from django.db.models import Case, Count, IntegerField, Q, Value, When
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.dateparse import parse_date
from django.utils import timezone
from django.views import View

from apps.cadastros.models import Fornecedor
from apps.compras.forms import (
    AdicionarItemEntradaForm, ConsultarChaveForm, EntradaNFForm, EntradaNFParcelaForm,
    ImportarXMLForm,
)
from apps.compras.models import (
    EntradaNF, EntradaNFParcela, ItemEntradaNF, ItemEntradaNFProdutoGerado, PedidoCompra,
)
from apps.compras.services.compra_service import (
    CompraService,
    ITEM_DIVIDIDO_MANUAL_LOTES,
    ITEM_REMOVIDO_ENTRADA,
)
from apps.compras.services.entrada_custo_service import EntradaCustoService
from apps.compras.services.entrada_financeiro_service import (
    gerar_contas_pagar_da_entrada, validar_geracao_contas_pagar,
)
from apps.compras.services.entrada_estorno_service import calcular_impacto_estorno_entrada, estornar_entrada
from apps.compras.services.entrada_produto_service import (
    criar_produto_e_vincular_item, desvincular_item_de_produto, reprocessar_vinculos_automaticos,
    sugerir_produtos_para_item, vincular_item_a_produto,
)
from apps.compras.services.entrada_xml_service import (
    EntradaXMLDuplicadaError,
    atualizar_equivalencias_fornecedor_xml, criar_fornecedor_por_emitente_xml,
    get_fornecedor_padrao, importar_xml_para_entrada, localizar_fornecedor,
)
from apps.core.models import RegistroAuditoria
from apps.core.services.exceptions import DomainError
from apps.core.services.auditoria import auditoria_para_objeto, registrar_auditoria, snapshot_modelo
from apps.core.services.permissions import PERMISSION_DENIED_MESSAGE, PermissaoRequiredMixin
from apps.estoque.models import Estoque, LoteProduto, MovimentacaoEstoque
from apps.produtos.models import Produto, ProdutoFornecedorEquivalencia
from apps.produtos.services.prontidao_comercial_service import avaliar_entrada_pos_efetivacao

logger = logging.getLogger(__name__)


STATUS_KPI = {
    'rascunho': [EntradaNF.Status.RASCUNHO],
    'aguardando': [
        EntradaNF.Status.AGUARDANDO_VINCULOS,
        EntradaNF.Status.AGUARDANDO_CONFERENCIA,
    ],
    'diferencas': [EntradaNF.Status.COM_DIFERENCAS],
    'efetivadas': [EntradaNF.Status.EFETIVADA],
}


def _decimal_localizado(valor, padrao=Decimal('1')) -> Decimal:
    if valor in (None, ''):
        return padrao
    texto = str(valor).strip().replace(' ', '')
    if ',' in texto:
        texto = texto.replace('.', '').replace(',', '.')
    elif '.' in texto:
        partes = texto.split('.')
        if len(partes) > 1 and all(len(parte) == 3 for parte in partes[1:]) and partes[0].isdigit():
            texto = ''.join(partes)
    return Decimal(texto)


def _parse_data_localizada(valor):
    texto = str(valor or '').strip()
    if not texto:
        return None
    data = parse_date(texto)
    if data:
        return data
    for formato in ('%d/%m/%Y', '%d-%m-%Y'):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def _bool_parametros(data, nome: str, padrao: bool = False) -> bool:
    if nome not in data:
        return padrao
    return str(data.get(nome)).strip().lower() in {'1', 'true', 'on', 'sim'}


def _entrada_aberta(entrada):
    return entrada.status in {
        EntradaNF.Status.RASCUNHO,
        EntradaNF.Status.AGUARDANDO_VINCULOS,
        EntradaNF.Status.AGUARDANDO_CONFERENCIA,
        EntradaNF.Status.COM_DIFERENCAS,
        EntradaNF.Status.CONFERIDA,
    }


def _atualizar_equivalencias_fornecedor(entrada):
    return atualizar_equivalencias_fornecedor_xml(
        entrada.filial,
        entrada.fornecedor,
        entrada.emitente_cnpj_xml,
    )


def _criar_fornecedor_do_xml(entrada) -> Fornecedor:
    return criar_fornecedor_por_emitente_xml(
        entrada.filial,
        {
            'documento': entrada.emitente_cnpj_xml,
            'razao_social': entrada.emitente_razao_social_xml,
            'nome_fantasia': entrada.emitente_nome_fantasia_xml,
            'ie': entrada.emitente_ie_xml,
            'endereco': entrada.emitente_endereco_xml,
            'municipio': entrada.emitente_municipio_xml,
            'uf': entrada.emitente_uf_xml,
            'cep': entrada.emitente_cep_xml,
            'telefone': entrada.emitente_telefone_xml,
        },
        exigir_dados=True,
    )


def _atualizar_diferenca_item(item):
    return CompraService.atualizar_diferenca_item(item)


def _avaliar_diferenca_item_para_tela(item):
    tipo, descricao, bloqueante = CompraService.avaliar_diferenca_item(item)
    item.diferenca_tipo = tipo
    item.diferenca_descricao = descricao
    item.diferenca_bloqueante = bloqueante
    return item


def _liberar_itens_com_equivalencia_removida(entrada):
    if not _entrada_aberta(entrada):
        return 0
    liberados = 0
    itens = entrada.itens.filter(produto__isnull=False).only(
        'id',
        'produto_id',
        'ean_xml',
        'codigo_produto_fornecedor',
        'observacao',
    )
    for item in itens:
        if 'Item removido da entrada.' in (item.observacao or ''):
            continue
        filtro_vinculo = Q()
        if item.codigo_produto_fornecedor:
            filtro_vinculo |= Q(codigo_fornecedor=item.codigo_produto_fornecedor)
        if item.ean_xml:
            filtro_vinculo |= Q(ean_utilizado=item.ean_xml)
        if not filtro_vinculo:
            continue
        equivalencias = ProdutoFornecedorEquivalencia.objects.filter(
            produto_id=item.produto_id,
        ).filter(filtro_vinculo)
        if equivalencias.filter(ativo=False).exists() and not equivalencias.filter(ativo=True).exists():
            desvincular_item_de_produto(item)
            liberados += 1
    if liberados:
        CompraService._atualizar_status_conferencia(entrada)
        entrada.refresh_from_db(fields=['status'])
    return liberados


def _quantidade_recebida_item(item):
    quantidade = item.quantidade_recebida
    if quantidade is None:
        quantidade = item.quantidade_estoque or item.quantidade
    return quantidade or Decimal('0')


def _quantidade_3(valor: Decimal) -> Decimal:
    return Decimal(valor or 0).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)


def _ordenacao_item_conferencia(item):
    identificador = str(item.codigo_produto_fornecedor or item.numero_item or '').strip()
    if identificador.isdigit():
        chave_identificador = (0, int(identificador))
    else:
        chave_identificador = (1, identificador.casefold())
    return (
        chave_identificador,
        str(item.ean_xml or ''),
        str(item.descricao_xml or getattr(item.produto, 'descricao', '') or '').casefold(),
        item.data_validade or datetime.max.date(),
        str(item.numero_lote or '').casefold(),
        item.pk,
    )


def _descricao_sem_codigo_barras_duplicado(descricao, codigo_barras):
    texto = str(descricao or '').strip()
    codigo = ''.join(filter(str.isdigit, str(codigo_barras or '')))
    if not texto or not codigo:
        return texto
    padrao = re.compile(rf'(?<!\d){re.escape(codigo)}(?!\d)')
    if not padrao.search(texto):
        return texto
    texto = padrao.sub(' ', texto)
    texto = re.sub(r'\s+', ' ', texto).strip(' -/|')
    return texto or str(descricao or '').strip()


def _centavos(valor: Decimal) -> Decimal:
    return Decimal(valor or 0).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _permissoes_compras(request):
    usuario = request.user
    return {
        'pode_ver': usuario.tem_permissao('compras', 'ver'),
        'pode_criar': usuario.tem_permissao('compras', 'criar'),
        'pode_editar': usuario.tem_permissao('compras', 'editar'),
        'pode_cancelar': usuario.tem_permissao('compras', 'cancelar'),
        'pode_aprovar': usuario.tem_permissao('compras', 'aprovar'),
        'pode_exportar': usuario.tem_permissao('compras', 'exportar'),
        'pode_gerar_financeiro': usuario.tem_permissao('financeiro', 'criar'),
    }


def _itens_removidos_restauraveis(entrada):
    logs_remocao = list(
        RegistroAuditoria.objects.filter(
            objeto_tipo=entrada._meta.label_lower,
            objeto_id=entrada.pk,
            acao='remover_item',
        )
        .select_related('usuario')
        .order_by('-criado_em')[:30]
    )
    ids_restaurados = _ids_remocoes_restauradas(entrada)

    restauraveis = []
    item_ids_ativos = set(entrada.itens.values_list('pk', flat=True))
    for log in logs_remocao:
        if log.pk in ids_restaurados:
            continue
        item_snapshot = (log.metadados or {}).get('item_removido') or {}
        if not item_snapshot:
            continue
        item_id = item_snapshot.get('id')
        if item_id in item_ids_ativos:
            continue
        item_snapshot = {
            **item_snapshot,
            'descricao_display': (
                item_snapshot.get('descricao_xml')
                or item_snapshot.get('produto_descricao')
                or item_snapshot.get('produto')
                or 'Item removido'
            ),
            'quantidade_xml_display': item_snapshot.get('quantidade_xml') or '0',
            'unidade_xml_display': item_snapshot.get('unidade_xml') or '',
            'numero_lote_display': item_snapshot.get('numero_lote') or '',
        }
        log.item_removido = item_snapshot
        restauraveis.append(log)
    return restauraveis


def _ids_remocoes_restauradas(entrada) -> set[int]:
    ids_restaurados = set()
    for log in RegistroAuditoria.objects.filter(
        objeto_tipo=entrada._meta.label_lower,
        objeto_id=entrada.pk,
        acao='restaurar_item',
    ).only('metadados'):
        metadados = log.metadados or {}
        item_removido_log_id = metadados.get('item_removido_log_id')
        if item_removido_log_id:
            ids_restaurados.add(item_removido_log_id)
        for item_log_id in metadados.get('item_removido_log_ids') or []:
            ids_restaurados.add(item_log_id)
    return ids_restaurados


def _chave_item_dividido_snapshot(snapshot: dict) -> tuple:
    return (
        str(snapshot.get('numero_item') or ''),
        str(snapshot.get('produto') or snapshot.get('produto_id') or ''),
        str(snapshot.get('ean_xml') or ''),
        str(snapshot.get('codigo_produto_fornecedor') or ''),
        str(snapshot.get('descricao_xml') or ''),
    )


def _snapshot_item(item) -> dict:
    return {
        'numero_item': item.numero_item,
        'produto_id': item.produto_id,
        'ean_xml': item.ean_xml,
        'cfop_xml': getattr(item, 'cfop_xml', ''),
        'codigo_produto_fornecedor': item.codigo_produto_fornecedor,
        'descricao_xml': item.descricao_xml,
    }


def _itens_ativos_sem_produto(entrada):
    return (
        entrada.itens
        .filter(produto__isnull=True, quantidade_recebida__gt=0)
        .exclude(produtos_gerados__isnull=False)
        .exclude(observacao__icontains=ITEM_REMOVIDO_ENTRADA)
        .distinct()
    )


def _item_tem_vinculo_estoque(item) -> bool:
    if item.produto_id:
        return True
    prefetched = getattr(item, '_prefetched_objects_cache', {})
    if 'produtos_gerados' in prefetched:
        return bool(prefetched['produtos_gerados'])
    return item.produtos_gerados.exists()


def _logs_remocao_por_item(entrada) -> dict[int, RegistroAuditoria]:
    ids_restaurados = _ids_remocoes_restauradas(entrada)
    logs_por_item = {}
    for log in RegistroAuditoria.objects.filter(
        objeto_tipo=entrada._meta.label_lower,
        objeto_id=entrada.pk,
        acao='remover_item',
    ).order_by('-criado_em'):
        if log.pk in ids_restaurados:
            continue
        item_snapshot = (log.metadados or {}).get('item_removido') or {}
        item_id = item_snapshot.get('id')
        if item_id and item_id not in logs_por_item:
            logs_por_item[item_id] = log
    return logs_por_item


def _aplicar_estado_remocao_itens(entrada, itens):
    logs_por_item = _logs_remocao_por_item(entrada)
    grupos_divididos = {}
    for item in itens:
        item.remocao_log = logs_por_item.get(item.pk)
        item.item_snapshot_remocao = (
            (item.remocao_log.metadados or {}).get('item_removido') or {}
            if item.remocao_log
            else {}
        )
        item.item_removido = ITEM_REMOVIDO_ENTRADA in (item.observacao or '')
        item.dividido_manual_lotes = (
            ITEM_DIVIDIDO_MANUAL_LOTES in (item.observacao or '')
            or ITEM_DIVIDIDO_MANUAL_LOTES in (item.item_snapshot_remocao.get('observacao') or '')
        )
        item.ocultar_linha_removida = False
        item.item_removido_grupo_original = False
        if item.item_removido and item.remocao_log is None:
            item.ocultar_linha_removida = True
            continue
        if item.dividido_manual_lotes:
            chave = _chave_item_dividido_snapshot(
                item.item_snapshot_remocao
                if item.item_snapshot_remocao
                else _snapshot_item(item)
            )
            grupos_divididos.setdefault(chave, []).append(item)

    for grupo in grupos_divididos.values():
        if len(grupo) <= 1:
            continue
        if not all(item.item_removido and item.remocao_log for item in grupo):
            continue
        grupo = sorted(grupo, key=lambda item: item.pk)
        representante = grupo[0]
        snapshots = [item.item_snapshot_remocao for item in grupo if item.item_snapshot_remocao]
        representante.item_removido_grupo_original = True
        representante.quantidade_xml_original_grupo = sum(
            (_decimal_localizado(snapshot.get('quantidade_xml'), Decimal('0')) for snapshot in snapshots),
            Decimal('0'),
        )
        representante.quantidade_recebida_original_grupo = sum(
            (_decimal_localizado(snapshot.get('quantidade_recebida'), Decimal('0')) for snapshot in snapshots),
            Decimal('0'),
        )
        representante.valor_total_original_grupo = sum(
            (_decimal_localizado(snapshot.get('valor_total'), Decimal('0')) for snapshot in snapshots),
            Decimal('0'),
        )
        lotes = [
            str(snapshot.get('numero_lote')).strip()
            for snapshot in snapshots
            if str(snapshot.get('numero_lote') or '').strip()
        ]
        representante.lotes_grupo_display = ', '.join(dict.fromkeys(lotes))
        for item in grupo[1:]:
            item.ocultar_linha_removida = True


def _logs_grupo_divisao_removida(entrada, item_snapshot: dict) -> list[RegistroAuditoria]:
    if not item_snapshot:
        return []
    chave = _chave_item_dividido_snapshot(item_snapshot)
    ids_restaurados = _ids_remocoes_restauradas(entrada)
    itens_por_id = {item.pk: item for item in entrada.itens.all()}
    logs = []
    for log in RegistroAuditoria.objects.filter(
        objeto_tipo=entrada._meta.label_lower,
        objeto_id=entrada.pk,
        acao='remover_item',
    ).order_by('pk'):
        if log.pk in ids_restaurados:
            continue
        snapshot = (log.metadados or {}).get('item_removido') or {}
        if _chave_item_dividido_snapshot(snapshot) != chave:
            continue
        item = itens_por_id.get(snapshot.get('id'))
        if item is None or ITEM_REMOVIDO_ENTRADA in (item.observacao or '') or item.quantidade_recebida <= 0:
            logs.append(log)
    return logs


def _itens_grupo_divisao_manual(entrada, item):
    if ITEM_DIVIDIDO_MANUAL_LOTES not in (item.observacao or ''):
        return [item]
    chave = _chave_item_dividido_snapshot(_snapshot_item(item))
    itens = []
    for candidato in entrada.itens.select_related('produto').all():
        if ITEM_DIVIDIDO_MANUAL_LOTES not in (candidato.observacao or ''):
            continue
        if ITEM_REMOVIDO_ENTRADA in (candidato.observacao or ''):
            continue
        if _chave_item_dividido_snapshot(_snapshot_item(candidato)) == chave:
            itens.append(candidato)
    return sorted(itens or [item], key=lambda item_grupo: item_grupo.pk)


def _auditar_entrada(request, acao, entrada, descricao='', justificativa='', antes=None, depois=None, relacionado=None, metadados=None):
    return registrar_auditoria(
        request=request,
        modulo='compras',
        acao=acao,
        objeto=entrada,
        descricao=descricao or f'NF {entrada.numero_nf}/{entrada.serie_nf}',
        justificativa=justificativa,
        antes=antes,
        depois=depois,
        relacionado=relacionado,
        metadados=metadados,
    )


def _snapshot_produtos_gerados(item):
    return [
        {
            'id': linha.pk,
            'produto_id': linha.produto_id,
            'produto': str(linha.produto),
            'ordem': linha.ordem,
            'quantidade': str(linha.quantidade),
            'unidade_estoque': linha.unidade_estoque,
            'numero_lote': linha.numero_lote,
            'data_validade': linha.data_validade.isoformat() if linha.data_validade else '',
            'custo_percentual': str(linha.custo_percentual) if linha.custo_percentual is not None else '',
            'observacao': linha.observacao,
        }
        for linha in item.produtos_gerados.select_related('produto').all()
    ]


def _redirect_entrada_duplicada(request, entrada: EntradaNF, origem: str = 'xml'):
    messages.warning(
        request,
        f'Esta nota ja existe nesta filial. Abrimos a NF {entrada.numero_nf}/{entrada.serie_nf} para voce revisar, continuar ou cancelar.',
    )
    return redirect(f"{reverse('compras:entrada-detail', args=[entrada.pk])}?duplicada={origem}")


class EntradaNFListView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    template_name = 'compras/entrada/list.html'

    def get(self, request):
        base_qs = EntradaNF.objects.for_filial(request.filial_ativa).select_related(
            'fornecedor', 'pedido_compra', 'usuario',
        ).annotate(
            total_itens=Count('itens', distinct=True),
            sem_produto_count=Count('itens', filter=Q(itens__produto__isnull=True), distinct=True),
            divergencias_count=Count(
                'itens',
                filter=Q(itens__diferenca_tipo__gt=''),
                distinct=True,
            ),
            divergencias_bloqueantes_count=Count(
                'itens',
                filter=Q(itens__diferenca_bloqueante=True),
                distinct=True,
            ),
            lote_pendente_count=Count(
                'itens',
                filter=(
                    Q(itens__produto__controla_lote=True, itens__numero_lote='')
                    | Q(itens__produto__controla_validade=True, itens__data_validade__isnull=True)
                ),
                distinct=True,
            ),
        )
        qs = base_qs
        busca = request.GET.get('q', '').strip()
        status = request.GET.get('status', '')
        origem = request.GET.get('origem', '')
        grupo = request.GET.get('grupo', 'abertas')
        pendencia = request.GET.get('pendencia', '')
        if busca:
            qs = qs.filter(
                Q(numero_nf__icontains=busca)
                | Q(chave_acesso_nf__icontains=busca)
                | Q(fornecedor__razao_social__icontains=busca)
                | Q(fornecedor__nome_fantasia__icontains=busca)
                | Q(fornecedor__cpf_cnpj__icontains=busca)
                | Q(emitente_razao_social_xml__icontains=busca)
                | Q(emitente_cnpj_xml__icontains=busca)
                | Q(itens__descricao_xml__icontains=busca)
                | Q(itens__ean_xml__icontains=busca)
                | Q(itens__codigo_produto_fornecedor__icontains=busca)
                | Q(itens__produto__descricao__icontains=busca)
                | Q(itens__produto__codigo__icontains=busca)
                | Q(itens__produto__codigo_barras__icontains=busca)
            )
        if status:
            qs = qs.filter(status=status)
        if origem:
            qs = qs.filter(origem_entrada=origem)
        if grupo == 'abertas':
            qs = qs.exclude(status__in=[
                EntradaNF.Status.EFETIVADA,
                EntradaNF.Status.CANCELADA,
                EntradaNF.Status.ESTORNADA,
            ])
        elif grupo == 'historico':
            qs = qs.filter(status__in=[
                EntradaNF.Status.EFETIVADA,
                EntradaNF.Status.CANCELADA,
                EntradaNF.Status.ESTORNADA,
            ])
        if pendencia == 'fornecedor':
            qs = qs.filter(fornecedor_pendente=True)
        elif pendencia == 'sem_produto':
            qs = qs.filter(itens__produto__isnull=True)
        elif pendencia == 'divergencia':
            qs = qs.filter(itens__diferenca_tipo__gt='')
        elif pendencia == 'lote':
            qs = qs.filter(
                Q(itens__produto__controla_lote=True, itens__numero_lote='')
                | Q(itens__produto__controla_validade=True, itens__data_validade__isnull=True)
            )
        elif pendencia == 'custo':
            qs = qs.filter(
                itens__produto__isnull=False,
                itens__quantidade_recebida__gt=0,
                itens__custo_unitario_total__lte=0,
            )
        qs = qs.distinct()

        agregados = base_qs.values('status').annotate(total=Count('id'))
        totais_status = {item['status']: item['total'] for item in agregados}
        kpis = {
            chave: sum(totais_status.get(status_item, 0) for status_item in status_list)
            for chave, status_list in STATUS_KPI.items()
        }
        pendencias_totais = {
            'fornecedor': base_qs.filter(fornecedor_pendente=True).count(),
            'sem_produto': base_qs.filter(itens__produto__isnull=True).distinct().count(),
            'divergencia': base_qs.filter(itens__diferenca_tipo__gt='').distinct().count(),
            'lote': base_qs.filter(
                Q(itens__produto__controla_lote=True, itens__numero_lote='')
                | Q(itens__produto__controla_validade=True, itens__data_validade__isnull=True)
            ).distinct().count(),
            'custo': base_qs.filter(
                itens__produto__isnull=False,
                itens__quantidade_recebida__gt=0,
                itens__custo_unitario_total__lte=0,
            ).distinct().count(),
        }
        grupo_totais = {
            'abertas': base_qs.exclude(status__in=[
                EntradaNF.Status.EFETIVADA,
                EntradaNF.Status.CANCELADA,
                EntradaNF.Status.ESTORNADA,
            ]).count(),
            'historico': base_qs.filter(status__in=[
                EntradaNF.Status.EFETIVADA,
                EntradaNF.Status.CANCELADA,
                EntradaNF.Status.ESTORNADA,
            ]).count(),
        }

        page_obj = Paginator(qs.order_by('-data_entrada'), 25).get_page(request.GET.get('page'))
        entradas = list(page_obj.object_list)
        _preparar_entradas_para_lista(entradas)
        return render(request, self.template_name, {
            'page_obj': page_obj,
            'entradas': entradas,
            'busca': busca,
            'status': status,
            'origem': origem,
            'grupo': grupo,
            'pendencia': pendencia,
            'status_choices': EntradaNF.Status.choices,
            'origem_choices': EntradaNF.OrigemEntrada.choices,
            'kpis': kpis,
            'pendencias_totais': pendencias_totais,
            'grupo_totais': grupo_totais,
            'permissoes_compras': _permissoes_compras(request),
        })


def _preparar_entradas_para_lista(entradas):
    for entrada in entradas:
        pendencias = []
        custo_critico_count = _custo_critico_lista_count(entrada)
        entrada.custo_critico_count = custo_critico_count

        if entrada.fornecedor_pendente:
            pendencias.append({
                'chave': 'fornecedor',
                'label': 'Fornecedor pendente',
                'classe': 'is-amber',
                'total': 1,
            })
        if entrada.sem_produto_count:
            pendencias.append({
                'chave': 'sem_produto',
                'label': f'{entrada.sem_produto_count} sem produto',
                'classe': 'is-red',
                'total': entrada.sem_produto_count,
            })
        if entrada.divergencias_count:
            pendencias.append({
                'chave': 'divergencia',
                'label': f'{entrada.divergencias_count} divergencia(s)',
                'classe': 'is-red' if entrada.divergencias_bloqueantes_count else 'is-amber',
                'total': entrada.divergencias_count,
            })
        if entrada.lote_pendente_count:
            pendencias.append({
                'chave': 'lote',
                'label': f'{entrada.lote_pendente_count} lote/validade',
                'classe': 'is-red',
                'total': entrada.lote_pendente_count,
            })
        if custo_critico_count:
            pendencias.append({
                'chave': 'custo',
                'label': f'{custo_critico_count} custo critico',
                'classe': 'is-red',
                'total': custo_critico_count,
            })
        if entrada.destinatario_documento_diferente:
            pendencias.append({
                'chave': 'documento',
                'label': 'Documento em alerta',
                'classe': 'is-blue',
                'total': 1,
            })

        entrada.pendencias_lista = pendencias
        entrada.tem_pendencia_bloqueante = bool(
            entrada.sem_produto_count
            or entrada.divergencias_bloqueantes_count
            or entrada.lote_pendente_count
            or custo_critico_count
        )
        entrada.grupo_operacional = (
            'Historico'
            if entrada.status in (
                EntradaNF.Status.EFETIVADA,
                EntradaNF.Status.CANCELADA,
                EntradaNF.Status.ESTORNADA,
            )
            else 'Aberta'
        )
        entrada.proxima_acao = _proxima_acao_entrada(entrada)


def _custo_critico_lista_count(entrada) -> int:
    if entrada.status in (
        EntradaNF.Status.EFETIVADA,
        EntradaNF.Status.CANCELADA,
        EntradaNF.Status.ESTORNADA,
    ):
        return 0
    return entrada.itens.filter(
        produto__isnull=False,
        quantidade_recebida__gt=0,
        custo_unitario_total__lte=0,
    ).count()


def _proxima_acao_entrada(entrada):
    if entrada.status == EntradaNF.Status.EFETIVADA:
        return {
            'label': 'Ver resultado',
            'hint': 'Movimentos, lotes e custos gravados.',
            'url': reverse_lazy('compras:entrada-detail', kwargs={'pk': entrada.pk}),
            'classe': 'btn-table-blue',
            'requer': 'ver',
        }
    if entrada.status in (EntradaNF.Status.CANCELADA, EntradaNF.Status.ESTORNADA):
        return {
            'label': 'Ver auditoria',
            'hint': 'Nota fechada sem acao operacional.',
            'url': reverse_lazy('compras:entrada-detail', kwargs={'pk': entrada.pk}),
            'classe': 'btn-table-slate',
            'requer': 'ver',
        }
    if entrada.fornecedor_pendente:
        return {
            'label': 'Resolver fornecedor',
            'hint': 'Vincule ou cadastre o fornecedor do XML.',
            'url': reverse_lazy('compras:entrada-fornecedor-pendente', kwargs={'pk': entrada.pk}),
            'classe': 'btn-table-slate',
            'requer': 'editar',
        }
    if entrada.sem_produto_count:
        return {
            'label': 'Vincular produtos',
            'hint': 'Associe itens da nota ao cadastro interno.',
            'url': reverse_lazy('compras:entrada-conferencia', kwargs={'pk': entrada.pk}),
            'classe': 'btn-table-red',
            'requer': 'editar',
        }
    if entrada.lote_pendente_count:
        return {
            'label': 'Preencher lote',
            'hint': 'Complete lote e validade obrigatorios.',
            'url': reverse_lazy('compras:entrada-conferencia', kwargs={'pk': entrada.pk}),
            'classe': 'btn-table-red',
            'requer': 'editar',
        }
    if entrada.divergencias_count:
        return {
            'label': 'Resolver divergencias',
            'hint': 'Revise quantidade fisica e justificativas.',
            'url': reverse_lazy('compras:entrada-diferencas', kwargs={'pk': entrada.pk}),
            'classe': 'btn-table-slate',
            'requer': 'editar',
        }
    if entrada.custo_critico_count:
        return {
            'label': 'Revisar custos',
            'hint': 'Corrija custo antes de efetivar.',
            'url': reverse_lazy('compras:entrada-custos', kwargs={'pk': entrada.pk}),
            'classe': 'btn-table-red',
            'requer': 'editar',
        }
    if entrada.status in (EntradaNF.Status.CONFERIDA, EntradaNF.Status.COM_DIFERENCAS):
        return {
            'label': 'Revisar finalizacao',
            'hint': 'Confira resumo final antes de efetivar.',
            'url': reverse_lazy('compras:entrada-finalizacao', kwargs={'pk': entrada.pk}),
            'classe': 'btn-table-blue',
            'requer': 'aprovar',
        }
    if entrada.status == EntradaNF.Status.RASCUNHO:
        return {
            'label': 'Continuar cadastro',
            'hint': 'Inclua ou revise itens da entrada.',
            'url': reverse_lazy('compras:entrada-detail', kwargs={'pk': entrada.pk}),
            'classe': 'btn-table-blue',
            'requer': 'editar',
        }
    return {
        'label': 'Conferir',
        'hint': 'Revise produtos, quantidade, lote e validade.',
        'url': reverse_lazy('compras:entrada-conferencia', kwargs={'pk': entrada.pk}),
        'classe': 'btn-table-blue',
        'requer': 'editar',
    }


class EntradaNFLocalizarNotaView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    template_name = 'compras/entrada/localizar_nota.html'

    def get(self, request):
        return render(request, self.template_name, {
            'permissoes_compras': _permissoes_compras(request),
        })


class EntradaNFImportarXMLView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'criar'
    template_name = 'compras/entrada/importar_xml.html'

    def get(self, request):
        return render(request, self.template_name, {'form': ImportarXMLForm()})

    def post(self, request):
        form = ImportarXMLForm(request.POST, request.FILES)
        if form.is_valid():
            arquivo = form.cleaned_data['arquivo_xml']
            raw = arquivo.read()
            try:
                xml_texto = raw.decode('utf-8')
            except UnicodeDecodeError:
                xml_texto = raw.decode('latin1')
            try:
                entrada = importar_xml_para_entrada(
                    xml_texto=xml_texto,
                    filial=request.filial_ativa,
                    usuario=request.user,
                    nome_arquivo=arquivo.name,
                )
                _auditar_entrada(
                    request,
                    'criar',
                    entrada,
                    'XML importado para entrada de mercadoria',
                    metadados={'arquivo': arquivo.name, 'origem': 'xml'},
                    depois=snapshot_modelo(entrada),
                )
                messages.success(request, f'XML importado. NF {entrada.numero_nf} pronta para conferencia.')
                return redirect('compras:entrada-conferencia', pk=entrada.pk)
            except DomainError as exc:
                if isinstance(exc, EntradaXMLDuplicadaError):
                    return _redirect_entrada_duplicada(request, exc.entrada, origem='xml')
                messages.error(request, str(exc))
        return render(request, self.template_name, {'form': form})


class EntradaNFConsultarChaveView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'criar'
    template_name = 'compras/entrada/consultar_chave.html'

    def get(self, request):
        return render(request, self.template_name, {'form': ConsultarChaveForm()})

    def post(self, request):
        form = ConsultarChaveForm(request.POST)
        if form.is_valid():
            chave = form.cleaned_data['chave_acesso']
            entrada_existente = (
                EntradaNF.objects.for_filial(request.filial_ativa)
                .filter(chave_acesso_nf=chave)
                .exclude(status__in=[EntradaNF.Status.CANCELADA, EntradaNF.Status.ESTORNADA])
                .first()
            )
            if entrada_existente:
                return _redirect_entrada_duplicada(request, entrada_existente, origem='chave')
            cnpj_emitente = chave[6:20]
            fornecedor, fornecedor_pendente = localizar_fornecedor(request.filial_ativa, cnpj_emitente)
            entrada = CompraService.criar_entrada_nf(
                filial=request.filial_ativa,
                usuario=request.user,
                fornecedor=fornecedor,
                numero_nf=chave[25:34].lstrip('0') or chave[25:34],
                serie_nf=chave[22:25].lstrip('0') or '1',
                data_emissao_nf=timezone.localdate(),
                chave_acesso_nf=chave,
                origem_entrada=EntradaNF.OrigemEntrada.CHAVE,
                fornecedor_pendente=fornecedor_pendente,
                dados_emitente_xml={'documento': cnpj_emitente},
                observacao='Criada pela chave de acesso. Consulta DF-e real ainda pendente.',
            )
            _auditar_entrada(
                request,
                'criar',
                entrada,
                'Entrada criada por chave de acesso',
                metadados={'chave': chave, 'origem': 'chave'},
                depois=snapshot_modelo(entrada),
            )
            messages.warning(
                request,
                'Chave registrada. Como a consulta SEFAZ real ainda esta em preparacao, confira ou preencha os itens manualmente.',
            )
            return redirect('compras:entrada-detail', pk=entrada.pk)
        return render(request, self.template_name, {'form': form})


class EntradaNFCreateView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'criar'
    template_name = 'compras/entrada/criar.html'

    def get(self, request):
        initial = {}
        if request.GET.get('chave'):
            initial['chave_acesso_nf'] = request.GET['chave']
        pedido_selecionado = None
        if request.GET.get('pedido_compra'):
            pedido_selecionado = (
                PedidoCompra.objects
                .for_filial(request.filial_ativa)
                .filter(pk=request.GET.get('pedido_compra'))
                .first()
            )
            if pedido_selecionado:
                initial['pedido_compra'] = pedido_selecionado.pk
                initial['fornecedor'] = pedido_selecionado.fornecedor_id
        return render(request, self.template_name, {
            'form': EntradaNFForm(initial=initial, filial=request.filial_ativa),
            'title': 'Entrada manual',
            'cancel_url': reverse_lazy('compras:entrada-list'),
            'pedido_selecionado': pedido_selecionado,
        })

    def post(self, request):
        form = EntradaNFForm(request.POST, filial=request.filial_ativa)
        if form.is_valid():
            try:
                fornecedor = form.cleaned_data.get('fornecedor')
                fornecedor_pendente = False
                if not fornecedor:
                    fornecedor = get_fornecedor_padrao(request.filial_ativa)
                    fornecedor_pendente = True
                entrada = CompraService.criar_entrada_nf(
                    filial=request.filial_ativa,
                    usuario=request.user,
                    fornecedor=fornecedor,
                    numero_nf=form.cleaned_data['numero_nf'],
                    serie_nf=form.cleaned_data.get('serie_nf') or '1',
                    data_emissao_nf=form.cleaned_data['data_emissao_nf'],
                    chave_acesso_nf=form.cleaned_data.get('chave_acesso_nf', ''),
                    pedido_compra=form.cleaned_data.get('pedido_compra'),
                    observacao=form.cleaned_data.get('observacao', ''),
                    origem_entrada=EntradaNF.OrigemEntrada.MANUAL,
                    fornecedor_pendente=fornecedor_pendente,
                )
                for campo in ('tipo', 'valor_frete', 'valor_seguro', 'valor_outras_despesas'):
                    setattr(entrada, campo, form.cleaned_data.get(campo) or 0)
                entrada.save()
                _auditar_entrada(
                    request,
                    'criar',
                    entrada,
                    'Entrada manual criada',
                    metadados={'origem': 'manual'},
                    depois=snapshot_modelo(entrada),
                )
                messages.success(request, f'Entrada NF {entrada.numero_nf} criada. Adicione os itens.')
                return redirect('compras:entrada-detail', pk=entrada.pk)
            except DomainError as e:
                messages.error(request, str(e))
        return render(request, self.template_name, {
            'form': form,
            'title': 'Entrada manual',
            'cancel_url': reverse_lazy('compras:entrada-list'),
        })


class EntradaNFDetailView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    template_name = 'compras/entrada/detail.html'
    fallback_template_name = 'compras/entrada/detail_fallback.html'

    def dispatch(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        if pk and not EntradaNF.objects.for_filial(request.filial_ativa).filter(pk=pk).exists():
            entrada_existe = EntradaNF.objects.select_related('filial').filter(pk=pk).first()
            if entrada_existe:
                messages.warning(
                    request,
                    (
                        'Esta entrada pertence a outra filial. Voce foi direcionado '
                        'para as entradas da filial ativa para evitar editar a nota no contexto errado.'
                    ),
                )
                return redirect(f"{reverse('compras:entrada-list')}?fora_filial=1")
        return super().dispatch(request, *args, **kwargs)

    def get_entrada(self, request, pk):
        return get_object_or_404(
            EntradaNF.objects.for_filial(request.filial_ativa)
            .select_related('fornecedor', 'pedido_compra', 'usuario', 'usuario_efetivacao', 'usuario_estorno'),
            pk=pk,
        )

    def get(self, request, pk):
        entrada = self.get_entrada(request, pk)
        if _entrada_aberta(entrada):
            try:
                CompraService.corrigir_restauracoes_lote_dividido(entrada)
            except Exception:
                logger.exception(
                    'Falha ao corrigir restauracoes de lote dividido na entrada',
                    extra={'entrada_id': entrada.pk},
                )
        itens = []
        try:
            itens = list(entrada.itens.select_related('produto', 'produto__unidade_medida', 'lote_gerado').all())
        except Exception:
            logger.exception(
                'Falha ao carregar itens da entrada',
                extra={'entrada_id': entrada.pk},
            )
        try:
            logs_restauraveis = _itens_removidos_restauraveis(entrada)
        except Exception:
            logger.exception(
                'Falha ao carregar itens removidos restauraveis da entrada',
                extra={'entrada_id': entrada.pk},
            )
            logs_restauraveis = []
        try:
            _aplicar_estado_remocao_itens(entrada, itens)
        except Exception:
            logger.exception(
                'Falha ao aplicar estado de remocao nos itens da entrada',
                extra={'entrada_id': entrada.pk},
            )
        for item in itens:
            item.quantidade_movimenta = _quantidade_recebida_item(item)
            item.item_recusado = (
                item.quantidade_movimenta <= 0
                and bool(item.justificativa_diferenca)
            )
            if item.produto_id:
                item.extrato_produto_url = (
                    f"{reverse('estoque:movimentacao-list')}?produto={item.produto_id}"
                )
                item.movimentacoes_nota_url = _movimentacoes_entrada_url(entrada)
        prontidao_pos_entrada = None
        resultado_efetivacao = None
        try:
            resultado_efetivacao = _resultado_efetivacao_entrada(request, entrada, itens)
        except Exception:
            logger.exception(
                'Falha ao montar resultado de efetivacao da entrada',
                extra={'entrada_id': entrada.pk},
            )
        if entrada.status in (EntradaNF.Status.EFETIVADA, EntradaNF.Status.ESTORNADA):
            try:
                prontidao_pos_entrada = avaliar_entrada_pos_efetivacao(entrada, itens)
            except Exception:
                logger.exception(
                    'Falha ao montar prontidao comercial pos-entrada',
                    extra={'entrada_id': entrada.pk},
                )
        try:
            auditoria_entrada = list(auditoria_para_objeto(entrada, limit=12))
        except Exception:
            logger.exception(
                'Falha ao carregar auditoria da entrada',
                extra={'entrada_id': entrada.pk},
            )
            auditoria_entrada = []
        try:
            permissoes_compras = _permissoes_compras(request)
        except Exception:
            logger.exception(
                'Falha ao carregar permissoes de compras no detalhe da entrada',
                extra={'entrada_id': entrada.pk},
            )
            permissoes_compras = {}
        try:
            entrada_proxima_acao = _proxima_acao_entrada(entrada)
        except AttributeError:
            entrada_proxima_acao = {
                'url': reverse_lazy('compras:entrada-conferencia', kwargs={'pk': entrada.pk}),
            }
        context = {
            'entrada': entrada,
            'itens': itens,
            'resultado_efetivacao': resultado_efetivacao,
            'prontidao_pos_entrada': prontidao_pos_entrada,
            'auditoria_entrada': auditoria_entrada,
            'itens_removidos_restauraveis': logs_restauraveis,
            'permissoes_compras': permissoes_compras,
            'entrada_alerta_duplicada': (
                request.GET.get('duplicada') in {'xml', 'chave'}
                and entrada.status == EntradaNF.Status.EFETIVADA
            ),
            'entrada_alerta_em_andamento': (
                request.GET.get('duplicada') in {'xml', 'chave'}
                and _entrada_aberta(entrada)
            ),
            'entrada_pode_cancelar': entrada.pode_cancelar,
            'entrada_pode_estornar': entrada.pode_estornar,
            'entrada_aberta': _entrada_aberta(entrada),
            'entrada_proxima_acao': entrada_proxima_acao,
        }
        try:
            return render(request, self.template_name, context)
        except Exception as exc:
            return self.render_fallback(request, entrada, exc)

    def render_fallback(self, request, entrada, exc):
        logger.exception(
            'Falha ao renderizar detalhe completo da entrada',
            extra={'entrada_id': entrada.pk},
        )
        context = {
            'entrada': entrada,
            'erro_tecnico': str(exc),
            'entrada_aberta': _entrada_aberta(entrada),
        }
        try:
            return render(request, self.fallback_template_name, context, status=200)
        except Exception:
            logger.exception(
                'Falha ao renderizar fallback do detalhe da entrada',
                extra={'entrada_id': entrada.pk},
            )
            return HttpResponse(
                (
                    '<!doctype html><html><head><meta charset="utf-8">'
                    '<title>Entrada de NF</title></head><body>'
                    f'<h1>Entrada NF {entrada.numero_nf}/{entrada.serie_nf}</h1>'
                    '<p>A tela principal nao pode ser carregada agora, '
                    'mas a entrada foi localizada.</p>'
                    f'<p>Status: {entrada.get_status_display()}</p>'
                    '<p><a href="/compras/entradas/">Voltar para entradas</a></p>'
                    '</body></html>'
                ),
                status=200,
            )


class EntradaNFConferenciaView(EntradaNFDetailView):
    template_name = 'compras/entrada/conferencia.html'
    fallback_template_name = 'compras/entrada/conferencia_fallback.html'

    def get(self, request, pk):
        entrada = self.get_entrada(request, pk)
        try:
            _liberar_itens_com_equivalencia_removida(entrada)
        except Exception:
            logger.exception(
                'Falha ao liberar itens com equivalencia removida na conferencia',
                extra={'entrada_id': entrada.pk},
            )
        if _entrada_aberta(entrada):
            try:
                reprocessar_vinculos_automaticos(entrada)
            except Exception:
                logger.exception(
                    'Falha ao reprocessar vinculos automaticos na conferencia',
                    extra={'entrada_id': entrada.pk},
                )
            try:
                CompraService.corrigir_restauracoes_lote_dividido(entrada)
            except Exception:
                logger.exception(
                    'Falha ao corrigir restauracoes de lote dividido na conferencia',
                    extra={'entrada_id': entrada.pk},
                )
            try:
                entrada.refresh_from_db(fields=['status'])
            except Exception:
                logger.exception(
                    'Falha ao atualizar status da entrada na conferencia',
                    extra={'entrada_id': entrada.pk},
                )
        try:
            itens = list(
                entrada.itens
                .select_related('produto', 'produto__unidade_medida')
                .prefetch_related('produtos_gerados__produto', 'produtos_gerados__produto__unidade_medida')
                .all()
            )
        except Exception:
            logger.exception(
                'Falha ao carregar itens da conferencia',
                extra={'entrada_id': entrada.pk},
            )
            itens = []
        try:
            logs_restauraveis = _itens_removidos_restauraveis(entrada)
        except Exception:
            logger.exception(
                'Falha ao carregar itens removidos restauraveis da conferencia',
                extra={'entrada_id': entrada.pk},
            )
            logs_restauraveis = []
        try:
            _aplicar_estado_remocao_itens(entrada, itens)
        except Exception:
            logger.exception(
                'Falha ao aplicar estado de remocao na conferencia',
                extra={'entrada_id': entrada.pk},
            )
        custo_por_item = {}
        custos_criticos = set()
        try:
            composicao_custo = EntradaCustoService.compor(
                entrada=entrada,
                metodo_rateio=entrada.custo_rateio_metodo,
                incluir_ipi=entrada.custo_incluir_ipi,
                incluir_icms_st=entrada.custo_incluir_icms_st,
                incluir_icms=entrada.custo_incluir_icms,
                custo_financeiro=entrada.custo_financeiro or Decimal('0'),
                usar_apenas_valor_nota=entrada.custo_usar_apenas_valor_nota,
            )
            custo_por_item = {
                linha.item.pk: linha
                for linha in composicao_custo.get('linhas', [])
            }
            custos_criticos = {
                linha.item.pk
                for linha in composicao_custo.get('alertas_custo', [])
                if linha.alerta_custo_nivel == 'critico'
            }
        except DomainError:
            composicao_custo = None
        except Exception:
            logger.exception(
                'Falha ao compor custo da conferencia',
                extra={'entrada_id': entrada.pk},
            )
            composicao_custo = None
        resumo_status = {
            'vinculados': 0,
            'varios_produtos': 0,
            'sem_produto': 0,
            'divergencias': 0,
            'lote_pendente': 0,
        }
        itens_mobile = []
        for item in itens:
            try:
                if item.ocultar_linha_removida:
                    continue
                item.codigo_barras_display = item.ean_xml
                if not item.codigo_barras_display and item.produto_id:
                    item.codigo_barras_display = item.produto.codigo_barras or ''
                    if not item.codigo_barras_display:
                        codigo_barras = item.produto.codigos_barras.filter(ativo=True).order_by('pk').first()
                        item.codigo_barras_display = codigo_barras.ean if codigo_barras else ''
                item.descricao_xml_display = _descricao_sem_codigo_barras_duplicado(
                    item.descricao_xml,
                    item.codigo_barras_display,
                )
                item.produtos_gerados_lista = list(item.produtos_gerados.all())
                item.recebe_varios_produtos = bool(item.produtos_gerados_lista)
                item.produtos_gerados_total = sum(
                    (linha.quantidade for linha in item.produtos_gerados_lista),
                    Decimal('0'),
                )
                item.produtos_gerados_count = len(item.produtos_gerados_lista)
                item.produtos_gerados_custo_percentual = sum(
                    (
                        linha.custo_percentual
                        for linha in item.produtos_gerados_lista
                        if linha.custo_percentual is not None
                    ),
                    Decimal('0'),
                )
                item.quantidade_movimenta = _quantidade_recebida_item(item)
                _avaliar_diferenca_item_para_tela(item)
                item.permite_varios_produtos = bool(
                    not item.item_removido
                    and not getattr(item, 'ocultar_linha_removida', False)
                )
                item.lote_pendente = bool(
                    item.produto_id
                    and not item.recebe_varios_produtos
                    and item.quantidade_movimenta > 0
                    and (
                        (item.produto.controla_lote and not item.numero_lote)
                        or (item.produto.controla_validade and not item.data_validade)
                    )
                )
                if item.recebe_varios_produtos:
                    item.lote_pendente = any(
                        linha.quantidade > 0
                        and (
                            (linha.produto.controla_lote and not linha.numero_lote)
                            or (linha.produto.controla_validade and not linha.data_validade)
                        )
                        for linha in item.produtos_gerados_lista
                    )
                item.linha_custo_preview = None
                item.custo_critico = False
                item.status_flags = []
                if item.item_removido:
                    item.status_flags.append(('Removido', 'is-red'))
                elif item.recebe_varios_produtos:
                    resumo_status['vinculados'] += 1
                    resumo_status['varios_produtos'] += 1
                    item.status_flags.append(('Varios produtos', 'is-green'))
                elif item.produto_id:
                    resumo_status['vinculados'] += 1
                    item.status_flags.append(('Vinculado', 'is-green'))
                else:
                    resumo_status['sem_produto'] += 1
                    item.status_flags.append(('Sem produto', 'is-red'))
                if item.diferenca_tipo and item.diferenca_tipo != 'produto_sem_vinculo':
                    resumo_status['divergencias'] += 1
                    item.status_flags.append((
                        'Divergencia',
                        'is-red' if item.diferenca_bloqueante else 'is-amber',
                    ))
                if item.lote_pendente:
                    resumo_status['lote_pendente'] += 1
                    item.status_flags.append(('Lote pendente', 'is-red'))
                if item.item_removido:
                    item.status_severidade = 'ok'
                elif item.lote_pendente or item.diferenca_bloqueante or (not item.produto_id and not item.recebe_varios_produtos):
                    item.status_severidade = 'critico'
                elif item.diferenca_tipo:
                    item.status_severidade = 'atencao'
                else:
                    item.status_severidade = 'ok'
                item.mobile_status_keys = ['todos']
                if item.status_severidade != 'ok':
                    item.mobile_status_keys.append('pendentes')
                if not item.produto_id and not item.recebe_varios_produtos:
                    item.mobile_status_keys.append('sem_produto')
                if item.lote_pendente:
                    item.mobile_status_keys.append('lote')
                if item.diferenca_tipo and item.diferenca_tipo != 'produto_sem_vinculo':
                    item.mobile_status_keys.append('divergencia')

                if item.lote_pendente:
                    item.mobile_action_label = 'Preencher lote'
                    item.mobile_action_hint = 'Informe lote ou validade obrigatoria.'
                    item.mobile_action_url = f'#mobile-edit-item-{item.pk}'
                    item.mobile_priority = 20
                elif item.recebe_varios_produtos:
                    item.mobile_action_label = 'Receber como varios produtos'
                    item.mobile_action_hint = 'Revise os produtos internos que este item vai gerar.'
                    item.mobile_action_url = f'#entrada-varios-item-{item.pk}'
                    item.mobile_priority = 30
                elif not item.produto_id:
                    item.mobile_action_label = 'Vincular produto'
                    item.mobile_action_hint = 'Escolha produto interno ou cadastre pelo XML.'
                    item.mobile_action_url = f'#mobile-edit-item-{item.pk}'
                    item.mobile_priority = 40
                elif item.diferenca_tipo:
                    item.mobile_action_label = 'Corrigir divergencia'
                    item.mobile_action_hint = item.diferenca_descricao or 'Revise a divergencia do item.'
                    item.mobile_action_url = f'#mobile-edit-item-{item.pk}'
                    item.mobile_priority = 50
                else:
                    item.mobile_action_label = 'Pronto'
                    item.mobile_action_hint = 'Item pronto para finalizacao.'
                    item.mobile_action_url = '#'
                    item.mobile_priority = 90
                item.mobile_status_data = ' '.join(item.mobile_status_keys)
                itens_mobile.append(item)
            except Exception:
                logger.exception(
                    'Falha ao montar item da conferencia',
                    extra={'entrada_id': entrada.pk, 'item_id': getattr(item, 'pk', None)},
                )
        resumo_status['pendentes'] = sum(1 for item in itens_mobile if item.status_severidade != 'ok')
        itens.sort(key=_ordenacao_item_conferencia)
        itens_varios_produtos = [
            item for item in itens
            if getattr(item, 'permite_varios_produtos', False)
        ]
        itens_mobile.sort(key=lambda item: (item.mobile_priority, item.numero_item or 0, item.pk))
        status_cards = [
            {
                'chave': 'vinculados',
                'titulo': 'Vinculados',
                'valor': resumo_status['vinculados'],
                'classe': 'is-green',
                'texto': 'Ja possuem produto interno definido.',
                'contagem_label': 'itens vinculados',
            },
            {
                'chave': 'sem_produto',
                'titulo': 'Sem produto',
                'valor': resumo_status['sem_produto'],
                'classe': 'is-red',
                'texto': 'Precisa vincular ou cadastrar produto.',
                'contagem_label': 'itens pendentes',
            },
            {
                'chave': 'divergencias',
                'titulo': 'Com divergencia',
                'valor': resumo_status['divergencias'],
                'classe': 'is-amber',
                'texto': 'Quantidade, lote, validade ou regra pendente.',
                'contagem_label': 'itens pendentes',
            },
            {
                'chave': 'lote_pendente',
                'titulo': 'Lote pendente',
                'valor': resumo_status['lote_pendente'],
                'classe': 'is-red',
                'texto': 'Produto exige lote ou validade antes de efetivar.',
                'contagem_label': 'itens pendentes',
            },
        ]
        mobile_filter_cards = [
            {'chave': 'pendentes', 'titulo': 'Pendentes', 'valor': resumo_status['pendentes']},
            {'chave': 'sem_produto', 'titulo': 'Sem produto', 'valor': resumo_status['sem_produto']},
            {'chave': 'lote', 'titulo': 'Lote', 'valor': resumo_status['lote_pendente']},
        ]
        try:
            permissoes_compras = _permissoes_compras(request)
        except Exception:
            logger.exception(
                'Falha ao carregar permissoes de compras na conferencia',
                extra={'entrada_id': entrada.pk},
            )
            permissoes_compras = {}
        try:
            adicionar_item_form = (
                AdicionarItemEntradaForm(filial=request.filial_ativa)
                if _entrada_aberta(entrada) and permissoes_compras.get('pode_editar')
                else None
            )
        except Exception:
            logger.exception(
                'Falha ao montar formulario de item manual da conferencia',
                extra={'entrada_id': entrada.pk},
            )
            adicionar_item_form = None
        context = {
            'entrada': entrada,
            'itens': itens,
            'itens_varios_produtos': itens_varios_produtos,
            'itens_mobile': itens_mobile,
            'resumo_status': resumo_status,
            'status_cards': status_cards,
            'mobile_filter_cards': mobile_filter_cards,
            'composicao_custo': composicao_custo,
            'itens_removidos_restauraveis': logs_restauraveis,
            'permissoes_compras': permissoes_compras,
            'adicionar_item_form': adicionar_item_form,
        }
        try:
            return render(request, self.template_name, context)
        except Exception as exc:
            return self.render_fallback(request, entrada, exc)


class EntradaNFProdutoSearchView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'ver'

    def get(self, request):
        termo = request.GET.get('q', '').strip()
        produtos = (
            Produto.objects.for_filial(request.filial_ativa)
            .filter(ativo=True)
            .select_related('unidade_medida')
        )
        if len(termo) >= 2 or termo.isdigit():
            filtro = (
                Q(descricao__icontains=termo)
                | Q(descricao_curta__icontains=termo)
                | Q(codigo__icontains=termo)
                | Q(codigo_barras__icontains=termo)
                | Q(codigos_barras_extras__icontains=termo)
                | Q(codigos_barras__ean__icontains=termo)
            )
            if termo.isdigit():
                filtro |= Q(pk=int(termo))
            produtos = produtos.filter(filtro).distinct()
        else:
            produtos = produtos.none()

        if termo.isdigit():
            produtos = produtos.annotate(
                prioridade_busca=Case(
                    When(pk=int(termo), then=Value(0)),
                    When(codigo=termo, then=Value(1)),
                    When(codigo_barras=termo, then=Value(2)),
                    default=Value(3),
                    output_field=IntegerField(),
                )
            ).order_by('prioridade_busca', 'descricao')
        else:
            produtos = produtos.annotate(
                prioridade_busca=Case(
                    When(codigo__iexact=termo, then=Value(0)),
                    When(codigo_barras__iexact=termo, then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField(),
                )
            ).order_by('prioridade_busca', 'descricao')

        resultados = []
        for produto in produtos[:20]:
            unidade = produto.unidade_medida.sigla if produto.unidade_medida_id else ''
            detalhes = []
            if produto.codigo:
                detalhes.append(f'Cod. {produto.codigo}')
            if produto.codigo_barras:
                detalhes.append(f'EAN {produto.codigo_barras}')
            if unidade:
                detalhes.append(unidade)
            resultados.append({
                'id': produto.pk,
                'label': f'{produto.pk} - {produto.descricao}',
                'descricao': produto.descricao,
                'unidade': unidade,
                'meta': ' | '.join(detalhes),
            })
        return JsonResponse({'results': resultados})


class EntradaNFVincularItemView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'editar'

    def post(self, request, pk, item_id):
        entrada = get_object_or_404(EntradaNF.objects.for_filial(request.filial_ativa), pk=pk)
        if not _entrada_aberta(entrada):
            messages.error(request, 'Entrada efetivada nao permite trocar produto, lote ou validade.')
            return redirect('compras:entrada-detail', pk=entrada.pk)
        item = get_object_or_404(entrada.itens.all(), pk=item_id)
        produto = get_object_or_404(
            Produto.objects.for_filial(request.filial_ativa).filter(ativo=True),
            pk=request.POST.get('produto'),
        )
        fator = _decimal_localizado(request.POST.get('fator_conversao'), item.fator_conversao or Decimal('1'))
        unidade_estoque = request.POST.get('unidade_estoque') or produto.unidade_medida.sigla
        validade = parse_date(request.POST.get('data_validade') or '')
        antes = snapshot_modelo(item)
        item.produtos_gerados.all().delete()
        vincular_item_a_produto(
            entrada=entrada,
            item=item,
            produto=produto,
            fator_conversao=fator,
            unidade_estoque=unidade_estoque,
            numero_lote=request.POST.get('numero_lote', item.numero_lote),
            data_validade=validade,
        )
        CompraService._atualizar_status_conferencia(entrada)
        item.refresh_from_db()
        _auditar_entrada(
            request,
            'vincular',
            entrada,
            f'Item {item.numero_item} vinculado ao produto {produto.descricao}',
            antes=antes,
            depois=snapshot_modelo(item),
            relacionado=item,
            metadados={'produto_id': produto.pk, 'fator_conversao': str(fator)},
        )
        messages.success(request, 'Produto vinculado e equivalencia salva para proximas entradas.')
        return redirect('compras:entrada-conferencia', pk=pk)


class EntradaNFDesvincularItemView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'editar'

    def post(self, request, pk, item_id):
        entrada = get_object_or_404(EntradaNF.objects.for_filial(request.filial_ativa), pk=pk)
        if not _entrada_aberta(entrada):
            messages.error(request, 'Entrada efetivada nao permite remover vinculo de produto.')
            return redirect('compras:entrada-detail', pk=entrada.pk)
        item = get_object_or_404(entrada.itens.select_related('produto'), pk=item_id)
        if not item.produto_id:
            messages.info(request, 'Este item ja esta sem produto vinculado.')
            return redirect('compras:entrada-conferencia', pk=entrada.pk)

        produto = item.produto
        antes = snapshot_modelo(item)
        desvincular_item_de_produto(item)
        CompraService._atualizar_status_conferencia(entrada)
        item.refresh_from_db()
        _auditar_entrada(
            request,
            'desvincular',
            entrada,
            f'Item {item.numero_item} desvinculado do produto {produto.descricao}',
            antes=antes,
            depois=snapshot_modelo(item),
            relacionado=item,
            metadados={'produto_id': produto.pk},
        )
        messages.success(request, 'Vinculo do produto removido deste item.')
        return redirect('compras:entrada-conferencia', pk=entrada.pk)


class EntradaNFReceberVariosProdutosView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'editar'

    def post(self, request, pk, item_id):
        entrada = get_object_or_404(EntradaNF.objects.for_filial(request.filial_ativa), pk=pk)
        if not _entrada_aberta(entrada):
            messages.error(request, 'Entrada fechada nao permite alterar varios produtos.')
            return redirect('compras:entrada-conferencia', pk=entrada.pk)

        item = get_object_or_404(entrada.itens.select_related('produto'), pk=item_id)
        produtos = request.POST.getlist('produto')
        quantidades = request.POST.getlist('quantidade')
        lotes = request.POST.getlist('numero_lote')
        validades = request.POST.getlist('data_validade')
        percentuais = request.POST.getlist('custo_percentual')
        observacoes = request.POST.getlist('observacao')
        total_linhas = max(
            len(produtos), len(quantidades), len(lotes), len(validades), len(percentuais), len(observacoes),
        )
        linhas = []
        erros = []
        soma_percentual = Decimal('0')
        usa_percentual = False
        for indice in range(total_linhas):
            produto_id = (produtos[indice] if indice < len(produtos) else '').strip()
            quantidade_raw = quantidades[indice] if indice < len(quantidades) else ''
            lote = (lotes[indice] if indice < len(lotes) else '').strip()[:60]
            validade_raw = validades[indice] if indice < len(validades) else ''
            percentual_raw = percentuais[indice] if indice < len(percentuais) else ''
            observacao = (observacoes[indice] if indice < len(observacoes) else '').strip()[:255]
            if not any([produto_id, str(quantidade_raw).strip(), lote, str(validade_raw).strip(), str(percentual_raw).strip(), observacao]):
                continue
            if not produto_id:
                erros.append(f'Linha {indice + 1}: selecione o produto interno.')
                continue
            produto = Produto.objects.for_filial(request.filial_ativa).filter(ativo=True, pk=produto_id).select_related('unidade_medida').first()
            if not produto:
                erros.append(f'Linha {indice + 1}: produto nao encontrado na filial.')
                continue
            try:
                quantidade = _quantidade_3(_decimal_localizado(quantidade_raw, Decimal('0')))
            except (InvalidOperation, ValueError):
                erros.append(f'Linha {indice + 1}: quantidade invalida.')
                continue
            if quantidade <= 0:
                erros.append(f'Linha {indice + 1}: quantidade deve ser maior que zero.')
            validade = _parse_data_localizada(validade_raw)
            if str(validade_raw or '').strip() and not validade:
                erros.append(f'Linha {indice + 1}: validade invalida. Use dd/mm/aaaa.')
            if produto.controla_lote and not lote:
                erros.append(f'Linha {indice + 1}: lote obrigatorio para {produto.descricao}.')
            if produto.controla_validade and not validade:
                erros.append(f'Linha {indice + 1}: validade obrigatoria para {produto.descricao}.')
            if produto.controla_validade and validade and validade < timezone.localdate():
                erros.append(f'Linha {indice + 1}: validade vencida nao pode movimentar estoque.')
            percentual = None
            if str(percentual_raw or '').strip():
                try:
                    percentual = _decimal_localizado(percentual_raw, Decimal('0'))
                except (InvalidOperation, ValueError):
                    erros.append(f'Linha {indice + 1}: custo % invalido.')
                    continue
                if percentual < 0:
                    erros.append(f'Linha {indice + 1}: custo % nao pode ser negativo.')
                usa_percentual = True
                soma_percentual += percentual
            linhas.append({
                'produto': produto,
                'quantidade': quantidade,
                'numero_lote': lote,
                'data_validade': validade,
                'custo_percentual': percentual,
                'observacao': observacao,
            })

        if not linhas:
            erros.append('Adicione ao menos um produto para receber este item como varios produtos.')
        if usa_percentual and soma_percentual != Decimal('100'):
            erros.append('Quando informar custo %, a soma das linhas precisa fechar 100%.')
        if erros:
            for erro in erros:
                messages.error(request, erro)
            return redirect('compras:entrada-conferencia', pk=entrada.pk)

        antes = {
            'item': snapshot_modelo(item),
            'produtos_gerados': _snapshot_produtos_gerados(item),
        }
        with transaction.atomic():
            item.produtos_gerados.all().delete()
            item.produto = None
            item.save(update_fields=['produto', 'updated_at'])
            for ordem, linha in enumerate(linhas, start=1):
                ItemEntradaNFProdutoGerado.objects.create(
                    item=item,
                    produto=linha['produto'],
                    ordem=ordem,
                    quantidade=linha['quantidade'],
                    unidade_estoque=linha['produto'].unidade_medida.sigla if linha['produto'].unidade_medida_id else '',
                    numero_lote=linha['numero_lote'],
                    data_validade=linha['data_validade'],
                    custo_percentual=linha['custo_percentual'],
                    observacao=linha['observacao'],
                )
            CompraService.atualizar_diferenca_item(item)
            CompraService._atualizar_status_conferencia(entrada)
        item.refresh_from_db()
        _auditar_entrada(
            request,
            'receber_varios_produtos',
            entrada,
            f'Item {item.numero_item} configurado para receber como varios produtos.',
            antes=antes,
            depois={
                'item': snapshot_modelo(item),
                'produtos_gerados': _snapshot_produtos_gerados(item),
            },
            relacionado=item,
            metadados={'total_produtos_gerados': len(linhas)},
        )
        messages.success(request, 'Item configurado para receber como varios produtos.')
        return redirect('compras:entrada-conferencia', pk=entrada.pk)


class EntradaNFDividirLotesItemView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'editar'

    def post(self, request, pk, item_id):
        entrada = get_object_or_404(EntradaNF.objects.for_filial(request.filial_ativa), pk=pk)
        if not _entrada_aberta(entrada):
            messages.error(request, 'Entrada fechada nao permite dividir lote ou validade.')
            return redirect('compras:entrada-conferencia', pk=entrada.pk)

        item = get_object_or_404(
            entrada.itens.select_related('produto', 'produto__unidade_medida', 'item_pedido_compra'),
            pk=item_id,
        )
        if not item.produto_id:
            messages.error(request, 'Vincule o produto antes de dividir lotes.')
            return redirect('compras:entrada-conferencia', pk=entrada.pk)

        quantidade_total = _quantidade_3(_quantidade_recebida_item(item))
        if quantidade_total <= 0:
            messages.error(request, 'Item sem quantidade recebida nao pode ser dividido em lotes.')
            return redirect('compras:entrada-conferencia', pk=entrada.pk)

        lotes = request.POST.getlist('numero_lote')
        validades = request.POST.getlist('data_validade')
        quantidades = request.POST.getlist('quantidade_lote')
        total_linhas = max(len(lotes), len(validades), len(quantidades))
        linhas = []
        erros = []
        for indice in range(total_linhas):
            numero_lote = (lotes[indice] if indice < len(lotes) else '').strip()[:60]
            validade_raw = validades[indice] if indice < len(validades) else ''
            validade = _parse_data_localizada(validade_raw)
            quantidade_raw = quantidades[indice] if indice < len(quantidades) else ''
            if not numero_lote and not validade and not str(quantidade_raw).strip():
                continue
            if str(validade_raw or '').strip() and not validade:
                erros.append(f'Linha {indice + 1}: validade invalida. Use dd/mm/aaaa.')
            try:
                quantidade = _quantidade_3(_decimal_localizado(quantidade_raw, Decimal('0')))
            except (InvalidOperation, ValueError):
                erros.append(f'Linha {indice + 1}: quantidade invalida.')
                continue
            if quantidade <= 0:
                erros.append(f'Linha {indice + 1}: quantidade deve ser maior que zero.')
            if quantidade > quantidade_total:
                erros.append(
                    f'Linha {indice + 1}: quantidade {quantidade} maior que a Qtd. final do item ({quantidade_total}).'
                )
            if item.produto.controla_lote and not numero_lote:
                erros.append(f'Linha {indice + 1}: lote obrigatorio.')
            if item.produto.controla_validade and not validade:
                erros.append(f'Linha {indice + 1}: validade obrigatoria.')
            if item.produto.controla_validade and validade and validade < timezone.localdate():
                erros.append(f'Linha {indice + 1}: validade vencida nao pode movimentar estoque.')
            linhas.append({
                'numero_lote': numero_lote,
                'data_validade': validade,
                'quantidade': quantidade,
            })

        if not linhas:
            erros.append('Informe ao menos uma linha de lote.')
        soma = _quantidade_3(sum((linha['quantidade'] for linha in linhas), Decimal('0')))
        if linhas and soma > quantidade_total:
            erros.append(
                f'A soma dos lotes ({soma}) ficou maior que a Qtd. final do item ({quantidade_total}). Ajuste as quantidades.'
            )
        elif linhas and soma < quantidade_total:
            erros.append(
                f'A soma dos lotes ({soma}) ficou menor que a Qtd. final do item ({quantidade_total}). Falta informar {quantidade_total - soma}.'
            )
        if erros:
            for erro in erros:
                messages.error(request, erro)
            return redirect('compras:entrada-conferencia', pk=entrada.pk)

        base_bruto = _centavos(item.valor_bruto or item.valor_total or item.valor_unitario * quantidade_total)
        base_total = _centavos(item.valor_total or item.valor_bruto or item.valor_unitario * quantidade_total)
        base_desconto = _centavos(item.valor_desconto)
        base_ipi = _centavos(item.valor_ipi)
        base_icms = _centavos(item.valor_icms)
        alocados = {
            'bruto': Decimal('0.00'),
            'total': Decimal('0.00'),
            'desconto': Decimal('0.00'),
            'ipi': Decimal('0.00'),
            'icms': Decimal('0.00'),
        }

        def parcela(base, chave, linha, ultima):
            if ultima:
                valor = base - alocados[chave]
            else:
                valor = _centavos(base * linha['quantidade'] / quantidade_total)
                alocados[chave] += valor
            return valor

        antes = snapshot_modelo(item)
        criados = 0
        with transaction.atomic():
            for indice, linha in enumerate(linhas):
                ultima = indice == len(linhas) - 1
                dados = {
                    'quantidade': linha['quantidade'],
                    'quantidade_xml': linha['quantidade'],
                    'quantidade_estoque': linha['quantidade'],
                    'quantidade_recebida': linha['quantidade'],
                    'unidade_xml': item.unidade_estoque or item.unidade_xml,
                    'fator_conversao': Decimal('1'),
                    'valor_bruto': parcela(base_bruto, 'bruto', linha, ultima),
                    'valor_total': parcela(base_total, 'total', linha, ultima),
                    'valor_desconto': parcela(base_desconto, 'desconto', linha, ultima),
                    'valor_ipi': parcela(base_ipi, 'ipi', linha, ultima),
                    'valor_icms': parcela(base_icms, 'icms', linha, ultima),
                    'numero_lote': linha['numero_lote'],
                    'data_validade': linha['data_validade'],
                    'lote_gerado': None,
                    'observacao': (
                        item.observacao
                        or ('Item dividido manualmente em lotes.' if len(linhas) > 1 else '')
                    ),
                }
                if dados['quantidade'] > 0 and dados['valor_total'] > 0:
                    dados['valor_unitario'] = (
                        dados['valor_total'] / dados['quantidade']
                    ).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
                else:
                    dados['valor_unitario'] = item.valor_unitario

                if indice == 0:
                    for campo, valor in dados.items():
                        setattr(item, campo, valor)
                    item.save()
                    CompraService.atualizar_diferenca_item(item)
                else:
                    novo = ItemEntradaNF.objects.create(
                        entrada=entrada,
                        item_pedido_compra=item.item_pedido_compra,
                        produto=item.produto,
                        numero_item=item.numero_item,
                        unidade_estoque=item.unidade_estoque,
                        custo_unitario_total=item.custo_unitario_total,
                        data_fabricacao=item.data_fabricacao,
                        ean_xml=item.ean_xml,
                        ncm_xml=item.ncm_xml,
                        cfop_xml=item.cfop_xml,
                        codigo_produto_fornecedor=item.codigo_produto_fornecedor,
                        descricao_xml=item.descricao_xml,
                        justificativa_diferenca=item.justificativa_diferenca,
                        **dados,
                    )
                    CompraService.atualizar_diferenca_item(novo)
                    criados += 1

            CompraService._atualizar_status_conferencia(entrada)

        item.refresh_from_db()
        _auditar_entrada(
            request,
            'dividir_lotes',
            entrada,
            f'Item {item.numero_item} dividido em {len(linhas)} lote(s).',
            antes=antes,
            depois=snapshot_modelo(item),
            relacionado=item,
            metadados={'lotes': len(linhas), 'itens_criados': criados},
        )
        messages.success(request, f'Lotes salvos. {len(linhas)} linha(s) somam {quantidade_total}.')
        return redirect('compras:entrada-conferencia', pk=entrada.pk)


class EntradaNFVincularSugestoesView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'editar'

    def post(self, request, pk):
        entrada = get_object_or_404(EntradaNF.objects.for_filial(request.filial_ativa), pk=pk)
        if not _entrada_aberta(entrada):
            messages.error(request, 'Entrada fechada nao permite alterar vinculos.')
            return redirect('compras:entrada-conferencia', pk=entrada.pk)

        item_ids = request.POST.getlist('item')
        if not item_ids:
            messages.warning(request, 'Selecione ao menos uma sugestao para confirmar.')
            return redirect('compras:entrada-conferencia', pk=entrada.pk)

        vinculados = 0
        ignorados = 0
        with transaction.atomic():
            itens = (
                entrada.itens
                .filter(pk__in=item_ids, produto__isnull=True)
                .select_related('produto')
            )
            for item in itens:
                produto_id = request.POST.get(f'produto_{item.pk}')
                sugestoes = sugerir_produtos_para_item(item, request.filial_ativa)
                sugestao = next(
                    (
                        item_sugestao
                        for item_sugestao in sugestoes
                        if str(item_sugestao.produto.pk) == str(produto_id)
                    ),
                    None,
                )
                if not sugestao:
                    ignorados += 1
                    continue

                try:
                    fator = _decimal_localizado(
                        request.POST.get(f'fator_conversao_{item.pk}'),
                        item.fator_conversao or Decimal('1'),
                    )
                except (InvalidOperation, ValueError):
                    ignorados += 1
                    continue

                if fator <= 0:
                    ignorados += 1
                    continue

                unidade_estoque = (
                    request.POST.get(f'unidade_estoque_{item.pk}')
                    or sugestao.produto.unidade_medida.sigla
                )
                validade = (
                    parse_date(request.POST.get(f'data_validade_{item.pk}') or '')
                    or item.data_validade
                )
                antes = snapshot_modelo(item)
                vincular_item_a_produto(
                    entrada=entrada,
                    item=item,
                    produto=sugestao.produto,
                    fator_conversao=fator,
                    unidade_estoque=unidade_estoque.strip()[:6],
                    numero_lote=request.POST.get(f'numero_lote_{item.pk}', item.numero_lote),
                    data_validade=validade,
                )
                item.refresh_from_db()
                _auditar_entrada(
                    request,
                    'vincular',
                    entrada,
                    f'Sugestao confirmada no item {item.numero_item}',
                    antes=antes,
                    depois=snapshot_modelo(item),
                    relacionado=item,
                    metadados={'produto_id': sugestao.produto.pk, 'origem': 'sugestao'},
                )
                vinculados += 1
            CompraService._atualizar_status_conferencia(entrada)

        if vinculados:
            messages.success(request, f'{vinculados} sugestao(oes) vinculada(s).')
        if ignorados:
            messages.warning(request, f'{ignorados} sugestao(oes) foram ignorada(s) por seguranca.')
        if not vinculados and not ignorados:
            messages.warning(request, 'Nenhum item pendente foi encontrado para confirmar.')
        return redirect('compras:entrada-conferencia', pk=entrada.pk)


class EntradaNFReprocessarVinculosView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'editar'

    def post(self, request, pk):
        entrada = get_object_or_404(
            EntradaNF.objects.for_filial(request.filial_ativa).select_related('fornecedor'),
            pk=pk,
        )
        if not _entrada_aberta(entrada):
            messages.error(request, 'Entrada fechada nao permite reprocessar vinculos.')
            return redirect('compras:entrada-conferencia', pk=entrada.pk)

        resultado = reprocessar_vinculos_automaticos(entrada)
        vinculados = resultado['vinculados']
        pendentes = resultado['pendentes']
        _auditar_entrada(
            request,
            'reprocessar',
            entrada,
            'Vinculos da entrada reprocessados',
            metadados={'vinculados': vinculados, 'pendentes': pendentes},
        )
        if vinculados:
            messages.success(
                request,
                f'{vinculados} item(ns) vinculado(s) automaticamente por EAN ou equivalencia segura.',
            )
        elif pendentes:
            messages.warning(
                request,
                'Nenhum novo vinculo seguro foi encontrado. Revise as sugestoes por nome ou cadastre pelo XML.',
            )
        else:
            messages.info(request, 'Nao havia itens pendentes para reprocessar.')
        return redirect('compras:entrada-conferencia', pk=entrada.pk)


class EntradaNFCriarProdutoItemView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'editar'

    def post(self, request, pk, item_id):
        entrada = get_object_or_404(EntradaNF.objects.for_filial(request.filial_ativa), pk=pk)
        if not _entrada_aberta(entrada):
            messages.error(request, 'Entrada efetivada nao permite cadastrar ou trocar produto pelo XML.')
            return redirect('compras:entrada-detail', pk=entrada.pk)
        item = get_object_or_404(entrada.itens.all(), pk=item_id)
        try:
            antes = snapshot_modelo(item)
            produto = criar_produto_e_vincular_item(entrada, item)
            CompraService._atualizar_status_conferencia(entrada)
            item.refresh_from_db()
            _auditar_entrada(
                request,
                'criar',
                entrada,
                f'Produto cadastrado pelo XML e vinculado ao item {item.numero_item}',
                antes=antes,
                depois=snapshot_modelo(item),
                relacionado=produto,
                metadados={'produto_id': produto.pk, 'item_id': item.pk},
            )
            messages.success(request, f'Produto "{produto.descricao}" cadastrado e vinculado ao item.')
        except Exception as exc:
            messages.error(request, f'Nao foi possivel cadastrar o produto: {exc}')
        return redirect('compras:entrada-conferencia', pk=pk)


class EntradaNFFornecedorPendenteView(EntradaNFDetailView):
    permissao_acao = 'editar'
    template_name = 'compras/entrada/fornecedor_pendente.html'

    def get(self, request, pk):
        entrada = self.get_entrada(request, pk)
        fornecedores = Fornecedor.objects.for_filial(request.filial_ativa).filter(ativo=True).order_by('razao_social')
        return render(request, self.template_name, {
            'entrada': entrada,
            'fornecedores': fornecedores,
        })

    def post(self, request, pk):
        entrada = self.get_entrada(request, pk)
        acao = request.POST.get('acao', 'vincular')
        if acao == 'criar_xml':
            try:
                antes = snapshot_modelo(entrada)
                with transaction.atomic():
                    fornecedor = _criar_fornecedor_do_xml(entrada)
                    entrada.fornecedor = fornecedor
                    entrada.fornecedor_pendente = False
                    entrada.save(update_fields=['fornecedor', 'fornecedor_pendente', 'updated_at'])
                    atualizadas = _atualizar_equivalencias_fornecedor(entrada)
                mensagem = 'Fornecedor criado a partir do XML e vinculado a entrada.'
                if atualizadas:
                    mensagem += f' {atualizadas} equivalencia(s) pendente(s) foram atualizadas.'
                entrada.refresh_from_db()
                _auditar_entrada(
                    request,
                    'vincular',
                    entrada,
                    'Fornecedor criado pelo XML e vinculado a entrada',
                    antes=antes,
                    depois=snapshot_modelo(entrada),
                    relacionado=fornecedor,
                    metadados={'fornecedor_id': fornecedor.pk, 'equivalencias_atualizadas': atualizadas},
                )
                messages.success(request, mensagem)
            except DomainError as exc:
                messages.error(request, str(exc))
            return redirect('compras:entrada-detail', pk=entrada.pk)

        fornecedor_id = request.POST.get('fornecedor')
        if fornecedor_id:
            fornecedor = get_object_or_404(
                Fornecedor.objects.for_filial(request.filial_ativa).filter(ativo=True),
                pk=fornecedor_id,
            )
            antes = snapshot_modelo(entrada)
            with transaction.atomic():
                entrada.fornecedor = fornecedor
                entrada.fornecedor_pendente = False
                entrada.save(update_fields=['fornecedor', 'fornecedor_pendente', 'updated_at'])
                atualizadas = _atualizar_equivalencias_fornecedor(entrada)
            mensagem = 'Fornecedor vinculado a entrada.'
            if atualizadas:
                mensagem += f' {atualizadas} equivalencia(s) pendente(s) foram atualizadas.'
            entrada.refresh_from_db()
            _auditar_entrada(
                request,
                'vincular',
                entrada,
                'Fornecedor vinculado a entrada',
                antes=antes,
                depois=snapshot_modelo(entrada),
                relacionado=fornecedor,
                metadados={'fornecedor_id': fornecedor.pk, 'equivalencias_atualizadas': atualizadas},
            )
            messages.success(request, mensagem)
        return redirect('compras:entrada-detail', pk=entrada.pk)


class EntradaNFDiferencasView(EntradaNFDetailView):
    template_name = 'compras/entrada/diferencas.html'

    def get_context(self, entrada, usuario=None):
        pode_editar = (
            usuario.tem_permissao('compras', 'editar')
            if usuario and usuario.is_authenticated
            else False
        )
        todos_itens = list(
            entrada.itens
            .select_related('produto')
            .order_by('numero_item', 'pk')
        )
        itens = []
        for item in todos_itens:
            _avaliar_diferenca_item_para_tela(item)
            if item.diferenca_tipo or item.diferenca_bloqueante or not item.produto_id:
                itens.append(item)
        return {
            'entrada': entrada,
            'itens': itens,
            'total_itens': len(todos_itens),
            'total_diferencas': len(itens),
            'total_bloqueantes': sum(1 for item in itens if item.diferenca_bloqueante or not item.produto_id),
            'total_alertas': sum(1 for item in itens if item.diferenca_tipo and not item.diferenca_bloqueante),
            'pode_editar_diferencas': _entrada_aberta(entrada) and pode_editar,
        }

    def get(self, request, pk):
        entrada = self.get_entrada(request, pk)
        contexto = self.get_context(entrada, request.user)
        contexto['permissoes_compras'] = _permissoes_compras(request)
        return render(request, self.template_name, contexto)

    def post(self, request, pk):
        entrada = self.get_entrada(request, pk)
        if not request.user.tem_permissao('compras', 'editar'):
            messages.error(request, PERMISSION_DENIED_MESSAGE)
            return redirect('compras:entrada-diferencas', pk=entrada.pk)
        if not _entrada_aberta(entrada):
            messages.error(request, 'Entrada fechada nao permite alterar diferencas.')
            return redirect('compras:entrada-diferencas', pk=entrada.pk)

        item = get_object_or_404(
            entrada.itens.select_related('produto'),
            pk=request.POST.get('item_id'),
        )
        antes = snapshot_modelo(item)
        try:
            item.quantidade_recebida = _decimal_localizado(
                request.POST.get('quantidade_recebida'),
                item.quantidade_recebida or item.quantidade_estoque,
            )
        except (InvalidOperation, ValueError):
            messages.error(request, 'Quantidade recebida invalida.')
            return redirect('compras:entrada-diferencas', pk=entrada.pk)

        item.numero_lote = (request.POST.get('numero_lote') or '').strip()
        item.data_validade = parse_date(request.POST.get('data_validade') or '')
        item.justificativa_diferenca = (request.POST.get('justificativa_diferenca') or '').strip()
        _atualizar_diferenca_item(item)
        CompraService._atualizar_status_conferencia(entrada)
        item.refresh_from_db()
        _auditar_entrada(
            request,
            'editar',
            entrada,
            f'Divergencia/conferencia alterada no item {item.numero_item}',
            justificativa=item.justificativa_diferenca,
            antes=antes,
            depois=snapshot_modelo(item),
            relacionado=item,
            metadados={'diferenca_tipo': item.diferenca_tipo, 'diferenca_bloqueante': item.diferenca_bloqueante},
        )

        if item.diferenca_bloqueante:
            messages.warning(request, 'Diferenca salva, mas ainda bloqueia a finalizacao.')
        elif item.diferenca_tipo:
            messages.success(request, 'Diferenca justificada. A entrada segue como alerta operacional.')
        else:
            messages.success(request, 'Diferenca resolvida.')
        return redirect('compras:entrada-diferencas', pk=entrada.pk)



class EntradaNFFinanceiroView(EntradaNFDetailView):
    template_name = 'compras/entrada/financeiro.html'

    def get_context(self, entrada, usuario=None):
        parcelas = list(entrada.parcelas_financeiras.all())
        total_parcelas = sum((parcela.valor for parcela in parcelas), Decimal('0'))
        diferenca_total = entrada.valor_total - total_parcelas
        pendentes_geracao = [
            parcela for parcela in parcelas
            if parcela.status == EntradaNFParcela.Status.PENDENTE and not parcela.conta_pagar_id
        ]
        bloqueios_geracao = validar_geracao_contas_pagar(entrada)
        pode_criar_contas = (
            usuario.tem_permissao('financeiro', 'criar')
            if usuario and usuario.is_authenticated
            else False
        )
        if not pode_criar_contas:
            bloqueios_geracao.append('Usuario sem permissao para criar contas a pagar.')
        return {
            'entrada': entrada,
            'parcelas': parcelas,
            'form': EntradaNFParcelaForm(),
            'total_parcelas': total_parcelas,
            'diferenca_total': diferenca_total,
            'pode_editar_financeiro': _entrada_aberta(entrada) and pode_criar_contas,
            'parcelas_pendentes_geracao': pendentes_geracao,
            'contas_geradas_count': sum(1 for parcela in parcelas if parcela.conta_pagar_id),
            'bloqueios_geracao': bloqueios_geracao,
            'pode_gerar_contas': bool(pendentes_geracao) and not bloqueios_geracao,
        }

    def get(self, request, pk):
        entrada = self.get_entrada(request, pk)
        contexto = self.get_context(entrada, request.user)
        contexto['permissoes_compras'] = _permissoes_compras(request)
        return render(request, self.template_name, contexto)

    def post(self, request, pk):
        entrada = self.get_entrada(request, pk)
        if not request.user.tem_permissao('financeiro', 'criar'):
            messages.error(request, PERMISSION_DENIED_MESSAGE)
            return redirect('compras:entrada-financeiro', pk=entrada.pk)
        if not _entrada_aberta(entrada):
            messages.error(request, 'Entrada fechada nao permite alterar parcelas.')
            return redirect('compras:entrada-financeiro', pk=entrada.pk)

        form = EntradaNFParcelaForm(request.POST)
        if form.is_valid():
            parcela = form.save(commit=False)
            parcela.entrada = entrada
            parcela.origem = EntradaNFParcela.Origem.MANUAL
            parcela.status = EntradaNFParcela.Status.PENDENTE
            parcela.fornecedor_pendente = entrada.fornecedor_pendente
            parcela.emitente_documento_xml = entrada.emitente_cnpj_xml
            parcela.emitente_nome_xml = entrada.emitente_razao_social_xml
            if not parcela.numero:
                proximo = entrada.parcelas_financeiras.count() + 1
                parcela.numero = str(proximo).zfill(3)
            parcela.save()
            registrar_auditoria(
                request=request,
                modulo='financeiro',
                acao='criar',
                objeto=parcela,
                descricao=f'Parcela financeira criada para NF {entrada.numero_nf}/{entrada.serie_nf}',
                relacionado=entrada,
                depois=snapshot_modelo(parcela),
                metadados={'entrada_id': entrada.pk, 'valor': str(parcela.valor)},
            )
            messages.success(request, 'Parcela adicionada para revisao financeira.')
            return redirect('compras:entrada-financeiro', pk=entrada.pk)

        contexto = self.get_context(entrada, request.user)
        contexto['form'] = form
        messages.error(request, 'Verifique os dados da parcela.')
        return render(request, self.template_name, contexto)


class EntradaNFGerarContasPagarView(PermissaoRequiredMixin, View):
    permissao_modulo = 'financeiro'
    permissao_acao = 'criar'

    def post(self, request, pk):
        entrada = get_object_or_404(
            EntradaNF.objects.for_filial(request.filial_ativa),
            pk=pk,
        )
        try:
            resultado = gerar_contas_pagar_da_entrada(entrada, request.user)
            registrar_auditoria(
                request=request,
                modulo='financeiro',
                acao='criar',
                objeto=entrada,
                descricao=f'Contas a pagar geradas para NF {entrada.numero_nf}/{entrada.serie_nf}',
                metadados={
                    'criadas': resultado.criadas,
                    'existentes': resultado.existentes,
                    'ignoradas': resultado.ignoradas,
                },
            )
            if resultado.criadas:
                messages.success(request, f'{resultado.criadas} conta(s) a pagar gerada(s).')
            if resultado.existentes:
                messages.info(request, f'{resultado.existentes} conta(s) ja existiam e foram vinculada(s).')
            if resultado.ignoradas:
                messages.warning(request, f'{resultado.ignoradas} parcela(s) ja estavam geradas.')
        except DomainError as exc:
            messages.error(request, str(exc))
        return redirect('compras:entrada-financeiro', pk=entrada.pk)


class EntradaNFCustosView(EntradaNFDetailView):
    permissao_acao = 'editar'
    template_name = 'compras/entrada/custos.html'

    def _preparar_linhas(self, composicao):
        for linha in composicao.get('linhas', []):
            item = linha.item
            item.identificador_nota_display = (
                'Manual'
                if not item.codigo_produto_fornecedor and not item.descricao_xml and item.produto_id
                else (item.codigo_produto_fornecedor or item.numero_item or '-')
            )
            item.codigo_barras_display = item.ean_xml
            if not item.codigo_barras_display and item.produto_id:
                item.codigo_barras_display = item.produto.codigo_barras or ''
                if not item.codigo_barras_display:
                    codigo_barras = item.produto.codigos_barras.filter(ativo=True).order_by('pk').first()
                    item.codigo_barras_display = codigo_barras.ean if codigo_barras else ''
            item.codigo_barras_display = item.codigo_barras_display or '-'
            descricao_base = item.produto.descricao if item.produto_id else item.descricao_xml
            item.descricao_custo_display = _descricao_sem_codigo_barras_duplicado(
                descricao_base,
                item.codigo_barras_display,
            )
            produtos_gerados = list(
                item.produtos_gerados
                .select_related('produto')
                .order_by('ordem', 'pk')
            )
            item.custo_modo = 'varios' if produtos_gerados else 'unico'
            item.produtos_gerados_custo_display = []
            if produtos_gerados:
                total_quantidade = sum(
                    (produto_gerado.quantidade for produto_gerado in produtos_gerados),
                    Decimal('0'),
                )
                usa_percentual = any(
                    produto_gerado.custo_percentual is not None
                    for produto_gerado in produtos_gerados
                )
                for produto_gerado in produtos_gerados:
                    percentual = produto_gerado.custo_percentual
                    percentual_auto = False
                    if percentual is None:
                        percentual_auto = True
                        percentual = (
                            (produto_gerado.quantidade / total_quantidade) * Decimal('100')
                            if total_quantidade > 0
                            else Decimal('0')
                        )
                    percentual = percentual.quantize(Decimal('0.01'))
                    custo_total = (
                        linha.custo_total * percentual / Decimal('100')
                    ).quantize(Decimal('0.01'))
                    custo_unitario = (
                        (custo_total / produto_gerado.quantidade).quantize(Decimal('0.0001'))
                        if produto_gerado.quantidade > 0
                        else Decimal('0')
                    )
                    item.produtos_gerados_custo_display.append({
                        'produto': produto_gerado.produto,
                        'quantidade': produto_gerado.quantidade,
                        'percentual': percentual,
                        'percentual_auto': percentual_auto and not usa_percentual,
                        'custo_total': custo_total,
                        'custo_unitario': custo_unitario,
                    })

    def _parametros(self, entrada, data):
        custo_financeiro = _decimal_localizado(
            data.get('custo_financeiro'),
            Decimal('0'),
        )
        metodo_rateio = data.get('metodo_rateio') or entrada.custo_rateio_metodo
        if metodo_rateio == EntradaNF.MetodoRateioCusto.PESO:
            metodo_rateio = EntradaNF.MetodoRateioCusto.VALOR
        return {
            'metodo_rateio': metodo_rateio,
            'incluir_ipi': _bool_parametros(data, 'incluir_ipi', entrada.custo_incluir_ipi),
            'incluir_icms_st': _bool_parametros(data, 'incluir_icms_st', entrada.custo_incluir_icms_st),
            'incluir_icms': _bool_parametros(data, 'incluir_icms', entrada.custo_incluir_icms),
            'custo_financeiro': custo_financeiro,
            'usar_apenas_valor_nota': _bool_parametros(
                data,
                'usar_apenas_valor_nota',
                entrada.custo_usar_apenas_valor_nota,
            ),
        }

    def _post_custo_unitario_manual(self, request, entrada):
        item_id = request.POST.get('item_id')
        valor_texto = request.POST.get('custo_unitario_manual')
        if valor_texto in (None, ''):
            raise DomainError('Informe o custo unitario agregado.')
        try:
            item = entrada.itens.select_related('produto').get(pk=item_id)
        except ItemEntradaNF.DoesNotExist as exc:
            raise DomainError('Item da entrada nao encontrado.') from exc

        valor_manual = _decimal_localizado(valor_texto, Decimal('0')).quantize(
            Decimal('0.0001'),
            rounding=ROUND_HALF_UP,
        )
        if valor_manual < 0:
            raise DomainError('Custo manual nao pode ser negativo.')

        valor_atual = (
            item.custo_unitario_manual
            if item.custo_unitario_manual is not None
            else item.custo_unitario_total
        )
        valor_atual = Decimal(str(valor_atual or '0')).quantize(
            Decimal('0.0001'),
            rounding=ROUND_HALF_UP,
        )
        if valor_atual == valor_manual:
            return

        antes = snapshot_modelo(item)
        item.custo_unitario_manual = valor_manual
        item.custo_unitario_total = valor_manual
        item.save(update_fields=[
            'custo_unitario_manual',
            'custo_unitario_total',
            'updated_at',
        ])
        _auditar_entrada(
            request,
            'editar_custo_manual',
            entrada,
            'Custo unitario agregado alterado manualmente',
            justificativa='Custo alterado manualmente na composicao de custo.',
            antes=antes,
            depois=snapshot_modelo(item),
            relacionado=item,
            metadados={
                'item_id': item.pk,
                'numero_item': item.numero_item,
                'produto_id': item.produto_id,
                'valor_anterior': str(valor_atual),
                'valor_manual': str(valor_manual),
                'nao_altera_nf_financeiro': True,
            },
        )
        messages.success(
            request,
            'Custo alterado manualmente. Nao altera a NF nem o financeiro.',
        )

    def _post_remover_custo_unitario_manual(self, request, entrada):
        item_id = request.POST.get('item_id')
        try:
            item = entrada.itens.select_related('produto').get(pk=item_id)
        except ItemEntradaNF.DoesNotExist as exc:
            raise DomainError('Item da entrada nao encontrado.') from exc

        if item.custo_unitario_manual is None:
            return

        with transaction.atomic():
            antes = snapshot_modelo(item)
            valor_manual = item.custo_unitario_manual
            item.custo_unitario_manual = None
            item.save(update_fields=['custo_unitario_manual', 'updated_at'])
            EntradaCustoService.aplicar_configurada(entrada)
            item.refresh_from_db()
            _auditar_entrada(
                request,
                'remover_custo_manual',
                entrada,
                'Custo unitario agregado voltou ao calculo da composicao',
                justificativa='Custo manual removido na composicao de custo.',
                antes=antes,
                depois=snapshot_modelo(item),
                relacionado=item,
                metadados={
                    'item_id': item.pk,
                    'numero_item': item.numero_item,
                    'produto_id': item.produto_id,
                    'valor_manual': str(valor_manual),
                    'valor_calculado': str(item.custo_unitario_total),
                    'nao_altera_nf_financeiro': True,
                },
            )
        messages.success(request, 'Custo manual removido. O item voltou ao custo calculado.')

    def get(self, request, pk):
        entrada = self.get_entrada(request, pk)
        sem_produto = _itens_ativos_sem_produto(entrada).count()
        permitir_sem_produto = request.GET.get('permitir_sem_produto') == '1'
        if sem_produto and not permitir_sem_produto:
            messages.error(
                request,
                f'Vincule ou remova {sem_produto} item(ns) sem produto antes de continuar para custos.',
            )
            return redirect('compras:entrada-conferencia', pk=entrada.pk)
        try:
            params = self._parametros(entrada, request.GET)
            composicao = EntradaCustoService.compor(entrada, **params)
        except (DomainError, InvalidOperation, ValueError) as exc:
            messages.error(request, f'Nao foi possivel calcular o custo: {exc}')
            params = {
                'metodo_rateio': entrada.custo_rateio_metodo,
                'incluir_ipi': entrada.custo_incluir_ipi,
                'incluir_icms_st': entrada.custo_incluir_icms_st,
                'incluir_icms': entrada.custo_incluir_icms,
                'custo_financeiro': entrada.custo_financeiro or Decimal('0'),
                'usar_apenas_valor_nota': entrada.custo_usar_apenas_valor_nota,
            }
            composicao = {
                'linhas': [],
                'resumo': {
                    'valor_mercadoria': Decimal('0'),
                    'frete': Decimal('0'),
                    'seguro': Decimal('0'),
                    'outras_despesas': Decimal('0'),
                    'desconto': Decimal('0'),
                    'ipi': Decimal('0'),
                    'icms_st': Decimal('0'),
                    'icms_nao_recuperavel': Decimal('0'),
                    'custo_financeiro': Decimal('0'),
                    'custo_total': Decimal('0'),
                    'alertas_custo': 0,
                    'alertas_custo_criticos': 0,
                },
                'alertas_custo': [],
                'metodo_efetivo': params['metodo_rateio'],
                'aviso_rateio': '',
                **params,
            }
        self._preparar_linhas(composicao)
        linhas_composicao = composicao.get('linhas', [])
        linhas_varios_count = sum(
            1
            for linha in linhas_composicao
            if getattr(linha.item, 'custo_modo', 'unico') == 'varios'
        )
        linhas_unico_count = len(linhas_composicao) - linhas_varios_count
        cost_mode_default = 'unico' if linhas_unico_count else 'varios'

        return render(request, self.template_name, {
            'entrada': entrada,
            'composicao': composicao,
            'resumo_executivo_custo': _resumo_executivo_custo(entrada, composicao),
            'alertas_custo_especificos': _alertas_custo_especificos(entrada, composicao),
            'metodos_rateio': EntradaNF.MetodoRateioCusto.choices,
            'pode_aplicar_custo': _entrada_aberta(entrada),
            'permissoes_compras': _permissoes_compras(request),
            'sem_produto_count': sem_produto,
            'linhas_unico_count': linhas_unico_count,
            'linhas_varios_count': linhas_varios_count,
            'cost_mode_default': cost_mode_default,
        })

    def post(self, request, pk):
        entrada = self.get_entrada(request, pk)
        if not _entrada_aberta(entrada):
            messages.error(request, 'Entrada fechada nao permite alterar composicao de custo.')
            return redirect('compras:entrada-custos', pk=entrada.pk)
        sem_produto = _itens_ativos_sem_produto(entrada).count()
        if sem_produto:
            messages.error(
                request,
                f'Vincule ou remova {sem_produto} item(ns) sem produto antes de continuar para custos.',
            )
            return redirect('compras:entrada-conferencia', pk=entrada.pk)
        acao = request.POST.get('acao')
        if acao == 'editar_custo_unitario_manual':
            try:
                self._post_custo_unitario_manual(request, entrada)
            except (DomainError, InvalidOperation, ValueError) as exc:
                messages.error(request, f'Nao foi possivel alterar o custo manual: {exc}')
            return redirect('compras:entrada-custos', pk=entrada.pk)
        if acao == 'remover_custo_unitario_manual':
            try:
                self._post_remover_custo_unitario_manual(request, entrada)
            except (DomainError, InvalidOperation, ValueError) as exc:
                messages.error(request, f'Nao foi possivel voltar o custo ao calculo: {exc}')
            return redirect('compras:entrada-custos', pk=entrada.pk)
        try:
            antes = snapshot_modelo(entrada)
            campos = [
                'valor_frete',
                'valor_seguro',
                'valor_outras_despesas',
                'valor_desconto',
                'valor_ipi',
                'valor_icms_st',
                'valor_icms',
            ]
            for campo in campos:
                valor = _decimal_localizado(request.POST.get(campo), getattr(entrada, campo) or Decimal('0'))
                if valor < 0:
                    raise DomainError('Valores de custo nao podem ser negativos.')
                setattr(entrada, campo, valor)
            entrada.valor_total = (
                entrada.valor_produtos
                + entrada.valor_frete
                + entrada.valor_seguro
                + entrada.valor_outras_despesas
                + entrada.valor_ipi
                + entrada.valor_icms_st
                - entrada.valor_desconto
            )
            entrada.save(update_fields=[
                'valor_frete',
                'valor_seguro',
                'valor_outras_despesas',
                'valor_desconto',
                'valor_ipi',
                'valor_icms_st',
                'valor_icms',
                'valor_total',
                'updated_at',
            ])
            params = self._parametros(entrada, request.POST)
            composicao = EntradaCustoService.compor(
                entrada,
                **params,
                salvar=True,
                salvar_configuracao=True,
            )
            entrada.refresh_from_db()
            _auditar_entrada(
                request,
                'editar',
                entrada,
                'Composicao de custo aplicada aos itens',
                justificativa=request.POST.get('justificativa') or 'Revisao de composicao de custo',
                antes=antes,
                depois=snapshot_modelo(entrada),
                metadados={
                    'campos_componentes': campos,
                    'metodo_rateio': params['metodo_rateio'],
                    'metodo_efetivo': composicao.get('metodo_efetivo'),
                    'custo_total': str((composicao.get('resumo') or {}).get('custo_total') or '0'),
                },
            )
            messages.success(request, 'Parametros, componentes e custo dos itens recalculados.')
        except (DomainError, InvalidOperation, ValueError) as exc:
            messages.error(request, f'Nao foi possivel aplicar o custo: {exc}')
        return redirect('compras:entrada-custos', pk=entrada.pk)


class EntradaNFFinalizacaoView(EntradaNFDetailView):
    template_name = 'compras/entrada/finalizacao.html'

    def get(self, request, pk):
        entrada = self.get_entrada(request, pk)
        itens = list(
            entrada.itens
            .select_related('produto', 'produto__unidade_medida', 'lote_gerado')
            .prefetch_related('produtos_gerados')
            .order_by('numero_item', 'pk')
        )
        for item in itens:
            _avaliar_diferenca_item_para_tela(item)
            item.quantidade_movimenta = _quantidade_recebida_item(item)
            item.item_recusado = item.produto_id and item.quantidade_movimenta <= 0
        hoje = timezone.localdate()
        bloqueios = []
        avisos = []
        informacoes = []
        itens_problematicos = []
        alertas_custo = []
        alertas_custo_criticos = []
        resumo_final = {
            'total_itens': len(itens),
            'vinculados': 0,
            'sem_produto': 0,
            'movimentam': 0,
            'recusados': 0,
            'divergencias': 0,
            'lotes_pendentes': 0,
            'validades_pendentes': 0,
            'validades_vencidas': 0,
            'custo_critico': 0,
            'componentes_custo': Decimal('0'),
            'custo_total': Decimal('0'),
        }
        if not itens:
            bloqueios.append('Entrada sem itens.')
        sem_produto = [item for item in itens if not _item_tem_vinculo_estoque(item)]
        resumo_final['sem_produto'] = len(sem_produto)
        resumo_final['vinculados'] = len(itens) - len(sem_produto)
        resumo_final['movimentam'] = sum(
            1 for item in itens
            if _item_tem_vinculo_estoque(item) and not item.item_recusado and item.quantidade_movimenta > 0
        )
        resumo_final['recusados'] = sum(1 for item in itens if item.item_recusado)
        if sem_produto:
            bloqueios.append(f'{len(sem_produto)} item(ns) sem produto interno vinculado.')
        diferencas_bloqueantes = [item for item in itens if item.diferenca_bloqueante]
        resumo_final['divergencias'] = sum(1 for item in itens if item.diferenca_tipo)
        if diferencas_bloqueantes:
            bloqueios.append(f'{len(diferencas_bloqueantes)} diferenca(s) bloqueante(s) pendente(s).')
        lotes_pendentes = [
            item for item in itens
            if item.produto_id and _quantidade_recebida_item(item) > 0
            and item.produto.controla_lote and not item.numero_lote
        ]
        resumo_final['lotes_pendentes'] = len(lotes_pendentes)
        if lotes_pendentes:
            bloqueios.append(f'{len(lotes_pendentes)} item(ns) com lote obrigatorio pendente.')
        validades_pendentes = [
            item for item in itens
            if item.produto_id and _quantidade_recebida_item(item) > 0
            and item.produto.controla_validade and not item.data_validade
        ]
        resumo_final['validades_pendentes'] = len(validades_pendentes)
        if validades_pendentes:
            bloqueios.append(f'{len(validades_pendentes)} item(ns) com validade obrigatoria pendente.')
        validades_vencidas = [
            item for item in itens
            if item.produto_id and _quantidade_recebida_item(item) > 0
            and item.produto.controla_validade
            and item.data_validade and item.data_validade < hoje
        ]
        resumo_final['validades_vencidas'] = len(validades_vencidas)
        if validades_vencidas:
            bloqueios.append(f'{len(validades_vencidas)} item(ns) com validade vencida.')
        validades_proximas = [
            item for item in itens
            if item.produto_id and _quantidade_recebida_item(item) > 0
            and item.produto.controla_validade
            and item.data_validade and item.data_validade >= hoje
            and item.produto.dias_aviso_vencimento is not None
            and (item.data_validade - hoje).days <= item.produto.dias_aviso_vencimento
        ]
        if validades_proximas:
            avisos.append(f'{len(validades_proximas)} item(ns) com validade proxima do vencimento.')
        if entrada.fornecedor_pendente:
            avisos.append('Fornecedor ainda pendente. Pode continuar, mas fica marcado para revisao.')
        if entrada.destinatario_documento_diferente:
            avisos.append('Documento destinatario diferente da filial. E apenas alerta operacional.')
        try:
            composicao_custo = EntradaCustoService.compor(
                entrada=entrada,
                metodo_rateio=entrada.custo_rateio_metodo,
                incluir_ipi=entrada.custo_incluir_ipi,
                incluir_icms_st=entrada.custo_incluir_icms_st,
                incluir_icms=entrada.custo_incluir_icms,
                custo_financeiro=entrada.custo_financeiro or Decimal('0'),
                usar_apenas_valor_nota=entrada.custo_usar_apenas_valor_nota,
            )
            custo_por_item = {
                linha.item.pk: linha.custo_unitario
                for linha in composicao_custo['linhas']
            }
            for item in itens:
                item.custo_unitario_preview = custo_por_item.get(item.pk, item.custo_unitario_total)
                if item.item_recusado:
                    item.custo_unitario_preview = Decimal('0')
            alertas_custo = composicao_custo.get('alertas_custo', [])
            if alertas_custo:
                alertas_custo_criticos = [
                    linha for linha in alertas_custo
                    if linha.alerta_custo_nivel == 'critico'
                ]
                resumo_final['custo_critico'] = len(alertas_custo_criticos)
                avisos.append(
                    f'{len(alertas_custo)} item(ns) com custo fora da referencia '
                    f'({len(alertas_custo_criticos)} critico(s)). Revise Custos antes de finalizar.'
                )
            resumo_final['componentes_custo'] = (
                (composicao_custo['resumo']['frete'] or Decimal('0'))
                + (composicao_custo['resumo']['seguro'] or Decimal('0'))
                + (composicao_custo['resumo']['outras_despesas'] or Decimal('0'))
                - (composicao_custo['resumo']['desconto'] or Decimal('0'))
                + (composicao_custo['resumo']['ipi'] or Decimal('0'))
                + (composicao_custo['resumo']['icms_st'] or Decimal('0'))
                + (composicao_custo['resumo']['icms_nao_recuperavel'] or Decimal('0'))
                + (composicao_custo['resumo']['custo_financeiro'] or Decimal('0'))
            )
            resumo_final['custo_total'] = composicao_custo['resumo']['custo_total']
            resumo_executivo_custo = _resumo_executivo_custo(entrada, composicao_custo)
            alertas_custo_especificos = _alertas_custo_especificos(entrada, composicao_custo)
            resumo_final.update({
                'custo_mercadorias': resumo_executivo_custo['custo_produtos'],
                'custo_acrescimos': resumo_executivo_custo['acrescimos'],
                'custo_descontos': resumo_executivo_custo['descontos'],
                'custo_final': resumo_executivo_custo['custo_final'],
                'custo_diferenca_nota': resumo_executivo_custo['diferenca_total_nota'],
                'impostos_no_custo': resumo_executivo_custo['impostos_nao_recuperaveis'],
                'impostos_fora_custo': resumo_executivo_custo['impostos_recuperaveis'],
            })
            for alerta in alertas_custo_especificos:
                avisos.append(alerta['texto'])
            if any([
                entrada.valor_frete,
                entrada.valor_seguro,
                entrada.valor_outras_despesas,
                entrada.valor_desconto,
                entrada.valor_ipi,
                entrada.valor_icms_st,
                entrada.custo_financeiro,
            ]):
                avisos.append('A entrada tem componentes fiscais/financeiros que alteram o custo. Revise a tela Custos antes de finalizar.')
        except DomainError as exc:
            composicao_custo = None
            resumo_executivo_custo = None
            alertas_custo_especificos = []
            bloqueios.append(f'Composicao de custo invalida: {exc}')
        total_parcelas = sum(
            (parcela.valor for parcela in entrada.parcelas_financeiras.all()),
            Decimal('0'),
        )
        if not total_parcelas:
            avisos.append('Nenhuma parcela financeira informada. Finaliza estoque, mas o contas a pagar fica para revisao manual.')
        elif total_parcelas != entrada.valor_total:
            avisos.append('Total das parcelas financeiras diferente do total da nota. Revise antes de gerar contas a pagar.')
        else:
            informacoes.append('Total financeiro bate com o total da nota.')

        for item in itens:
            problemas = []
            proximas_acoes = []
            prioridade = 90
            if not item.produto_id:
                problemas.append('Sem produto interno')
                proximas_acoes.append('Vincular produto')
                prioridade = min(prioridade, 10)
            if getattr(item, 'diferenca_tipo', ''):
                problemas.append(item.diferenca_descricao or 'Divergencia de conferencia')
                proximas_acoes.append('Resolver divergencia')
                prioridade = min(prioridade, 20 if item.diferenca_bloqueante else 50)
            if item in lotes_pendentes:
                problemas.append('Lote obrigatorio pendente')
                proximas_acoes.append('Preencher lote')
                prioridade = min(prioridade, 30)
            if item in validades_pendentes:
                problemas.append('Validade obrigatoria pendente')
                proximas_acoes.append('Preencher validade')
                prioridade = min(prioridade, 35)
            if item in validades_vencidas:
                problemas.append('Validade vencida')
                proximas_acoes.append('Corrigir validade')
                prioridade = min(prioridade, 25)
            custo_critico = any(linha.item.pk == item.pk for linha in alertas_custo_criticos)
            if custo_critico:
                problemas.append('Custo critico')
                proximas_acoes.append('Revisar custo')
                prioridade = min(prioridade, 45)
            item.finalizacao_problemas = problemas
            item.finalizacao_proxima_acao = ' / '.join(dict.fromkeys(proximas_acoes)) or 'Revisado'
            item.finalizacao_prioridade = prioridade
            if problemas:
                itens_problematicos.append(item)
        itens_problematicos.sort(key=lambda item: (item.finalizacao_prioridade, item.numero_item or 0, item.pk))

        if bloqueios:
            painel_finalizacao = {
                'nivel': 'red',
                'titulo': 'Bloqueado para efetivar',
                'descricao': 'Resolva as pendencias obrigatorias antes de criar movimentos, lotes e custo medio.',
                'acao': 'Resolver pendencias',
            }
        elif alertas_custo_criticos or avisos:
            painel_finalizacao = {
                'nivel': 'amber',
                'titulo': 'Exige atencao e confirmacao',
                'descricao': 'A entrada pode seguir, mas ha alertas que precisam de aceite explicito.',
                'acao': 'Confirmar e efetivar',
            }
        else:
            painel_finalizacao = {
                'nivel': 'green',
                'titulo': 'Pronto para efetivar',
                'descricao': 'Todos os pontos obrigatorios estao revisados para movimentar estoque.',
                'acao': 'Efetivar entrada',
            }
        informacoes.append(f'{resumo_final["movimentam"]} item(ns) vao movimentar estoque nesta filial.')

        return render(request, self.template_name, {
            'entrada': entrada,
            'itens': itens,
            'itens_problematicos': itens_problematicos,
            'bloqueios': bloqueios,
            'avisos': avisos,
            'informacoes': informacoes,
            'painel_finalizacao': painel_finalizacao,
            'total_parcelas': total_parcelas,
            'composicao_custo': composicao_custo,
            'resumo_executivo_custo': resumo_executivo_custo,
            'alertas_custo_especificos': alertas_custo_especificos,
            'alertas_custo': alertas_custo,
            'alertas_custo_criticos': alertas_custo_criticos,
            'confirmacao_custo_critico_obrigatoria': bool(alertas_custo_criticos),
            'confirmacao_custo_composto_obrigatoria': _entrada_exige_confirmacao_custo_composto(entrada),
            'resumo_final': resumo_final,
            'pode_finalizar_visualmente': entrada.pode_efetivar and not bloqueios,
            'pode_efetivar_entrada': request.user.tem_permissao('compras', 'aprovar'),
            'permissoes_compras': _permissoes_compras(request),
        })


class AdicionarItemEntradaView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'editar'

    def _post_item_manual(self, post, index):
        dados = {}
        for campo in AdicionarItemEntradaForm.base_fields:
            valores = post.getlist(campo)
            dados[campo] = valores[index] if len(valores) > index else post.get(campo, '')
        return dados

    def _adicionar_item_manual(self, entrada, form):
        CompraService.adicionar_item_entrada(
            entrada=entrada,
            produto=form.cleaned_data['produto'],
            quantidade=form.cleaned_data['quantidade'],
            valor_unitario=form.cleaned_data['valor_unitario'],
            valor_ipi=form.cleaned_data.get('valor_ipi') or 0,
            valor_icms=form.cleaned_data.get('valor_icms') or 0,
            numero_lote=form.cleaned_data.get('numero_lote', ''),
            data_fabricacao=form.cleaned_data.get('data_fabricacao'),
            data_validade=form.cleaned_data.get('data_validade'),
            ean_xml=form.cleaned_data.get('ean_xml', ''),
            codigo_produto_fornecedor=form.cleaned_data.get('codigo_produto_fornecedor', ''),
            descricao_xml=form.cleaned_data.get('descricao_xml', ''),
            unidade_xml=form.cleaned_data.get('unidade_xml', ''),
            fator_conversao=form.cleaned_data.get('fator_conversao') or Decimal('1'),
            quantidade_recebida=form.cleaned_data.get('quantidade_recebida'),
        )

    def post(self, request, pk):
        entrada = get_object_or_404(EntradaNF.objects.for_filial(request.filial_ativa), pk=pk)
        destino = 'compras:entrada-conferencia' if request.POST.get('next') == 'conferencia' else 'compras:entrada-detail'
        if not _entrada_aberta(entrada):
            messages.error(request, 'Entrada efetivada nao permite adicionar itens.')
            return redirect(destino, pk=entrada.pk)
        total_linhas = max(1, len(request.POST.getlist('produto')))
        adicionados = 0
        for index in range(total_linhas):
            dados = self._post_item_manual(request.POST, index)
            if not any(str(dados.get(campo, '')).strip() for campo in ('produto', 'quantidade', 'numero_lote', 'data_validade')):
                continue
            form = AdicionarItemEntradaForm(dados, filial=request.filial_ativa)
            if form.is_valid():
                try:
                    self._adicionar_item_manual(entrada, form)
                    adicionados += 1
                except DomainError as e:
                    messages.error(request, f'Linha {index + 1}: {e}')
            else:
                for erro in form.non_field_errors():
                    messages.error(request, f'Linha {index + 1}: {erro}')
                messages.error(request, f'Linha {index + 1}: verifique os dados do item.')
        if adicionados:
            messages.success(request, f'{adicionados} item(ns) adicionado(s).')
        elif total_linhas > 1:
            messages.error(request, 'Nenhum item valido para adicionar.')
        return redirect(destino, pk=pk)


class RemoverItemEntradaView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'editar'

    def post(self, request, pk, item_id):
        entrada = get_object_or_404(EntradaNF.objects.for_filial(request.filial_ativa), pk=pk)
        item = get_object_or_404(entrada.itens.select_related('produto'), pk=item_id)
        if ITEM_REMOVIDO_ENTRADA in (item.observacao or ''):
            messages.info(request, 'Este item ja esta removido da entrada.')
            if request.POST.get('next') == 'conferencia':
                return redirect('compras:entrada-conferencia', pk=entrada.pk)
            return redirect('compras:entrada-detail', pk=entrada.pk)
        try:
            antes = snapshot_modelo(entrada)
            itens_para_remover = _itens_grupo_divisao_manual(entrada, item)
            snapshots = []
            with transaction.atomic():
                for item_grupo in itens_para_remover:
                    snapshots.append((item_grupo, CompraService.remover_item_entrada(item_grupo)))
            entrada.refresh_from_db()
            depois = snapshot_modelo(entrada)
            for item_grupo, item_snapshot in snapshots:
                _auditar_entrada(
                    request,
                    'remover_item',
                    entrada,
                    (
                        f"Item {item_snapshot.get('numero_item')} removido da NF "
                        f"{entrada.numero_nf}/{entrada.serie_nf}"
                    ),
                    justificativa=request.POST.get('motivo', 'Remocao manual de item da entrada.'),
                    antes=antes,
                    depois=depois,
                    relacionado=item_grupo,
                    metadados={'item_removido': item_snapshot},
                )
            if len(snapshots) > 1:
                messages.success(request, 'Todos os lotes deste item foram removidos e registrados na auditoria.')
            else:
                messages.success(request, 'Item removido da entrada e registrado na auditoria.')
        except DomainError as e:
            messages.error(request, str(e))
        if request.POST.get('next') == 'conferencia':
            return redirect('compras:entrada-conferencia', pk=entrada.pk)
        return redirect('compras:entrada-detail', pk=entrada.pk)


class RestaurarItemEntradaView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'editar'

    def post(self, request, pk, log_id):
        entrada = get_object_or_404(EntradaNF.objects.for_filial(request.filial_ativa), pk=pk)
        log = get_object_or_404(
            RegistroAuditoria.objects.filter(
                objeto_tipo=entrada._meta.label_lower,
                objeto_id=entrada.pk,
                acao='remover_item',
            ),
            pk=log_id,
        )
        item_snapshot = (log.metadados or {}).get('item_removido') or {}
        logs_grupo = _logs_grupo_divisao_removida(entrada, item_snapshot)
        ids_logs_grupo = [log_grupo.pk for log_grupo in logs_grupo] or [log.pk]
        ids_restaurados = _ids_remocoes_restauradas(entrada)
        if any(log_id in ids_restaurados for log_id in ids_logs_grupo):
            messages.info(request, 'Este item ja foi restaurado.')
        else:
            if not item_snapshot:
                messages.error(request, 'Nao encontrei os dados do item removido para restaurar.')
            else:
                antes = snapshot_modelo(entrada)
                try:
                    snapshots_grupo = [
                        (log_grupo.metadados or {}).get('item_removido') or {}
                        for log_grupo in logs_grupo
                    ]
                    item = CompraService.restaurar_item_entrada(
                        entrada,
                        item_snapshot,
                        snapshots_grupo=snapshots_grupo,
                    )
                    entrada.refresh_from_db()
                    _auditar_entrada(
                        request,
                        'restaurar_item',
                        entrada,
                        f'Item {item.numero_item} restaurado na NF {entrada.numero_nf}/{entrada.serie_nf}',
                        justificativa='Restauracao manual de item removido da entrada.',
                        antes=antes,
                        depois=snapshot_modelo(entrada),
                        relacionado=item,
                        metadados={
                            'item_restaurado': snapshot_modelo(item),
                            'item_removido_log_id': log.pk,
                            'item_removido_log_ids': ids_logs_grupo,
                        },
                    )
                    messages.success(request, 'Item restaurado na entrada.')
                except DomainError as e:
                    messages.error(request, str(e))
                except Exception:
                    logger.exception(
                        'Falha inesperada ao restaurar item removido da entrada',
                        extra={
                            'entrada_id': entrada.pk,
                            'log_id': log.pk,
                            'logs_grupo': ids_logs_grupo,
                        },
                    )
                    messages.error(
                        request,
                        'Nao foi possivel restaurar este item agora. O erro foi registrado para correcao.',
                    )
        if request.POST.get('next') == 'conferencia':
            return redirect('compras:entrada-conferencia', pk=entrada.pk)
        return redirect('compras:entrada-detail', pk=entrada.pk)


class EfetivarEntradaView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'aprovar'

    def post(self, request, pk):
        entrada = get_object_or_404(EntradaNF.objects.for_filial(request.filial_ativa), pk=pk)
        if request.POST.get('confirmar_resumo_final') != '1':
            messages.error(
                request,
                'Confirme a revisao final da entrada antes de efetivar.',
            )
            return redirect('compras:entrada-finalizacao', pk=pk)
        if _entrada_exige_confirmacao_custo_composto(entrada) and request.POST.get('confirmar_custo_composto') != '1':
            messages.error(
                request,
                'Confirme a revisao dos componentes de custo antes de efetivar a entrada.',
            )
            return redirect('compras:entrada-finalizacao', pk=pk)
        try:
            antes = snapshot_modelo(entrada)
            CompraService.efetivar_entrada(
                entrada,
                request.user,
                confirmar_custo_critico=request.POST.get('confirmar_custo_critico') == '1',
            )
            entrada.refresh_from_db()
            resultado = _resultado_efetivacao_entrada(request, entrada)
            _auditar_entrada(
                request,
                'efetivar',
                entrada,
                f'Entrada NF {entrada.numero_nf}/{entrada.serie_nf} efetivada',
                antes=antes,
                depois=snapshot_modelo(entrada),
                metadados={
                    'produtos_movimentados': resultado['produtos_movimentados'] if resultado else 0,
                    'quantidade_total': str(resultado['quantidade_total']) if resultado else '0',
                    'custo_total': str(resultado['custo_total']) if resultado else '0',
                },
            )
            messages.success(
                request,
                (
                    f"Entrada efetivada: {resultado['produtos_movimentados']} produto(s), "
                    f"{resultado['quantidade_total']} unidade(s), "
                    f"R$ {resultado['custo_total_formatado']} custo total"
                ),
            )
        except DomainError as e:
            messages.error(request, str(e))
        return redirect('compras:entrada-detail', pk=pk)


class EstornarEntradaView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'cancelar'
    template_name = 'compras/entrada/estorno.html'

    def get(self, request, pk):
        entrada = get_object_or_404(
            EntradaNF.objects.for_filial(request.filial_ativa).select_related('fornecedor'),
            pk=pk,
        )
        impacto = calcular_impacto_estorno_entrada(entrada)
        return render(request, self.template_name, {
            'entrada': entrada,
            'impacto': impacto,
        })

    def post(self, request, pk):
        entrada = get_object_or_404(
            EntradaNF.objects.for_filial(request.filial_ativa).select_related('fornecedor'),
            pk=pk,
        )
        motivo = request.POST.get('motivo', '').strip()
        if not motivo:
            messages.error(request, 'Informe a justificativa para cancelar a entrada.')
            return redirect('compras:entrada-estorno', pk=entrada.pk)
        try:
            antes = snapshot_modelo(entrada)
            entrada, movimentos = estornar_entrada(entrada, request.user, motivo)
            _auditar_entrada(
                request,
                'cancelar',
                entrada,
                f'Entrada NF {entrada.numero_nf}/{entrada.serie_nf} cancelada com reversao de estoque',
                justificativa=motivo,
                antes=antes,
                depois=snapshot_modelo(entrada),
                metadados={
                    'movimentos_estorno': [mov.pk for mov in movimentos],
                    'quantidade_movimentos': len(movimentos),
                },
            )
            messages.success(request, f'Entrada cancelada com {len(movimentos)} movimento(s) de reversao.')
            return redirect('compras:entrada-detail', pk=entrada.pk)
        except DomainError as exc:
            messages.error(request, str(exc))
            return redirect('compras:entrada-estorno', pk=entrada.pk)


def _movimentacoes_entrada_url(entrada: EntradaNF) -> str:
    return (
        f"{reverse('estoque:movimentacao-list')}"
        f"?documento_tipo={MovimentacaoEstoque.DocumentoTipo.NFE}"
        f"&documento_id={entrada.pk}"
    )


def _resultado_efetivacao_entrada(request, entrada: EntradaNF, itens=None) -> dict | None:
    if entrada.status not in (EntradaNF.Status.EFETIVADA, EntradaNF.Status.ESTORNADA):
        return None

    itens = list(itens) if itens is not None else list(
        entrada.itens.select_related('produto', 'produto__unidade_medida', 'lote_gerado')
    )
    movimentos = list(
        MovimentacaoEstoque.objects.for_filial(entrada.filial)
        .filter(
            documento_tipo=MovimentacaoEstoque.DocumentoTipo.NFE,
            documento_id=entrada.pk,
        )
        .select_related('produto', 'lote', 'usuario')
        .order_by('produto__descricao', 'pk')
    )
    movimentos_estorno = list(
        MovimentacaoEstoque.objects.for_filial(entrada.filial)
        .filter(
            documento_tipo=MovimentacaoEstoque.DocumentoTipo.ESTORNO_ENTRADA,
            documento_id=entrada.pk,
        )
        .select_related('produto', 'lote', 'usuario')
        .order_by('produto__descricao', 'pk')
    )
    lotes_ids = [item.lote_gerado_id for item in itens if item.lote_gerado_id]
    lotes = list(
        LoteProduto.objects.for_filial(entrada.filial)
        .filter(pk__in=lotes_ids)
        .select_related('produto')
        .order_by('produto__descricao', 'numero_lote')
    )
    estoques = {
        estoque.produto_id: estoque
        for estoque in Estoque.objects.filter(
            filial=entrada.filial,
            produto_id__in=[item.produto_id for item in itens if item.produto_id],
        )
    }

    itens_movimentados = []
    itens_recusados = []
    custo_total = Decimal('0')
    quantidade_total = Decimal('0')
    for item in itens:
        item.quantidade_movimenta = _quantidade_recebida_item(item)
        item.item_recusado = (
            item.produto_id
            and item.quantidade_movimenta <= 0
            and bool(item.justificativa_diferenca)
        )
        item.custo_total_efetivado = (
            (item.custo_unitario_total or Decimal('0')) * item.quantidade_movimenta
            if item.quantidade_movimenta > 0
            else Decimal('0')
        )
        item.estoque_custo_medio = (
            estoques[item.produto_id].custo_medio
            if item.produto_id in estoques
            else None
        )
        if item.produto_id:
            item.extrato_produto_url = (
                f"{reverse('estoque:movimentacao-list')}?produto={item.produto_id}"
            )
            item.movimentacoes_nota_url = _movimentacoes_entrada_url(entrada)
        if item.item_recusado:
            itens_recusados.append(item)
        elif item.produto_id and item.quantidade_movimenta > 0:
            itens_movimentados.append(item)
            quantidade_total += item.quantidade_movimenta
            custo_total += item.custo_total_efetivado

    custo_total_formatado = f'{custo_total:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return {
        'movimentacoes_url': _movimentacoes_entrada_url(entrada),
        'movimentacoes': movimentos,
        'movimentacoes_estorno': movimentos_estorno,
        'movimentos_count': len(movimentos),
        'movimentos_estorno_count': len(movimentos_estorno),
        'lotes': lotes,
        'lotes_count': len(lotes),
        'itens_movimentados': itens_movimentados,
        'itens_recusados': itens_recusados,
        'recusados_count': len(itens_recusados),
        'produtos_movimentados': len({item.produto_id for item in itens_movimentados}),
        'quantidade_total': quantidade_total.normalize() if quantidade_total else Decimal('0'),
        'custo_total': custo_total,
        'custo_total_formatado': custo_total_formatado,
        'estornada': entrada.status == EntradaNF.Status.ESTORNADA,
    }


def _entrada_exige_confirmacao_custo_composto(entrada: EntradaNF) -> bool:
    componentes = [
        entrada.valor_frete,
        entrada.valor_seguro,
        entrada.valor_outras_despesas,
        entrada.valor_desconto,
        entrada.valor_ipi,
        entrada.valor_icms_st,
        entrada.valor_icms,
        entrada.custo_financeiro,
    ]
    return any(Decimal(str(valor or '0')) != 0 for valor in componentes)


def _resumo_executivo_custo(entrada: EntradaNF, composicao: dict) -> dict:
    resumo = composicao.get('resumo') or {}
    zero = Decimal('0')
    custo_produtos = Decimal(str(resumo.get('valor_mercadoria') or zero))
    despesas_custo = (
        Decimal(str(resumo.get('frete') or zero))
        + Decimal(str(resumo.get('seguro') or zero))
        + Decimal(str(resumo.get('outras_despesas') or zero))
        + Decimal(str(resumo.get('custo_financeiro') or zero))
    )
    impostos_nao_recuperaveis = (
        Decimal(str(resumo.get('ipi') or zero))
        + Decimal(str(resumo.get('icms_st') or zero))
        + Decimal(str(resumo.get('icms_nao_recuperavel') or zero))
    )
    impostos_recuperaveis = (
        (Decimal(str(entrada.valor_ipi or zero)) if not composicao.get('incluir_ipi') else zero)
        + (Decimal(str(entrada.valor_icms_st or zero)) if not composicao.get('incluir_icms_st') else zero)
        + (Decimal(str(entrada.valor_icms or zero)) if not composicao.get('incluir_icms') else zero)
    )
    descontos = Decimal(str(resumo.get('desconto') or zero))
    acrescimos = despesas_custo + impostos_nao_recuperaveis
    custo_final = Decimal(str(resumo.get('custo_total') or zero))
    custo_antes_desconto = custo_final + descontos
    total_nota = Decimal(str(entrada.valor_total or zero))
    return {
        'custo_produtos': custo_produtos,
        'despesas_custo': despesas_custo,
        'impostos_nao_recuperaveis': impostos_nao_recuperaveis,
        'impostos_recuperaveis': impostos_recuperaveis,
        'descontos': descontos,
        'acrescimos': acrescimos,
        'custo_final': custo_final,
        'custo_antes_desconto': custo_antes_desconto,
        'total_nota': total_nota,
        'diferenca_total_nota': custo_final - total_nota,
    }


def _alertas_custo_especificos(entrada: EntradaNF, composicao: dict) -> list[dict]:
    alertas = []
    zero = Decimal('0')
    if Decimal(str(entrada.valor_icms or zero)) > 0 and composicao.get('incluir_icms'):
        alertas.append({
            'nivel': 'amber',
            'titulo': 'ICMS como custo',
            'texto': 'ICMS marcado como custo, confirme se e nao recuperavel.',
        })
    if Decimal(str(entrada.valor_icms_st or zero)) > 0 and not composicao.get('incluir_icms_st'):
        alertas.append({
            'nivel': 'red',
            'titulo': 'ST fora do custo',
            'texto': 'ST sem inclusao no custo.',
        })
    if Decimal(str(entrada.valor_frete or zero)) > 0 and not entrada.custo_composto_em:
        alertas.append({
            'nivel': 'amber',
            'titulo': 'Frete pendente',
            'texto': 'Frete informado mas nao revisado.',
        })
    if (
        composicao.get('metodo_rateio') == EntradaNF.MetodoRateioCusto.PESO
        and composicao.get('metodo_efetivo') != EntradaNF.MetodoRateioCusto.PESO
    ):
        alertas.append({
            'nivel': 'amber',
            'titulo': 'Rateio por peso indisponivel',
            'texto': 'Produto sem peso usando fallback de rateio.',
        })
    return alertas


class CancelarEntradaView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'cancelar'

    def post(self, request, pk):
        entrada = get_object_or_404(EntradaNF.objects.for_filial(request.filial_ativa), pk=pk)
        motivo = request.POST.get('motivo', '').strip()
        if not motivo:
            messages.error(request, 'Informe a justificativa para cancelar a entrada.')
            return redirect('compras:entrada-detail', pk=pk)
        try:
            antes = snapshot_modelo(entrada)
            CompraService.cancelar_entrada(entrada, request.user, motivo)
            entrada.refresh_from_db()
            _auditar_entrada(
                request,
                'cancelar',
                entrada,
                f'Entrada NF {entrada.numero_nf}/{entrada.serie_nf} cancelada',
                justificativa=motivo,
                antes=antes,
                depois=snapshot_modelo(entrada),
            )
            messages.success(request, 'Entrada cancelada.')
        except DomainError as e:
            messages.error(request, str(e))
        return redirect('compras:entrada-detail', pk=pk)
