# 23 — Error Handling

**Estado:** COMPLETE (Fase 23)  
**Fecha:** 25/08/2026

---

## Patrones detectados

| Patrón | Ubicación | Frecuencia |
|--------|-----------|:----------:|
| try/except genérico | Servicios MySQL | Alta |
| logger.error + raise | Servicios core | Media |
| logger.error + return fallback | login/administranet_auth.py | Media |
| session.flush() en error MySQL | request_scoped_mysql.py | Baja |
| JSON error response | API views | Alta |
| messages.error (Django) | Views HTML | Alta |
| transaction.atomic() | legacy_db, captura | Media |

## Manejo global

| Handler | Archivo | Función |
|---------|---------|---------|
| handler403 | core/views/error_403_view | Permisos denegados |
| custom_ajax_login_required | settings.py | 401 JSON para AJAX |
| AdministraNETAuth fallback | login/ | Empresa default si falla catálogo |

## Fallos silenciosos detectados

| Ubicación | Comportamiento | Riesgo |
|-----------|---------------|--------|
| Celery tasks sin worker | Task encolada, nunca ejecuta | **Alto** |
| OCR thread exception | Puede perderse sin notify | Medio |
| get_empresas() except | Retorna empresa local default | Medio |
| docker-entrypoint.sh | `|| true` en varios commands | Bajo |
| Cache miss | Ejecuta query (correcto) | — |

## Retries

| Componente | Retry | Backoff |
|----------|:-----:|:-------:|
| docker-entrypoint PG | Sí (loop) | 2-3s |
| mysql_pool reconnect | Sí (nueva conn) | — |
| tiendanube outbox | Sí (drain command) | — |
| HTTP relays ecom | Timeout only | — |
| pyafipws SOAP | Interno pyafipws | — |

## Rollback

- `transaction.atomic()` en operaciones PG multi-step
- MySQL: manual conn.rollback() en legacy_db services
- Sin transacciones distribuidas PG+MySQL

---

*Generado por auditoría READ ONLY.*
