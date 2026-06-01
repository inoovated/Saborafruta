"""Servico de custo medio ponderado.

Compatibilidade para chamadas antigas: entradas agora passam pelo
MovimentacaoService, que e a fonte unica para alterar saldo.
"""
from apps.estoque.models import Estoque, MovimentacaoEstoque
from apps.estoque.services.movimentacao_service import MovimentacaoService
from apps.produtos.models import Produto


class CustoMedioService:

    @staticmethod
    def registrar_entrada(
        produto,
        filial,
        quantidade,
        valor_unitario,
        usuario,
        lote=None,
        documento_tipo='',
        documento_id=None,
        documento_numero='',
        observacao='',
    ):
        """Registra entrada usando o service central de movimentacao."""
        mov = MovimentacaoService.registrar_movimentacao(
            produto_id=produto.pk,
            filial_id=filial.pk,
            tipo_operacao=MovimentacaoEstoque.TipoOperacao.ENTRADA,
            quantidade=quantidade,
            usuario_id=usuario.pk,
            lote_id=lote.pk if lote else None,
            valor_unitario=valor_unitario,
            documento_tipo=documento_tipo,
            documento_id=documento_id,
            documento_numero=documento_numero,
            observacao=observacao,
        )
        estoque = Estoque.objects.get(produto=produto, filial=filial)
        return estoque, mov


def recalcular_custo_medio_global():
    """Recalcula custo medio dos produtos a partir da ultima movimentacao."""
    from django.db.models import OuterRef, Subquery

    ultima_mov = MovimentacaoEstoque.objects.filter(
        produto=OuterRef('pk'),
    ).order_by('-data_movimentacao').values('custo_medio_posterior')[:1]

    Produto.objects.update(
        preco_custo_medio=Subquery(ultima_mov),
    )
    return 'ok'
