# 11 — Catálogo de APIs

**Estado:** COMPLETE (Fase 11)  
**Fecha:** 25/08/2026

---

## Resumen

| Métrica | Valor |
|---------|------:|
| Endpoints con patrón `/api/` (runtime) | **411** |
| Archivos urls | 27 |
| Patrones `path(` totales (incl. HTML) | ~750+ |
| Apps con API REST (DRF) | 10 |
| APIs versionadas (`/api/v1/`) | **4** (solo ecom) |
| Namespace DRF | 8 |

**Clasificación:** CONFIRMADO POR CÓDIGO — conteo runtime vía `django.urls.get_resolver()` (subagente API catalog); `~750+` incluye rutas HTML no-API.

### Distribución por app (endpoints `/api/`)

| App | Endpoints |
|-----|----------:|
| reports | 72 |
| ecom | 64 |
| self_checkout | 39 |
| mpr | 35 |
| factura_compra_captura | 33 |
| core | 32 |
| tiendanube_administranet | 28 |
| ia | 25 |
| logistica | 25 |
| stock | 22 |
| ventas | 20 |
| fe_afip | 8 |
| legacy_db | 8 |

---

## APIs por módulo

### core — `/core/api/` (namespace: `core_api`)

| Método | Path | Auth | DB |
|--------|------|------|-----|
| GET | `/core/api/articulos/search/` | Session | MySQL |
| GET | `/core/api/clientes/search/` | Session | MySQL |
| GET | `/core/api/proveedores/search/` | Session | MySQL |
| GET | `/core/api/depositos/search/` | Session | MySQL |
| GET | `/core/api/contacts/search/` | Session | PG |
| GET | `/core/api/geocode/` | Session | External |
| GET | `/core/api/fecha-servidor/` | Session | — |
| GET | `/core/api/support/conocimiento/` | JWT (prod) | PG |
| GET/POST | `/core/api/users/` | Session+DRF | PG |
| GET/POST | `/core/api/roles/` | Session+DRF | PG |
| GET | `/core/api/branches/` | Session+DRF | PG |

**Nota routing:** Posible eclipse por `include('core.urls')` — ver ARCH-004.

### reports — `/api/reports/` (namespace: `reports-api`)

| Método | Path | Auth | DB |
|--------|------|------|-----|
| GET | `/api/reports/definitions/` | Session+DRF | PG |
| GET | `/api/reports/dashboards/{slug}/data/` | Session | MySQL+PG |
| POST | `/api/reports/execute/` | Session | MySQL |
| GET | `/api/reports/workspaces/` | Session+DRF | PG |
| *+60 endpoints* | Varios runners, exports, presets | Session | MySQL |

72 patterns en `reports/api_urls.py`.

### ecom — `/ecom/` (153 URL patterns)

| Grupo | Paths | Auth | DB |
|-------|-------|------|-----|
| Hub pedidos | `/ecom/pedidos/`, kanban, aprobación | Session | MySQL+PG |
| Compra mayorista | `/ecom/compra-mayorista/` | Session | MySQL |
| Pedido masivo | `/ecom/pedido-masivo/` | Session | PG+MySQL |
| Catálogo | `/ecom/catalogo/` | Session | MySQL |
| Vendedor operativo | `/ecom/vendedor/` | Session | MySQL |
| Relays | `/ecom/api/relay/*` | Session | HTTP→PHP |
| Config VCM | `/ecom/config/vendedor-cliente-marca/` | Session | MySQL |

### self_checkout — `/api/self-checkout/` (39 patterns)

| Método | Path | Auth | DB |
|--------|------|------|-----|
| POST | `/api/self-checkout/venta/` | Session | MySQL |
| POST | `/api/self-checkout/caja/cierre/` | Session | MySQL |
| GET | `/api/self-checkout/articulos/` | Session | MySQL |
| POST | `/api/self-checkout/fe/cae/` | Session | MySQL+AFIP |

### mpr — `/mpr/` (110 patterns)

| Grupo | Paths | Auth | DB |
|-------|-------|------|-----|
| Wizard | `/mpr/wizard/` | Session | PG+MySQL |
| OPT | `/mpr/opt/` | Session | PG+MySQL |
| Tablero | `/mpr/tablero/` | Session | MySQL |
| Partes | `/mpr/api/parte/` | Session | MySQL+PG |
| Armado | `/mpr/armado/` | Session | MySQL |

### factura_compra_captura — `/api/compras/`

| Método | Path | Auth | DB |
|--------|------|------|-----|
| POST | `/api/compras/expediente/` | Session+DRF | PG |
| POST | `/api/compras/expediente/{id}/documento/` | Session+DRF | PG+FS |
| GET | `/api/compras/expediente/{id}/` | Session+DRF | PG |
| POST | `/api/compras/expediente/{id}/aprobar/` | Session+DRF | PG |

### ia — `/api/ia/` (namespace: `ia-api`)

| Método | Path | Auth | DB |
|--------|------|------|-----|
| GET/POST | `/api/ia/conversaciones/` | Session+DRF | PG |
| POST | `/api/ia/conversaciones/{id}/mensaje/` | Session+DRF | PG+External |
| GET | `/api/ia/agentes/` | Session+DRF | PG |

### tiendanube — `/api/tiendanube_administranet/`

| Método | Path | Auth | DB |
|--------|------|------|-----|
| POST | `.../webhook/` | **@csrf_exempt** | PG |
| GET/POST | `.../sync/` | Session+DRF | PG+MySQL |
| GET | `.../mappings/` | Session+DRF | PG |

### legacy_db — `/api/legacy-hub/`

| Método | Path | Auth | DB |
|--------|------|------|-----|
| GET/POST | `/api/legacy-hub/compras/` | Session | MySQL |

### stock — `/stock/` (45 patterns, mix HTML+API)

| Método | Path | Auth | DB |
|--------|------|------|-----|
| POST | `/stock/api/movimiento/` | Session | MySQL |
| GET | `/stock/api/inventario/` | Session | MySQL |

---

## Versionado

Solo **ecom** expone rutas versionadas bajo `/ecom/api/v1/` (4 endpoints). El resto de APIs no usa prefijo `/api/v1/`.

**Riesgo:** Breaking changes en reports, mpr, self_checkout, etc. afectan todos los consumidores sin contrato de versión.

---

## Endpoints sin autenticación detectados

| Path | Auth | Riesgo |
|------|------|--------|
| `/login/api/empresas/` | **Sin auth** (rate limit 90/min) | **MEDIUM** — enumeración empresas |
| `/tiendanube_administranet/webhook/` | @csrf_exempt, HMAC en prod | Esperado (webhook) |
| `/sw.js`, `/manifest.json` | Público | Esperado (PWA) |
| `/media/*` | Público con path | Medio — path traversal mitigado |
| Static files | Público | Esperado |

---

## Duplicaciones detectadas

| Recurso | Paths | Nota |
|---------|-------|------|
| Pedidos ecom | `/ecom/api/relay/pedidos/` vs `/ecom/api/v1/pedidos/` | Relay PHP vs API nativa |
| Logística vs Reports | `/api/logistica/...` vs `/api/reports/...` | Mismo dominio, dos superficies |
| Búsqueda artículos | `/core/api/articulos/search/` vs módulo-specific | Posible duplicación |
| Dashboard | `/core/dashboard/` vs `/dashboard/` (legacy) | Legacy stub |
| Reports data | HTML views + API endpoints | Paralelos intencionales |

---

## Contratos implícitos

- Respuestas JSON sin schema formal (no OpenAPI/Swagger)
- Formato de error inconsistente entre módulos
- Paginación DRF solo en endpoints que usan ViewSets
- Fechas: mezcla ISO y YYYYMMDD según módulo

---

*Generado por auditoría READ ONLY.*
