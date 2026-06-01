from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def superuser_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied('Apenas superusuarios podem acessar esta area.')
        return view_func(request, *args, **kwargs)

    return _wrapped


def admin_area_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        perfil = getattr(request.user, '_perfil_ativo', None) or getattr(request.user, 'perfil', None)
        if not (request.user.is_superuser or getattr(perfil, 'is_admin', False)):
            raise PermissionDenied('Apenas administradores podem acessar esta area.')
        return view_func(request, *args, **kwargs)

    return _wrapped
