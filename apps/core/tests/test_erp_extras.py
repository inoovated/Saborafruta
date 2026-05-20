from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.core.templatetags.erp_extras import filial_apelido


class FilialApelidoTests(SimpleTestCase):
    def test_usa_trecho_operacional_apos_separador(self):
        filial = SimpleNamespace(
            nome_fantasia='Polpa do Nordeste — Matriz Natal',
            razao_social='POLPA DO NORDESTE',
            cidade='Natal',
            is_matriz=True,
        )

        self.assertEqual(filial_apelido(filial), 'Matriz Natal')

    def test_diferencia_filial_sem_mostrar_prefixo_repetido(self):
        filial = SimpleNamespace(
            nome_fantasia='Polpa do Nordeste — Mossoró',
            razao_social='POLPA DO NORDESTE',
            cidade='Mossoró',
            is_matriz=False,
        )

        self.assertEqual(filial_apelido(filial), 'Mossoró')

    def test_matriz_sem_apelido_recebe_cidade(self):
        filial = SimpleNamespace(
            nome_fantasia='Polpa do Nordeste',
            razao_social='POLPA DO NORDESTE',
            cidade='Natal',
            is_matriz=True,
        )

        self.assertEqual(filial_apelido(filial), 'Matriz Natal')
