# Seguridad: API de conocimiento RAG (Support ↔ Synap)

Índice general de **todos** los cambios de seguridad del proyecto (login, settings, APIs, XSS, etc.): [SEGURIDAD_CAMBIOS_SYNAP.md](SEGURIDAD_CAMBIOS_SYNAP.md).

## Endpoint

`GET /core/api/support/conocimiento/` devuelve fragmentos de texto para ingesta RAG del módulo Support (lee `docs/` en Synap).

## Autenticación

Mismo mecanismo que el cliente HTTP de Support (`support/backend/apps/integrations/adapters/synap_client.py`): header `Authorization: Bearer <jwt>` con JWT firmado en **HS256** y claim **`exp`** obligatorio.

El secret compartido es la variable de entorno **`SUPPORT_SYNAP_JWT_SECRET`**: debe definirse con **el mismo valor** en:

- Synap (`django_project/settings.py` → `SUPPORT_SYNAP_JWT_SECRET`)
- Support backend (`SUPPORT_SYNAP_JWT_SECRET` en el `.env` del proyecto Support)

## Comportamiento por entorno (Synap)

| `ENVIRONMENT` | `DEBUG` | `SUPPORT_SYNAP_JWT_SECRET` | Comportamiento |
|---------------|---------|----------------------------|----------------|
| `production` / `produccion` | — | vacío | `503` — configurar secret antes de exponer el endpoint. |
| `production` / `produccion` | — | definido | Exige Bearer JWT válido y no expirado. |
| otro | `True` | vacío | Permite acceso sin token (solo desarrollo local). |
| otro | `False` | vacío | `503` — staging sin JWT abierto; definir secret o usar JWT. |
| otro | — | definido | Exige Bearer JWT válido. |

## Otros endurecimientos relacionados

- **`SECRET_KEY`** y **`POSTGRES_PASSWORD`**: obligatorios no vacíos si `ENVIRONMENT` es `production` / `produccion` (`django_project/settings.py`).
- **Rate limit** login POST y `GET /login/api/empresas/` por IP vía cache (`core.utils.rate_limit`, `login.views`).
- **Tipos de envío por sucursal**: comprobación de `id_sucursal` en sesión (o admin supervisor) y que el registro pertenezca a la sucursal de la URL (`core.api.views`, `AdministraNETSucursalesService.tipo_envio_pertenece_a_sucursal`).
- **XSS**: filtros `safe_svg_icon` / `safe_ui_slot` (`core.templatetags.security_extras`) y `json_script` para datos de gráficos en dashboard.

## Media pública en login

Los logos de empresa se sirven bajo el prefijo `empresas/logos/` sin sesión para permitir favicon/logo en la pantalla de login. El resto de rutas bajo `/media/` requieren sesión administraNET. Ver implementación en `core.views.media_views.serve_media_file`.

## POST `/set-device-hint/`

La vista `core.views.device_views.set_device_hint` está protegida con CSRF (`@csrf_protect`). Si se integra un cliente que llame a este endpoint por POST, debe enviar la cookie `csrftoken` y el header `X-CSRFToken` (o el token en el cuerpo del formulario), igual que el resto de vistas Django.

## Referencias

- Tests: `core/tests/test_support_conocimiento_api.py`
- Vista: `core.api.views.support_conocimiento_api`
