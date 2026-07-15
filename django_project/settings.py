import os
import sys

# firebase_config.py
# import firebase_admin
# from firebase_admin import credentials, auth

from decouple import config, Csv
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

ENVIRONMENT = config('ENVIRONMENT', default='production')
DEBUG = config('DEBUG', default=False, cast=bool)

# Base Directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Seguridad
_SECRET_KEY_RAW = config('SECRET_KEY', default='')
SECRET_KEY = _SECRET_KEY_RAW or 'insecure-placeholder'
if ENVIRONMENT.strip().lower() in ('production', 'produccion') and not str(_SECRET_KEY_RAW).strip():
    raise ImproperlyConfigured(
        'SECRET_KEY es obligatorio cuando ENVIRONMENT es production o produccion.'
    )
ALLOWED_HOSTS = list(config('ALLOWED_HOSTS', default='127.0.0.1,localhost,testserver,synap.administranet.com.ar', cast=Csv()))
# host.docker.internal: útil para clientes en Docker que llaman a Synap en el host (integraciones locales).
if 'host.docker.internal' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('host.docker.internal')

# Clickjacking: el valor por defecto de Django es DENY y bloquea cualquier iframe, incluso same-origin.
# SAMEORIGIN sigue impidiendo que sitios externos embeban Synap, pero permite el visor PDF en
# /compras/captura/revision/<uuid>/documento/<id>/ dentro de la propia app.
X_FRAME_OPTIONS = 'SAMEORIGIN'

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
    'logistica',  # Logística (operación entregas; dominio MySQL compartido con Reports)
    'reports',
    'ia',  # Módulo transversal de asistentes IA persistentes
    'self_checkout',  # Self-checkout / TPV (comandos manage.py y vistas)
    'fe_afip',  # Facturación electrónica AFIP/ARCA (config, certificados, CAEA)
    'stock',  # Stock AdministraNET (movimientos, referencias, consultas)
    'ventas',  # Objetivos de venta (MySQL legacy) e informes asociados
    'compras',  # Remitos de compra (PRemito.frm - AdministraNET)
    'factura_compra_posting',  # Contrato + stub posting factura compra (sin MySQL en Fase 1)
    'factura_compra_captura',  # Expediente captura/workflow factura compra (PostgreSQL)
    'legacy_db',  # Capa escritura compatible VB6 (tablas MySQL administraNET)
    'mpr',  # MPR - Manufacturing / Producción (plan ANALISIS_MPR_PROPUESTA_MVP)
    'odoo_migracion',  # Migración/sincronización AdministraNET → Odoo 19
    'ecom',  # Migración administraNET-ecom (mayorista B2B / relays PHP)
    'tiendanube_administranet',  # Integración Tienda Nube ↔ AdministraNET (MySQL vía pool Synap)
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
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    # Mensajes antes de RequestScopedMysql: si hay que cerrar sesión por MySQL inválido, messages.error funciona.
    'django.contrib.messages.middleware.MessageMiddleware',
    'core.middleware.request_scoped_mysql.RequestScopedMysqlMiddleware',  # Una conexión MySQL por request
    'django.middleware.locale.LocaleMiddleware',  # Middleware para i18n
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.middleware.RequestUserMiddleware',
    'core.middleware.AdminAccessMiddleware',
    'core.middleware.DeviceDetectionMiddleware',  # Detección de dispositivos
    'core.middleware.mobile_level_a_middleware.MobileLevelAOnlyMiddleware',  # Móvil: solo Nivel A (login, perfil, TPV, PWA)
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

# MySQL: en producción DB_PASSWORD es obligatorio (sin default en código).
_DB_PASSWORD = config('DB_PASSWORD', default='')
if ENVIRONMENT.strip().lower() in ('production', 'produccion') and not str(_DB_PASSWORD).strip():
    raise ImproperlyConfigured(
        'DB_PASSWORD es obligatorio cuando ENVIRONMENT es production o produccion.'
    )

_POSTGRES_PASSWORD = config('POSTGRES_PASSWORD', default='')
if ENVIRONMENT.strip().lower() in ('production', 'produccion') and not str(_POSTGRES_PASSWORD).strip():
    raise ImproperlyConfigured(
        'POSTGRES_PASSWORD es obligatorio cuando ENVIRONMENT es production o produccion.'
    )

# Base de datos
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('POSTGRES_DB', default='mydatabase'),
        'USER': config('POSTGRES_USER', default='myuser'),
        'PASSWORD': _POSTGRES_PASSWORD.strip() if str(_POSTGRES_PASSWORD).strip() else 'mypassword',
        'HOST': config('POSTGRES_HOST', default='db'),
        'PORT': config('POSTGRES_PORT', default='5432'),
    },
    'mysql': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME', default='administranet'),
        'USER': config('DB_USER', default='administranet'),
        'PASSWORD': _DB_PASSWORD,
        'HOST': config('DB_HOST', default='mysql'),
        'PORT': config('DB_PORT', default='3306'),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'latin1',
        },
    }
}

# makemigrations/migrate comprueban el historial en todas las conexiones; un MySQL 5.7 remoto
# (AdministraNET) hace fallar init_connection_state en Django 4.2+. Las migraciones Synap
# viven solo en PostgreSQL. SYNAP_MIGRATIONS_POSTGRES_ONLY=1 solo durante esos comandos
# (no en runserver/gunicorn aunque la variable siga en el entorno del contenedor).
_MIGRATION_CMDS_POSTGRES_ONLY = frozenset(
    ('migrate', 'makemigrations', 'sqlmigrate', 'showmigrations', 'squashmigrations')
)


def _synap_migrations_postgres_only_active() -> bool:
    if os.environ.get('SYNAP_MIGRATIONS_POSTGRES_ONLY') != '1':
        return False
    if len(sys.argv) < 2:
        return False
    return sys.argv[1] in _MIGRATION_CMDS_POSTGRES_ONLY


if _synap_migrations_postgres_only_active():
    DATABASES = {'default': DATABASES['default']}

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

# -----------------------------------------------------------------------------
# AFIP / ARCA: certificados y claves privadas
# -----------------------------------------------------------------------------
# En Docker, montar un volumen (no bind de la carpeta del repo) en SYNAP_AFIP_STORAGE
# para evitar errores EDEADLK al leer certificados desde pyafipws (macOS + bind mount).
# Estructura: <SYNAP_AFIP_STORAGE>/pending/*.key, <SYNAP_AFIP_STORAGE>/certs/<base>/certificado.crt|clave.key
_SYNAP_AFIP_STORAGE = config('SYNAP_AFIP_STORAGE', default='').strip()
if _SYNAP_AFIP_STORAGE:
    _afip_root = Path(_SYNAP_AFIP_STORAGE).resolve()
else:
    _afip_root = (BASE_DIR / 'private' / 'afip').resolve()
FE_AFIP_CERT_STORAGE_DIR = str(_afip_root / 'certs')
FE_AFIP_PENDING_DIR = str(_afip_root / 'pending')
# Explorador de rutas en la UI FE-AFIP (debe incluir el volumen de secretos).
FE_AFIP_BROWSE_ROOTS = ['/', '/tmp', '/var', '/home', str(_afip_root)]

# Tailwind CSS
TAILWIND_APP_NAME = 'theme'
INTERNAL_IPS = ['127.0.0.1']

# Google OAuth
GOOGLE_CLIENT_ID = config('GOOGLE_CLIENT_ID', default='')
GOOGLE_CLIENT_SECRET = config('GOOGLE_CLIENT_SECRET', default='')

# Geocodificación (CargaSucursal / APIs core); no se acepta clave desde el cliente
GOOGLE_GEOCODING_API_KEY = config('GOOGLE_GEOCODING_API_KEY', default='')

# AES para validación de password_usuario en MySQL (paridad AdministraNET Gestión); preferir variable en prod
ADMINISTRANET_MYSQL_AES_KEY = config('ADMINISTRANET_MYSQL_AES_KEY', default='a7v8xx2')

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
    'DEFAULT_THROTTLE_RATES': {
        'compras_document_upload': '120/min',
    },
}

CSRF_COOKIE_HTTPONLY = False

CSRF_TRUSTED_ORIGINS = [
    "https://synap.administranet.com.ar",
]
_extra_csrf = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())
for origin in _extra_csrf:
    origin = origin.strip().rstrip('/')
    if origin and origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(origin)
_site_url = config('SITE_URL', default='').strip().rstrip('/')
if _site_url.startswith('https://') and _site_url not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append(_site_url)

if ENVIRONMENT.strip().lower() in ('production', 'produccion'):
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# CSRF_COOKIE_HTTPONLY=False permite leer csrftoken desde JS (login SPA). Mitigar XSS en el resto de la UI.
SESSION_COOKIE_HTTPONLY = True
SECURE_CONTENT_TYPE_NOSNIFF = True

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

# Factura compra — captura / posting (Fase 1: fake | noop; legacy en fases posteriores)
FACTURA_COMPRA_POSTING_BACKEND = config(
    'FACTURA_COMPRA_POSTING_BACKEND', default='fake'
)
# Fase 4–5: SQL real contra MySQL legacy solo si True (test gate + runbook).
FACTURA_COMPRA_LEGACY_SQL_ENABLED = config(
    'FACTURA_COMPRA_LEGACY_SQL_ENABLED', default=False, cast=bool
)
# Mapeo opcional empresa Synap (pk) → nombre base MySQL AdministraNET (validación fiscal CAE).
FACTURA_COMPRA_BASE_EMPRESA_BY_EMPRESA_ID: dict = {}

# Fase 2 — documentos / OCR (heuristic + Tesseract en imagen; http opcional)
FACTURA_COMPRA_DOCUMENTO_MAX_BYTES = config(
    'FACTURA_COMPRA_DOCUMENTO_MAX_BYTES',
    default=15 * 1024 * 1024,
    cast=int,
)
FACTURA_COMPRA_DOCUMENTO_MIME_PERMITIDOS = (
    'image/jpeg',
    'image/png',
    'application/pdf',
)
FACTURA_COMPRA_OCR_ADAPTER = config(
    'FACTURA_COMPRA_OCR_ADAPTER', default='heuristic'
)
# False = ejecutar OCR en el mismo proceso tras guardar (recomendado en tests; válido en dev).
# True = encolar tras transaction.on_commit en hilo (producción; no bloquea la respuesta HTTP).
FACTURA_COMPRA_OCR_DEFER = config(
    'FACTURA_COMPRA_OCR_DEFER', default=False, cast=bool
)
FACTURA_COMPRA_OCR_SYNC = config(
    'FACTURA_COMPRA_OCR_SYNC', default=False, cast=bool
)
FACTURA_COMPRA_OCR_HTTP_URL = config('FACTURA_COMPRA_OCR_HTTP_URL', default='')
FACTURA_COMPRA_OCR_HTTP_BEARER_TOKEN = config(
    'FACTURA_COMPRA_OCR_HTTP_BEARER_TOKEN', default=''
)
FACTURA_COMPRA_OCR_HTTP_TIMEOUT = config(
    'FACTURA_COMPRA_OCR_HTTP_TIMEOUT', default=30, cast=int
)
FACTURA_COMPRA_OCR_HTTP_VERIFY_SSL = config(
    'FACTURA_COMPRA_OCR_HTTP_VERIFY_SSL', default=True, cast=bool
)
# Tesseract: OCR en servidor para fotos (JPEG/PNG) desde PWA / cámara móvil
FACTURA_COMPRA_OCR_TESSERACT_ENABLED = config(
    'FACTURA_COMPRA_OCR_TESSERACT_ENABLED', default=True, cast=bool
)
FACTURA_COMPRA_OCR_TESSERACT_LANG = config(
    'FACTURA_COMPRA_OCR_TESSERACT_LANG', default='spa+eng'
)
FACTURA_COMPRA_OCR_TESSERACT_CMD = config(
    'FACTURA_COMPRA_OCR_TESSERACT_CMD', default=''
)
# Stage 1 motor documento: legacy | preprocess_only | structured_ocr (solo imágenes)
FACTURA_COMPRA_OCR_ENGINE_MODE = config(
    'FACTURA_COMPRA_OCR_ENGINE_MODE', default='legacy'
)

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
        'level': 'DEBUG' if DEBUG else 'INFO',
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

# Kill switch de emergencia (ops/deploy). Control operativo: UI TiendanubeConfig / WebhookConfig.
TIENDANUBE_SYNC_ENABLED = config('TIENDANUBE_SYNC_ENABLED', default=True, cast=bool)
TIENDANUBE_WEBHOOKS_ENABLED = config('TIENDANUBE_WEBHOOKS_ENABLED', default=True, cast=bool)

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

# (Retirado) Sync legacy Synap → permiso_sistema. Mantener False; usar synap_* + apply/backfill.
SYNAP_AUTO_SYNC_PERMISSIONS = config('SYNAP_AUTO_SYNC_PERMISSIONS', default=False, cast=bool)
# TTL en segundos para no repetir sync por empresa (default 24h)
SYNAP_AUTO_SYNC_PERMISSIONS_TTL = config('SYNAP_AUTO_SYNC_PERMISSIONS_TTL', default=86400, cast=int)

# Fuente de verdad para el cálculo de permisos Synap en runtime:
#   'legacy' → permiso_sistema + permiso_sistema_puesto (comportamiento actual, default)
# Fuente de permisos runtime (menú / get_permisos_totales):
#   'synap'  → solo tablas synap_* (cutover; sin fallback a permiso_sistema*)
#   'dual'   → unión de ambas; WARNING si difieren (validación de paridad)
#   'legacy' → permiso_sistema + permiso_sistema_puesto (rollback)
# permiso_sistema* no se usa para armar el menú en modo synap.
# Ver docs/general/PERMISOS_SYNAP_STORE.md
SYNAP_PERMISOS_SOURCE = config('SYNAP_PERMISOS_SOURCE', default='legacy')

# Los puestos (puestos.idpuesto) son el ancla fija de AdministraNET: Synap no debe
# crearlos (evita MAX(idpuesto)+1). Los puestos se crean en AdministraNET; en Synap
# se gestionan roles/permisos sobre esos puestos. Poner en False solo si se requiere
# temporalmente permitir la creación de puestos desde Synap.
SYNAP_BLOQUEAR_CREAR_PUESTOS = config('SYNAP_BLOQUEAR_CREAR_PUESTOS', default=True, cast=bool)

# Asegurar (crear si faltan) las tablas synap_* + catálogo tras login / al abrir la UI.
# Independiente de SYNAP_AUTO_SYNC_PERMISSIONS (sync legacy en desuso). No escribe en VB6.
SYNAP_AUTO_ENSURE_SCHEMA = config('SYNAP_AUTO_ENSURE_SCHEMA', default=True, cast=bool)
SYNAP_AUTO_ENSURE_SCHEMA_TTL = config('SYNAP_AUTO_ENSURE_SCHEMA_TTL', default=86400, cast=int)

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

# Export lista de precios PDF (ecom mayorista, Fase P3) — umbrales/guardrails.
# Defaults = paridad legacy exporta_lista_pdf.php (ver docs/general/RUNBOOK_EXPORTACION_PDF.md).
# Re-medir LP_PDF_MAX_SECONDS* en el entorno objetivo (reportlab != mPDF).
LP_PDF_MAX_ITEMS = config('LP_PDF_MAX_ITEMS', default=2500, cast=int)
LP_PDF_MAX_ITEMS_CON_IMAGEN = config('LP_PDF_MAX_ITEMS_CON_IMAGEN', default=1800, cast=int)
LP_PDF_MAX_SECONDS = config('LP_PDF_MAX_SECONDS', default=90, cast=int)
LP_PDF_MAX_SECONDS_CON_IMAGEN = config('LP_PDF_MAX_SECONDS_CON_IMAGEN', default=180, cast=int)

# Celery Configuration - ELIMINADO (No necesario para Reportes básico)
# CELERY_BROKER_URL = "redis://localhost:6379/0"
# CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
# CELERY_ACCEPT_CONTENT = ["json"]
# CELERY_TASK_SERIALIZER = "json"
# CELERY_RESULT_SERIALIZER = "json"
# CELERY_TIMEZONE = "UTC"
