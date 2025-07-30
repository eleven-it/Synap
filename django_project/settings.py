import os

# firebase_config.py
# import firebase_admin
# from firebase_admin import credentials, auth

from decouple import config, Csv
from pathlib import Path

DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
ENVIRONMENT = os.getenv('ENVIRONMENT', 'production')

# Base Directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Seguridad
SECRET_KEY = config('SECRET_KEY', default='insecure-placeholder')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1', cast=Csv())

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

    # Apps propias
    'core',
    'login',
    'dashboard',
    'sales',
    'inventory',
    'tiendanube',
    'tiendanube_administranet',
    'django_celery_beat',
    'celery',
    'accounting',
    'purchases',
    'reports',
    'mercadopago',
    'clover',
    'administraNET_integration',
    'logistics',
    'finance',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.middleware.RequestUserMiddleware',
    'core.middleware.AdminAccessMiddleware',
    'core.middleware.IdiomaUsuarioMiddleware',
    'core.middleware.DeviceDetectionMiddleware',  # Detección de dispositivos
    'core.middleware.module_middleware.ModuleMiddleware',  # Gestión de módulos
    'core.middleware.module_middleware.ModulePermissionMiddleware',  # Permisos de módulos
    'core.middleware.module_middleware.ModuleContextMiddleware',  # Contexto de módulos
    'core.middleware.module_middleware.ModuleCacheMiddleware',  # Cache de módulos
    'django.contrib.messages.middleware.MessageMiddleware',
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
                'core.context_processors.inventory_menu_context',
                'core.context_processors.tiendanube_menu_context',
                'core.context_processors.purchases_menu_context',
                'administraNET_integration.context_processors.administraNET_integration_menu',
            ],
        },
    },
]

# Base de datos
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'mydatabase'),
        'USER': os.getenv('POSTGRES_USER', 'myuser'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'mypassword'),
        'HOST': os.getenv('POSTGRES_HOST', 'db'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
    },
    'mysql': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'administranet',
        'USER': 'testuser',
        'PASSWORD': 'testpass',
        'HOST': 'mysql',
        'PORT': '3306',
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# Internacionalización
LANGUAGE_CODE = 'es-ar'
TIME_ZONE = 'America/Argentina/Buenos_Aires'
USE_I18N = True
USE_L10N = True
USE_TZ = True

LANGUAGES = [
    ('es', 'Español'),
    ('en', 'Inglés'),
    ('pt', 'Portugués'),
]
LOCALE_PATHS = [BASE_DIR / 'locale']

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

# Firebase
FIREBASE_CONFIG = {
    "apiKey": os.getenv("FIREBASE_API_KEY"),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
    "projectId": os.getenv("FIREBASE_PROJECT_ID"),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.getenv("FIREBASE_APP_ID"),
    "measurementId": os.getenv("FIREBASE_MEASUREMENT_ID"),
    "clientId": os.getenv("FIREBASE_CLIENT_ID"),  
}
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH")

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
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
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
# CONFIGURACIÓN TIENDANUBE
# ─────────────────────────────────────────────

# Configuración de TiendaNube
TIENDANUBE_ACCESS_TOKEN = config('TIENDANUBE_ACCESS_TOKEN', default='')
TIENDANUBE_STORE_ID = config('TIENDANUBE_STORE_ID', default='')
TIENDANUBE_WEBHOOK_SECRET = config('TIENDANUBE_WEBHOOK_SECRET', default='')
TIENDANUBE_API_URL = config('TIENDANUBE_API_URL', default='https://api.tiendanube.com/v1')
TIENDANUBE_AUTO_SYNC = config('TIENDANUBE_AUTO_SYNC', default=True, cast=bool)
TIENDANUBE_SYNC_INTERVAL = config('TIENDANUBE_SYNC_INTERVAL', default=30, cast=int)

# Configuración de caché para TiendaNube
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://redis:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Configuración de logging específica para TiendaNube
LOGGING['loggers'] = {
    'tiendanube': {
        'handlers': ['console'],
        'level': 'INFO',
        'propagate': False,
    },
}

# Celery settings
CELERY_BROKER_URL = 'redis://redis:6379/0'
CELERY_RESULT_BACKEND = 'redis://redis:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# URL base pública del sitio (para imágenes, enlaces externos, etc.)
SITE_URL = os.getenv('SITE_URL', 'https://tudominio.com')

CRISPY_ALLOWED_TEMPLATE_PACKS = "tailwind"
CRISPY_TEMPLATE_PACK = "tailwind"

# =============================================================================
# CDN CONFIGURATION
# =============================================================================

# CDN URL Configuration dinámica
if DEBUG or ENVIRONMENT == 'development':
    STATIC_URL = '/static/'
    MEDIA_URL = '/media/'
else:
    CLOUDFLARE_DOMAIN = os.getenv('CLOUDFLARE_DOMAIN', 'synap.administranet.com.ar')
    STATIC_URL = f'https://{CLOUDFLARE_DOMAIN}/static/'
    MEDIA_URL = f'https://{CLOUDFLARE_DOMAIN}/media/'

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

