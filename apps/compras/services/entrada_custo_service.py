"""Composicao de custo de entrada de NF.

Este servico transforma valores da nota (frete, ST, desconto etc.) em custo
unitario por item. A efetivacao da entrada usa esse snapshot para custo medio
e custo por lote.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone

from apps.compras.models import EntradaNF, ItemEntradaNF
from apps.core.services.exceptions import DadosInvalidosError


CENTAVOS = Decimal('0.01')
QUATRO_CASAS = Decimal('0.0001')
ITEM_REMOVIDO_ENTRADA = 'Item removido da entrada.'


@dataclass
class LinhaCustoEntrada:
    item: ItemEntradaNF
    quantidade: Decimal
    base_rateio: Decimal
    valor_mercadoria: Decimal
    valor_liquido_nf: Decimal
    valor_agregado_antes_desconto: Decimal
    frete: Decimal
    seguro: Decimal
    outras_despesas: Decimal
    desconto: Decimal
    ipi: Decimal
    icms_st: Decimal
    icms_nao_recuperavel: Decimal
    custo_financeiro: Decimal
    acrescimos_total: Decimal
    custo_total: Decimal
    custo_unitario_nf: Decimal
    custo_unitario: Decimal
    custo_referencia: Decimal
    custo_referencia_origem: str
    variacao_percentual: Decimal
    alerta_custo_nivel: str
    alerta_custo_texto: str


class EntradaCustoService:
    """Calcula e salva custo composto por item de entrada."""

    METODOS = {
        EntradaNF.MetodoRateioCusto.VALOR,
        EntradaNF.MetodoRateioCusto.QUANTIDADE,
        EntradaNF.MetodoRateioCusto.PESO,
    }

    @classmethod
    def compor(
        cls,
        entrada: EntradaNF,
        metodo_rateio: str = EntradaNF.MetodoRateioCusto.VALOR,
        incluir_ipi: bool = True,
        incluir_icms_st: bool = True,
        incluir_icms: bool = False,
        custo_financeiro: Decimal = Decimal('0'),
        usar_apenas_valor_nota: bool = False,
        salvar: bool = False,
        salvar_configuracao: bool = False,
    ) -> dict:
        metodo_rateio = metodo_rateio or EntradaNF.MetodoRateioCusto.VALOR
        if metodo_rateio not in cls.METODOS:
            raise DadosInvalidosError('Metodo de rateio de custo invalido.')

        custo_financeiro = cls._decimal(custo_financeiro).quantize(CENTAVOS)
        itens = list(
            entrada.itens
            .select_related('produto')
            .order_by('numero_item', 'pk')
        )
        if not itens:
            raise DadosInvalidosError('Entrada sem itens para compor custo.')

        itens_custeaveis = [
            item for item in itens
            if cls._item_custeavel(item)
        ]
        if not itens_custeaveis:
            raise DadosInvalidosError('Entrada sem itens recebidos para compor custo.')

        linhas_base = [cls._linha_base(item) for item in itens_custeaveis]
        bases, metodo_efetivo, aviso_rateio = cls._bases_para_rateio(linhas_base, metodo_rateio)
        if usar_apenas_valor_nota:
            incluir_ipi = False
            incluir_icms_st = False
            incluir_icms = False
            custo_financeiro = Decimal('0.00')

        rateios = {
            'frete': cls._ratear(Decimal('0') if usar_apenas_valor_nota else entrada.valor_frete, bases),
            'seguro': cls._ratear(Decimal('0') if usar_apenas_valor_nota else entrada.valor_seguro, bases),
            'outras_despesas': cls._ratear(
                Decimal('0') if usar_apenas_valor_nota else entrada.valor_outras_despesas,
                bases,
            ),
            'ipi': cls._ratear(entrada.valor_ipi if incluir_ipi else Decimal('0'), bases),
            'icms_st': cls._ratear(
                entrada.valor_icms_st if incluir_icms_st else Decimal('0'),
                bases,
            ),
            'icms_nao_recuperavel': cls._ratear(
                entrada.valor_icms if incluir_icms else Decimal('0'),
                bases,
            ),
            'custo_financeiro': cls._ratear(custo_financeiro, bases),
        }
        limites_desconto = []
        for index, base in enumerate(linhas_base):
            limites_desconto.append((
                base['valor_mercadoria']
                + rateios['frete'][index]
                + rateios['seguro'][index]
                + rateios['outras_despesas'][index]
                + rateios['ipi'][index]
                + rateios['icms_st'][index]
                + rateios['icms_nao_recuperavel'][index]
                + rateios['custo_financeiro'][index]
            ).quantize(CENTAVOS))
        rateios['desconto'] = cls._ratear_com_limite(
            entrada.valor_desconto,
            bases,
            limites_desconto,
        )

        linhas: list[LinhaCustoEntrada] = []
        for index, base in enumerate(linhas_base):
            acrescimos_total = (
                rateios['frete'][index]
                + rateios['seguro'][index]
                + rateios['outras_despesas'][index]
                + rateios['ipi'][index]
                + rateios['icms_st'][index]
                + rateios['icms_nao_recuperavel'][index]
                + rateios['custo_financeiro'][index]
            ).quantize(CENTAVOS)
            custo_total = (
                base['valor_mercadoria']
                + rateios['frete'][index]
                + rateios['seguro'][index]
                + rateios['outras_despesas'][index]
                - rateios['desconto'][index]
                + rateios['ipi'][index]
                + rateios['icms_st'][index]
                + rateios['icms_nao_recuperavel'][index]
                + rateios['custo_financeiro'][index]
            ).quantize(CENTAVOS)
            if custo_total < 0:
                raise DadosInvalidosError(
                    f'Composicao de custo negativa no item {base["item"].numero_item}.'
                )
            custo_unitario = (
                (custo_total / base['quantidade']).quantize(QUATRO_CASAS, rounding=ROUND_HALF_UP)
                if base['quantidade']
                else Decimal('0')
            )
            custo_unitario_nf = (
                (base['valor_mercadoria'] / base['quantidade']).quantize(QUATRO_CASAS, rounding=ROUND_HALF_UP)
                if base['quantidade']
                else Decimal('0')
            )
            referencia = cls._referencia_custo(base['item'], entrada)
            alerta = cls._alerta_variacao(
                custo_unitario=custo_unitario,
                custo_referencia=referencia['valor'],
                origem=referencia['origem'],
            )
            linhas.append(LinhaCustoEntrada(
                item=base['item'],
                quantidade=base['quantidade'],
                base_rateio=bases[index],
                valor_mercadoria=base['valor_mercadoria'],
                valor_liquido_nf=(base['valor_mercadoria'] - rateios['desconto'][index]).quantize(CENTAVOS),
                valor_agregado_antes_desconto=(custo_total + rateios['desconto'][index]).quantize(CENTAVOS),
                frete=rateios['frete'][index],
                seguro=rateios['seguro'][index],
                outras_despesas=rateios['outras_despesas'][index],
                desconto=rateios['desconto'][index],
                ipi=rateios['ipi'][index],
                icms_st=rateios['icms_st'][index],
                icms_nao_recuperavel=rateios['icms_nao_recuperavel'][index],
                custo_financeiro=rateios['custo_financeiro'][index],
                acrescimos_total=acrescimos_total,
                custo_total=custo_total,
                custo_unitario_nf=custo_unitario_nf,
                custo_unitario=custo_unitario,
                custo_referencia=referencia['valor'],
                custo_referencia_origem=referencia['origem'],
                variacao_percentual=alerta['variacao_percentual'],
                alerta_custo_nivel=alerta['nivel'],
                alerta_custo_texto=alerta['texto'],
            ))

        resumo = cls._resumo(
            linhas,
            entrada,
            incluir_ipi,
            incluir_icms_st,
            incluir_icms,
            custo_financeiro,
            usar_apenas_valor_nota,
        )
        if salvar:
            itens_com_custo = {linha.item.pk for linha in linhas}
            cls._salvar(
                entrada=entrada,
                linhas=linhas,
                itens_sem_custo=[
                    item for item in itens
                    if item.pk not in itens_com_custo
                ],
                metodo_rateio=metodo_rateio,
                incluir_ipi=incluir_ipi,
                incluir_icms_st=incluir_icms_st,
                incluir_icms=incluir_icms,
                custo_financeiro=custo_financeiro,
                usar_apenas_valor_nota=usar_apenas_valor_nota,
                salvar_configuracao=salvar_configuracao,
            )

        return {
            'entrada': entrada,
            'linhas': linhas,
            'resumo': resumo,
            'alertas_custo': [linha for linha in linhas if linha.alerta_custo_nivel],
            'metodo_rateio': metodo_rateio,
            'metodo_efetivo': metodo_efetivo,
            'aviso_rateio': aviso_rateio,
            'incluir_ipi': incluir_ipi,
            'incluir_icms_st': incluir_icms_st,
            'incluir_icms': incluir_icms,
            'custo_financeiro': custo_financeiro,
            'usar_apenas_valor_nota': usar_apenas_valor_nota,
        }

    @classmethod
    def aplicar_configurada(cls, entrada: EntradaNF) -> dict:
        return cls.compor(
            entrada=entrada,
            metodo_rateio=entrada.custo_rateio_metodo or EntradaNF.MetodoRateioCusto.VALOR,
            incluir_ipi=entrada.custo_incluir_ipi,
            incluir_icms_st=entrada.custo_incluir_icms_st,
            incluir_icms=entrada.custo_incluir_icms,
            custo_financeiro=entrada.custo_financeiro or Decimal('0'),
            usar_apenas_valor_nota=entrada.custo_usar_apenas_valor_nota,
            salvar=True,
            salvar_configuracao=False,
        )

    @classmethod
    def aplicar_padrao(cls, entrada: EntradaNF) -> dict:
        return cls.compor(entrada=entrada, salvar=True, salvar_configuracao=True)

    @staticmethod
    def _decimal(valor) -> Decimal:
        if isinstance(valor, Decimal):
            return valor
        return Decimal(str(valor or '0'))

    @classmethod
    def _quantidade_recebida(cls, item: ItemEntradaNF) -> Decimal:
        quantidade = item.quantidade_recebida
        if quantidade is None:
            quantidade = item.quantidade_estoque or item.quantidade
        return cls._decimal(quantidade)

    @classmethod
    def _item_custeavel(cls, item: ItemEntradaNF) -> bool:
        if ITEM_REMOVIDO_ENTRADA in (item.observacao or ''):
            return False
        return cls._quantidade_recebida(item) > 0

    @classmethod
    def _linha_base(cls, item: ItemEntradaNF) -> dict:
        quantidade = cls._quantidade_recebida(item)
        if quantidade <= 0:
            raise DadosInvalidosError(f'Item {item.numero_item}: quantidade recebida deve ser positiva.')

        valor_mercadoria = cls._decimal(
            item.valor_bruto or item.valor_total or (item.valor_unitario * quantidade)
        ).quantize(CENTAVOS)
        usa_custo_cadastrado = False
        if valor_mercadoria <= 0 and cls._item_manual(item):
            referencia = cls._referencia_custo(item, item.entrada)
            valor_mercadoria = (referencia['valor'] * quantidade).quantize(CENTAVOS)
            usa_custo_cadastrado = valor_mercadoria > 0
        peso_unitario = Decimal('0')
        if item.produto_id:
            peso_unitario = cls._decimal(
                item.produto.peso_liquido or item.produto.peso_bruto or Decimal('0')
            )
        base_quantidade = quantidade if quantidade > 0 else Decimal('0')
        base_peso = quantidade * peso_unitario if peso_unitario > 0 else Decimal('0')
        if usa_custo_cadastrado:
            base_valor = Decimal('0')
            base_quantidade = Decimal('0')
            base_peso = Decimal('0')
        else:
            base_valor = valor_mercadoria if valor_mercadoria > 0 else Decimal('0')
        return {
            'item': item,
            'quantidade': quantidade,
            'valor_mercadoria': valor_mercadoria,
            'base_valor': base_valor,
            'base_quantidade': base_quantidade,
            'base_peso': base_peso,
            'usa_custo_cadastrado': usa_custo_cadastrado,
        }

    @staticmethod
    def _item_manual(item: ItemEntradaNF) -> bool:
        return bool(
            item.produto_id
            and not (item.ean_xml or '').strip()
            and not (item.codigo_produto_fornecedor or '').strip()
            and not (item.descricao_xml or '').strip()
        )

    @classmethod
    def _referencia_custo(cls, item: ItemEntradaNF, entrada: EntradaNF) -> dict:
        if not item.produto_id:
            return {'valor': Decimal('0'), 'origem': ''}

        from apps.estoque.models import Estoque

        estoque = Estoque.objects.filter(
            produto_id=item.produto_id,
            filial_id=entrada.filial_id,
        ).first()
        if estoque and cls._decimal(estoque.custo_medio) > 0:
            return {
                'valor': cls._decimal(estoque.custo_medio).quantize(QUATRO_CASAS),
                'origem': 'Custo medio da filial',
            }

        produto = item.produto
        if cls._decimal(produto.preco_custo_medio) > 0:
            return {
                'valor': cls._decimal(produto.preco_custo_medio).quantize(QUATRO_CASAS),
                'origem': 'Custo medio do produto',
            }
        if cls._decimal(produto.preco_custo) > 0:
            return {
                'valor': cls._decimal(produto.preco_custo).quantize(QUATRO_CASAS),
                'origem': 'Custo cadastrado',
            }
        return {'valor': Decimal('0'), 'origem': ''}

    @staticmethod
    def _alerta_variacao(custo_unitario: Decimal, custo_referencia: Decimal, origem: str) -> dict:
        if not origem or custo_referencia <= 0:
            return {
                'nivel': '',
                'texto': '',
                'variacao_percentual': Decimal('0.00'),
            }

        variacao = (
            ((custo_unitario - custo_referencia) / custo_referencia) * Decimal('100')
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        variacao_abs = abs(variacao)
        if variacao_abs >= Decimal('50'):
            nivel = 'critico'
        elif variacao_abs >= Decimal('20'):
            nivel = 'atencao'
        else:
            nivel = ''

        if not nivel:
            texto = ''
        else:
            direcao = 'acima' if variacao > 0 else 'abaixo'
            texto = (
                f'Custo composto {variacao_abs}% {direcao} de {origem.lower()}. '
                'Revise frete, ST, desconto e impostos recuperaveis antes de efetivar.'
            )
        return {
            'nivel': nivel,
            'texto': texto,
            'variacao_percentual': variacao,
        }

    @classmethod
    def _bases_para_rateio(cls, linhas_base: list[dict], metodo_rateio: str):
        aviso = ''
        campos = {
            EntradaNF.MetodoRateioCusto.VALOR: 'base_valor',
            EntradaNF.MetodoRateioCusto.QUANTIDADE: 'base_quantidade',
            EntradaNF.MetodoRateioCusto.PESO: 'base_peso',
        }
        campo = campos[metodo_rateio]
        bases = [linha[campo] for linha in linhas_base]
        if sum(bases, Decimal('0')) > 0:
            return bases, metodo_rateio, aviso

        if metodo_rateio == EntradaNF.MetodoRateioCusto.PESO:
            bases = [linha['base_quantidade'] for linha in linhas_base]
            if sum(bases, Decimal('0')) > 0:
                return bases, EntradaNF.MetodoRateioCusto.QUANTIDADE, (
                    'Nenhum peso valido nos produtos; o rateio por peso caiu para quantidade.'
                )

        bases = [linha['base_valor'] for linha in linhas_base]
        if sum(bases, Decimal('0')) > 0:
            return bases, EntradaNF.MetodoRateioCusto.VALOR, (
                'Base escolhida sem valor positivo; o rateio caiu para valor dos itens.'
            )

        bases_sem_custo_cadastrado = [
            Decimal('0') if linha.get('usa_custo_cadastrado') else Decimal('1')
            for linha in linhas_base
        ]
        if sum(bases_sem_custo_cadastrado, Decimal('0')) > 0:
            return bases_sem_custo_cadastrado, EntradaNF.MetodoRateioCusto.VALOR, (
                'Itens sem base positiva; o rateio foi dividido igualmente entre os itens da nota.'
            )

        return [Decimal('0') for _ in linhas_base], EntradaNF.MetodoRateioCusto.VALOR, (
            'Itens manuais sem valor na nota usaram o custo cadastrado do produto.'
        )

    @classmethod
    def _ratear(cls, valor, bases: list[Decimal]) -> list[Decimal]:
        valor = cls._decimal(valor).quantize(CENTAVOS)
        if not bases:
            return []
        total_base = sum(bases, Decimal('0'))
        if valor == 0 or total_base <= 0:
            return [Decimal('0.00') for _ in bases]

        partes = []
        acumulado = Decimal('0.00')
        ultimo = len(bases) - 1
        for index, base in enumerate(bases):
            if index == ultimo:
                parte = valor - acumulado
            else:
                parte = (valor * base / total_base).quantize(CENTAVOS, rounding=ROUND_HALF_UP)
                acumulado += parte
            partes.append(parte)
        return partes

    @classmethod
    def _ratear_com_limite(
        cls,
        valor,
        bases: list[Decimal],
        limites: list[Decimal],
    ) -> list[Decimal]:
        valor = cls._decimal(valor).quantize(CENTAVOS)
        if valor == 0 or not bases:
            return [Decimal('0.00') for _ in bases]
        total_limite = sum(limites, Decimal('0.00')).quantize(CENTAVOS)
        if valor > total_limite:
            raise DadosInvalidosError('Desconto maior que o custo total dos itens.')

        partes = [Decimal('0.00') for _ in bases]
        pendente = valor
        ativos = {index for index, limite in enumerate(limites) if limite > 0}
        while pendente > 0 and ativos:
            bases_ativas = [
                bases[index] if index in ativos else Decimal('0')
                for index in range(len(bases))
            ]
            if sum(bases_ativas, Decimal('0')) <= 0:
                bases_ativas = [
                    Decimal('1') if index in ativos else Decimal('0')
                    for index in range(len(bases))
                ]
            proposta = cls._ratear(pendente, bases_ativas)
            travou = False
            for index in list(ativos):
                capacidade = (limites[index] - partes[index]).quantize(CENTAVOS)
                if capacidade <= 0:
                    ativos.remove(index)
                    continue
                if proposta[index] >= capacidade:
                    partes[index] += capacidade
                    pendente -= capacidade
                    ativos.remove(index)
                    travou = True
            if not travou:
                for index in ativos:
                    partes[index] += proposta[index]
                    pendente -= proposta[index]
                break

        if pendente > 0:
            for index, limite in enumerate(limites):
                capacidade = (limite - partes[index]).quantize(CENTAVOS)
                if capacidade <= 0:
                    continue
                ajuste = min(capacidade, pendente)
                partes[index] += ajuste
                pendente -= ajuste
                if pendente == 0:
                    break
        return [parte.quantize(CENTAVOS) for parte in partes]

    @staticmethod
    def _resumo(
        linhas: list[LinhaCustoEntrada],
        entrada: EntradaNF,
        incluir_ipi: bool,
        incluir_icms_st: bool,
        incluir_icms: bool,
        custo_financeiro: Decimal,
        usar_apenas_valor_nota: bool,
    ) -> dict:
        return {
            'valor_mercadoria': sum((linha.valor_mercadoria for linha in linhas), Decimal('0')),
            'frete': Decimal('0') if usar_apenas_valor_nota else entrada.valor_frete or Decimal('0'),
            'seguro': Decimal('0') if usar_apenas_valor_nota else entrada.valor_seguro or Decimal('0'),
            'outras_despesas': (
                Decimal('0') if usar_apenas_valor_nota else entrada.valor_outras_despesas or Decimal('0')
            ),
            'desconto': entrada.valor_desconto or Decimal('0'),
            'ipi': entrada.valor_ipi if incluir_ipi else Decimal('0'),
            'icms_st': entrada.valor_icms_st if incluir_icms_st else Decimal('0'),
            'icms_nao_recuperavel': entrada.valor_icms if incluir_icms else Decimal('0'),
            'custo_financeiro': custo_financeiro,
            'custo_total': sum((linha.custo_total for linha in linhas), Decimal('0')),
            'alertas_custo': sum(1 for linha in linhas if linha.alerta_custo_nivel),
            'alertas_custo_criticos': sum(
                1 for linha in linhas if linha.alerta_custo_nivel == 'critico'
            ),
        }

    @staticmethod
    @transaction.atomic
    def _salvar(
        entrada: EntradaNF,
        linhas: list[LinhaCustoEntrada],
        itens_sem_custo: list[ItemEntradaNF],
        metodo_rateio: str,
        incluir_ipi: bool,
        incluir_icms_st: bool,
        incluir_icms: bool,
        custo_financeiro: Decimal,
        usar_apenas_valor_nota: bool,
        salvar_configuracao: bool,
    ) -> None:
        for linha in linhas:
            linha.item.custo_unitario_total = linha.custo_unitario
            linha.item.save(update_fields=['custo_unitario_total', 'updated_at'])
        for item in itens_sem_custo:
            item.custo_unitario_total = Decimal('0')
            item.save(update_fields=['custo_unitario_total', 'updated_at'])

        update_fields = ['custo_composto_em', 'updated_at']
        entrada.custo_composto_em = timezone.now()
        if salvar_configuracao:
            entrada.custo_rateio_metodo = metodo_rateio
            entrada.custo_incluir_ipi = incluir_ipi
            entrada.custo_incluir_icms_st = incluir_icms_st
            entrada.custo_incluir_icms = incluir_icms
            entrada.custo_usar_apenas_valor_nota = usar_apenas_valor_nota
            update_fields.extend([
                'custo_rateio_metodo',
                'custo_incluir_ipi',
                'custo_incluir_icms_st',
                'custo_incluir_icms',
                'custo_usar_apenas_valor_nota',
            ])
            if not usar_apenas_valor_nota:
                entrada.custo_financeiro = custo_financeiro
                update_fields.append('custo_financeiro')
        entrada.save(update_fields=update_fields)
