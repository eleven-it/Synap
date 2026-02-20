# Configuración del Backend

## Variables de entorno

Documentadas en `support/backend/.env.example`. Resumen:

| Variable | Descripción | Ejemplo / default |
|----------|-------------|-------------------|
| ENVIRONMENT | Entorno (local, dev, staging, prod) | local |
| DEBUG | Modo debug Django | True (local) |
| SECRET_KEY | Clave secreta Django | Cambiar en producción |
| DATABASE_URL | URL de conexión PostgreSQL | postgres://user:pass@host:5432/dbname |
| POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD | Alternativa a DATABASE_URL | |
| REDIS_URL | Redis (broker y cache) | redis://localhost:6379/0 |
| CELERY_BROKER_URL | Broker de Celery | Si no se define, se usa REDIS_URL |
| SUPPORT_SYNAP_API_URL | URL base de la API Synap (para empresas y **conocimiento RAG**) | |
| SUPPORT_SYNAP_JWT_SECRET | Secret para firmar JWT hacia Synap | |
| OPENAI_API_KEY | API key OpenAI para embeddings (RAG). Puede ser la misma que en Config → IA | |
| EMBEDDING_DIMENSION | Dimensión del vector (default 1536, text-embedding-3-small) | 1536 |
| S3_ENDPOINT_URL | Endpoint S3/MinIO (MinIO: http://minio:9000) | |
| S3_ACCESS_KEY, S3_SECRET_KEY | Credenciales S3 | |
| S3_BUCKET_NAME | Bucket de adjuntos | support-attachments |
| S3_REGION | Región (opcional) | us-east-1 |
| S3_PRESIGNED_EXPIRES | Segundos de validez de URLs firmadas | 3600 |
| ATTACHMENT_MAX_SIZE_BYTES | Tamaño máximo por archivo (bytes) | 10485760 (10 MB) |
| ATTACHMENT_ALLOWED_CONTENT_TYPES | Lista de tipos MIME permitidos | image/jpeg, image/png, application/pdf, ... |
| CORS_ALLOW_ALL_ORIGINS | Permitir cualquier origen (desarrollo) | True en local |
| CORS_ALLOWED_ORIGINS | Lista de orígenes permitidos (producción) | |
| ALLOWED_HOSTS | Hosts permitidos (lista separada por comas) | |
| DJANGO_SETTINGS_MODULE | Módulo de settings a cargar | config.settings.local |

## Settings por entorno

- **config.settings.local** — Desarrollo local: DEBUG True, CORS abierto, email en consola, Synap opcional.
- **config.settings.dev** — Integración: DEBUG False, CORS y ALLOWED_HOSTS por variable.
- **config.settings.staging** — Staging: mismo patrón que dev.
- **config.settings.prod** — Producción: DEBUG False, SECURE_PROXY_SSL_HEADER, CORS restringido.

Se activa el entorno con `DJANGO_SETTINGS_MODULE=config.settings.<entorno>` o con la variable `ENVIRONMENT` si se usa un loader que la mapee a un módulo.

## Logging

En `config.settings.base.LOGGING` se define un handler console y formateador (structlog en desarrollo, JSON en producción). El nivel raíz depende de DEBUG. Para correlación (request_id, case_id, empresa_id) está previsto usar `apps.core.logging_utils` (structlog y contextvars).

---

## Seguridad para SPA React (cookie-session)

El backend usa **autenticación por sesión (cookie)**. Para un frontend React en otro origen:

1. **CORS**
   - En desarrollo: `CORS_ALLOW_ALL_ORIGINS=True` (o `CORS_ALLOWED_ORIGINS` con el origen del SPA).
   - En producción: definir `CORS_ALLOWED_ORIGINS` con la URL exacta del SPA (ej. `https://support.ejemplo.com`). No usar `*` con credenciales.
   - Las peticiones desde el SPA deben enviar `credentials: 'include'` (fetch) o `withCredentials: true` (axios) para que se envíe la cookie de sesión.

2. **CSRF**
   - Django exige token CSRF en POST/PATCH/PUT/DELETE cuando se usa `SessionAuthentication`. El SPA debe obtener el token desde una cookie (Django envía `csrftoken`) o desde un header que el backend acepte.
   - Opción recomendada: leer la cookie `csrftoken` (o el nombre configurado en `CSRF_COOKIE_NAME`) y enviarla en el header `X-CSRFToken` en cada petición mutante.
   - En desarrollo, si el SPA está en otro puerto (ej. localhost:3000), asegurar que `CSRF_TRUSTED_ORIGINS` incluye `http://localhost:3000` y que `CORS_ALLOWED_ORIGINS` también.

3. **SameSite**
   - Por defecto Django puede enviar la cookie de sesión con `SameSite=Lax`. Para que el SPA en subdominio reciba la cookie en peticiones cross-site, en producción se puede configurar `SESSION_COOKIE_SAME_SITE = 'None'` y `SESSION_COOKIE_SECURE = True` (HTTPS obligatorio). En ese caso CORS debe estar correctamente restringido por origen.

4. **Resumen**
   - API requiere autenticación y roles: todos los endpoints (salvo health, login, webhooks) usan `IsAuthenticated` y en muchos casos `IsAgentOrAdmin` o `IsAdmin`. El SPA debe enviar credenciales y, si usa sesión, el token CSRF en mutaciones.
   - Si en el futuro se cambia a auth por JWT, CORS se mantiene; CSRF deja de ser necesario para peticiones que solo envían el Bearer token (no cookies).
