# Delta spec — Margen bruto (resumen ejecutivo ventas)

**Cambio:** `resumen-gerencial-margen-bruto`  
**Base:** `openspec/specs/reports-ejecutivo-ventas/spec.md`

## Requisitos nuevos

### REQ-EXEC-MARG-01 — Definición de margen bruto (día)

- El payload **MUST** incluir **`margen_bruto`** con:
  - **`venta_neta_lineas`**: suma de `stock.PrecioNetoxR` con signo FA/NC, mismos filtros que `top_productos` / unidades del día.
  - **`costo_neto_lineas`**: suma de `stock.PrecioCostoxR` con el **mismo** signo FA/NC.
  - **`margen_absoluto`**: `venta_neta_lineas − costo_neto_lineas` (2 decimales).
  - **`pct_sobre_venta_lineas`**: si `venta_neta_lineas ≠ 0`, `(margen_absoluto / venta_neta_lineas) × 100` redondeado a 2 decimales; si no, **`null`**.
- El sistema **MUST NOT** usar para esta v1 el costo «actual» de `articulo.PrecioCosto` en lugar del costo de renglón del comprobante.

### REQ-EXEC-MARG-02 — Desglose por rubro

- El payload **MUST** incluir **`margen_por_rubro`**: lista ordenada por **`venta_neta`** descendente.
- Cada ítem **MUST** incluir: `codigo_rubro` (int; valor sentinela acordado p. ej. `-1` para «Sin clasificar»), `nombre_rubro` (string), `venta_neta`, `costo_neto`, `margen_absoluto`, `pct_sobre_venta` (misma política de `null` si venta del grupo es 0).
- Clasificación vía **`articulo.CodigoRubro`** y join a **`rubro`**.

### REQ-EXEC-MARG-03 — Desglose por subrubro

- El payload **MUST** incluir **`margen_por_subrubro`**: lista ordenada por **`venta_neta`** descendente.
- Cada ítem **MUST** incluir: `id_subrubro` (int; sentinela para sin clasificar), `codigo_rubro` (int opcional o sentinela), `nombre_rubro`, `nombre_subrubro`, y las mismas cuatro métricas numéricas que en rubro.
- Clasificación vía **`articulo.IDSubRubro`** y join a **`subrubro`**.

### REQ-EXEC-MARG-04 — Paridad de filtros

- Con **`sucursal`** informada, los agregados de **REQ-EXEC-MARG-01..03** **MUST** limitarse a la misma sucursal que el resto del panel (`cuentacliente.CodSucursal`).
- Sin filtro de sucursal, **MUST** incluir todos los comprobantes elegibles del día.

### REQ-EXEC-MARG-05 — Metadatos

- **`meta`** **MUST** incluir `margen_costo_criterio` = `precio_costoxr_linea` y `margen_venta_criterio` = `precio_netoxr_linea`.
- **`meta.definicion`** **SHOULD** actualizarse a versión que refleje el contrato extendido (p. ej. `executive-sales-v2`).

### REQ-EXEC-MARG-06 — Conciliación con ventas netas KPI

- La documentación y tooltips **MUST** indicar que **`kpis.ventas_netas_dia`** proviene de totales de comprobante (`SubtotalDesc`) y puede **no** coincidir con **`margen_bruto.venta_neta_lineas`**; el % de margen del bloque rentabilidad es **sobre venta de líneas** del universo `stock` definido.

### REQ-EXEC-MARG-07 — UI

- La pantalla **MUST** mostrar el margen del día y los desgloses por rubro y subrubro en español, con formato monetario y porcentual coherente con el resto del panel y la normativa UI de reportes/MPR.

## Escenarios nuevos

5. **Dado** un día con renglones `stock` con costo cargado, **cuando** se consulta el panel, **entonces** `margen_bruto.margen_absoluto` = venta neta líneas − costo neto líneas y las listas por rubro/subrubro suman a los mismos totales de líneas (salvo «Sin clasificar» explícito).
6. **Dado** artículos sin rubro/subrubro enlazado, **cuando** se agrupa, **entonces** aparecen bajo «Sin clasificar» sin fallar la API.
7. **Dado** filtro `sucursal`, **cuando** se cargan rentabilidad y Top 10, **entonces** ambos usan el mismo subconjunto de comprobantes del día.
