from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone

from apps.core.services.exceptions import DadosInvalidosError, EstoqueInsuficienteError
from apps.estoque.models import MovimentacaoEstoque
from apps.estoque.services.movimentacao_service import MovimentacaoService
from apps.financeiro.models import FormaPagamento
from apps.pdv.models import ItemVendaPDV, PagamentoVendaPDV, VendaPDV
from apps.produtos.models import Produto
from apps.produtos.services.preco_service import PrecoService


class VendaPDVService:
    """Contrato central entre PDV, promocoes e estoque."""

    MONEY = Decimal("0.01")
    UNIT = Decimal("0.0001")

    @classmethod
    @transaction.atomic
    def finalizar_venda(
        cls,
        *,
        sessao,
        filial,
        usuario,
        itens: list[dict],
        pagamentos: list[dict],
        cliente_id: int | None = None,
        desconto=Decimal("0"),
        acrescimo=Decimal("0"),
        delivery: bool = False,
        endereco_entrega: dict | None = None,
    ) -> VendaPDV:
        if not sessao:
            raise DadosInvalidosError("Nenhuma sessao de caixa aberta.")
        if not itens:
            raise DadosInvalidosError("Carrinho vazio.")
        if not pagamentos:
            raise DadosInvalidosError("Informe ao menos uma forma de pagamento.")

        desconto = cls._decimal(desconto, cls.MONEY)
        acrescimo = cls._decimal(acrescimo, cls.MONEY)
        numero = cls._proximo_numero_venda(filial)
        venda = VendaPDV.objects.create(
            sessao_pdv=sessao,
            filial=filial,
            numero_venda=numero,
            cliente_id=cliente_id or None,
            status="finalizada",
            delivery=delivery,
            endereco_entrega=endereco_entrega or {},
            valor_desconto=desconto,
            valor_acrescimo=acrescimo,
            usuario=usuario,
            data_venda=timezone.now(),
        )

        subtotal = Decimal("0.00")
        for idx, item_dados in enumerate(itens, start=1):
            item = cls._criar_item_e_baixar_estoque(
                venda=venda,
                filial=filial,
                usuario=usuario,
                item_dados=item_dados,
                numero_item=idx,
            )
            subtotal += item.valor_total

        valor_total = cls._decimal(subtotal - desconto + acrescimo, cls.MONEY)
        if valor_total < 0:
            raise DadosInvalidosError("Total da venda nao pode ficar negativo.")

        valor_pago, troco_total = cls._registrar_pagamentos(
            venda=venda,
            filial=filial,
            pagamentos=pagamentos,
            valor_total=valor_total,
        )

        venda.valor_subtotal = subtotal
        venda.valor_total = valor_total
        venda.valor_pago = valor_pago
        venda.troco = troco_total
        venda.save(update_fields=[
            "valor_subtotal",
            "valor_total",
            "valor_pago",
            "troco",
            "updated_at",
        ])

        sessao.total_vendas = (sessao.total_vendas or Decimal("0")) + valor_total
        sessao.save(update_fields=["total_vendas"])
        return venda

    @classmethod
    def resolver_preco_produto(cls, produto: Produto, filial, quantidade: Decimal) -> dict:
        info = PrecoService.melhor_preco_produto_detalhado(
            produto,
            filial=filial,
            quantidade=quantidade,
            data=timezone.localdate(),
        )
        preco = cls._decimal(info["preco"], cls.UNIT)
        return {
            "preco": preco,
            "tipo": info.get("tipo", "normal") or "normal",
            "origem": info.get("origem", "Preco de venda") or "Preco de venda",
            "detalhe": info.get("detalhe", "") or "",
        }

    @classmethod
    def _criar_item_e_baixar_estoque(
        cls,
        *,
        venda: VendaPDV,
        filial,
        usuario,
        item_dados: dict,
        numero_item: int,
    ) -> ItemVendaPDV:
        produto_id = int(item_dados["produto_id"])
        quantidade = cls._decimal(item_dados.get("quantidade", "0"), Decimal("0.001"))
        if quantidade <= 0:
            raise DadosInvalidosError("Quantidade deve ser positiva.")

        try:
            produto = (
                Produto.objects
                .for_filial(filial)
                .select_related("unidade_medida")
                .get(pk=produto_id, ativo=True)
            )
        except Produto.DoesNotExist:
            raise DadosInvalidosError("Produto nao encontrado ou nao vinculado a filial ativa.")

        preco_info = cls.resolver_preco_produto(produto, filial, quantidade)
        valor_unitario = preco_info["preco"]
        valor_total_item = cls._decimal(quantidade * valor_unitario, cls.MONEY)
        unidade = produto.unidade_medida.sigla if produto.unidade_medida_id else "UN"
        custo_snapshot = produto.preco_custo_medio or produto.preco_custo or Decimal("0")

        item = ItemVendaPDV.objects.create(
            venda_pdv=venda,
            produto=produto,
            numero_item=numero_item,
            quantidade=quantidade,
            unidade_medida=unidade,
            valor_unitario=valor_unitario,
            valor_unitario_tabela=produto.preco_venda,
            custo_unitario_snapshot=custo_snapshot,
            preco_origem=preco_info["tipo"],
            preco_origem_detalhe=preco_info["detalhe"] or preco_info["origem"],
            valor_total=valor_total_item,
        )

        if produto.tipo_produto == Produto.TipoProduto.SERVICO:
            return item

        try:
            movimentacoes = MovimentacaoService.registrar_saida_fefo(
                produto_id=produto.pk,
                filial_id=filial.pk,
                quantidade=quantidade,
                usuario_id=usuario.pk,
                tipo_operacao=MovimentacaoEstoque.TipoOperacao.SAIDA,
                documento_tipo=MovimentacaoEstoque.DocumentoTipo.NFCE,
                documento_id=venda.pk,
                documento_numero=str(venda.numero_venda),
            )
        except EstoqueInsuficienteError:
            raise

        item.estoque_baixado = True
        item.movimentacoes_estoque_ids = [mov.pk for mov in movimentacoes]
        item.save(update_fields=[
            "estoque_baixado",
            "movimentacoes_estoque_ids",
        ])
        return item

    @classmethod
    def _registrar_pagamentos(
        cls,
        *,
        venda: VendaPDV,
        filial,
        pagamentos: list[dict],
        valor_total: Decimal,
    ) -> tuple[Decimal, Decimal]:
        valor_pago = Decimal("0.00")
        troco_total = Decimal("0.00")
        for pgto in pagamentos:
            forma_id = int(pgto["forma_id"])
            valor_pgto = cls._decimal(pgto.get("valor", "0"), cls.MONEY)
            if valor_pgto <= 0:
                raise DadosInvalidosError("Valor do pagamento deve ser positivo.")
            try:
                forma = FormaPagamento.objects.get(
                    pk=forma_id,
                    empresa=filial.empresa,
                    ativo=True,
                )
            except FormaPagamento.DoesNotExist:
                raise DadosInvalidosError("Forma de pagamento nao encontrada.")

            troco = max(Decimal("0.00"), valor_pgto - (valor_total - valor_pago))
            PagamentoVendaPDV.objects.create(
                venda_pdv=venda,
                forma_pagamento=forma,
                valor=valor_pgto,
                troco=troco,
            )
            valor_pago += valor_pgto
            troco_total += troco

        if valor_pago < valor_total:
            raise DadosInvalidosError("Valor pago menor que o total da venda.")
        return valor_pago, troco_total

    @staticmethod
    def _proximo_numero_venda(filial) -> int:
        ultimo_num = (
            VendaPDV.objects.filter(filial=filial)
            .order_by("-numero_venda")
            .values_list("numero_venda", flat=True)
            .first()
        )
        return (ultimo_num or 0) + 1

    @staticmethod
    def _decimal(valor, quantizador: Decimal) -> Decimal:
        return Decimal(str(valor or "0")).quantize(quantizador, rounding=ROUND_HALF_UP)
