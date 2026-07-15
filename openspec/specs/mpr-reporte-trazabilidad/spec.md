# Spec — Trazabilidad línea de tiempo componente

**Capability:** `mpr-reporte-trazabilidad`  
**Change:** `mpr-reportes-trazabilidad-produccion`

---

## Requirements

### REQ-TRAZ-01 — Selección componente

The report MUST require `id_articulo` (componente) via autocomplete or query param.

Period MUST inherit global filter with optional narrowing.

### REQ-TRAZ-02 — Eventos ordenados

The system MUST return chronologically ordered events:

| Tipo | Origen | Campos mínimos |
|------|--------|----------------|
| envio | `mpr_envio_produccion` | fecha, cantidad, usuario |
| parte | `mpr_parte` + líneas | fecha, cantidad, operario |
| clasificacion | `mpr_transicion_lote` | fecha, semi, segunda, scrap |
| armado | `mpr_armado_lote` (si existe) | fecha, cantidad |

### REQ-TRAZ-03 — Timeline visual

UI MUST render vertical timeline with connector line, filled nodes for events, icons/labels in Spanish.

### REQ-TRAZ-04 — Gaps informativos

When envío exists without subsequent parte within period, UI MAY show hollow node «Sin parte registrada» after last envío (informational, not blocking).

### REQ-TRAZ-05 — Enlaces operativos

Event rows SHOULD link to operational screens when IDs available (parte detail, tablero).

---

## Scenarios

### ESC-TRAZ-01 — Cadena completa

**Given** componente con envío, parte y clasificación en período  
**When** usuario abre trazabilidad  
**Then** timeline muestra 3+ nodos en orden cronológico con cantidades

### ESC-TRAZ-02 — Sin artículo

**Given** reporte trazabilidad sin `id_articulo`  
**When** usuario entra al reporte  
**Then** muestra prompt «Seleccione un componente» sin timeline vacío confuso
