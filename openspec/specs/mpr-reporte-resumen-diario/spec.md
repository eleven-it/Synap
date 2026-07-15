# Spec — Resumen diario planta MPR

**Capability:** `mpr-reporte-resumen-diario`  
**Change:** `mpr-reportes-trazabilidad-produccion`

---

## Requirements

### REQ-RESUMEN-01 — Agregación diaria

The system MUST aggregate per calendar day (timezone servidor empresa):

| Métrica | Fuente |
|---------|--------|
| Enviado | `SUM(cantidad)` from `mpr_envio_produccion` where `DATE(creado_en)` |
| Parte | `SUM(cantidad)` from `mpr_parte_linea` joined `mpr_parte` where `DATE(fecha_produccion)` |
| Clasificado | `SUM` Semi + 2da + Scrap from `mpr_transicion_lote` where `DATE(creado_en)` |
| Scrap | scrap portion of clasificado |

### REQ-RESUMEN-02 — KPI strip periodo

The system MUST compute period totals and scrap % = scrap / clasificado (0 if clasificado = 0).

### REQ-RESUMEN-03 — Columna gap

Each day row MUST include `gap_envio_parte = max(0, enviado - parte)` with visual pill when > 0.

### REQ-RESUMEN-04 — Fila totales

Table MUST include sticky footer row summing numeric columns.

### REQ-RESUMEN-05 — Tipos AdministraNET

All MySQL reads MUST normalize types via `core.utils.administranet_types`.

---

## Scenarios

### ESC-RESUMEN-01 — Día con envío sin parte

**Given** 10 u. enviadas y 0 parte el mismo día  
**When** usuario consulta resumen diario  
**Then** gap_envio_parte = 10 y pill ámbar visible

### ESC-RESUMEN-02 — Período sin datos

**Given** no ledger rows in range  
**When** usuario consulta  
**Then** empty state con enlace a tablero consolidado
