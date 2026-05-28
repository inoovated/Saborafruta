from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.core.models import Empresa, Filial, PerfilAcesso, Usuario
from apps.financeiro.constants.enums import TipoFormaPagamento
from apps.financeiro.models import FormaPagamento


class FormasPagamentoFinanceiroTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa = Empresa.objects.create(
            razao_social="Empresa Financeiro LTDA",
            nome_fantasia="Empresa Financeiro",
            cnpj="72345678000191",
            regime_tributario=Empresa.RegimeTributario.SIMPLES_NACIONAL,
            codigo_regime_tributario=1,
        )
        cls.filial = Filial.objects.create(
            empresa=cls.empresa,
            razao_social="Filial Financeiro",
            nome_fantasia="Matriz",
            cnpj="72345678000192",
            uf="RN",
        )
        cls.filial_destino = Filial.objects.create(
            empresa=cls.empresa,
            razao_social="Filial Destino",
            nome_fantasia="Destino",
            cnpj="72345678000193",
            uf="RN",
        )
        cls.perfil = PerfilAcesso.objects.create(
            empresa=cls.empresa,
            nome="Admin Financeiro",
            is_admin=True,
        )
        cls.usuario = Usuario.objects.create_user(
            email="financeiro-formas@inoovated.com",
            nome="Usuario Financeiro",
            password="teste1234",
            empresa=cls.empresa,
            filial=cls.filial,
            perfil=cls.perfil,
        )

    def setUp(self):
        self.client.force_login(self.usuario)
        session = self.client.session
        session["filial_ativa_id"] = self.filial.pk
        session.save()

    def test_salva_forma_de_pagamento_na_filial_ativa(self):
        response = self.client.post(reverse("financeiro:formas_pagamento"), {
            "acao": "salvar",
            "descricao": "PIX",
            "tipo": TipoFormaPagamento.PIX,
            "codigo_sefaz": "17",
            "prazo_liquidacao_dias": "0",
            "taxa_administrativa": "0.00",
            "ativo": "on",
        })

        self.assertEqual(response.status_code, 302)
        forma = FormaPagamento.objects.get(descricao="PIX")
        self.assertEqual(forma.filial, self.filial)
        self.assertEqual(forma.empresa, self.empresa)

    def test_replicar_forma_de_pagamento_para_outra_filial(self):
        forma = FormaPagamento.objects.create(
            empresa=self.empresa,
            filial=self.filial,
            descricao="Cartão de Crédito",
            tipo=TipoFormaPagamento.CARTAO_CREDITO,
            codigo_sefaz="03",
            requer_tef=True,
            taxa_administrativa=Decimal("2.50"),
        )

        response = self.client.post(reverse("financeiro:formas_pagamento"), {
            "acao": "replicar",
            "id": forma.pk,
            "filiais_destino": [str(self.filial_destino.pk)],
        })

        self.assertEqual(response.status_code, 302)
        replica = FormaPagamento.objects.get(
            filial=self.filial_destino,
            descricao="Cartão de Crédito",
        )
        self.assertEqual(replica.tipo, TipoFormaPagamento.CARTAO_CREDITO)
        self.assertTrue(replica.requer_tef)
        self.assertEqual(replica.taxa_administrativa, Decimal("2.50"))
