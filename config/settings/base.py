"""
Configurações base do projeto ERP iNoovaTed.
"""
from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(DEBUG=(bool, False))
env_file = BASE_DIR / '.env'
if env_file.exists():
    environ.Env.read_env(str(env_file))

SECRET_KEY = env('SECRET_KEY', default='change-me')
DEBUG = env('DEBUG', default=False)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

# Apps
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'widget_tweaks',
    'django_celery_beat',
    'django_celery_results',
]

LOCAL_APPS = [
    'apps.core',
    'apps.cadastros',
    'apps.produtos',
    'apps.estoque',
    'apps.producao',
    'apps.vendas',
    'apps.compras',
    # Novos módulos (mai/2026)
    'apps.financeiro',
    'apps.fiscal',
    'apps.pdv',
    'apps.qualidade',
    'apps.analytics',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Middlewares customizados
    'apps.core.middleware.filial.FilialMiddleware',
    'apps.core.middleware.audit.AuditMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.core.context_processors.filial_context',
                'apps.core.context_processors.parametros_sistema',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': env.db("DATABASE_URL"),
}

# Auth
AUTH_USER_MODEL = 'core.Usuario'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/auth/login/'

# i18n
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# Static / Media
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = env('MEDIA_URL', default='/media/')
MEDIA_ROOT = Path(env('MEDIA_ROOT', default=str(BASE_DIR / 'media')))

# PK padrão: INTEGER incremental (requisito do cliente)
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework + JWT
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# Cache — Django nativo (LocMem em dev)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'erp-inoovated-cache',
    }
}

# Celery
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='django-db')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Email
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@inoovated.com.br')

# Integrações externas
VIACEP_URL = env('VIACEP_URL', default='https://viacep.com.br/ws/{cep}/json/')

# Focus NFe — emissão de documentos fiscais (https://doc.focusnfe.com.br)
ERP_FOCUSNFE_TOKEN = env('FOCUSNFE_TOKEN', default='')
ERP_FOCUSNFE_AMBIENTE = env.int('FOCUSNFE_AMBIENTE', default=2)   # 1=producao, 2=homologacao
ERP_FOCUSNFE_WEBHOOK_TOKEN = env('FOCUSNFE_WEBHOOK_TOKEN', default='')

# Sessão
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 60 * 60 * 8  # 8 horas
