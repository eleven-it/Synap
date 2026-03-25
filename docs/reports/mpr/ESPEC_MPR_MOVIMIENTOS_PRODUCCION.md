# Especificación: Reporte MPR — Movimientos de producción

**Estado: IMPLEMENTADO**  
**Prioridad: Media**  
**Módulos afectados:** reports (QueryRunnerService, widget), mpr (services)  
**Slug reporte (Reports):** `mpr-movimientos-produccion`

---

## 1. Resumen

Actividad reciente de producción en formato **tabla**: fecha, tipo de movimiento (OPT, OPP, OPA, Armado), código de movimiento, número de comprobante, detalle (resumido). Pensado para tiempo real. Consumo: catálogo Reports, dashboard_detail, API query. `base_empresa` desde sesión.

---

## 2. Data sources

| Origen | Uso |
|--------|-----|
| `movimiento_stock` | Filtro: `tipo_mov IN ('OPT', 'OPP', 'OPA', 'Armado')` o equivalente por `motivo_movimiento`. Campos: fecha, tipo_mov, codigo_movimiento, nro_comprobante, detalle, anulado. |

**Servicio MPR:** `listar_movimientos_recientes_mpr(base_empresa, limit=200)` o `reporte_mpr_movimientos(base_empresa, limit=200)` con salida en formato tabla (columnas planas).

---

## 3. Entradas

| Parámetro | Origen | Obligatorio | Descripción |
|-----------|--------|-------------|-------------|
| `base_empresa` | `payload.filters.base_empresa` | Sí | Base MySQL |
| `limit` | config o payload | No | Default 200 |

---

## 4. Salidas

**Tipo:** `QueryResult` (reports).

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `meta.slug` | str | `"mpr-movimientos-produccion"` |
| `data` | list[dict] | Una fila por movimiento. Columnas: `fecha`, `tipo_mov`, `codigo_movimiento`, `nro_comprobante`, `detalle` (string corto). Orden: más reciente primero. |
| `totals` | dict | `total_movimientos` (cantidad de filas) |
| `notes` | list[str] | base_empresa; mensaje si falta base_empresa |

---

## 5. Reglas de negocio

- Solo movimientos **no anulados** (`COALESCE(anulado, 'No') = 'No'`).
- Tipo normalizado a: OPT, OPP, OPA, Armado (mapear desde motivo si hace falta).
- Orden: `codigo_movimiento` DESC o por fecha DESC (más reciente primero).
- Sin `base_empresa` → data vacía o notes.

---

## 6. Criterios de aceptación

| ID | Descripción |
|----|-------------|
| CA-MP-01 | Sin `base_empresa` → `data` vacía o `notes` con mensaje. |
| CA-MP-02 | Cada fila tiene al menos `fecha`, `tipo_mov`, `codigo_movimiento`. |
| CA-MP-03 | Número de filas <= `limit` (default 200). |
| CA-MP-04 | `meta.slug = "mpr-movimientos-produccion"`. |

---

## 7. Casos borde

- Sin movimientos: `data = []`.
- Tabla `movimiento_stock` sin columna `tipo_mov`: usar solo `motivo_movimiento` y mapear a OPT/OPP/OPA/Armado según especificación MPR.

---

## 8. Implementación

- **Servicio:** `mpr.services.reporte_mpr_movimientos(base_empresa, limit=200)` — consulta `movimiento_stock`, normaliza tipo (OPT/OPP/OPA/Armado), devuelve lista de dicts con `fecha`, `tipo_mov`, `codigo_movimiento`, `nro_comprobante`, `detalle`.
- **Runner:** `QueryRunnerService._run_mpr_movimientos_produccion` — resuelve `base_empresa`, llama al servicio, devuelve `QueryResult` con `totals.total_movimientos`.
- **Dashboard:** Widget `pivot-table` "Movimientos de producción" (migración 0033). Resumen con tarjeta "TOTAL MOVIMIENTOS" (entero).
