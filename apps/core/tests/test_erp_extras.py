from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.core.templatetags.erp_extras import filial_apelido, telefone


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


class TelefoneFilterTests(SimpleTestCase):
    def test_formata_celular_com_ddd(self):
        self.assertEqual(telefone('84988887777'), '(84) 98888-7777')

    def test_formata_telefone_fixo_com_ddd(self):
        self.assertEqual(telefone('8433334444'), '(84) 3333-4444')
