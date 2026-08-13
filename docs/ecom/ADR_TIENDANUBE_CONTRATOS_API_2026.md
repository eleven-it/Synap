# ADR: Contratos API Tienda Nube 2026 (sin bump de versión)

## Estado

Aceptado — 13/08/2026  
Change SDD: `tiendanube-administranet-reflote`

## Contexto

Nuvemshop/Tienda Nube publica evoluciones de contrato en la documentación **2026** (visibilidad de productos, `inventory_levels`, clasificación de errores de plan). Synap ya opera sobre la versión estable **`2025-03`**. Este ADR fija las reglas de payload y errores **sin** cambiar la versión en URL ni constantes.

Relacionado con [ADR_TIENDANUBE_API_VERSIONING.md](ADR_TIENDANUBE_API_VERSIONING.md) (versión y URLs base).

## Decisiones

### 1. Versión API fija `2025-03`

| Regla | Detalle |
|-------|---------|
| Constante | `NUVEMSHOP_API_VERSION = "2025-03"` en `tiendanube_administranet/services/tiendanube_service.py` |
| URL base | `https://api.tiendanube.com/2025-03/{store_id}` (BR: dominio `nuvemshop.com.br`) |
| **MUST NOT** | Bump a `2026-xx` ni usar `/v1` en integraciones nuevas sin ADR y pruebas smoke |

### 2. Header de autenticación canónico

| Regla | Detalle |
|-------|---------|
| **Canónico** | `Authentication: bearer {access_token}` (minúscula en `bearer`) |
| **NO canónico** | `Authorization: Bearer {token}` — ejemplos genéricos OAuth; **no** usar salvo evidencia contraria en smoke |
| Helper | `build_tiendanube_auth_headers()` en `tiendanube_service.py` |
| Smoke test | `tests/test_tiendanube_api_auth.py` — mock GET store captura header `Authentication` |

También obligatorio: `User-Agent` de contacto (ya enviado por la app).

### 3. HTTP 402 → NOT CONFIGURED

Clasificación en `services/sync_errors.py` (`classify_tiendanube_response`):

| Código HTTP | Clase `SyncErrorKind` | Retry |
|-------------|----------------------|-------|
| **402** | `NOT_CONFIGURED` | **No** — límite de plan, feature no contratada o tienda mal configurada en TN |
| 429, 502, 503, 504 | `TRANSIENT_FAILURE` | Sí (backoff / `next_retry_at`) |
| Otros 4xx/5xx | `INVALID_DATA` (default) | No |

**402** indica que ops debe revisar plan Nuvemshop, scopes OAuth o flags de la tienda — **no** reintentar como fallo transitorio.

### 4. Productos: `visibility` XOR `published`

Contrato API 2026 para create/update de producto:

| Regla | Implementación |
|-------|----------------|
| Enviar **uno u otro** | `visibility` (`visible` / `hidden`) **o** legacy `published` (bool) |
| **MUST NOT** | Ambos campos en el mismo payload |
| Normalización | `normalize_product_visibility_payload()` en `sync_service.py` — si hay `published`, convierte a `visibility` y elimina `published` |
| Prioridad | Si ya existe `visibility`, se elimina `published` del payload |

### 5. Stock: `inventory_levels` + `location_id` opcional

Push masivo vía `PATCH /products/stock-price`:

```json
{
  "variants": [
    {
      "id": 12345,
      "inventory_levels": [
        { "stock": 10 }
      ]
    }
  ]
}
```

Con ubicación TN configurada en Synap (`TiendanubeConfig.location_id`, migración **0026**):

```json
{ "location_id": 987654, "stock": 10 }
```

| Regla | Detalle |
|-------|---------|
| Estructura | Siempre `inventory_levels[]` por variante (no `stock` suelto en raíz de variante en batch) |
| `location_id` | Opcional — vacío en config → entrada solo `{ "stock": N }` |
| Origen stock | Depósito AdministraNET `deposito_tiendanube_id` (ver [TIENDANUBE_PRECIOS_STOCK.md](TIENDANUBE_PRECIOS_STOCK.md)) |
| Helper | `build_inventory_level_entry()` en `sync_service.py` |

### 6. Fuera de alcance (este change)

| Capacidad TN | Estado |
|--------------|--------|
| **Price Tables** | Fuera de alcance — no implementar en reflote |
| **Kits / productos compuestos** | Fuera de alcance |
| Bump versión API | Fuera de alcance |
| OAuth renovación real end-to-end | Documentado en checklist; no parte del reflote de código |

## Consecuencias

- Tests de contrato: `tests/test_api_payload_contracts.py`, `tests/test_tiendanube_api_auth.py`.
- Cambios futuros de Nuvemshop en productos multi-inventario → revisar este ADR antes de ampliar sync.
- Webhooks entrantes no usan estos payloads; aplican a **sync saliente** y outbox.

## Referencias

- [ADR_TIENDANUBE_API_VERSIONING.md](ADR_TIENDANUBE_API_VERSIONING.md)
- [TIENDANUBE_PRECIOS_STOCK.md](TIENDANUBE_PRECIOS_STOCK.md)
- [TIENDANUBE_WEBHOOKS_API_2025-03.md](TIENDANUBE_WEBHOOKS_API_2025-03.md)
- [TIENDANUBE_REFLOTE_DEUDA_PENDIENTE.md](TIENDANUBE_REFLOTE_DEUDA_PENDIENTE.md)
- Código: `sync_service.py`, `sync_errors.py`, `tiendanube_service.py`
