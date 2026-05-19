"""
Middleware de auditoria — armazena IP e user-agent na request para uso nos signals.
Os signals post_save/post_delete é que fazem o registro real em LogSistema.
"""
import threading

_local = threading.local()


def get_current_request():
    """Recupera a request do contexto atual (usado por signals)."""
    return getattr(_local, 'request', None)


class AuditMiddleware:
    """
    Armazena a request na thread local para que signals de audit possam acessar
    o usuário, IP e user-agent.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _local.request = request
        try:
            response = self.get_response(request)
        finally:
            if hasattr(_local, 'request'):
                del _local.request
        return response


def get_client_ip(request):
    """Extrai o IP real considerando proxies reversos."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')
