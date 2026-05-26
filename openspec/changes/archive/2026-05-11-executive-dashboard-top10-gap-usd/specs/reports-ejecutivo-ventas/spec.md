# Delta spec — Panel ejecutivo ventas (Synap)

## Contexto

Slug `resumen-ejecutivo-ventas`, API `GET /api/reports/executive-summary/`, servicio `run_executive_summary`.

## Requisitos

### REQ-EXEC-GAP-01 — Gap vs ayer en moneda

- El payload **MUST** incluir en `kpis` el campo **`gap_vs_ayer_monto`**: diferencia `ventas_netas_dia − ventas_ayer_monto`, redondeada a centavos (2 decimales), con signo (positivo = mejor día que ayer en neto facturado).
- La UI del KPI «Vs ayer» **MUST** mostrar el **porcentaje** existente (`pct_vs_ayer`) y, en la misma tarjeta, el **monto de la diferencia** en moneda local formateada (es-AR), sin sustituir el %.

### REQ-EXEC-TOP10-01 — Top 10 productos

- El payload **MUST** incluir **`top_productos`**: arreglo ordenado descendente (máximo 10 ítems).
- Cada ítem **MUST** incluir: `id_art` (int), `codigo_articulo` (string), `descripcion` (string), `unidades` (número, signo FA/NC), `importe_neto` (número, 2 decimales).
- Criterio de orden (**v1**): **`importe_neto`** = suma de `PrecioNetoxR` por renglón `stock` con signo según `TipoComprobante` del `cuentacliente` asociado, mismos filtros que «Unidades vendidas» del día (`Fecha` comprobante, `Anulado`, `TipoComp` en stock, tipos FA/NC).
- Si no hay renglones elegibles, el arreglo **MUST** ser `[]`.

### REQ-EXEC-TOP10-02 — Metadatos de criterio

- El objeto **`meta`** del payload **SHOULD** incluir `top_productos_criterio` con valor literal `importe_neto_linea` para trazabilidad de versiones de definición.

### REQ-EXEC-TOP10-03 — UI responsive

- La sección Top 10 **MUST** ser usable en viewport móvil: tabla con scroll horizontal opcional **o** apilado de filas tipo tarjeta; **MUST** reutilizar tokens visuales del panel (slate/sky, bordes, tipografía del resto de `executive_summary`).

## Escenarios

1. **Dado** hoy con ventas y ayer con ventas positivas, **cuando** se carga el panel, **entonces** el KPI «Vs ayer» muestra % y diferencia en $ coherente con `ventas_netas_dia` y `ventas_ayer_monto`.
2. **Dado** ayer con neto 0, **cuando** se muestra el %, **entonces** la UI mantiene política actual (N/D en %) y el gap en $ sigue mostrando el neto de hoy si aplica.
3. **Dado** ventas con renglones en `stock`, **cuando** se consulta Top 10, **entonces** el orden coincide con el criterio `importe_neto` y no más de 10 filas.
