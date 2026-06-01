"""Service de autenticação e troca de filial."""
from __future__ import annotations

from django.contrib.auth import authenticate
from django.utils import timezone

from apps.core.middleware.audit import get_client_ip
from apps.core.models import Filial, LogAcesso, Usuario
from apps.core.services.exceptions import DadosInvalidosError, PermissaoNegadaError


class AuthService:
    """Encapsula regras de autenticação, bloqueio e troca de filial."""

    MAX_TENTATIVAS = 5
    BLOQUEIO_MINUTOS = 15

    @classmethod
    def login(cls, request, email: str, senha: str) -> Usuario:
        """
        Autentica usuário. Registra tentativas falhas e bloqueia após N erros.
        Levanta DadosInvalidosError se credenciais inválidas.
        """
        user = authenticate(request, username=email, password=senha)

        if user is None:
            cls._registrar_falha(request, email)
            raise DadosInvalidosError('E-mail ou senha incorretos.')

        if not user.ativo:
            raise DadosInvalidosError('Usuário desativado. Contate o administrador.')

        if user.bloqueado_ate and user.bloqueado_ate > timezone.now():
            minutos = int((user.bloqueado_ate - timezone.now()).total_seconds() / 60)
            raise DadosInvalidosError(
                f'Usuário bloqueado por tentativas inválidas. '
                f'Tente novamente em {minutos} minuto(s).'
            )

        # Login bem-sucedido — reseta bloqueios
        Usuario.objects.filter(pk=user.pk).update(
            tentativas_login_falhas=0,
            bloqueado_ate=None,
            ultimo_acesso=timezone.now(),
            ip_ultimo_acesso=get_client_ip(request),
        )

        LogAcesso.objects.create(
            usuario=user,
            filial=user.filial,
            tipo=LogAcesso.Tipo.LOGIN,
            ip_acesso=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            sucesso=True,
        )

        return user

    @classmethod
    def _registrar_falha(cls, request, email: str):
        try:
            user = Usuario.objects.get(email=email)
        except Usuario.DoesNotExist:
            return

        tentativas = user.tentativas_login_falhas + 1
        bloqueado_ate = None

        if tentativas >= cls.MAX_TENTATIVAS:
            bloqueado_ate = timezone.now() + timezone.timedelta(minutes=cls.BLOQUEIO_MINUTOS)
            tentativas = 0

        Usuario.objects.filter(pk=user.pk).update(
            tentativas_login_falhas=tentativas,
            bloqueado_ate=bloqueado_ate,
        )

        LogAcesso.objects.create(
            usuario=user,
            filial=user.filial,
            tipo=LogAcesso.Tipo.BLOQUEIO if bloqueado_ate else LogAcesso.Tipo.SENHA_ERRADA,
            ip_acesso=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            sucesso=False,
        )

    @staticmethod
    def trocar_filial(request, filial_id: int) -> Filial:
        """Troca a filial ativa na sessão. Valida se o usuário pode acessar."""
        try:
            filial = Filial.objects.get(pk=filial_id, ativo=True)
        except Filial.DoesNotExist:
            raise DadosInvalidosError('Filial não encontrada.')

        if not request.user.pode_acessar_filial(filial):
            raise PermissaoNegadaError('Você não tem acesso a essa filial.')

        request.session['filial_ativa_id'] = filial.pk
        return filial

    @staticmethod
    def logout_registro(request):
        """Registra logout no log de acesso."""
        if request.user.is_authenticated:
            LogAcesso.objects.create(
                usuario=request.user,
                filial=getattr(request, 'filial_ativa', None),
                tipo=LogAcesso.Tipo.LOGOUT,
                ip_acesso=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                sucesso=True,
            )
