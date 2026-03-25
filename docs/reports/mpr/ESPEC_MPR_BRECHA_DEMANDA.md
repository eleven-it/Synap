# Especificación: Reporte MPR — Demanda vs. stock (brecha)

**Estado: PENDIENTE**  
**Prioridad: Alta**  
**Módulos afectados:** reports (QueryRunnerService), mpr (services)  
**Slug reporte (Reports):** `mpr-brecha-demanda`

---

## 1. Resumen

Por **artículo**: demanda pendiente, stock terminado, cantidad a fabricar (brecha) e indicador de **urgente**. Fuente de datos: lógica equivalente a `listar_ventana_pack` (lista_produccion_agrupada + stock por depósito). Pensado para panel de producción en tiempo real. Consumo: catálogo Reports, dashboard_detail, API query. `base_empresa` desde sesión.

---

## 2. Data sources

| Origen | Uso |
|--------|-----|
| `lista_produccion_agrupada` | Demanda pendiente por artículo |
| Stock por depósito / artículo | Stock terminado (depósitos de producto terminado) |
| `articulo` | Código y descripción |

**Servicio MPR:** `reporte_mpr_brecha_demanda(base_empresa, limit=200)`.

---

## 3. Entradas

| Parámetro | Origen | Obligatorio | Descripción |
|-----------|--------|-------------|-------------|
| `base_empresa` | `payload.filters.base_empresa` | Sí | Base MySQL |
| `limit` | config o payload | No | Límite de artículos (default 200) |

---

## 4. Salidas

**Tipo:** `QueryResult` (reports).

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `meta.slug` | str | `"mpr-brecha-demanda"` |
| `data` | list[dict] | Una fila por artículo. Columnas: `codigo_articulo`, `descripcion_articulo`, `demanda_pendiente`, `stock_terminado`, `cantidad_a_fabricar`, `urgente` (bool o int). |
| `totals` | dict | Opcional: total artículos, total unidades a fabricar. |
| `notes` | list[str] | base_empresa; mensaje si falta base_empresa |

---

## 5. Reglas de negocio

- Solo artículos con demanda o brecha > 0 (o según criterio: incluir todos con demanda pendiente).
- Orden: **urgente** primero, luego por `cantidad_a_fabricar` descendente.
- `cantidad_a_fabricar` >= 0 (brecha = max(0, demanda - stock) o equivalente).
- Sin `base_empresa` → data vacía o notes con error.

---

## 6. Criterios de aceptación

| ID | Descripción |
|----|-------------|
| CA-BR-01 | Sin `base_empresa` → `data` vacía o `notes` con error. |
| CA-BR-02 | Cada fila de `data` tiene las columnas obligatorias: `codigo_articulo`, `descripcion_articulo`, `demanda_pendiente`, `stock_terminado`, `cantidad_a_fabricar`, `urgente`. |
| CA-BR-03 | `cantidad_a_fabricar` >= 0 en todas las filas. |
| CA-BR-04 | `meta.slug = "mpr-brecha-demanda"`. |

---

## 7. Casos borde

- Sin artículos con brecha: `data = []`.
- Stock mayor que demanda: `cantidad_a_fabricar = 0`.
- Límite: respetar `limit` en número de filas devueltas.
