"""Helpers de permissao do modulo de estoque."""
from django.contrib import messages
from django.shortcuts import redirect


def permissoes_estoque(request):
    usuario = request.user
    return {
        'pode_ver': usuario.tem_permissao('estoque', 'ver'),
        'pode_criar': usuario.tem_permissao('estoque', 'criar'),
        'pode_editar': usuario.tem_permissao('estoque', 'editar'),
        'pode_cancelar': usuario.tem_permissao('estoque', 'cancelar'),
        'pode_exportar': usuario.tem_permissao('estoque', 'exportar'),
    }


def bloquear_exportacao_sem_permissao(request, fallback='estoque:estoque-list', **kwargs):
    if request.user.tem_permissao('estoque', 'exportar'):
        return None
    messages.error(request, 'Voce nao tem permissao para exportar dados de estoque.')
    return redirect(fallback, **kwargs)
