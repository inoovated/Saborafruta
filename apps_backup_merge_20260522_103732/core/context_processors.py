"""Context processors: disponibilizam dados em todos os templates."""
from apps.core.models import Filial


def parametros_sistema(request):
    """Injeta os parâmetros do sistema (logo) em todos os templates.

    Logado: usa a logo da filial ativa. Sem filial (ex.: tela de login):
    usa a primeira logo cadastrada como fallback.
    """
    from apps.core.models.parametros import ParametrosSistema
    params = None
    try:
        filial = getattr(request, 'filial_ativa', None)
        if filial is not None:
            params = ParametrosSistema.objects.filter(filial=filial).first()
        if params is None or not params.logo:
            fallback = (
                ParametrosSistema.objects
                .exclude(logo='').exclude(logo__isnull=True)
                .first()
            )
            if fallback is not None:
                params = fallback
    except Exception:
        params = None
    return {'parametros_sistema': params}


def filial_context(request):
    """Injeta filial ativa e filiais disponíveis em todos os templates."""
    ctx = {
        'filial_ativa': getattr(request, 'filial_ativa', None),
        'filiais_disponiveis': [],
    }
    if not request.user.is_authenticated:
        return ctx
    try:
        user = request.user
        qs = Filial.objects.filter(ativo=True)
        perfil = getattr(user, 'perfil', None)
        is_admin = user.is_superuser or (perfil is not None and perfil.is_admin)
        if user.is_superuser and ctx['filial_ativa']:
            qs = qs.filter(empresa_id=ctx['filial_ativa'].empresa_id)
        elif not user.is_superuser:
            qs = qs.filter(empresa=user.empresa)
        if not is_admin:
            acessos_ids = list(user.acessos_filiais.filter(ativo=True).values_list('filial_id', flat=True))
            if acessos_ids:
                qs = qs.filter(pk__in=acessos_ids)
            elif user.filial_id:
                qs = qs.filter(pk=user.filial_id)
        ctx['filiais_disponiveis'] = list(qs.order_by('nome_fantasia', 'razao_social'))
    except Exception:
        pass
    return ctx
