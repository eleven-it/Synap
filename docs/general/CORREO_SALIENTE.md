# Correo saliente (SMTP)

**Fecha:** 17/07/2026

## Propósito

Configuración centralizada del correo saliente de Synap. Los parámetros operativos se guardan en Postgres (`SystemConfiguration`, claves `email.outbound.*`). Si no hay config activa en DB, se usa el fallback de variables `EMAIL_*` en `django_project/settings.py` / `.env`.

## Claves SystemConfiguration

| Clave | Descripción | Default |
|-------|-------------|---------|
| `email.outbound.enabled` | Habilitar SMTP desde DB | `false` |
| `email.outbound.host` | Servidor SMTP | — |
| `email.outbound.port` | Puerto | `587` |
| `email.outbound.use_tls` | STARTTLS | `true` |
| `email.outbound.use_ssl` | SSL implícito | `false` |
| `email.outbound.username` | Usuario SMTP | — |
| `email.outbound.password` | Contraseña (no se expone en lectura UI) | — |
| `email.outbound.from_email` | Remitente From | fallback `DEFAULT_FROM_EMAIL` |
| `email.outbound.timeout` | Timeout segundos | `20` |

Servicio: `core.services.outbound_email` (`leer_config_correo_saliente`, `guardar_config_correo_saliente`, `resolver_parametros_smtp`, `get_connection_correo_saliente`, `from_email_correo_saliente`, `probar_conexion_correo_saliente`).

## Fallback `.env` / settings

Ver `.env.example`:

- `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`
- `EMAIL_USE_TLS`, `EMAIL_USE_SSL`, `DEFAULT_FROM_EMAIL`, `EMAIL_TIMEOUT`

Prioridad: DB activa (`enabled` + `host`) → settings Django.

## UI

- **Ruta:** `/configuracion/correo-saliente/`
- **Permiso:** `configuracion.sistema`
- **Menú:** Settings → Configuración del sistema → Correo saliente
- **Vista:** `core.views.views_outbound_email.OutboundEmailConfigView` (template `core/system_config/correo_saliente.html`, base `core_app_base.html`, Alpine + canon UI slate/sky).

### Campos del formulario

| Campo | Notas |
|-------|-------|
| Correo saliente activo | Toggle Activo/Inactivo (`enabled`). Si Inactivo o sin host → fallback `EMAIL_*` del entorno. |
| Servidor SMTP (Host) | `host` |
| Puerto | `port` (default 587) |
| Timeout (segundos) | `timeout` (default 20) |
| Usuario SMTP | `username` |
| Contraseña | `password`. Placeholder `••••••••` si ya hay una guardada; **vacío = no cambiar**. |
| Remitente (From) | `from_email` |
| TLS (STARTTLS) / SSL implícito | Toggles mutuamente excluyentes (activar uno desactiva el otro). |

Badge de estado **Configurado / No configurado** según `correo_saliente_configurado()`.

### APIs

| Método | Path | Nombre URL | Body | Respuesta |
|--------|------|-----------|------|-----------|
| POST | `/api/configuracion/correo-saliente/` | `core:api_outbound_email_save` | `{ enabled, host, port, username, password?, from_email, use_tls, use_ssl, timeout }` (`password` solo si se cambia) | `{ ok, message, configurado, ...config }` |
| POST | `/api/configuracion/correo-saliente/probar/` | `core:api_outbound_email_test` | `{ "to_email": "..." }` (opcional) | `{ ok, message }` |

Vistas API: `OutboundEmailConfigAPIView`, `OutboundEmailTestAPIView` (`LoginRequired` + permiso `configuracion.sistema`, CSRF vía `X-CSRFToken`).

## Cola e-com

El worker `process_ecom_mail_queue` (`ecom.management.commands.process_ecom_mail_queue`) procesa `EcomMailQueue` usando `get_connection_correo_saliente()` y adjunta PDF de pedidos (PED) al enviar.

Si no hay SMTP configurado, el item queda en error con mensaje «Correo saliente no configurado».
