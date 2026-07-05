# Spec — Cadena envío → parte → clasificación

**Capability:** `mpr-reporte-cadena-pipeline`  
**Change:** `mpr-reportes-trazabilidad-produccion`

---

## Requirements

### REQ-CADENA-01 — Agregación por componente

For period `[fecha_desde, fecha_hasta]` the system MUST return one row per `id_articulo` (componente) with:

| Campo | Fuente |
|-------|--------|
| `enviado` | `SUM(cantidad)` from `mpr_envio_produccion` where `DATE(creado_en)` in range |
| `parte` | `SUM(cantidad)` from `mpr_parte_linea` + `mpr_parte` where `DATE(fecha_produccion)` in range |
| `clasificado` | `SUM(semi + segunda + scrap)` from `mpr_transicion_lote` where `DATE(creado_en)` in range |
| `scrap` | scrap portion only |

### REQ-CADENA-02 — Estado pipeline

Each row MUST include `estado`:

| Condición | Estado |
|-----------|--------|
| `enviado = 0` | `sin_envio` |
| `enviado > parte` | `falta_parte` |
| `parte > clasificado` | `falta_clasificar` |
| else | `completo` |

### REQ-CADENA-03 — Orden default

Rows MUST sort by `max(0, enviado - parte) DESC`, then `pendiente_nombre`.

### REQ-CADENA-04 — Barra pipeline visual

UI MUST render per-row pipeline bar with segments proportional to `max(enviado, parte, clasificado)` baseline, colors: enviado slate, parte emerald, clasificado purple, gap segments rose/amber per estado.

### REQ-CADENA-05 — KPI strip

Period KPIs: componentes con gap, total enviado, total parte, total clasificado.

### REQ-CADENA-06 — Drill-down

Clicking a component row SHOULD navigate to Trazabilidad with `id_articulo` and same period pre-filled.

---

## Scenarios

### ESC-CADENA-01 — Gap envío sin parte

**Given** componente with enviado=20, parte=0 in period  
**When** user views cadena pipeline  
**Then** row shows estado `falta_parte` and gap segment visible

### ESC-CADENA-02 — Pipeline completo

**Given** enviado=10, parte=10, clasificado=10  
**When** user views row  
**Then** badge «Completo» emerald and no gap highlight
