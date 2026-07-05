# Spec — Pendiente componentes (demanda vs pipeline)

**Capability:** `mpr-reporte-pendiente-componentes`  
**Change:** `mpr-reportes-trazabilidad-produccion`

---

## Requirements

### REQ-PEND-01 — Fuente tablero consolidado

The system MUST derive pendiente rows from `listar_tablero_por_articulo(base_empresa, solo_pendiente=True)` — same algorithm as tablero producción, NOT `lista_produccion_agrupada`.

### REQ-PEND-02 — Columnas mínimas

Each row MUST expose:

| Campo | Origen fila tablero |
|-------|---------------------|
| `codigo_articulo` | código componente |
| `descripcion_articulo` | descripción |
| `demanda` | demanda total componente |
| `stock_pipeline` | stock en pipeline MPR |
| `pendiente` | unidades pendientes |
| `enviado` | enviado tablero |
| `ultimo_envio` | fecha último `mpr_envio_produccion` (optional P0) |

### REQ-PEND-03 — KPI strip

MUST show: componentes pendientes (count), unidades pendientes (sum), críticos count (pendiente > umbral default 50 or configurable constant).

### REQ-PEND-04 — Badge crítico

Row with `pendiente >= UMBRAL_CRITICO` MUST display badge «Crítico» amber.

### REQ-PEND-05 — Enlace accionable

Each row MUST link to tablero producción filtered by component or trazabilidad report.

### REQ-PEND-06 — Reemplazo navegación default

**Producción → Pendiente componentes** MUST replace legacy **Pendiente OPT** as default pendiente view in new shell. Legacy pendiente ONLY under Histórico OPT.

---

## Scenarios

### ESC-PEND-01 — Lista solo pendientes

**Given** tablero has 3 components with pendiente > 0  
**When** user opens Pendiente componentes  
**Then** exactly 3 rows shown sorted by pendiente DESC

### ESC-PEND-02 — Sin pendientes

**Given** all components covered  
**When** user opens report  
**Then** empty state «No hay componentes pendientes» with link to tablero
