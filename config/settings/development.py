from .base import *  # noqa

DEBUG = True
ALLOWED_HOSTS = ['*']

# Debug toolbar
try:
    import debug_toolbar  # noqa
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE
    INTERNAL_IPS = ['127.0.0.1']
except ImportError:
    pass

# Em dev, usar SQLite se DATABASE_URL não definido
if 'sqlite' in DATABASES['default']['ENGINE']:
    DATABASES['default']['NAME'] = BASE_DIR / 'db.sqlite3'
