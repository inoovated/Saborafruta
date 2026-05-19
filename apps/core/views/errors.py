from django.shortcuts import render


def permission_denied(request, exception=None):
    message = str(exception) if exception else 'Voce nao tem permissao para acessar esta tela.'
    if not message:
        message = 'Voce nao tem permissao para acessar esta tela.'
    return render(request, '403.html', {'permission_message': message}, status=403)
