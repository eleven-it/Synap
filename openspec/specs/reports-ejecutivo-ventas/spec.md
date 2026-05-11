# Especificación — Panel ejecutivo ventas (Synap)

Fuente de verdad OpenSpec para el slug `resumen-ejecutivo-ventas`, API `GET /api/reports/executive-summary/` y servicio `run_executive_summary`.

Incorpora el delta del cambio archivado `executive-dashboard-top10-gap-usd` y extensiones posteriores (filtro sucursal, orden Top 10, persistencia PV en PostgreSQL). Detalle operativo y tablas legacy: `docs/reports/SPEC_DASHBOARD_RESUMEN_EJECUTIVO_VENTAS.md`.

## Requisitos

### REQ-EXEC-GAP-01 — Gap vs ayer en moneda

- El payload **MUST** incluir en `kpis` el campo **`gap_vs_ayer_monto`**: diferencia `ventas_netas_dia − ventas_ayer_monto`, redondeada a centavos (2 decimales), con signo (positivo = mejor día que ayer en neto facturado).
- La UI del KPI «Vs ayer» **MUST** mostrar el **porcentaje** existente (`pct_vs_ayer`) y, en la misma tarjeta, el **monto de la diferencia** en moneda local formateada (es-AR), sin sustituir el %.

### REQ-EXEC-TOP10-01 — Top 10 productos

- El payload **MUST** incluir **`top_productos`**: arreglo ordenado descendente (máximo 10 ítems).
- Cada ítem **MUST** incluir: `id_art` (int), `codigo_articulo` (string), `descripcion` (string), `unidades` (número, signo FA/NC), `importe_neto` (número, 2 decimales).
- Criterio de orden configurable (**v1+**): por **`importe_neto`** (defecto) o por **`unidades`**, con desempate por la otra métrica; mismos filtros que «Unidades vendidas» del día (`Fecha` comprobante, `Anulado`, `TipoComp` en stock, tipos FA/NC, y sucursal si aplica).
- Si no hay renglones elegibles, el arreglo **MUST** ser `[]`.

### REQ-EXEC-TOP10-02 — Metadatos de criterio

- El objeto **`meta`** del payload **SHOULD** incluir `top_productos_criterio` con valor literal `importe_neto_linea` para trazabilidad de definición de importe por renglón.
- **`meta`** **MUST** exponer `top_productos_orden` (`importe_neto` | `unidades`) y **`meta.cod_sucursal_filtro`** (int o null) coherente con los filtros aplicados.

### REQ-EXEC-TOP10-03 — UI responsive

- La sección Top 10 **MUST** ser usable en viewport móvil: tabla con scroll horizontal opcional **o** apilado de filas tipo tarjeta; **MUST** reutilizar tokens visuales del panel (slate/sky, bordes, tipografía del resto de `executive_summary`).

### REQ-EXEC-SUC-01 — Filtro por sucursal

- La API **MUST** aceptar query opcional **`sucursal`** (id numérico alineado a `cuentacliente.CodSucursal` / `id_sucursal` en listado); vacío o equivalente «todas» = sin filtro.
- Con sucursal informada, **todos** los agregados del payload (KPIs, series, split mayorista/salón, Top 10) **MUST** limitarse a esa sucursal.
- El payload **MUST** incluir **`sucursales_disponibles`** (lista `{ id_sucursal, nombre_sucursal }` desde MySQL `sucursales` no anuladas) para armar el selector en UI.

### REQ-EXEC-API-01 — Parámetros de consulta

- **`GET /api/reports/executive-summary/`** **MUST** aceptar: `fecha` (yyyy-MM-dd, opcional), `sucursal` (opcional), `top_orden` = `importe_neto` | `unidades` (opcional).

### REQ-EXEC-PV-01 — Clasificación PV en PostgreSQL

- El modelo **`PuntoVentaCanalEjecutivo`** **MUST** persistir en PostgreSQL (Synap), no en MySQL legacy.
- La migración **`reports.0031_add_puntoventacanalejecutivo`** **MUST** existir en el repo; el comando de arranque **`fix_reports_migrations`** **MUST NOT** eliminar archivos `0030_*` ni `0031_*` oficiales (prefijos válidos acordes a la última migración publicada de `reports`).

### REQ-EXEC-MARG-01 — Definición de margen bruto (día)

- El payload **MUST** incluir **`margen_bruto`** con **`venta_neta_lineas`**, **`costo_neto_lineas`**, **`margen_absoluto`**, **`pct_sobre_venta_lineas`** (`null` si venta de líneas es 0), calculados desde **`stock.PrecioNetoxR`** y **`stock.PrecioCostoxR`** con el mismo signo FA/NC y los mismos filtros de renglón que **`top_productos`** / unidades del día.
- Para esta versión el costo **MUST** ser el del renglón de comprobante (**`PrecioCostoxR`**), no el **`articulo.PrecioCosto`** actual.

### REQ-EXEC-MARG-02 — Desglose por rubro

- El payload **MUST** incluir **`margen_por_rubro`**: lista ordenada por **`venta_neta`** descendente; ítems con `codigo_rubro`, `nombre_rubro`, `venta_neta`, `costo_neto`, `margen_absoluto`, `pct_sobre_venta` (sentinela y nombre «Sin clasificar» cuando no hay vínculo a **`rubro`**).

### REQ-EXEC-MARG-03 — Desglose por subrubro

- El payload **MUST** incluir **`margen_por_subrubro`**: lista ordenada por **`venta_neta`** descendente; ítems con identificadores y nombres de rubro/subrubro y las mismas métricas numéricas (sentinela «Sin clasificar» cuando aplique).

### REQ-EXEC-MARG-04 — Paridad de filtros

- Con **`sucursal`** informada, los agregados de margen **MUST** usar la misma ventana que KPIs, series, split y Top 10.

### REQ-EXEC-MARG-05 — Metadatos de rentabilidad

- **`meta`** **MUST** incluir **`margen_costo_criterio`** = `precio_costoxr_linea` y **`margen_venta_criterio`** = `precio_netoxr_linea`.
- **`meta.definicion`** **SHOULD** reflejar el contrato extendido (p. ej. **`executive-sales-v2`**) cuando el payload incluya rentabilidad.

### REQ-EXEC-MARG-06 — Conciliación con ventas netas KPI

- **`kpis.ventas_netas_dia`** ( **`cuentacliente.SubtotalDesc`** ) puede **no** coincidir con **`margen_bruto.venta_neta_lineas`**; el % de margen mostrado en el bloque rentabilidad **MUST** basarse en **venta de líneas** del universo `stock` definido. La UI o documentación **MUST** comunicar esta diferencia de criterio.

### REQ-EXEC-MARG-07 — UI rentabilidad

- El panel **MUST** mostrar en español el margen del día y desgloses por rubro y subrubro, con formato coherente con **`FUENTE_VERDAD_UI_REPORTES_MPR.md`** y el resto de **`executive_summary`**.

## Escenarios

1. **Dado** hoy con ventas y ayer con ventas positivas, **cuando** se carga el panel, **entonces** el KPI «Vs ayer» muestra % y diferencia en $ coherente con `ventas_netas_dia` y `ventas_ayer_monto`.
2. **Dado** ayer con neto 0, **cuando** se muestra el %, **entonces** la UI mantiene política actual (N/D en %) y el gap en $ sigue mostrando el neto de hoy si aplica.
3. **Dado** ventas con renglones en `stock`, **cuando** se consulta Top 10 con `top_orden=importe_neto`, **entonces** el orden coincide con el criterio por importe y no más de 10 filas.
4. **Dado** el mismo día, **cuando** se filtra por `sucursal`, **entonces** los totales y el Top 10 reflejan solo movimientos de esa sucursal.
5. **Dado** renglones `stock` con costo en el día, **cuando** se carga el panel, **entonces** `margen_bruto` y los totales implícitos en `margen_por_rubro` / `margen_por_subrubro` son coherentes con las sumas de líneas (salvo bucket «Sin clasificar»).
6. **Dado** artículos sin rubro o subrubro enlazado, **cuando** se agrupa rentabilidad, **entonces** la API responde sin error y etiqueta «Sin clasificar» donde corresponda.
7. **Dado** filtro `sucursal`, **cuando** se comparan rentabilidad y Top 10, **entonces** ambos usan el mismo subconjunto de comprobantes del día.

## Planificación (cambio activo)

Delta y tareas: **`openspec/changes/resumen-gerencial-margen-bruto/`** (modo híbrido OpenSpec + Engram hasta implementación y archivo).
