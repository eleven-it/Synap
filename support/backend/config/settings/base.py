"""
Configuración base del proyecto Support (Django).
No importar desde fuera de /support/backend.
"""
import os
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    DATABASE_URL=(str, ""),
    REDIS_URL=(str, "redis://localhost:6379/0"),
    CELERY_BROKER_URL=(str, ""),
    SECRET_KEY=(str, "change-me-in-production"),
    CONFIG_ENCRYPTION_KEY=(str, ""),
    ENVIRONMENT=(str, "local"),
    SUPPORT_SYNAP_API_URL=(str, ""),
    SUPPORT_SYNAP_JWT_SECRET=(str, ""),
    EMBEDDING_DIMENSION=(int, 1536),
    OPENAI_API_KEY=(str, ""),
    ALLOW_EXTERNAL_TESTS=(bool, True),
)

# Un solo .env en la raíz de Support (support/.env). overwrite=False: Docker/env ya definidos no se sobrescriben.
_SUPPORT_ROOT = BASE_DIR.parent
environ.Env.read_env(_SUPPORT_ROOT / ".env", overwrite=False)

SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
ENVIRONMENT = env("ENVIRONMENT", default="local")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
if DEBUG and "*" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append("*")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "corsheaders",
    "apps.companies",
    "apps.support_users",
    "apps.agents",
    "apps.cases",
    "apps.attachments",
    "apps.sla",
    "apps.audit",
    "apps.knowledge",
    "apps.integrations",
    "apps.system_config",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.locale.LocaleMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es"
TIME_ZONE = "America/Argentina/Buenos_Aires"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# DRF
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 20,
    "MAX_PAGE_SIZE": 100,
    "EXCEPTION_HANDLER": "apps.core.exceptions.custom_exception_handler",
}

# CORS: con cookies (withCredentials) el servidor no puede usar '*'; debe devolver el origen concreto
CORS_ALLOW_ALL_ORIGINS = env.bool("CORS_ALLOW_ALL_ORIGINS", default=DEBUG)
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True

# Base de datos
DATABASES = {}
if env("DATABASE_URL", default=""):
    DATABASES["default"] = env.db("DATABASE_URL")
else:
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="support"),
        "USER": env("POSTGRES_USER", default="support"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="support"),
        "HOST": env("POSTGRES_HOST", default="localhost"),
        "PORT": env("POSTGRES_PORT", default="5432"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {"options": "-c search_path=public"},
    }

# Redis
REDIS_URL = env("REDIS_URL") or env("CELERY_BROKER_URL") or "redis://localhost:6379/0"
CELERY_BROKER_URL = env("CELERY_BROKER_URL") or REDIS_URL
CELERY_RESULT_BACKEND = CELERY_BROKER_URL

# Synap API (solo integración HTTP)
SUPPORT_SYNAP_API_URL = env("SUPPORT_SYNAP_API_URL", default="")
SUPPORT_SYNAP_JWT_SECRET = env("SUPPORT_SYNAP_JWT_SECRET", default="")

# RAG / pgvector: dimensión del embedding (1536 OpenAI text-embedding-3-small)
EMBEDDING_DIMENSION = env.int("EMBEDDING_DIMENSION", default=1536)
OPENAI_API_KEY = env("OPENAI_API_KEY", default="")
# LangChain PGVector: colección fija para RAG (schema langchain-postgres)
LANGCHAIN_PGVECTOR_COLLECTION_NAME = env("LANGCHAIN_PGVECTOR_COLLECTION_NAME", default="support_rag")

# Configuración producto: clave para cifrar secretos (base64 url-safe, ver cryptography.fernet)
CONFIG_ENCRYPTION_KEY = env("CONFIG_ENCRYPTION_KEY", default="")
# Tests de canales/IA/storage: si False, validar solo estructura y marcar skipped
ALLOW_EXTERNAL_TESTS = env.bool("ALLOW_EXTERNAL_TESTS", default=True)

# S3 / MinIO
S3_ENDPOINT_URL = env("S3_ENDPOINT_URL", default=None)
S3_ACCESS_KEY = env("S3_ACCESS_KEY", default="")
S3_SECRET_KEY = env("S3_SECRET_KEY", default="")
S3_BUCKET_NAME = env("S3_BUCKET_NAME", default="support-attachments")
S3_REGION = env("S3_REGION", default="us-east-1")
S3_PRESIGNED_EXPIRES = env.int("S3_PRESIGNED_EXPIRES", default=3600)
ATTACHMENT_MAX_SIZE_BYTES = env.int("ATTACHMENT_MAX_SIZE_BYTES", default=10 * 1024 * 1024)  # 10 MB
ATTACHMENT_ALLOWED_CONTENT_TYPES = env.list(
    "ATTACHMENT_ALLOWED_CONTENT_TYPES",
    default=[
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "application/pdf",
        "text/plain",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ],
)

# Logging: formatter estándar para Django (evita TypeError con structlog en log_response)
# y structlog para el resto. El ProcessorFormatter no maneja bien LogRecord de Django.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        },
        "structlog": {
            "()": "structlog.stdlib.ProcessorFormatter",
            "processor": "structlog.dev.ConsoleRenderer" if DEBUG else "structlog.processors.JSONRenderer",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO" if not DEBUG else "DEBUG",
    },
}
