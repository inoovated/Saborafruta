from decimal import Decimal
from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.estoque.views.inventario import _resumo_inventario


class ResumoInventarioTests(SimpleTestCase):
    def item(self, contada=None, diferenca=None, valor=None):
        return SimpleNamespace(
            quantidade_contada=contada,
            diferenca=diferenca,
            valor_diferenca=valor,
        )

    def test_resumo_calcula_contagem_pendencias_e_divergencias(self):
        resumo = _resumo_inventario([
            self.item(contada=Decimal('10'), diferenca=Decimal('0'), valor=Decimal('0')),
            self.item(contada=Decimal('8'), diferenca=Decimal('-2'), valor=Decimal('-5.00')),
            self.item(contada=Decimal('12'), diferenca=Decimal('2'), valor=Decimal('7.50')),
            self.item(),
        ])

        self.assertEqual(resumo['total'], 4)
        self.assertEqual(resumo['contados'], 3)
        self.assertEqual(resumo['pendentes'], 1)
        self.assertEqual(resumo['divergentes'], 2)
        self.assertEqual(resumo['sem_divergencia'], 1)
        self.assertEqual(resumo['valor_falta'], Decimal('5.00'))
        self.assertEqual(resumo['valor_sobra'], Decimal('7.50'))
        self.assertEqual(resumo['valor_liquido'], Decimal('2.50'))
        self.assertEqual(resumo['progresso_percentual'], 75)

    def test_resumo_sem_itens_nao_divide_por_zero(self):
        resumo = _resumo_inventario([])

        self.assertEqual(resumo['total'], 0)
        self.assertEqual(resumo['contados'], 0)
        self.assertEqual(resumo['pendentes'], 0)
        self.assertEqual(resumo['progresso_percentual'], 0)
