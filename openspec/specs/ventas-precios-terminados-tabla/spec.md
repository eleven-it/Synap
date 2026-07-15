# Spec: ventas-precios-terminados-tabla

## Requirements

### R1 — Universo y filtro primario

The system MUST show only articles with `tipo_art_fab` matching the selected `tipo_producto` (`terminado` → `Terminado`, `2da` → `Fabricado 2da`) and `Discontinuo = 'No'`.

When the user changes `tipo_producto`, the system MUST reset secondary filters and reload dependent catalogs.

### R2 — Filtros secundarios

The system MUST support multi-tag filters for marca, código (predictive), proveedor, rubro, subrubro, scoped to the active `tipo_producto`.

The system MUST support selecting visible price lists 1–5 via tags.

### R3 — Tabla editable

The table MUST display IDArt, id_manual, NombreArticulo, stock_reserva, and for each visible list: Precio neto and Precio final as editable inputs.

Editing neto MUST recalculate final and vice versa using article IVA and impuesto_interno.

Modified cells MUST be visually distinct (dirty state).

### R4 — Guardado

On save, the system MUST UPDATE `articulo`, recalculate `Util1-5` for touched lists, INSERT `precios_historial`, and update `stock_reserva` when changed.

### R5 — Cambio masivo

Bulk operations MUST apply to all articles matching current filters (server-side), with preview count before apply.

Operations MUST include percentage, fixed amount add/subtract, set value, and round for prices and reserva.

## Scenarios

### S1 — Cambio de tipo

**Given** filtros marca y código activos en Terminado  
**When** el usuario elige 2da selección  
**Then** se limpian filtros secundarios y la tabla muestra solo `Fabricado 2da`

### S2 — Recálculo neto → final

**Given** artículo con alícuota 21% e impuesto interno 0  
**When** el usuario cambia neto a 100  
**Then** final muestra 121,00 y la celda queda marcada como modificada

### S3 — Guardado con historial

**Given** cambios pendientes en lista 4  
**When** el usuario confirma guardar  
**Then** `articulo.Precio4V/VI` y `Util4` se actualizan y existe fila en `precios_historial`
