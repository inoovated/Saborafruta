"""Conferencia operacional de consistencia do estoque."""
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.models import Sum

from apps.estoque.models import Estoque, LoteProduto, MovimentacaoEstoque


TOLERANCIA = Decimal('0.0005')


def _decimal(value):
    return Decimal(str(value or '0'))


def _diverge(a, b):
    return abs(_decimal(a) - _decimal(b)) > TOLERANCIA


class Command(BaseCommand):
    help = (
        'Confere consistencia entre saldo consolidado, disponibilidade, '
        'snapshots de movimentacao e lotes.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--filial', type=int, help='Filtra por ID da filial.')
        parser.add_argument('--produto', type=int, help='Filtra por ID do produto.')
        parser.add_argument(
            '--fix-disponivel',
            action='store_true',
            help='Corrige apenas quantidade_disponivel quando divergir de atual - reservado.',
        )
        parser.add_argument(
            '--fail-on-issues',
            action='store_true',
            help='Retorna erro quando encontrar divergencias.',
        )

    def handle(self, *args, **options):
        existing_tables = set(connection.introspection.table_names())
        required_tables = {
            'estoque',
            'movimentacoes_estoque',
            'lotes_produto',
            'produtos',
            'filiais',
        }
        missing = required_tables - existing_tables
        if missing:
            self.stdout.write(self.style.WARNING(
                f'Conferencia ignorada: tabelas ausentes: {", ".join(sorted(missing))}'
            ))
            return

        qs = Estoque.objects.select_related('produto', 'filial').order_by(
            'filial_id',
            'produto__descricao',
        )
        if options.get('filial'):
            qs = qs.filter(filial_id=options['filial'])
        if options.get('produto'):
            qs = qs.filter(produto_id=options['produto'])

        total = 0
        issues = 0
        corrigidos = 0

        self.stdout.write(self.style.NOTICE('Conferindo estoque consolidado...'))
        for estoque in qs.iterator(chunk_size=500):
            total += 1
            produto = estoque.produto
            prefixo = (
                f'filial={estoque.filial_id} produto={produto.pk} '
                f'({produto.descricao})'
            )

            esperado_disponivel = estoque.quantidade_atual - estoque.quantidade_reservada
            if _diverge(estoque.quantidade_disponivel, esperado_disponivel):
                issues += 1
                self.stdout.write(self.style.WARNING(
                    f'{prefixo}: disponivel={estoque.quantidade_disponivel} '
                    f'esperado={esperado_disponivel}'
                ))
                if options['fix_disponivel']:
                    estoque.quantidade_disponivel = esperado_disponivel
                    estoque.save(update_fields=['quantidade_disponivel', 'updated_at'])
                    corrigidos += 1

            if estoque.quantidade_reservada < 0:
                issues += 1
                self.stdout.write(self.style.WARNING(
                    f'{prefixo}: quantidade_reservada negativa={estoque.quantidade_reservada}'
                ))

            divergencia_snapshot = self._conferir_snapshot(prefixo, estoque)
            if divergencia_snapshot:
                issues += 1
            if produto.controla_lote:
                divergencia_lote = self._conferir_lotes(prefixo, estoque)
                if divergencia_lote:
                    issues += 1

        resumo = (
            f'Conferencia concluida: {total} saldos, '
            f'{issues} divergencias, {corrigidos} disponiveis corrigidos.'
        )
        if issues:
            self.stdout.write(self.style.WARNING(resumo))
            if options['fail_on_issues']:
                raise CommandError(resumo)
        else:
            self.stdout.write(self.style.SUCCESS(resumo))

    def _conferir_snapshot(self, prefixo, estoque):
        ultima = (
            MovimentacaoEstoque.objects
            .filter(produto_id=estoque.produto_id, filial_id=estoque.filial_id)
            .order_by('-data_movimentacao', '-pk')
            .first()
        )
        if not ultima:
            if estoque.quantidade_atual:
                self.stdout.write(self.style.WARNING(
                    f'{prefixo}: saldo atual={estoque.quantidade_atual} sem movimentacao.'
                ))
                return True
            return False
        if _diverge(ultima.quantidade_posterior, estoque.quantidade_atual):
            self.stdout.write(self.style.WARNING(
                f'{prefixo}: ultimo_snapshot={ultima.quantidade_posterior} '
                f'saldo_atual={estoque.quantidade_atual} mov={ultima.pk}'
            ))
            return True
        return False

    def _conferir_lotes(self, prefixo, estoque):
        total_lotes = (
            LoteProduto.objects
            .filter(produto_id=estoque.produto_id, filial_id=estoque.filial_id)
            .aggregate(total=Sum('quantidade_atual'))
            .get('total')
            or Decimal('0')
        )
        if not _diverge(total_lotes, estoque.quantidade_atual):
            return False
        self.stdout.write(self.style.WARNING(
            f'{prefixo}: total_lotes={total_lotes} saldo_atual={estoque.quantidade_atual}'
        ))
        return True
