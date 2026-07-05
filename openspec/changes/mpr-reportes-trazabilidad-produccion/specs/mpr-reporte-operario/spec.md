# Spec — Producción por operario (MPR parte)

**Capability:** `mpr-reporte-operario`  
**Change:** `mpr-reportes-trazabilidad-produccion`

---

## Requirements

### REQ-OPER-01 — Fuente canónica parte

The system MUST compute operario productivity from `mpr_parte_linea` joined to `mpr_parte`, NOT from `lista_produccion_historico`.

Legacy operario report MUST NOT be exposed in `/mpr/reportes/`.

### REQ-OPER-02 — Agregación por operario

For period `[fecha_desde, fecha_hasta]` the system MUST aggregate per `id_operario` (from `mpr_parte`):

| Campo | Cálculo |
|-------|---------|
| `unidades` | `SUM(mpr_parte_linea.cantidad)` |
| `partes` | `COUNT(DISTINCT mpr_parte.id)` |
| `componentes` | `COUNT(DISTINCT mpr_parte_linea.id_articulo)` |
| `pct_total` | `unidades / SUM(unidades) * 100` (0 if total = 0) |

Filter date MUST use `DATE(mpr_parte.fecha_produccion)` within range.

### REQ-OPER-03 — Nombre operario

The system MUST resolve operario display name from `sue_abm_empleado.nombre_empleado` via `id_sue_abm_empleado`; fallback `"Operario {id}"`.

### REQ-OPER-04 — KPI strip

Period KPIs MUST include: total unidades planta, operarios activos (count rows), promedio u./operario, top operario name + units.

### REQ-OPER-05 — Visual ranking

UI MUST show horizontal proportion bar per row (`pct_total` width) ordered by `unidades DESC`.

### REQ-OPER-06 — Tipos AdministraNET

All MySQL reads/writes MUST normalize via `core.utils.administranet_types`.

---

## Scenarios

### ESC-OPER-01 — Ranking con datos parte

**Given** two operarios with parte lines in period  
**When** user opens Producción → Operario with valid dates  
**Then** table lists both ordered by unidades DESC with pct bars summing ~100%

### ESC-OPER-02 — Sin partes en período

**Given** no `mpr_parte` rows in range  
**When** user opens report  
**Then** KPI strip shows zeros and empty state suggests registrar parte de producción
