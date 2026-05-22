"""Rastreabilidade bidirecional de lotes."""
from django.db.models import Q
from django.shortcuts import render
from django.views import View

from apps.core.services.permissions import PermissaoRequiredMixin
from apps.compras.models import ItemEntradaNF
from apps.estoque.models import LoteProduto, MovimentacaoEstoque
from apps.vendas.models import ItemSeparacao


class LoteRastreabilidadeView(PermissaoRequiredMixin, View):
    permissao_modulo = 'estoque'
    template_name = 'lotes/rastreabilidade.html'

    def get(self, request):
        filial = request.filial_ativa
        busca = request.GET.get('q', '').strip()
        lote_selecionado = None
        contexto = {}

        lotes_encontrados = []
        if busca:
            lotes_encontrados = list(
                LoteProduto.objects.for_filial(filial)
                .filter(
                    Q(numero_lote__icontains=busca)
                    | Q(produto__descricao__icontains=busca)
                    | Q(produto__codigo__icontains=busca)
                )
                .select_related('produto', 'fornecedor')
                .order_by('data_validade', 'numero_lote')[:20]
            )
            if len(lotes_encontrados) == 1:
                lote_selecionado = lotes_encontrados[0]

        lote_pk = request.GET.get('lote')
        if lote_pk:
            try:
                lote_selecionado = (
                    LoteProduto.objects.for_filial(filial)
                    .select_related('produto', 'fornecedor')
                    .get(pk=lote_pk)
                )
            except LoteProduto.DoesNotExist:
                pass

        if lote_selecionado:
            contexto = self._montar_rastreio(lote_selecionado)

        return render(request, self.template_name, {
            'busca': busca,
            'lotes_encontrados': lotes_encontrados,
            'lote': lote_selecionado,
            **contexto,
        })

    def _montar_rastreio(self, lote):
        # Origem via compra
        item_entrada = (
            ItemEntradaNF.objects
            .filter(lote_gerado=lote)
            .select_related(
                'entrada', 'entrada__fornecedor',
                'produto',
            )
            .order_by('-entrada__data_entrada', '-pk')
            .first()
        )

        # Origem via produção
        ordem_producao = None
        apontamentos = []
        componentes_consumidos = []
        if lote.ordem_producao_id:
            try:
                from apps.producao.models import OrdemProducao, ApontamentoProducao
                ordem_producao = (
                    OrdemProducao.objects
                    .select_related('ficha_tecnica', 'produto_acabado', 'usuario_abertura', 'usuario_encerramento')
                    .get(pk=lote.ordem_producao_id)
                )
                apontamentos = list(
                    ApontamentoProducao.objects
                    .filter(ordem_producao=ordem_producao)
                    .select_related('operador')
                    .order_by('data_hora_inicio')
                )
                if ordem_producao.ficha_tecnica_id:
                    componentes_consumidos = list(
                        ordem_producao.ficha_tecnica.itens
                        .select_related('materia_prima')
                        .all()
                    )
            except Exception:
                pass
        else:
            # Busca OP pelo related_name (ordens_origem)
            op_qs = lote.ordens_origem.select_related(
                'ficha_tecnica', 'produto_acabado', 'usuario_abertura', 'usuario_encerramento'
            ).order_by('-created_at')
            if op_qs.exists():
                ordem_producao = op_qs.first()
                try:
                    from apps.producao.models import ApontamentoProducao
                    apontamentos = list(
                        ApontamentoProducao.objects
                        .filter(ordem_producao=ordem_producao)
                        .select_related('operador')
                        .order_by('data_hora_inicio')
                    )
                    if ordem_producao.ficha_tecnica_id:
                        componentes_consumidos = list(
                            ordem_producao.ficha_tecnica.itens
                            .select_related('materia_prima')
                            .all()
                        )
                except Exception:
                    pass

        # Inspeções
        from apps.lotes.models import InspecaoLote
        inspecoes = list(
            InspecaoLote.objects
            .filter(lote=lote)
            .select_related('responsavel')
            .order_by('-data_inspecao')
        )

        # Movimentações de estoque
        movimentacoes = list(
            MovimentacaoEstoque.objects
            .filter(lote=lote)
            .select_related('usuario')
            .order_by('-created_at')[:30]
        )

        # Destino: separações (saídas para clientes)
        itens_separacao = list(
            ItemSeparacao.objects
            .filter(lote=lote)
            .select_related(
                'separacao',
                'separacao__pedido',
                'separacao__pedido__cliente',
                'separacao__usuario_separador',
                'item_pedido',
            )
            .order_by('-separacao__data_inicio')
        )

        clientes_atendidos = {}
        for item in itens_separacao:
            cliente = item.separacao.pedido.cliente
            if cliente.pk not in clientes_atendidos:
                clientes_atendidos[cliente.pk] = {
                    'cliente': cliente,
                    'pedidos': [],
                    'quantidade_total': 0,
                }
            clientes_atendidos[cliente.pk]['pedidos'].append(item.separacao.pedido)
            clientes_atendidos[cliente.pk]['quantidade_total'] += float(item.quantidade_separada)

        return {
            'item_entrada': item_entrada,
            'ordem_producao': ordem_producao,
            'apontamentos': apontamentos,
            'componentes_consumidos': componentes_consumidos,
            'inspecoes': inspecoes,
            'movimentacoes': movimentacoes,
            'itens_separacao': itens_separacao,
            'clientes_atendidos': list(clientes_atendidos.values()),
        }
