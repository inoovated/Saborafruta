"""Decorator e mixin para controle de permissao por modulo/acao."""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


PERMISSION_DENIED_MESSAGE = 'Você não tem permissão para esta ação.'


def requer_permissao(modulo: str, acao: str = 'ver'):
    """
    Decorator para views baseadas em funcao.

    Uso:
        @requer_permissao('produtos', 'criar')
        def produto_create(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if not request.user.tem_permissao(modulo, acao):
                messages.error(request, PERMISSION_DENIED_MESSAGE)
                return redirect('core:dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


class PermissaoRequiredMixin:
    """
    Mixin para views baseadas em classe.

    Uso:
        class ProdutoCreateView(PermissaoRequiredMixin, View):
            permissao_modulo = 'produtos'
            permissao_acao = 'criar'
    """
    permissao_modulo: str | None = None
    permissao_acao: str = 'ver'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('core:login')
        if self.permissao_modulo and not request.user.tem_permissao(
            self.permissao_modulo, self.permissao_acao,
        ):
            messages.error(request, PERMISSION_DENIED_MESSAGE)
            return redirect('core:dashboard')
        return super().dispatch(request, *args, **kwargs)
