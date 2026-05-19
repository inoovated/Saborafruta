"""Rastreabilidade ascendente e descendente.

Ascendente (de produto acabado → matéria-prima):
  Lote produto acabado → OP → Movimentações de consumo → Lotes MP → Fornecedor

Descendente (de matéria-prima → cliente final):
  Lote MP → OPs que consumiram → Lotes PA gerados → Vendas → Cliente
"""
from apps.estoque.models import LoteProduto, MovimentacaoEstoque
from apps.estoque.constants.enums import TipoOperacaoMovimentacao


class RastreabilidadeService:

    @staticmethod
    def ascendente(lote_produto_acabado: LoteProduto):
        """Retorna a árvore de origem de um lote de produto acabado."""
        if not lote_produto_acabado.ordem_producao_id:
            return {"lote": lote_produto_acabado, "ordem_producao": None,
                    "consumos": [], "fornecedores": []}

        consumos = MovimentacaoEstoque.objects.filter(
            ordem_producao_id=lote_produto_acabado.ordem_producao_id,
            tipo_operacao__in=[TipoOperacaoMovimentacao.CONSUMO_MP,
                               TipoOperacaoMovimentacao.PRODUCAO_SAIDA],
        ).select_related("lote", "lote__fornecedor", "produto")

        fornecedores = list({
            c.lote.fornecedor for c in consumos if c.lote and c.lote.fornecedor
        })
        return {
            "lote": lote_produto_acabado,
            "ordem_producao": lote_produto_acabado.ordem_producao,
            "consumos": list(consumos),
            "fornecedores": fornecedores,
        }

    @staticmethod
    def descendente(lote_materia_prima: LoteProduto):
        """De um lote de matéria-prima, lista todos os PA → vendas → clientes."""
        consumos = MovimentacaoEstoque.objects.filter(
            lote=lote_materia_prima,
            tipo_operacao=TipoOperacaoMovimentacao.CONSUMO_MP,
        ).select_related("ordem_producao")

        ops = {c.ordem_producao for c in consumos if c.ordem_producao_id}
        lotes_pa = LoteProduto.objects.filter(ordem_producao__in=ops)

        # Vendas: ItemDocumentoFiscal e itens_pedido_venda referenciam lote
        from apps.financeiro.models import ItemDocumentoFiscal
        itens = ItemDocumentoFiscal.objects.filter(lote__in=lotes_pa).select_related(
            "documento_fiscal", "documento_fiscal__destinatario_id"
        )
        return {
            "lote_mp": lote_materia_prima,
            "ordens_producao": list(ops),
            "lotes_produto_acabado": list(lotes_pa),
            "vendas": list(itens),
        }
