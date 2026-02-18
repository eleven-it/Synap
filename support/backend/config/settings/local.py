"""Settings para entorno local (desarrollo)."""
from .base import *  # noqa: F401, F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "*"]
# Frontend con cookies: no usar *; listar orígenes y permitir credenciales
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
CORS_ALLOW_CREDENTIALS = True

# CSRF: mismo origen que CORS para que el login desde el frontend (localhost:3000) sea aceptado
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Email en consola
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Synap API opcional en local
SUPPORT_SYNAP_API_URL = env("SUPPORT_SYNAP_API_URL", default="")
SUPPORT_SYNAP_JWT_SECRET = env("SUPPORT_SYNAP_JWT_SECRET", default="")
