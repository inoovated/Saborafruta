"""Servicos de pedido de compra e entrada de mercadoria."""
from __future__ import annotations

import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Avg, F
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.compras.models import (
    AvaliacaoFornecedor, EntradaNF, ItemEntradaNF, ItemPedidoCompra, PedidoCompra,
)
from apps.core.services.exceptions import DadosInvalidosError
from apps.estoque.services.movimentacao_service import MovimentacaoService
from apps.compras.services.entrada_custo_service import EntradaCustoService

logger = logging.getLogger(__name__)

ITEM_DIVIDIDO_MANUAL_LOTES = 'Item dividido manualmente em lotes.'
ITEM_REMOVIDO_ENTRADA = 'Item removido da entrada.'


def _decimal_snapshot(valor, padrao='0'):
    if valor in (None, ''):
        valor = padrao
    texto = str(valor).strip().replace(' ', '')
    if ',' in texto:
        texto = texto.replace('.', '').replace(',', '.')
    return Decimal(texto)


def _inteiro_snapshot(valor, padrao=1):
    if valor in (None, ''):
        return padrao
    try:
        return int(valor)
    except (TypeError, ValueError):
        return int(_decimal_snapshot(valor, str(padrao)))


def _id_snapshot(valor, padrao=None):
    if valor in (None, ''):
        return padrao
    if isinstance(valor, int):
        return valor
    texto = str(valor).strip()
    if texto.isdigit():
        return int(texto)
    return padrao


def _chave_item_snapshot(snapshot: dict) -> tuple:
    return (
        str(snapshot.get('numero_item') or ''),
        str(snapshot.get('produto_id') or snapshot.get('produto') or ''),
        str(snapshot.get('ean_xml') or ''),
        str(snapshot.get('codigo_produto_fornecedor') or ''),
        str(snapshot.get('descricao_xml') or ''),
    )


class CompraService:
    @classmethod
    @transaction.atomic
    def criar_pedido(
        cls, filial, usuario, fornecedor,
        data_entrega_prevista=None, observacao: str = '',
    ) -> PedidoCompra:
        numero = cls._gerar_numero_pedido(filial)
        return PedidoCompra.objects.create(
            filial=filial,
            numero_pedido=numero,
            fornecedor=fornecedor,
            usuario=usuario,
            status=PedidoCompra.Status.RASCUNHO,
            data_emissao=timezone.now(),
            data_entrega_prevista=data_entrega_prevista,
            observacao=observacao,
        )

    @staticmethod
    def _gerar_numero_pedido(filial) -> str:
        ultimo = PedidoCompra.objects.filter(filial=filial).order_by('-pk').first()
        if not ultimo or not ultimo.numero_pedido.startswith('PC-'):
            return 'PC-0000001'
        try:
            num = int(ultimo.numero_pedido.split('-')[1]) + 1
        except (ValueError, IndexError):
            num = 1
        return f'PC-{num:07d}'

    @classmethod
    @transaction.atomic
    def adicionar_item(
        cls, pedido: PedidoCompra, produto, quantidade: Decimal,
        valor_unitario: Decimal, valor_ipi: Decimal = Decimal('0'),
    ) -> ItemPedidoCompra:
        if pedido.status != PedidoCompra.Status.RASCUNHO:
            raise DadosInvalidosError('So e possivel adicionar itens em pedidos em rascunho.')
        if quantidade <= 0:
            raise DadosInvalidosError('Quantidade deve ser positiva.')

        numero_item = pedido.itens.count() + 1
        item = ItemPedidoCompra(
            pedido=pedido,
            produto=produto,
            numero_item=numero_item,
            quantidade=quantidade,
            valor_unitario=valor_unitario,
            valor_ipi=valor_ipi,
        )
        item.calcular_totais()
        item.save()

        pedido.recalcular_totais()
        pedido.save()
        return item

    @classmethod
    @transaction.atomic
    def remover_item(cls, pedido: PedidoCompra, item_id: int):
        if pedido.status != PedidoCompra.Status.RASCUNHO:
            raise DadosInvalidosError('So e possivel remover itens em pedidos em rascunho.')
        ItemPedidoCompra.objects.filter(pedido=pedido, pk=item_id).delete()
        pedido.recalcular_totais()
        pedido.save()

    @classmethod
    @transaction.atomic
    def aprovar_pedido(cls, pedido: PedidoCompra, usuario) -> PedidoCompra:
        if not pedido.pode_aprovar:
            raise DadosInvalidosError(
                f'Pedido nao pode ser aprovado no status "{pedido.get_status_display()}".'
            )
        if not pedido.itens.exists():
            raise DadosInvalidosError('Pedido sem itens nao pode ser aprovado.')

        pedido.status = PedidoCompra.Status.APROVADO
        pedido.aprovado_por = usuario
        pedido.data_aprovacao = timezone.now()
        pedido.save(update_fields=[
            'status', 'aprovado_por', 'data_aprovacao', 'updated_at',
        ])
        return pedido

    @classmethod
    @transaction.atomic
    def enviar_fornecedor(cls, pedido: PedidoCompra, usuario) -> PedidoCompra:
        if not pedido.pode_enviar:
            raise DadosInvalidosError(
                f'Pedido nao pode ser enviado no status "{pedido.get_status_display()}".'
            )
        pedido.status = PedidoCompra.Status.ENVIADO_FORNECEDOR
        pedido.save(update_fields=['status', 'updated_at'])
        return pedido

    @classmethod
    @transaction.atomic
    def cancelar_pedido(cls, pedido: PedidoCompra, usuario, motivo: str) -> PedidoCompra:
        if not pedido.pode_cancelar:
            raise DadosInvalidosError(
                f'Pedido nao pode ser cancelado no status "{pedido.get_status_display()}".'
            )
        if not motivo.strip():
            raise DadosInvalidosError('Informe o motivo do cancelamento.')
        pedido.status = PedidoCompra.Status.CANCELADO
        pedido.motivo_cancelamento = motivo
        pedido.save(update_fields=[
            'status', 'motivo_cancelamento', 'updated_at',
        ])
        return pedido

    @classmethod
    @transaction.atomic
    def criar_entrada_nf(
        cls, filial, usuario, fornecedor, numero_nf: str, serie_nf: str,
        data_emissao_nf, chave_acesso_nf: str = '',
        pedido_compra: PedidoCompra | None = None,
        observacao: str = '',
        origem_entrada: str = EntradaNF.OrigemEntrada.MANUAL,
        fornecedor_pendente: bool = False,
        dados_emitente_xml: dict | None = None,
    ) -> EntradaNF:
        chave_acesso_nf = ''.join(ch for ch in (chave_acesso_nf or '') if ch.isdigit())
        if chave_acesso_nf and len(chave_acesso_nf) != 44:
            raise DadosInvalidosError('Chave de acesso deve ter 44 digitos.')
        if chave_acesso_nf and EntradaNF.objects.for_filial(filial).filter(
            chave_acesso_nf=chave_acesso_nf,
        ).exclude(
            status__in=[EntradaNF.Status.CANCELADA, EntradaNF.Status.ESTORNADA],
        ).exists():
            raise DadosInvalidosError('Esta chave de acesso ja foi cadastrada nesta filial.')
        dados_emitente_xml = dados_emitente_xml or {}
        return EntradaNF.objects.create(
            filial=filial,
            pedido_compra=pedido_compra,
            fornecedor=fornecedor,
            numero_nf=numero_nf,
            serie_nf=serie_nf or '1',
            chave_acesso_nf=chave_acesso_nf,
            origem_entrada=origem_entrada,
            data_emissao_nf=data_emissao_nf,
            data_entrada=timezone.now(),
            status=EntradaNF.Status.RASCUNHO,
            usuario=usuario,
            fornecedor_pendente=fornecedor_pendente,
            emitente_cnpj_xml=dados_emitente_xml.get('documento', ''),
            emitente_razao_social_xml=dados_emitente_xml.get('razao_social', ''),
            emitente_nome_fantasia_xml=dados_emitente_xml.get('nome_fantasia', ''),
            emitente_ie_xml=dados_emitente_xml.get('ie', ''),
            emitente_endereco_xml=dados_emitente_xml.get('endereco', ''),
            emitente_municipio_xml=dados_emitente_xml.get('municipio', ''),
            emitente_uf_xml=dados_emitente_xml.get('uf', ''),
            emitente_cep_xml=dados_emitente_xml.get('cep', ''),
            emitente_telefone_xml=dados_emitente_xml.get('telefone', ''),
            observacao=observacao,
        )

    @classmethod
    @transaction.atomic
    def adicionar_item_entrada(
        cls, entrada: EntradaNF, produto,
        quantidade: Decimal, valor_unitario: Decimal,
        valor_ipi: Decimal = Decimal('0'), valor_icms: Decimal = Decimal('0'),
        numero_lote: str = '', data_fabricacao=None, data_validade=None,
        item_pedido_compra: ItemPedidoCompra | None = None,
        ean_xml: str = '',
        codigo_produto_fornecedor: str = '',
        descricao_xml: str = '',
        unidade_xml: str = '',
        unidade_estoque: str = '',
        fator_conversao: Decimal = Decimal('1'),
        quantidade_recebida: Decimal | None = None,
    ) -> ItemEntradaNF:
        if entrada.status not in (
            EntradaNF.Status.RASCUNHO,
            EntradaNF.Status.AGUARDANDO_VINCULOS,
            EntradaNF.Status.AGUARDANDO_CONFERENCIA,
            EntradaNF.Status.COM_DIFERENCAS,
            EntradaNF.Status.CONFERIDA,
        ):
            raise DadosInvalidosError('So e possivel adicionar itens em entradas abertas.')
        if quantidade <= 0:
            raise DadosInvalidosError('Quantidade deve ser positiva.')
        if produto and produto.controla_lote and not numero_lote:
            raise DadosInvalidosError(f'Produto "{produto}" requer numero de lote.')
        if produto and produto.controla_validade and not data_validade:
            raise DadosInvalidosError(f'Produto "{produto}" requer data de validade.')
        if produto and produto.controla_validade and data_validade < timezone.localdate():
            raise DadosInvalidosError(
                f'Produto "{produto}" nao pode entrar com validade vencida.'
            )

        fator_conversao = fator_conversao or Decimal('1')
        quantidade_estoque = quantidade * fator_conversao
        valor_bruto_xml = quantidade * valor_unitario
        valor_unitario_estoque = (
            valor_bruto_xml / quantidade_estoque
            if quantidade_estoque
            else valor_unitario
        )
        if produto and not ean_xml:
            ean_xml = produto.codigo_barras or ''
            if not ean_xml:
                codigo_barras = produto.codigos_barras.filter(ativo=True).order_by('pk').first()
                ean_xml = codigo_barras.ean if codigo_barras else ''
        item = ItemEntradaNF(
            entrada=entrada,
            item_pedido_compra=item_pedido_compra,
            produto=produto,
            numero_item=entrada.itens.count() + 1,
            quantidade=quantidade_estoque,
            quantidade_xml=quantidade,
            quantidade_estoque=quantidade_estoque,
            quantidade_recebida=quantidade_recebida or quantidade_estoque,
            unidade_xml=unidade_xml,
            unidade_estoque=unidade_estoque or (
                produto.unidade_medida.sigla if produto and produto.unidade_medida_id else ''
            ),
            fator_conversao=fator_conversao,
            valor_unitario=valor_unitario_estoque,
            valor_ipi=valor_ipi,
            valor_icms=valor_icms,
            numero_lote=numero_lote,
            data_fabricacao=data_fabricacao,
            data_validade=data_validade,
            ean_xml=ean_xml,
            codigo_produto_fornecedor=codigo_produto_fornecedor,
            descricao_xml=descricao_xml,
        )
        item.calcular_totais()
        item.save()
        cls.atualizar_diferenca_item(item)

        cls._recalcular_totais_entrada(entrada)
        cls._atualizar_status_conferencia(entrada)
        return item

    @classmethod
    @transaction.atomic
    def remover_item_entrada(cls, item: ItemEntradaNF) -> dict:
        entrada = item.entrada
        if entrada.status not in (
            EntradaNF.Status.RASCUNHO,
            EntradaNF.Status.AGUARDANDO_VINCULOS,
            EntradaNF.Status.AGUARDANDO_CONFERENCIA,
            EntradaNF.Status.COM_DIFERENCAS,
            EntradaNF.Status.CONFERIDA,
        ):
            raise DadosInvalidosError('So e possivel remover itens de entradas abertas.')

        snapshot = {
            **{
                'id': item.pk,
                'produto_id': item.produto_id,
                'produto_descricao': str(item.produto) if item.produto_id else '',
            },
            **{
                campo.name: (
                    str(getattr(item, campo.name))
                    if isinstance(getattr(item, campo.name), Decimal)
                    else (
                        getattr(item, campo.name).isoformat()
                        if getattr(item, campo.name, None) and hasattr(getattr(item, campo.name), 'isoformat')
                        else getattr(item, campo.attname if campo.is_relation else campo.name)
                    )
                )
                for campo in item._meta.concrete_fields
                if campo.name not in {'id', 'entrada', 'lote_gerado'}
            },
        }
        item.quantidade_recebida = Decimal('0')
        item.valor_bruto = Decimal('0.00')
        item.valor_desconto = Decimal('0.00')
        item.valor_ipi = Decimal('0.00')
        item.valor_icms = Decimal('0.00')
        item.valor_total = Decimal('0.00')
        item.justificativa_diferenca = ITEM_REMOVIDO_ENTRADA
        item.observacao = ITEM_REMOVIDO_ENTRADA
        item.save(update_fields=[
            'quantidade_recebida', 'valor_bruto', 'valor_desconto', 'valor_ipi',
            'valor_icms', 'valor_total', 'justificativa_diferenca', 'observacao', 'updated_at',
        ])
        cls.atualizar_diferenca_item(item)
        cls._recalcular_totais_entrada(entrada)
        cls._atualizar_status_conferencia(entrada)
        return snapshot

    @classmethod
    @transaction.atomic
    def restaurar_item_entrada(
        cls,
        entrada: EntradaNF,
        item_snapshot: dict,
        snapshots_grupo: list[dict] | None = None,
    ) -> ItemEntradaNF:
        if entrada.status not in (
            EntradaNF.Status.RASCUNHO,
            EntradaNF.Status.AGUARDANDO_VINCULOS,
            EntradaNF.Status.AGUARDANDO_CONFERENCIA,
            EntradaNF.Status.COM_DIFERENCAS,
            EntradaNF.Status.CONFERIDA,
        ):
            raise DadosInvalidosError('So e possivel restaurar itens em entradas abertas.')

        snapshots_grupo = snapshots_grupo or []
        if len(snapshots_grupo) > 1:
            snapshot_original = cls._snapshot_original_divisao_manual(entrada, snapshots_grupo)
            base_snapshot = snapshot_original or item_snapshot
            ids_grupo = [snapshot.get('id') for snapshot in snapshots_grupo if snapshot.get('id')]
            itens_grupo = list(
                entrada.itens.select_for_update().filter(pk__in=ids_grupo).order_by('pk')
            )
            item = itens_grupo[0] if itens_grupo else None
            if item is None:
                item = ItemEntradaNF(entrada=entrada)
            produto_id = _id_snapshot(
                base_snapshot.get('produto_id'),
                _id_snapshot(base_snapshot.get('produto'), getattr(item, 'produto_id', None)),
            )
            item_pedido_id = _id_snapshot(
                base_snapshot.get('item_pedido_compra_id'),
                _id_snapshot(base_snapshot.get('item_pedido_compra'), getattr(item, 'item_pedido_compra_id', None)),
            )

            campos_soma = [
                'quantidade', 'quantidade_xml', 'quantidade_estoque', 'quantidade_recebida',
                'valor_bruto', 'valor_desconto', 'valor_ipi', 'valor_icms', 'valor_total',
            ]
            somas = {
                campo: sum(
                    (_decimal_snapshot(snapshot.get(campo)) for snapshot in snapshots_grupo),
                    Decimal('0'),
                )
                for campo in campos_soma
            }
            campos_valor = [
                'valor_bruto', 'valor_desconto', 'valor_ipi', 'valor_icms', 'valor_total',
            ]
            item.item_pedido_compra_id = item_pedido_id
            item.produto_id = produto_id
            item.numero_item = _inteiro_snapshot(
                base_snapshot.get('numero_item'),
                item.numero_item or entrada.itens.count() + 1,
            )
            if snapshot_original:
                item.quantidade = _decimal_snapshot(base_snapshot.get('quantidade'))
                item.quantidade_xml = _decimal_snapshot(base_snapshot.get('quantidade_xml'))
                item.quantidade_estoque = _decimal_snapshot(base_snapshot.get('quantidade_estoque'))
                item.quantidade_recebida = _decimal_snapshot(base_snapshot.get('quantidade_recebida'))
            else:
                for campo in [
                    'quantidade', 'quantidade_xml', 'quantidade_estoque', 'quantidade_recebida',
                ]:
                    setattr(item, campo, somas[campo])
            for campo in campos_valor:
                valor = somas[campo]
                setattr(item, campo, valor)
            item.unidade_xml = base_snapshot.get('unidade_xml') or ''
            item.unidade_estoque = base_snapshot.get('unidade_estoque') or ''
            item.fator_conversao = _decimal_snapshot(base_snapshot.get('fator_conversao'), '1')
            item.valor_unitario = _decimal_snapshot(base_snapshot.get('valor_unitario'))
            if item.quantidade and item.valor_total:
                item.valor_unitario = (item.valor_total / item.quantidade).quantize(Decimal('0.0001'))
            cls._corrigir_quantidade_original_por_equivalencia(entrada, item, base_snapshot)
            item.custo_unitario_total = _decimal_snapshot(base_snapshot.get('custo_unitario_total'))
            item.numero_lote = ''
            item.data_fabricacao = None
            item.data_validade = None
            item.ean_xml = base_snapshot.get('ean_xml') or ''
            item.ncm_xml = base_snapshot.get('ncm_xml') or ''
            item.codigo_produto_fornecedor = base_snapshot.get('codigo_produto_fornecedor') or ''
            item.descricao_xml = base_snapshot.get('descricao_xml') or ''
            item.diferenca_tipo = base_snapshot.get('diferenca_tipo') or ''
            item.diferenca_descricao = base_snapshot.get('diferenca_descricao') or ''
            item.diferenca_bloqueante = bool(base_snapshot.get('diferenca_bloqueante') or False)
            item.justificativa_diferenca = base_snapshot.get('justificativa_diferenca') or ''
            item.observacao = ''
            item.save()
            ids_manter = {item.pk}
            if ids_grupo:
                entrada.itens.filter(pk__in=ids_grupo).exclude(pk__in=ids_manter).update(
                    quantidade_recebida=Decimal('0'),
                    valor_bruto=Decimal('0.00'),
                    valor_desconto=Decimal('0.00'),
                    valor_ipi=Decimal('0.00'),
                    valor_icms=Decimal('0.00'),
                    valor_total=Decimal('0.00'),
                    justificativa_diferenca=ITEM_REMOVIDO_ENTRADA,
                    observacao=ITEM_REMOVIDO_ENTRADA,
                    updated_at=timezone.now(),
                )
            cls.atualizar_diferenca_item(item)
            cls._recalcular_totais_entrada(entrada)
            cls._atualizar_status_conferencia(entrada)
            return item

        item_existente = None
        item_id = item_snapshot.get('id')
        if item_id:
            item_existente = entrada.itens.filter(pk=item_id).first()
        produto_id = _id_snapshot(
            item_snapshot.get('produto_id'),
            _id_snapshot(item_snapshot.get('produto'), getattr(item_existente, 'produto_id', None)),
        )
        item_pedido_id = _id_snapshot(
            item_snapshot.get('item_pedido_compra_id'),
            _id_snapshot(item_snapshot.get('item_pedido_compra'), getattr(item_existente, 'item_pedido_compra_id', None)),
        )
        if item_existente and (
            ITEM_REMOVIDO_ENTRADA in (item_existente.observacao or '')
            or item_existente.quantidade_recebida <= 0
        ):
            campos = [
                'item_pedido_compra_id', 'produto_id', 'numero_item', 'quantidade',
                'quantidade_xml', 'quantidade_estoque', 'quantidade_recebida',
                'unidade_xml', 'unidade_estoque', 'fator_conversao', 'valor_unitario',
                'custo_unitario_total', 'valor_bruto', 'valor_desconto', 'valor_ipi',
                'valor_icms', 'valor_total', 'numero_lote', 'data_fabricacao',
                'data_validade', 'ean_xml', 'ncm_xml', 'cfop_xml', 'codigo_produto_fornecedor',
                'descricao_xml', 'diferenca_tipo', 'diferenca_descricao',
                'diferenca_bloqueante', 'justificativa_diferenca', 'observacao',
            ]
            item_existente.item_pedido_compra_id = item_pedido_id
            item_existente.produto_id = produto_id
            item_existente.numero_item = _inteiro_snapshot(
                item_snapshot.get('numero_item'),
                item_existente.numero_item,
            )
            item_existente.quantidade = _decimal_snapshot(item_snapshot.get('quantidade'))
            item_existente.quantidade_xml = _decimal_snapshot(item_snapshot.get('quantidade_xml'))
            item_existente.quantidade_estoque = _decimal_snapshot(item_snapshot.get('quantidade_estoque'))
            item_existente.quantidade_recebida = _decimal_snapshot(item_snapshot.get('quantidade_recebida'))
            item_existente.unidade_xml = item_snapshot.get('unidade_xml') or ''
            item_existente.unidade_estoque = item_snapshot.get('unidade_estoque') or ''
            item_existente.fator_conversao = _decimal_snapshot(item_snapshot.get('fator_conversao'), '1')
            item_existente.valor_unitario = _decimal_snapshot(item_snapshot.get('valor_unitario'))
            item_existente.custo_unitario_total = _decimal_snapshot(item_snapshot.get('custo_unitario_total'))
            item_existente.valor_bruto = _decimal_snapshot(item_snapshot.get('valor_bruto'))
            item_existente.valor_desconto = _decimal_snapshot(item_snapshot.get('valor_desconto'))
            item_existente.valor_ipi = _decimal_snapshot(item_snapshot.get('valor_ipi'))
            item_existente.valor_icms = _decimal_snapshot(item_snapshot.get('valor_icms'))
            item_existente.valor_total = _decimal_snapshot(item_snapshot.get('valor_total'))
            item_existente.numero_lote = item_snapshot.get('numero_lote') or ''
            item_existente.data_fabricacao = parse_date(item_snapshot.get('data_fabricacao') or '')
            item_existente.data_validade = parse_date(item_snapshot.get('data_validade') or '')
            item_existente.ean_xml = item_snapshot.get('ean_xml') or ''
            item_existente.ncm_xml = item_snapshot.get('ncm_xml') or ''
            item_existente.cfop_xml = item_snapshot.get('cfop_xml') or ''
            item_existente.codigo_produto_fornecedor = item_snapshot.get('codigo_produto_fornecedor') or ''
            item_existente.descricao_xml = item_snapshot.get('descricao_xml') or ''
            item_existente.diferenca_tipo = item_snapshot.get('diferenca_tipo') or ''
            item_existente.diferenca_descricao = item_snapshot.get('diferenca_descricao') or ''
            item_existente.diferenca_bloqueante = bool(item_snapshot.get('diferenca_bloqueante') or False)
            item_existente.justificativa_diferenca = item_snapshot.get('justificativa_diferenca') or ''
            item_existente.observacao = item_snapshot.get('observacao') or ''
            item_existente.save(update_fields=[*campos, 'updated_at'])
            cls.atualizar_diferenca_item(item_existente)
            cls._recalcular_totais_entrada(entrada)
            cls._atualizar_status_conferencia(entrada)
            return item_existente
        if ITEM_DIVIDIDO_MANUAL_LOTES in (item_snapshot.get('observacao') or ''):
            irmaos = list(
                entrada.itens.select_for_update()
                .filter(
                    numero_item=int(item_snapshot.get('numero_item') or 0),
                    produto_id=produto_id,
                    ean_xml=item_snapshot.get('ean_xml') or '',
                    codigo_produto_fornecedor=item_snapshot.get('codigo_produto_fornecedor') or '',
                    descricao_xml=item_snapshot.get('descricao_xml') or '',
                    observacao__icontains=ITEM_DIVIDIDO_MANUAL_LOTES,
                )
                .order_by('pk')
            )
            if len(irmaos) == 1:
                item = irmaos[0]
                snapshot_original = cls._snapshot_original_divisao_manual(
                    entrada,
                    [item_snapshot],
                    ids_extras=[item.pk],
                )
                campos_soma = [
                    'quantidade', 'quantidade_xml', 'quantidade_estoque', 'quantidade_recebida',
                    'valor_bruto', 'valor_desconto', 'valor_ipi', 'valor_icms', 'valor_total',
                ]
                campos_valor = [
                    'valor_bruto', 'valor_desconto', 'valor_ipi', 'valor_icms', 'valor_total',
                ]
                if snapshot_original:
                    item.quantidade = _decimal_snapshot(snapshot_original.get('quantidade'))
                    item.quantidade_xml = _decimal_snapshot(snapshot_original.get('quantidade_xml'))
                    item.quantidade_estoque = _decimal_snapshot(snapshot_original.get('quantidade_estoque'))
                    item.quantidade_recebida = _decimal_snapshot(snapshot_original.get('quantidade_recebida'))
                    item.fator_conversao = _decimal_snapshot(snapshot_original.get('fator_conversao'), '1')
                    item.unidade_xml = snapshot_original.get('unidade_xml') or item.unidade_xml
                    item.unidade_estoque = snapshot_original.get('unidade_estoque') or item.unidade_estoque
                    item.numero_lote = ''
                    item.data_fabricacao = None
                    item.data_validade = None
                    cls._corrigir_quantidade_original_por_equivalencia(
                        entrada,
                        item,
                        snapshot_original,
                    )
                else:
                    for campo in [
                        'quantidade', 'quantidade_xml', 'quantidade_estoque', 'quantidade_recebida',
                    ]:
                        setattr(item, campo, getattr(item, campo) + _decimal_snapshot(item_snapshot.get(campo)))
                for campo in campos_valor:
                    setattr(item, campo, getattr(item, campo) + _decimal_snapshot(item_snapshot.get(campo)))
                cls._corrigir_quantidade_original_por_equivalencia(
                    entrada,
                    item,
                    snapshot_original or item_snapshot,
                )
                if item.quantidade and item.valor_total:
                    item.valor_unitario = (item.valor_total / item.quantidade).quantize(Decimal('0.0001'))
                item.observacao = ''
                item.save(update_fields=[
                    *campos_soma,
                    'unidade_xml', 'unidade_estoque', 'fator_conversao',
                    'numero_lote', 'data_fabricacao', 'data_validade',
                    'valor_unitario', 'observacao', 'updated_at',
                ])
                cls.atualizar_diferenca_item(item)
                cls._recalcular_totais_entrada(entrada)
                cls._atualizar_status_conferencia(entrada)
                return item

        item = ItemEntradaNF.objects.create(
            entrada=entrada,
            item_pedido_compra_id=item_pedido_id,
            produto_id=produto_id,
            numero_item=_inteiro_snapshot(item_snapshot.get('numero_item'), entrada.itens.count() + 1),
            quantidade=_decimal_snapshot(item_snapshot.get('quantidade')),
            quantidade_xml=_decimal_snapshot(item_snapshot.get('quantidade_xml')),
            quantidade_estoque=_decimal_snapshot(item_snapshot.get('quantidade_estoque')),
            quantidade_recebida=_decimal_snapshot(item_snapshot.get('quantidade_recebida')),
            unidade_xml=item_snapshot.get('unidade_xml') or '',
            unidade_estoque=item_snapshot.get('unidade_estoque') or '',
            fator_conversao=_decimal_snapshot(item_snapshot.get('fator_conversao'), '1'),
            valor_unitario=_decimal_snapshot(item_snapshot.get('valor_unitario')),
            custo_unitario_total=_decimal_snapshot(item_snapshot.get('custo_unitario_total')),
            valor_bruto=_decimal_snapshot(item_snapshot.get('valor_bruto')),
            valor_desconto=_decimal_snapshot(item_snapshot.get('valor_desconto')),
            valor_ipi=_decimal_snapshot(item_snapshot.get('valor_ipi')),
            valor_icms=_decimal_snapshot(item_snapshot.get('valor_icms')),
            valor_total=_decimal_snapshot(item_snapshot.get('valor_total')),
            numero_lote=item_snapshot.get('numero_lote') or '',
            data_fabricacao=parse_date(item_snapshot.get('data_fabricacao') or ''),
            data_validade=parse_date(item_snapshot.get('data_validade') or ''),
            ean_xml=item_snapshot.get('ean_xml') or '',
            ncm_xml=item_snapshot.get('ncm_xml') or '',
            cfop_xml=item_snapshot.get('cfop_xml') or '',
            codigo_produto_fornecedor=item_snapshot.get('codigo_produto_fornecedor') or '',
            descricao_xml=item_snapshot.get('descricao_xml') or '',
            diferenca_tipo=item_snapshot.get('diferenca_tipo') or '',
            diferenca_descricao=item_snapshot.get('diferenca_descricao') or '',
            diferenca_bloqueante=bool(item_snapshot.get('diferenca_bloqueante') or False),
            justificativa_diferenca=item_snapshot.get('justificativa_diferenca') or '',
            observacao=item_snapshot.get('observacao') or '',
        )
        cls.atualizar_diferenca_item(item)
        cls._recalcular_totais_entrada(entrada)
        cls._atualizar_status_conferencia(entrada)
        return item

    @classmethod
    @transaction.atomic
    def corrigir_restauracoes_lote_dividido(cls, entrada: EntradaNF) -> int:
        if entrada.status not in (
            EntradaNF.Status.RASCUNHO,
            EntradaNF.Status.AGUARDANDO_VINCULOS,
            EntradaNF.Status.AGUARDANDO_CONFERENCIA,
            EntradaNF.Status.COM_DIFERENCAS,
            EntradaNF.Status.CONFERIDA,
        ):
            return 0

        from apps.core.models import RegistroAuditoria

        ids_itens = set()
        snapshots_removidos_por_item = {}
        for log in RegistroAuditoria.objects.filter(
            objeto_tipo=entrada._meta.label_lower,
            objeto_id=entrada.pk,
            acao='restaurar_item',
        ).only('metadados'):
            metadados = log.metadados or {}
            item_restaurado = metadados.get('item_restaurado') or {}
            item_id = _id_snapshot(item_restaurado.get('id'))
            if item_id:
                ids_itens.add(item_id)
                ids_logs = (
                    metadados.get('item_removido_log_ids')
                    or [metadados.get('item_removido_log_id')]
                )
                ids_logs = [log_id for log_id in ids_logs if log_id]
                if ids_logs:
                    snapshots_removidos_por_item[item_id] = [
                        (log_remocao.metadados or {}).get('item_removido') or {}
                        for log_remocao in RegistroAuditoria.objects.filter(
                            objeto_tipo=entrada._meta.label_lower,
                            objeto_id=entrada.pk,
                            acao='remover_item',
                            pk__in=ids_logs,
                        )
                    ]

        if not ids_itens:
            return 0

        corrigidos = 0
        itens = (
            entrada.itens.select_for_update()
            .filter(
                pk__in=ids_itens,
                observacao='',
                numero_lote='',
                fator_conversao__lte=Decimal('1'),
            )
        )
        for item in itens:
            quantidade_xml_anterior = item.quantidade_xml
            fator_anterior = item.fator_conversao
            unidade_xml_anterior = item.unidade_xml
            unidade_estoque_anterior = item.unidade_estoque
            snapshots_removidos = snapshots_removidos_por_item.get(item.pk) or []
            snapshot_original = cls._snapshot_original_divisao_manual(
                entrada,
                snapshots_removidos,
                ids_extras=[item.pk],
            ) if snapshots_removidos else None
            if snapshot_original:
                item.quantidade = _decimal_snapshot(snapshot_original.get('quantidade'))
                item.quantidade_xml = _decimal_snapshot(snapshot_original.get('quantidade_xml'))
                item.quantidade_estoque = _decimal_snapshot(snapshot_original.get('quantidade_estoque'))
                item.quantidade_recebida = _decimal_snapshot(snapshot_original.get('quantidade_recebida'))
                item.fator_conversao = _decimal_snapshot(snapshot_original.get('fator_conversao'), '1')
                item.unidade_xml = snapshot_original.get('unidade_xml') or item.unidade_xml
                item.unidade_estoque = snapshot_original.get('unidade_estoque') or item.unidade_estoque
                if item.quantidade and item.valor_total:
                    item.valor_unitario = (item.valor_total / item.quantidade).quantize(Decimal('0.0001'))
            else:
                cls._corrigir_quantidade_original_por_equivalencia(
                    entrada,
                    item,
                    {
                        'produto_id': item.produto_id,
                        'ean_xml': item.ean_xml,
                        'codigo_produto_fornecedor': item.codigo_produto_fornecedor,
                    },
                )
            if (
                item.quantidade_xml == quantidade_xml_anterior
                and item.fator_conversao == fator_anterior
                and item.unidade_xml == unidade_xml_anterior
                and item.unidade_estoque == unidade_estoque_anterior
            ):
                continue
            item.save(update_fields=[
                'quantidade', 'quantidade_xml', 'quantidade_estoque',
                'quantidade_recebida', 'unidade_xml', 'unidade_estoque',
                'fator_conversao', 'valor_unitario', 'updated_at',
            ])
            cls.atualizar_diferenca_item(item)
            corrigidos += 1

        if corrigidos:
            cls._recalcular_totais_entrada(entrada)
            cls._atualizar_status_conferencia(entrada)
        return corrigidos

    @classmethod
    def _corrigir_quantidade_original_por_equivalencia(
        cls,
        entrada: EntradaNF,
        item: ItemEntradaNF,
        snapshot: dict,
    ):
        if item.fator_conversao and item.fator_conversao > Decimal('1'):
            return
        fator = cls._fator_conversao_cadastrado(entrada, item, snapshot)
        if fator <= Decimal('1'):
            return
        quantidade_final = item.quantidade_recebida or item.quantidade_estoque or item.quantidade
        if not quantidade_final or quantidade_final <= 0:
            return
        item.fator_conversao = fator
        item.quantidade_recebida = quantidade_final
        item.quantidade_estoque = quantidade_final
        item.quantidade = quantidade_final
        item.quantidade_xml = (quantidade_final / fator).quantize(Decimal('0.001'))
        if item.quantidade and item.valor_total:
            item.valor_unitario = (item.valor_total / item.quantidade).quantize(Decimal('0.0001'))

    @staticmethod
    def _fator_conversao_cadastrado(
        entrada: EntradaNF,
        item: ItemEntradaNF,
        snapshot: dict,
    ) -> Decimal:
        from apps.produtos.models import (
            Produto, ProdutoCodigoBarras, ProdutoFornecedorEquivalencia,
        )

        produto_id = _id_snapshot(
            snapshot.get('produto_id'),
            _id_snapshot(snapshot.get('produto'), item.produto_id),
        )
        if not produto_id:
            return Decimal('1')
        ean = str(snapshot.get('ean_xml') or item.ean_xml or '').strip()
        codigo = str(
            snapshot.get('codigo_produto_fornecedor')
            or item.codigo_produto_fornecedor
            or ''
        ).strip()

        def fator_valido(valor) -> Decimal | None:
            try:
                fator = _decimal_snapshot(valor, '1')
            except Exception:
                return None
            return fator if fator > Decimal('1') else None

        equivalencias_base = ProdutoFornecedorEquivalencia.objects.filter(
            produto_id=produto_id,
            ativo=True,
        )
        filtros = []
        if codigo and entrada.fornecedor_id:
            filtros.append({'codigo_fornecedor': codigo, 'fornecedor_id': entrada.fornecedor_id})
        if codigo and entrada.emitente_cnpj_xml:
            filtros.append({'codigo_fornecedor': codigo, 'fornecedor_cnpj_xml': entrada.emitente_cnpj_xml})
        if ean and entrada.fornecedor_id:
            filtros.append({'ean_utilizado': ean, 'fornecedor_id': entrada.fornecedor_id})
        if ean and entrada.emitente_cnpj_xml:
            filtros.append({'ean_utilizado': ean, 'fornecedor_cnpj_xml': entrada.emitente_cnpj_xml})
        if codigo:
            filtros.append({'codigo_fornecedor': codigo})
        if ean:
            filtros.append({'ean_utilizado': ean})

        for filtro in filtros:
            equivalencia = equivalencias_base.filter(**filtro).order_by('-updated_at').first()
            if equivalencia:
                fator = fator_valido(equivalencia.fator_conversao)
                if fator:
                    return fator

        if ean:
            codigo_barras = (
                ProdutoCodigoBarras.objects
                .filter(produto_id=produto_id, ean=ean, ativo=True)
                .order_by('-updated_at')
                .first()
            )
            if codigo_barras:
                fator = fator_valido(codigo_barras.quantidade_conversao)
                if fator:
                    return fator

        produto = Produto.objects.filter(pk=produto_id).only('fator_conversao_compra').first()
        if produto:
            fator = fator_valido(produto.fator_conversao_compra)
            if fator:
                return fator
        return Decimal('1')

    @staticmethod
    def _snapshot_original_divisao_manual(
        entrada: EntradaNF,
        snapshots: list[dict],
        ids_extras: list[int] | None = None,
    ) -> dict | None:
        """Recupera o estado da linha antes de ser dividida em lotes."""
        from apps.core.models import RegistroAuditoria

        ids = {
            str(snapshot.get('id'))
            for snapshot in snapshots
            if snapshot and snapshot.get('id') not in (None, '')
        }
        ids.update(str(item_id) for item_id in (ids_extras or []) if item_id not in (None, ''))
        chaves = {
            _chave_item_snapshot(snapshot)
            for snapshot in snapshots
            if snapshot
        }
        logs = RegistroAuditoria.objects.filter(
            objeto_tipo=entrada._meta.label_lower,
            objeto_id=entrada.pk,
            acao='dividir_lotes',
        ).order_by('-criado_em')

        def melhor_snapshot(snapshots_encontrados):
            for snapshot in snapshots_encontrados:
                fator = _decimal_snapshot(snapshot.get('fator_conversao'), '1')
                quantidade = _decimal_snapshot(snapshot.get('quantidade'))
                quantidade_xml = _decimal_snapshot(snapshot.get('quantidade_xml'))
                if fator > Decimal('1') or (
                    quantidade
                    and quantidade_xml
                    and quantidade != quantidade_xml
                ):
                    return snapshot
            return snapshots_encontrados[0] if snapshots_encontrados else None

        snapshots_por_id = []
        for log in logs:
            anterior = log.dados_anteriores or {}
            if not anterior:
                continue
            if ids and (
                str(log.relacionado_id or '') in ids
                or str(anterior.get('id') or '') in ids
            ):
                snapshots_por_id.append(anterior)
        snapshot_por_id = melhor_snapshot(snapshots_por_id)
        if snapshot_por_id:
            return snapshot_por_id
        snapshots_por_chave = []
        for log in logs:
            anterior = log.dados_anteriores or {}
            if anterior and _chave_item_snapshot(anterior) in chaves:
                snapshots_por_chave.append(anterior)
        return melhor_snapshot(snapshots_por_chave)

    @staticmethod
    def _recalcular_totais_entrada(entrada: EntradaNF):
        from django.db.models import Sum
        agg = entrada.itens.aggregate(
            produtos=Sum('valor_bruto'),
            desconto=Sum('valor_desconto'),
            ipi=Sum('valor_ipi'),
            icms=Sum('valor_icms'),
            total=Sum('valor_total'),
        )
        entrada.valor_produtos = agg['produtos'] or 0
        entrada.valor_desconto = agg['desconto'] or 0
        entrada.valor_ipi = agg['ipi'] or 0
        entrada.valor_icms = agg['icms'] or 0
        entrada.valor_total = (
            (agg['total'] or 0)
            + entrada.valor_frete
            + entrada.valor_seguro
            + entrada.valor_outras_despesas
        )
        entrada.save()

    @classmethod
    @transaction.atomic
    def efetivar_entrada(
        cls,
        entrada: EntradaNF,
        usuario,
        confirmar_custo_critico: bool = False,
    ) -> EntradaNF:
        if not entrada.pode_efetivar:
            raise DadosInvalidosError(
                f'Entrada ja foi efetivada (status: {entrada.get_status_display()}).'
            )
        if not entrada.itens.exists():
            raise DadosInvalidosError('Entrada sem itens nao pode ser efetivada.')

        cls._validar_itens_para_efetivar(entrada)
        cls._validar_custo_para_efetivar(
            entrada,
            confirmar_custo_critico=confirmar_custo_critico,
        )
        EntradaCustoService.aplicar_configurada(entrada)

        entrada.status = EntradaNF.Status.PROCESSANDO
        entrada.save(update_fields=['status', 'updated_at'])

        for item in entrada.itens.select_related('produto', 'item_pedido_compra'):
            quantidade_movimento = item.quantidade_recebida
            if quantidade_movimento is None:
                quantidade_movimento = item.quantidade_estoque or item.quantidade
            custo_final = item.custo_unitario_total or item.valor_unitario

            if quantidade_movimento <= 0:
                item.quantidade = quantidade_movimento
                item.quantidade_estoque = quantidade_movimento
                item.quantidade_recebida = quantidade_movimento
                item.custo_unitario_total = Decimal('0')
                item.save(update_fields=[
                    'quantidade',
                    'quantidade_estoque',
                    'quantidade_recebida',
                    'custo_unitario_total',
                    'updated_at',
                ])
                continue

            mov = MovimentacaoService.registrar_entrada_compra(
                produto_id=item.produto_id,
                filial_id=entrada.filial_id,
                quantidade=quantidade_movimento,
                valor_unitario=custo_final,
                usuario_id=usuario.pk,
                fornecedor_id=entrada.fornecedor_id,
                numero_lote=item.numero_lote,
                data_fabricacao=item.data_fabricacao,
                data_validade=item.data_validade,
                numero_nota=entrada.numero_nf,
                documento_id=entrada.pk,
            )

            if mov.lote_id:
                item.lote_gerado_id = mov.lote_id
            item.quantidade = quantidade_movimento
            item.quantidade_estoque = quantidade_movimento
            item.quantidade_recebida = quantidade_movimento
            item.custo_unitario_total = custo_final
            item.save(update_fields=[
                'lote_gerado',
                'quantidade',
                'quantidade_estoque',
                'quantidade_recebida',
                'custo_unitario_total',
                'updated_at',
            ])

            if item.item_pedido_compra_id:
                ItemPedidoCompra.objects.filter(pk=item.item_pedido_compra_id).update(
                    quantidade_recebida=F('quantidade_recebida') + quantidade_movimento,
                )

        if entrada.pedido_compra_id:
            cls._atualizar_status_pedido(entrada.pedido_compra)
            cls._avaliar_fornecedor(entrada)

        entrada.status = EntradaNF.Status.EFETIVADA
        entrada.usuario_efetivacao = usuario
        entrada.data_efetivacao = timezone.now()
        entrada.save(update_fields=[
            'status', 'usuario_efetivacao', 'data_efetivacao', 'updated_at',
        ])
        return entrada

    @staticmethod
    def _validar_custo_para_efetivar(
        entrada: EntradaNF,
        confirmar_custo_critico: bool = False,
    ):
        composicao = EntradaCustoService.compor(
            entrada=entrada,
            metodo_rateio=entrada.custo_rateio_metodo,
            incluir_ipi=entrada.custo_incluir_ipi,
            incluir_icms_st=entrada.custo_incluir_icms_st,
            incluir_icms=entrada.custo_incluir_icms,
            custo_financeiro=entrada.custo_financeiro or Decimal('0'),
        )
        criticos = [
            linha for linha in composicao.get('alertas_custo', [])
            if linha.alerta_custo_nivel == 'critico'
        ]
        if criticos and not confirmar_custo_critico:
            raise DadosInvalidosError(
                'Custo critico exige confirmacao antes de finalizar a entrada. '
                'Revise a tela Custos e marque a confirmacao na finalizacao.'
            )

    @staticmethod
    def _validar_itens_para_efetivar(entrada: EntradaNF):
        bloqueios = []
        for item in entrada.itens.select_related('produto'):
            CompraService.atualizar_diferenca_item(item)
            if not item.produto_id:
                bloqueios.append(f'Item {item.numero_item}: produto sem vinculo.')
                continue
            quantidade_recebida = item.quantidade_recebida
            if quantidade_recebida is None:
                quantidade_recebida = item.quantidade_estoque or item.quantidade
            if quantidade_recebida <= 0:
                if not item.justificativa_diferenca.strip():
                    bloqueios.append(
                        f'Item {item.numero_item}: recebimento zerado exige justificativa.'
                    )
                continue
            if item.produto.controla_lote and not item.numero_lote:
                bloqueios.append(f'Item {item.numero_item}: lote obrigatorio nao informado.')
            if item.produto.controla_validade and not item.data_validade:
                bloqueios.append(f'Item {item.numero_item}: validade obrigatoria nao informada.')
            if (
                item.produto.controla_validade
                and item.data_validade
                and item.data_validade < timezone.localdate()
            ):
                bloqueios.append(f'Item {item.numero_item}: validade vencida nao pode movimentar estoque.')
            if item.diferenca_bloqueante:
                detalhe = item.diferenca_descricao or 'diferenca bloqueante'
                bloqueios.append(f'Item {item.numero_item}: {detalhe}.')
        if bloqueios:
            raise DadosInvalidosError('Nao e possivel finalizar: ' + ' '.join(bloqueios))

    @staticmethod
    def avaliar_diferenca_item(item) -> tuple[str, str, bool]:
        if not item.produto_id:
            return 'produto_sem_vinculo', 'Produto sem equivalencia interna.', True

        quantidade_recebida = item.quantidade_recebida
        if quantidade_recebida is None:
            quantidade_recebida = item.quantidade_estoque or item.quantidade
        if quantidade_recebida <= 0:
            return (
                'quantidade_recebida',
                (
                    'Item recusado na conferencia. '
                    f'Nota: {item.quantidade_estoque}, recebido: {quantidade_recebida}.'
                ),
                not bool(item.justificativa_diferenca.strip()),
            )

        hoje = timezone.localdate()
        if item.produto.controla_lote and not item.numero_lote:
            return 'lote_obrigatorio', 'Produto exige lote para movimentar estoque.', True
        if item.produto.controla_validade and not item.data_validade:
            return 'validade_obrigatoria', 'Produto exige validade para movimentar estoque.', True
        if (
            item.produto.controla_validade
            and item.data_validade
            and item.data_validade < hoje
        ):
            return (
                'validade_vencida',
                f'Validade vencida em {item.data_validade:%d/%m/%Y}.',
                True,
            )
        if (
            item.produto.controla_validade
            and item.data_validade
            and item.produto.dias_aviso_vencimento is not None
        ):
            dias_para_vencer = (item.data_validade - hoje).days
            if 0 <= dias_para_vencer <= item.produto.dias_aviso_vencimento:
                return (
                    'validade_proxima',
                    f'Validade proxima: vence em {dias_para_vencer} dia(s).',
                    False,
                )
        if item.quantidade_recebida != item.quantidade_estoque:
            return (
                'quantidade_recebida',
                (
                    f'Quantidade recebida diferente da nota. '
                    f'Nota: {item.quantidade_estoque}, recebido: {item.quantidade_recebida}.'
                ),
                not bool(item.justificativa_diferenca.strip()),
            )
        return '', '', False

    @staticmethod
    def atualizar_diferenca_item(item):
        tipo, descricao, bloqueante = CompraService.avaliar_diferenca_item(item)
        item.diferenca_tipo = tipo
        item.diferenca_descricao = descricao
        item.diferenca_bloqueante = bloqueante
        item.save(update_fields=[
            'quantidade_recebida',
            'numero_lote',
            'data_validade',
            'diferenca_tipo',
            'diferenca_descricao',
            'diferenca_bloqueante',
            'justificativa_diferenca',
            'updated_at',
        ])
        return item

    @staticmethod
    def _atualizar_status_conferencia(entrada: EntradaNF):
        itens = list(entrada.itens.all())
        if not itens:
            return
        if any(item.diferenca_bloqueante or not item.produto_id for item in itens):
            entrada.status = EntradaNF.Status.AGUARDANDO_VINCULOS
        elif any(item.diferenca_tipo for item in itens):
            entrada.status = EntradaNF.Status.COM_DIFERENCAS
        else:
            entrada.status = EntradaNF.Status.AGUARDANDO_CONFERENCIA
        entrada.save(update_fields=['status', 'updated_at'])

    @staticmethod
    def _atualizar_status_pedido(pedido: PedidoCompra):
        pedido.refresh_from_db()
        itens = list(pedido.itens.all())
        if all(item.recebido_completo for item in itens):
            pedido.status = PedidoCompra.Status.RECEBIDO
            pedido.data_entrega_realizada = timezone.now().date()
        else:
            pedido.status = PedidoCompra.Status.PARCIALMENTE_RECEBIDO
        pedido.save(update_fields=['status', 'data_entrega_realizada', 'updated_at'])

    @staticmethod
    def _avaliar_fornecedor(entrada: EntradaNF):
        pedido = entrada.pedido_compra
        if not pedido or not pedido.data_entrega_prevista:
            return

        data_real = entrada.data_entrada.date()
        dias_atraso = (data_real - pedido.data_entrega_prevista).days
        no_prazo = dias_atraso <= 0

        if dias_atraso <= 0:
            nota_pont = 5
        elif dias_atraso <= 2:
            nota_pont = 4
        elif dias_atraso <= 5:
            nota_pont = 3
        elif dias_atraso <= 10:
            nota_pont = 2
        else:
            nota_pont = 1

        avaliacao = AvaliacaoFornecedor.objects.create(
            filial=entrada.filial,
            fornecedor=entrada.fornecedor,
            pedido_compra=pedido,
            entrada_nf=entrada,
            data_prevista=pedido.data_entrega_prevista,
            data_real=data_real,
            dias_atraso=dias_atraso,
            entregue_no_prazo=no_prazo,
            nota_pontualidade=nota_pont,
            nota_qualidade=5,
            nota_geral=Decimal(str(nota_pont)),
        )

        fornecedor = entrada.fornecedor
        agg = AvaliacaoFornecedor.objects.filter(fornecedor=fornecedor).aggregate(
            media=Avg('nota_geral'),
        )
        total = AvaliacaoFornecedor.objects.filter(fornecedor=fornecedor).count()
        no_prazo_count = AvaliacaoFornecedor.objects.filter(
            fornecedor=fornecedor, entregue_no_prazo=True,
        ).count()

        fornecedor.nota_qualidade = agg['media'] or 0
        fornecedor.total_entregas = total
        fornecedor.entregas_no_prazo = no_prazo_count
        fornecedor.save(update_fields=[
            'nota_qualidade', 'total_entregas', 'entregas_no_prazo', 'updated_at',
        ])
        return avaliacao

    @classmethod
    @transaction.atomic
    def cancelar_entrada(cls, entrada: EntradaNF, usuario, motivo: str) -> EntradaNF:
        if not entrada.pode_cancelar:
            raise DadosInvalidosError(
                'So e possivel cancelar entradas abertas. Para efetivadas, use cancelamento com reversao de estoque.'
            )
        entrada.status = EntradaNF.Status.CANCELADA
        entrada.observacao = f'{entrada.observacao}\n[CANCELADA]: {motivo}'.strip()
        entrada.save(update_fields=['status', 'observacao', 'updated_at'])
        return entrada
