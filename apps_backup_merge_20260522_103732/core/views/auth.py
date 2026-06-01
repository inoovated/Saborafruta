"""Views de autenticação: login, logout, seleção e troca de filial."""
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.decorators.http import require_POST

from apps.core.forms import LoginForm
from apps.core.models import Empresa, Filial
from apps.core.services.auth_service import AuthService
from apps.core.services.exceptions import DomainError


class LoginView(View):
    template_name = 'core/auth/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('core:dashboard')
        return render(request, self.template_name, {'form': LoginForm()})

    def post(self, request):
        form = LoginForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        try:
            user = AuthService.login(
                request,
                email=form.cleaned_data['email'],
                senha=form.cleaned_data['senha'],
            )
        except DomainError as e:
            messages.error(request, str(e))
            return render(request, self.template_name, {'form': form})

        login(request, user)
        filiais = _filiais_permitidas(user)
        if user.is_superuser:
            request.session.pop('filial_ativa_id', None)
            return redirect('core:selecionar-filial')
        if filiais.count() == 1:
            request.session['filial_ativa_id'] = filiais.first().pk
            return redirect('core:dashboard')
        return redirect('core:selecionar-filial')


def _filiais_permitidas(user):
    qs = Filial.objects.filter(ativo=True)
    if user.is_superuser:
        return qs.order_by('nome_fantasia', 'razao_social')
    qs = qs.filter(empresa=user.empresa)
    perfil = getattr(user, 'perfil', None)
    if perfil and perfil.is_admin:
        return qs.order_by('nome_fantasia', 'razao_social')
    acessos_ids = list(user.acessos_filiais.filter(ativo=True).values_list('filial_id', flat=True))
    if acessos_ids:
        return qs.filter(pk__in=acessos_ids).order_by('nome_fantasia', 'razao_social')
    if user.filial_id:
        return qs.filter(pk=user.filial_id).order_by('nome_fantasia', 'razao_social')
    return qs.none()


@login_required
def logout_view(request):
    AuthService.logout_registro(request)
    logout(request)
    messages.info(request, 'Sessão encerrada.')
    return redirect('core:login')


@login_required
@require_POST
def atualizar_minha_foto(request):
    user = request.user
    foto = request.FILES.get('foto')
    remover = request.POST.get('remover_foto') == '1'
    voltar_para = request.META.get('HTTP_REFERER') or reverse_lazy('core:dashboard')

    if remover:
        if user.foto:
            user.foto.delete(save=False)
            user.foto = None
            user.save(update_fields=['foto', 'updated_at'])
            messages.success(request, 'Foto removida.')
        return redirect(voltar_para)

    if not foto:
        messages.error(request, 'Selecione uma imagem para atualizar sua foto.')
        return redirect(voltar_para)

    if foto.size > 5 * 1024 * 1024:
        messages.error(request, 'Envie uma imagem com ate 5 MB.')
        return redirect(voltar_para)

    if foto.content_type and not foto.content_type.startswith('image/'):
        messages.error(request, 'O arquivo selecionado precisa ser uma imagem.')
        return redirect(voltar_para)

    foto_antiga = user.foto.name if user.foto else ''
    user.foto = foto
    user.save(update_fields=['foto', 'updated_at'])

    if foto_antiga and foto_antiga != user.foto.name:
        user.foto.storage.delete(foto_antiga)

    messages.success(request, 'Foto atualizada.')
    return redirect(voltar_para)


class SelecionarFilialView(View):
    """Tela de seleção de filial após login quando usuário tem múltiplas filiais."""

    template_name = 'core/auth/selecionar_filial.html'

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('core:login')

        filiais = _filiais_permitidas(request.user)

        if not request.user.is_superuser and filiais.count() == 1:
            request.session['filial_ativa_id'] = filiais.first().pk
            return redirect('core:dashboard')

        empresas = []
        if request.user.is_superuser:
            empresas = Empresa.objects.filter(
                filiais__in=filiais,
                ativo=True,
            ).distinct().order_by('nome_fantasia', 'razao_social')

        return render(request, self.template_name, {
            'filiais': filiais.select_related('empresa'),
            'empresas': empresas,
            'is_global_selection': request.user.is_superuser,
        })


class TrocarFilialView(View):
    """Troca de filial na sessão sem reload completo (chamado via AJAX ou GET)."""

    def get(self, request, filial_id):
        if not request.user.is_authenticated:
            return redirect('core:login')
        try:
            filial = AuthService.trocar_filial(request, filial_id)
            messages.success(request, f'Filial alterada para {filial}.')
        except DomainError as e:
            messages.error(request, str(e))
        referer = request.META.get('HTTP_REFERER', '')
        if 'selecionar-filial' in referer:
            return redirect('core:dashboard')
        return redirect(referer or reverse_lazy('core:dashboard'))
