from unittest.mock import patch

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from apps.core.models import Empresa, Filial, PerfilAcesso, Usuario
from apps.core.views.parametros import parametros_sistema


class ParametrosSistemaAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa = Empresa.objects.create(
            razao_social='Empresa Parametros LTDA',
            nome_fantasia='Empresa Parametros',
            cnpj='72345678000191',
            regime_tributario=Empresa.RegimeTributario.SIMPLES_NACIONAL,
            codigo_regime_tributario=1,
        )
        cls.filial = Filial.objects.create(
            empresa=cls.empresa,
            razao_social='Filial Parametros',
            nome_fantasia='Filial Parametros',
            cnpj='72345678000192',
            uf='RN',
        )
        cls.perfil_admin = PerfilAcesso.objects.create(
            empresa=cls.empresa,
            nome='Administrador',
            is_admin=True,
        )
        cls.perfil_operador = PerfilAcesso.objects.create(
            empresa=cls.empresa,
            nome='Operador',
            is_admin=False,
        )
        cls.admin = Usuario.objects.create_user(
            email='admin-parametros@inoovated.com',
            nome='Admin Parametros',
            password='teste1234',
            empresa=cls.empresa,
            filial=cls.filial,
            perfil=cls.perfil_admin,
        )
        cls.operador = Usuario.objects.create_user(
            email='operador-parametros@inoovated.com',
            nome='Operador Parametros',
            password='teste1234',
            empresa=cls.empresa,
            filial=cls.filial,
            perfil=cls.perfil_operador,
        )

    def test_admin_acessa_parametros(self):
        request = RequestFactory().get('/gestao/parametros/')
        request.user = self.admin
        request.user._perfil_ativo = self.perfil_admin
        request.filial_ativa = self.filial

        with patch('apps.core.views.parametros.render', return_value=HttpResponse('ok')) as render_mock:
            response = parametros_sistema(request)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(render_mock.called)

    def test_operador_nao_acessa_parametros(self):
        request = RequestFactory().get('/gestao/parametros/')
        request.user = self.operador
        request.user._perfil_ativo = self.perfil_operador
        request.filial_ativa = self.filial

        with self.assertRaises(PermissionDenied):
            parametros_sistema(request)
