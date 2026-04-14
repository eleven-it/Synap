# Webhooks Tienda Nube / Nuvemshop — API 2025-03

Referencia alineada con la documentación oficial:  
[Webhook | Nuvemshop API](https://tiendanube.github.io/api-documentation/resources/webhook)

## Prefijo HTTP

Todas las operaciones sobre webhooks usan el prefijo de tienda:

`https://api.tiendanube.com/2025-03/{store_id}`

(Brasil: `https://api.nuvemshop.com.br/2025-03/{store_id}`.)

**No** se usa el patrón antiguo `/stores/{store_id}/webhooks` sobre `api_url` genérica.

## Endpoints implementados en Synap (`WebhookService`)

| Operación | Método y ruta (relativa al prefijo) | Cuerpo / notas |
|-----------|-------------------------------------|----------------|
| Listar | `GET /webhooks` | Query opcional: `since_id`, `event`, `url`, paginación, etc. |
| Obtener uno | `GET /webhooks/{id}` | |
| Crear | `POST /webhooks` | JSON: `{"url": "https://...", "event": "order/paid"}` (un evento por registro). |
| Actualizar | `PUT /webhooks/{id}` | JSON: `url` + `event` (la API no usa `events[]` ni `description` en el recurso publicado). |
| Eliminar | `DELETE /webhooks/{id}` | Respuesta documentada: `{}` con 200. |

## “Probar” webhook

La documentación **no** define `POST /webhooks/{id}/test`. En Synap, **Probar** ejecuta `GET /webhooks/{id}` para comprobar que el registro existe y la autenticación es válida. Para una prueba de entrega real hay que disparar el evento en la tienda o usar una URL pública de captura (p. ej. RequestCatcher), según la guía oficial.

## Receptor en Synap

URL recomendada (pública HTTPS):

`{SITE_URL}/tiendanube_administranet/webhook/`

Configurable vía `TIENDANUBE_WEBHOOK_BASE_URL` o `SITE_URL` en `settings` (ver `_get_webhook_url` en `webhook_service.py`).

## Firma HMAC

Los POST entrantes pueden incluir la cabecera `x-linkedstore-hmac-sha256` (ver documentación *Verifying a webhook*). El código de verificación debe alinearse con el **app secret** del partner, no solo con `webhook_secret` del modelo local.

## Eventos obligatorios LGPD (apps en partner portal)

`store/redact`, `customers/redact`, `customers/data_request` — deben registrarse según políticas de Nuvemshop; ver la misma página de documentación y la colección Postman de pruebas LGPD.
