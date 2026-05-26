# Especificación — Dashboard gerencial: ventas por medio de cobro

**Capacidad:** `reports-executive-dashboard-ventas-cobros`  
**Cambio:** `adminnet-module-migration-command-center-finance`  
**Versión de contrato:** `executive-dashboard-v1`

---

## Purpose

Dos series comparables: importes **facturados por medio** al emitir vs **cobrados en caja** en el período. Sin KPIs de impuestos.

---

## Requirements

### REQ-ED-COB-01 — Ruta P0

- **`GET /api/reports/executive-dashboard/ventas/cobros/resumen/`** **MUST** existir y cumplir requisitos transversales del spec padre.

### REQ-ED-COB-02 — Serie facturado por medio

- Objeto **`facturado_por_medio`** **MUST** incluir buckets: `efectivo`, `tarjeta`, `cuenta_corriente`, `cheque`, `transferencia`, `otros`, `total`.
- Fuente primaria: **`resumen_venta_cv`** agregado por `fecha` / sucursal del comprobante en período.
- Complemento: facturas FA/FB (y tipos venta definidos en design) sin fila en resumen **MUST** sumar desde `cuentacliente` (`tpv_importe_*`, `TotalEfectivoP`, `Total_Tarjeta`, etc.).
- **`total`** **MUST** ser la suma de buckets (redondeo 2 decimales).

### REQ-ED-COB-03 — Serie cobrado en caja

- Objeto **`cobrado_caja_por_medio`** **MUST** incluir: `efectivo`, `tarjeta`, `cheque`, `transferencia`, `otros`, `total`.
- Fuente: **`caja`** período, `anulado='No'`, solo filas con `ingreso > 0`.
- Medio **MUST** derivarse de heurística alineada a `_get_payment_method` (`tipo_comprobante`, `Tipo`).
- Ingresos FA/FB en contado y REC en cobranza **MUST** incluirse en esta serie.

### REQ-ED-COB-04 — Semántica y notas

- **`meta.notas_semanticas`** **MUST** explicar que facturado ≠ cobrado para ventas a cuenta corriente.
- **`meta.notas_semanticas`** **MUST** referenciar que ventas netas del área `ventas` incluyen facturas no cobradas.
- La respuesta **MUST NOT** incluir bloques de impuestos ni egresos impositivos.

### REQ-ED-COB-05 — Filtros

- Período y `sucursal` **MUST** aplicarse igual que otros endpoints gerenciales (`cod_sucursal` / join sucursal según design).

### REQ-ED-COB-06 — Disponibilidad

- **`disponible`**: `true` por defecto en éxito; modo degradado solo si fallo parcial documentado (no aplica en P0).

### REQ-ED-COB-P1-01 — Detalle (fuera P0)

- **`GET .../ventas/cobros/detalle/`** **MAY** usar `medio_cobpag` por REC; no requisito P0.

---

## Escenarios

#### Scenario: Dos series en respuesta

- GIVEN usuario gerencial y período mayo 2026
- WHEN `GET .../ventas/cobros/resumen/?fecha_inicio=2026-05-01&fecha_fin=2026-05-31`
- THEN 200 con `facturado_por_medio.total` y `cobrado_caja_por_medio.total` numéricos

#### Scenario: Cuenta corriente en facturado sin cobro

- GIVEN facturas a plazo sin REC en período
- WHEN se consulta el resumen
- THEN `facturado_por_medio.cuenta_corriente` puede ser > 0 y `cobrado_caja_por_medio` no necesariamente iguala facturado

#### Scenario: Sin impuestos

- GIVEN respuesta exitosa
- WHEN se inspecciona el JSON
- THEN no existe clave `impuestos` ni equivalente

#### Scenario: Período inválido

- GIVEN `fecha_inicio` > `fecha_fin`
- WHEN `GET .../ventas/cobros/resumen/`
- THEN 400
