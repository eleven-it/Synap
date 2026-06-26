# Deuda técnica Tienda Nube — P0–P2

Documentación del cambio SDD `tiendanube-deuda-tecnica-p0-p2` (Engram).

## Resumen

Corrección de deuda técnica priorizada en el módulo `tiendanube_administranet`, alineado con la API oficial Nuvemshop/Tienda Nube **2025-03**.

## P0 — Implementado

| Ítem | Cambio |
|------|--------|
| `sync_customer_to_adminet` / `sync_customer_to_tiendanube` | Métodos nuevos en `sync_service.py`; skip si `last_synced` < 5 min |
| Duplicado `sync_customers_from_tiendanube` | Eliminado bloque duplicado |
| `SyncLog` inválido | Corregido en `signals.py`, `hooks.py`, `tasks/sync_tasks.py` |
| HMAC webhooks | Habilitado (`x-linkedstore-hmac-sha256`, secret en `TiendanubeConfig.webhook_secret`) |
| Emails ficticios `@example.com` | Eliminados; error si cliente sin email |
| Modelos legacy AdministraNET | `managed = False` (6 tablas de catálogo geográfico) |
| `ProductMapping` duplicados | Campos `_old` duplicados eliminados del modelo |
| `api_url` default | `https://api.tiendanube.com/2025-03` |
| Webhooks LGPD | Eventos `store/redact`, `customers/redact`, `customers/data_request` en auto-config |
| Migración | `0022_legacy_managed_and_api_url.py` |

## P1 — Implementado

| Ítem | Estado |
|------|--------|
| `administranet_types` en sync/webhook | `customer_payload.py`, `adminet_service`, `webhook_processor` |
| Permisos vistas webhook UI | `LoginMixin` + `PermissionRequiredMixin` |
| Residual `/v1` en forms/wizard/migrate | Corregido → `2025-03` |
| Feature flags sync/webhooks | Kill switch `.env` + fuente de verdad UI (`is_active`, `auto_sync`, `WebhookConfig.is_active`) |

## P2 — Implementado / parcial

| Ítem | Estado |
|------|--------|
| Split `views/__init__.py` | `webhook_config_views.py`, `product_views.py`, `config_views.py` + re-export |
| Rate limit 2 req/s | `services/rate_limit.py` en `TiendanubeService._request` — **P0 ampliado:** headers `x-rate-limit-*`, retry 429/502/503/504 |
| Sync inicial por lotes | `InitialSyncService`, checkpoint `InitialSyncCheckpoint`, comando `tiendanube_initial_sync`, task Celery `initial_sync_batch_task` |
| Productos stock-price batch | `PATCH /products/stock-price` (hasta 50 variantes/request) en sync incremental |
| Dedup clientes TN | `find_customer_by_email` antes de `POST /customers` |
| Suite tests | **68 tests** (rate limit, retry, initial sync, stock-price, email dedup) — cobertura 80% pendiente |
| ADR versioning | `docs/ecom/ADR_TIENDANUBE_API_VERSIONING.md` |

## Stock productos (regla de negocio)

- Tiendanube opera **a nivel artículo por unidades** (1 `IDArt` = 1 variante en TN).
- El stock publicado es **`max(0, saldo - saldo_pedido_cliente)`** del **`deposito_tiendanube_id`** (no `articulo.saldo_articulo`).
- Helpers: `product_stock.py` (stock), `product_pricing.py` (precio/costo **final** con IVA — Lista 4 Web por defecto). Ver **`docs/ecom/TIENDANUBE_PRECIOS_STOCK.md`**.
- La sync masiva Adminet → TN **requiere** depósito configurado.
- Tras **`order/paid`**: reserva en depósito TN + push inmediato vía `order_stock_push.py`. Ver **`docs/ecom/TIENDANUBE_PEDIDOS_ORDER_PAID.md`**.

## Pedidos `order/paid`

- Alta en `comp_ped` con estado **`En preparación`**, `TipoPedido='Ecom cliente'`, `estado_pago_ecom='Si'`.
- REC **a cuenta** (adelanto) con datos de pago TN. Ver **`docs/ecom/TIENDANUBE_PEDIDOS_ORDER_PAID.md`**.

## Pendiente menor

- Cobertura tests ≥80% del módulo completo (suite ampliada en progreso)

## Tests

```bash
docker exec Synap_app python manage.py test tiendanube_administranet.tests
```

Tests smoke actuales:

- `test_sync_service.py` — skip reciente, validación `tiendanube_id`
- `test_webhook_hmac.py` — verificación HMAC hex oficial
- `test_rate_limit.py` — intervalo 2 req/s
- `test_customer_payload.py` — normalización `administranet_types`
- `test_feature_flags.py` — flags sync/webhooks

## Control sync / webhooks

**Fuente de verdad (UI):**

| Acción | Dónde en UI |
|--------|-------------|
| Desactivar tienda / sync manual | `TiendanubeConfig.is_active` (formulario config) |
| Sync automática programada | Checkbox «Habilitar sincronización automática» → `auto_sync` |
| Qué sincronizar | `sync_products`, `sync_customers`, etc. |
| Webhook individual | `WebhookConfig.is_active` en `/webhooks/` |

**Kill switch de emergencia (solo ops/deploy):**

```env
TIENDANUBE_SYNC_ENABLED=false      # corta toda sync aunque UI esté activa
TIENDANUBE_WEBHOOKS_ENABLED=false   # rechaza webhooks entrantes
```

Default `true`: no hace falta definirlos en `.env` en uso normal.

## Configuración HMAC

1. Configurar `TiendanubeConfig.webhook_secret` con el **App Secret** de la app Nuvemshop.
2. En `ENVIRONMENT=production`, webhooks sin secret válido se rechazan con HTTP 401.

## Open questions (defaults aplicados)

1. Skip sync si `last_synced` < **5 min** → Sí  
2. APP_SECRET → `TiendanubeConfig.webhook_secret`  
3. Campos `_old` ProductMapping → cleanup post-P2  
4. Split views + urls → mismo PR  
5. `administranet_types` en webhook_processor → Sí  

## Referencias

- Plan SDD: Engram `sdd/tiendanube-deuda-tecnica-p0-p2/*`
- Endurecimiento mapeo clientes: `openspec/changes/tiendanube-customer-mapping-hardening/` y `docs/ecom/TIENDANUBE_CUSTOMER_MAPPING_HARDENING.md`
- API: `NUVEMSHOP_API_VERSION = "2025-03"` en servicios HTTP
- Regla subagentes: `.cursor/rules/subagentes-y-modelos.mdc`
