"""
Configurações de produção — Railway
"""
from .base import *  # noqa

DEBUG = False

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['.railway.app', '*'])

# Banco Railway interno — sem sslmode (rede interna não usa SSL)
DATABASES = {
    'default': {
        **env.db('DATABASE_URL'),
        'CONN_MAX_AGE': 0,
    }
}

# Whitenoise — serve arquivos estáticos direto pelo Django, sem precisar de nginx
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Uploads no Railway
# O volume persistente deve ser montado em /app/media. Se MEDIA_ROOT nao for
# informado no painel, este default evita salvar dentro da pasta do projeto.
MEDIA_ROOT = Path(env('MEDIA_ROOT', default='/app/media'))
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
MEDIA_URL = env('MEDIA_URL', default='/media/')
if not MEDIA_URL.endswith('/'):
    MEDIA_URL = f'{MEDIA_URL}/'

# Segurança básica para HTTPS
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
