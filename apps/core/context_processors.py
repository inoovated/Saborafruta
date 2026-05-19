"""Context processors: disponibilizam dados em todos os templates."""
from apps.core.models import Filial

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
