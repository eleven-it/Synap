import os

# firebase_config.py
# import firebase_admin
# from firebase_admin import credentials, auth

from decouple import config, Csv
from pathlib import Path

DEBUG = config('DEBUG', default=False, cast=bool)
ENVIRONMENT = config('ENVIRONMENT', default='production')

# Base Directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Seguridad
SECRET_KEY = config('SECRET_KEY', default='insecure-placeholder')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = list(config('ALLOWED_HOSTS', default='127.0.0.1,localhost,testserver,synap.administranet.com.ar', cast=Csv()))
# Permitir peticiones desde Support en Docker (host.docker.internal) para RAG /core/api/support/conocimiento/
if 'host.docker.internal' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('host.docker.internal')

# Aplicaciones instaladas
INSTALLED_APPS = [

    # Terceros
    'theme',
    'tailwind',
    'rest_framework',
    'widget_tweaks',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'corsheaders',
    'crispy_forms',
    'crispy_tailwind',

    # Apps propias - Instalación mínima para Reportes
    'core',
    'login',
    'dashboard',
    'reports',
    'self_checkout',  # Self-checkout / TPV (comandos manage.py y vistas)
    'stock',  # Stock AdministraNET (movimientos, referencias, consultas)
    'compras',  # Remitos de compra (PRemito.frm - AdministraNET)
    'legacy_db',  # Capa escritura compatible VB6 (tablas MySQL administraNET)
    'mpr',  # MPR - Manufacturing / Producción (plan ANALISIS_MPR_PROPUESTA_MVP)
    # Módulos eliminados para instalación mínima de Reportes
    # 'reports_ai',  # No necesario
    # 'administraNET_integration',  # No necesario
    # 'sales',
    # 'inventory',
    # 'tiendanube',
    # 'tiendanube_administranet',
    # 'django_celery_beat',
    # 'celery',
    # 'accounting',
    # 'purchases',
    # 'mercadopago',
    # 'clover',
    # 'logistics',
    # 'finance',
    # "support_ai",
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',  # Middleware para i18n
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',  # Movido antes de los middlewares personalizados
    'core.middleware.RequestUserMiddleware',
    'core.middleware.AdminAccessMiddleware',
    'core.middleware.DeviceDetectionMiddleware',  # Detección de dispositivos
    'core.middleware.module_middleware.ModuleMiddleware',  # Gestión de módulos
    'core.middleware.module_middleware.ModulePermissionMiddleware',  # Permisos de módulos
    'core.middleware.module_middleware.ModuleContextMiddleware',  # Contexto de módulos
    'core.middleware.module_middleware.ModuleCacheMiddleware',  # Cache de módulos
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_project.settings.custom_ajax_login_required',
    # 'core.middleware.CDNCacheMiddleware',  # Comentado temporalmente
]

# Middleware para AJAX login

def custom_ajax_login_required(get_response):
    def middleware(request):
        response = get_response(request)
        if response.status_code == 302 and request.headers.get('x-requested-with') == 'XMLHttpRequest':
            from django.http import JsonResponse
            return JsonResponse({'success': False, 'error': 'No autenticado'}, status=401)
        return response
    return middleware

HANDLER403 = "core.views.error_403_view"

# URLs y WSGI
ROOT_URLCONF = 'django_project.urls'
WSGI_APPLICATION = 'django_project.wsgi.application'

# Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',
            BASE_DIR / 'theme' / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.usuario_y_permisos',
                'core.context_processors.menu_context',
                # Context processors deshabilitados para administraNET Analytics
                # 'core.context_processors.inventory_menu_context',
                # 'core.context_processors.tiendanube_menu_context',
                # 'core.context_processors.purchases_menu_context',
                # 'administraNET_integration.context_processors.administraNET_integration_menu',
            ],
        },
    },
]

# Base de datos
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('POSTGRES_DB', default='mydatabase'),
        'USER': config('POSTGRES_USER', default='myuser'),
        'PASSWORD': config('POSTGRES_PASSWORD', default='mypassword'),
        'HOST': config('POSTGRES_HOST', default='db'),
        'PORT': config('POSTGRES_PORT', default='5432'),
    },
    'mysql': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME', default='administranet'),
        'USER': config('DB_USER', default='administranet'),
        'PASSWORD': config('DB_PASSWORD', default='a7v8xx0805'),
        'HOST': config('DB_HOST', default='mysql'),
        'PORT': config('DB_PORT', default='3306'),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'latin1',
        },
    }
}

# Base MySQL por defecto para reportes (BO, ventas, etc.) cuando no viene en sesión/filtros
DEFAULT_BASE_EMPRESA = config('DB_NAME', default='administranet')

# Router: legacy_db usa siempre la conexión MySQL (administraNET)
DATABASE_ROUTERS = ['legacy_db.db_router.LegacyDbRouter']

# Configuración regional
LANGUAGE_CODE = 'es-ar'
TIME_ZONE = 'America/Argentina/Buenos_Aires'
USE_I18N = True  # Habilitado para soporte de traducciones i18n
USE_L10N = True
USE_TZ = True

# Archivos estáticos
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / "theme" / "static",
    BASE_DIR / "theme" / "static_src",
]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Archivos de Medios (subidos por usuarios)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Tailwind CSS
TAILWIND_APP_NAME = 'theme'
INTERNAL_IPS = ['127.0.0.1']

# Google OAuth
GOOGLE_CLIENT_ID = config('GOOGLE_CLIENT_ID', default='')
GOOGLE_CLIENT_SECRET = config('GOOGLE_CLIENT_SECRET', default='')

# Configuración adicional para desarrollo
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
)


LOGIN_REDIRECT_URL = '/core/dashboard/'
LOGIN_URL = '/login/'

# administraNET Analytics - Configuración de autenticación
# Se usa autenticación directa contra MySQL de administraNET Gestión
# Las credenciales se configuran en la conexión 'mysql' de DATABASES

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}

CSRF_COOKIE_HTTPONLY = False

CSRF_TRUSTED_ORIGINS = [
    "https://synap.administranet.com.ar"
]

# Configuración HTTPS
SECURE_SSL_REDIRECT = not DEBUG
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_REDIRECT_EXEMPT = [r'^static/', r'^media/']
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Configuración de mensajes
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'
AUTH_USER_MODEL = 'core.UsuarioExtendido'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
}

# ─────────────────────────────────────────────
# CONFIGURACIONES ELIMINADAS (No necesarias para Reportes)
# ─────────────────────────────────────────────

# Configuración de TiendaNube - ELIMINADA
# TIENDANUBE_ACCESS_TOKEN = config('TIENDANUBE_ACCESS_TOKEN', default='')
# TIENDANUBE_STORE_ID = config('TIENDANUBE_STORE_ID', default='')
# TIENDANUBE_WEBHOOK_SECRET = config('TIENDANUBE_WEBHOOK_SECRET', default='')
# TIENDANUBE_API_URL = config('TIENDANUBE_API_URL', default='https://api.tiendanube.com/v1')
# TIENDANUBE_AUTO_SYNC = config('TIENDANUBE_AUTO_SYNC', default=True, cast=bool)
# TIENDANUBE_SYNC_INTERVAL = config('TIENDANUBE_SYNC_INTERVAL', default=30, cast=int)

# API Keys para integraciones - ELIMINADA
# INGEST_API_KEY = config('INGEST_API_KEY', default='posdif9834usidf@iiu$@&ujsid')

# Configuración de n8n - ELIMINADA
# N8N_SQL_CHAT_WEBHOOK = config('N8N_SQL_CHAT_WEBHOOK', default='')

# Configuración para el chat SQL de IA - ELIMINADA
# FINANCE_MAX_ROWS = config('FINANCE_MAX_ROWS', default=200, cast=int)

# Configuración de caché para TiendaNube
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://redis:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'decode_responses': False,  # Importante para datos serializados
            }
        }
    }
}

# Sincronización automática de permisos Synap → permiso_sistema (AdministraNET) tras login
SYNAP_AUTO_SYNC_PERMISSIONS = config('SYNAP_AUTO_SYNC_PERMISSIONS', default=True, cast=bool)
# TTL en segundos para no repetir sync por empresa (default 24h)
SYNAP_AUTO_SYNC_PERMISSIONS_TTL = config('SYNAP_AUTO_SYNC_PERMISSIONS_TTL', default=86400, cast=int)

# Configuración de logging - Sin módulos específicos
LOGGING['loggers'] = {
    # Loggers específicos de módulos eliminados
}

# Celery settings - ELIMINADO (No necesario para Reportes básico)
# CELERY_BROKER_URL = 'redis://redis:6379/0'
# CELERY_RESULT_BACKEND = 'redis://redis:6379/0'
# CELERY_ACCEPT_CONTENT = ['json']
# CELERY_TASK_SERIALIZER = 'json'
# CELERY_RESULT_SERIALIZER = 'json'
# CELERY_TIMEZONE = TIME_ZONE

# Configuración de Celery Beat - ELIMINADO
# CELERY_BEAT_SCHEDULE = {}

# URL base pública del sitio (para imágenes, enlaces externos, etc.)
SITE_URL = config('SITE_URL', default='https://synap.administranet.com.ar')

CRISPY_ALLOWED_TEMPLATE_PACKS = "tailwind"
CRISPY_TEMPLATE_PACK = "tailwind"

# =============================================================================
# CDN CONFIGURATION
# =============================================================================

# Estáticos y media: STATIC_URL siempre relativa para que WhiteNoise sirva
# correctamente y no haya redirect loops con SECURE_SSL_REDIRECT.
# Cloudflare (CDN) cachea los estáticos por la URL relativa /static/*.
STATIC_URL = '/static/'
MEDIA_URL = '/media/'

# CDN Cache Headers
CDN_CACHE_HEADERS = {
    'static': {
        'Cache-Control': 'public, max-age=31536000, immutable',  # 1 year
    },
    'media': {
        'Cache-Control': 'public, max-age=86400',  # 1 day
    },
    'images': {
        'Cache-Control': 'public, max-age=604800',  # 1 week
    }
}


# Reports cache - desactivado para que los datos se refresquen inmediatamente
REPORTS_CACHE_ENABLED = config('REPORTS_CACHE_ENABLED', default=False, cast=bool)

# Celery Configuration - ELIMINADO (No necesario para Reportes básico)
# CELERY_BROKER_URL = "redis://localhost:6379/0"
# CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
# CELERY_ACCEPT_CONTENT = ["json"]
# CELERY_TASK_SERIALIZER = "json"
# CELERY_RESULT_SERIALIZER = "json"
# CELERY_TIMEZONE = "UTC"
