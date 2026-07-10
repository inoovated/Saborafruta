from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.pdv.models import VendaPDV, ItemVendaPDV, PagamentoVendaPDV, MovimentacaoCaixa, SessaoPDV, Caixa
from apps.estoque.models import MovimentacaoEstoque, Estoque
from apps.financeiro.models.receber_pagar import ContaReceber


SAIDAS = {
    MovimentacaoEstoque.TipoOperacao.SAIDA,
    MovimentacaoEstoque.TipoOperacao.BRINDE,
    MovimentacaoEstoque.TipoOperacao.DEVOLUCAO_FORNECEDOR,
    MovimentacaoEstoque.TipoOperacao.PERDA,
    MovimentacaoEstoque.TipoOperacao.ROUBO,
    MovimentacaoEstoque.TipoOperacao.DETERIORACAO,
    MovimentacaoEstoque.TipoOperacao.BAIXA_VALIDADE,
    MovimentacaoEstoque.TipoOperacao.USO_PROPRIO,
    MovimentacaoEstoque.TipoOperacao.QUEBRA,
    MovimentacaoEstoque.TipoOperacao.PRODUCAO_SAIDA,
    MovimentacaoEstoque.TipoOperacao.TRANSFERENCIA_SAIDA,
    MovimentacaoEstoque.TipoOperacao.AJUSTE_MENOS,
}


class Command(BaseCommand):
    help = 'Remove todas as vendas do PDV e dados gerados (apenas para ambiente de testes)'

    @transaction.atomic
    def handle(self, *args, **options):
        venda_ids = list(VendaPDV.objects.values_list('pk', flat=True))
        total_vendas = len(venda_ids)

        # --- 1. Reverter movimentos de estoque das vendas PDV ---
        movimentos = MovimentacaoEstoque.objects.filter(
            documento_tipo=MovimentacaoEstoque.DocumentoTipo.NFCE,
            documento_id__in=venda_ids,
        )
        estoques_a_atualizar = {}
        for mov in movimentos:
            chave = (mov.produto_id, mov.filial_id)
            delta = mov.quantidade if mov.tipo_operacao in SAIDAS else -mov.quantidade
            estoques_a_atualizar[chave] = estoques_a_atualizar.get(chave, Decimal('0')) + delta

        total_mov = movimentos.count()
        movimentos.delete()

        for (produto_id, filial_id), delta in estoques_a_atualizar.items():
            try:
                est = Estoque.objects.get(produto_id=produto_id, filial_id=filial_id)
                est.quantidade_atual += delta
                est.atualizar_disponivel()
                est.save(update_fields=['quantidade_atual', 'quantidade_disponivel', 'updated_at'])
            except Estoque.DoesNotExist:
                pass

        # --- 2. Contas a receber geradas pelo PDV (crediário/parcelado) ---
        cr_pdv = ContaReceber.objects.filter(
            documento_tipo__in=['venda_pdv', 'nfce'],
            documento_id__in=venda_ids,
        )
        total_cr = cr_pdv.count()
        cr_pdv.delete()

        # --- 3. Pagamentos, itens, movimentações de caixa, sessões e vendas ---
        PagamentoVendaPDV.objects.all().delete()
        ItemVendaPDV.objects.all().delete()
        MovimentacaoCaixa.objects.all().delete()
        SessaoPDV.objects.all().delete()
        VendaPDV.objects.all().delete()

        self.stdout.write(self.style.SUCCESS(
            f'{total_vendas} vendas removidas | '
            f'{total_mov} movimentos de estoque revertidos | '
            f'{total_cr} contas a receber excluídas.'
        ))
