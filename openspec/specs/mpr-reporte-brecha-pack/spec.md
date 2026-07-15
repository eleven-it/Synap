# Spec — Brecha demanda pack (PED en vivo)

**Capability:** `mpr-reporte-brecha-pack`  
**Change:** `mpr-reportes-trazabilidad-produccion`

---

## Requirements

### REQ-BRECHA-01 — Fuente PED en vivo

The system MUST compute brecha from `listar_demanda_pack_desde_pedidos` aligned with tablero consolidado, NOT stale `lista_produccion_agrupada` snapshots.

Existing `reporte_mpr_brecha_demanda` MUST be refactored to call demanda PED en vivo before UI exposure.

### REQ-BRECHA-02 — Columnas

| Campo | Descripción |
|-------|-------------|
| `pack` / `descripcion` | Artículo pack |
| `demanda` | Unidades demandadas PED |
| `stock_terminado` | Stock producto terminado |
| `brecha` | max(0, demanda − stock_terminado) |
| `urgente` | bool — pedido prioritario sin cubrir |
| `pedidos` | Resumen IDs/cantidades PED (texto o count) |

### REQ-BRECHA-03 — KPI strip

MUST show: packs con brecha, unidades faltantes total, packs urgentes.

### REQ-BRECHA-04 — Highlight urgente

Row with `urgente=True` MUST use `bg-amber-50 border-l-4 border-amber-500`.

### REQ-BRECHA-05 — Grupo Demanda

Report MUST live under navigation group **Demanda**, not Producción.

---

## Scenarios

### ESC-BRECHA-01 — Pack con brecha urgente

**Given** pack with brecha > 0 and pedido urgente flag  
**When** user opens Brecha pack  
**Then** row highlighted amber and KPI packs urgentes >= 1

### ESC-BRECHA-02 — Sin brecha

**Given** all packs covered by stock  
**When** user opens report  
**Then** empty state or all brecha=0 with message explicativo
