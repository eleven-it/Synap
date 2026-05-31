# Delta spec — Margen ejecutivo paridad rentabilidad AdministraNET

**Cambio:** `margen-ejecutivo-costo-display-bulto`  
**Base:** `openspec/specs/reports-ejecutivo-ventas/spec.md`

## MODIFIED Requirements

### REQ-EXEC-MARG-01 — Definición de margen bruto (día)

- El payload **MUST** incluir **`margen_bruto`** con **`venta_neta_lineas`**, **`costo_neto_lineas`**, **`margen_absoluto`**, **`pct_sobre_venta_lineas`** (`null` si venta de líneas es 0), calculados con el mismo signo FA/NC y los mismos filtros de renglón que **`top_productos`** / unidades del día.
- **`venta_neta_lineas`** **MUST** ser la suma firmada de **`stock.PrecioNetoxR`** (criterio vigente, sin cambio).
- **`costo_neto_lineas`** **MUST** ser la suma firmada de **`stock.PrecioCostoxR`** por renglón elegible, con el mismo `CASE` FA/NC que la venta neta del panel (**paridad informe rentabilidad AdministraNET** / vista `venta_rentabilidad_resumen`).
- El sistema **MUST NOT** re-escalar costo por `tipo_unidad`, `cantidad_dividir`, `multiplicador_comp` ni `Calculo_Costo_Display_Bulto` en el agregado de margen del panel.
- El sistema **MUST NOT** usar **`articulo.PrecioCosto`** actual como costo agregado.
- La misma expresión de costo **MUST** alimentar **`margen_por_rubro`** y **`margen_por_subrubro`**.

#### Scenario: Renglón Display con empaque múltiple

- GIVEN un renglón `stock` del día con `tipo_unidad='Display'` y `PrecioCostoxR` persistido en facturación
- WHEN se consulta `GET /api/reports/executive-summary/`
- THEN `margen_bruto.costo_neto_lineas` incluye `PrecioCostoxR` del renglón (sin divisor adicional)
- AND el resultado es comparable al informe Crystal rentabilidad AdministraNET del mismo periodo

#### Scenario: Renglón Bulto

- GIVEN un renglón con `tipo_unidad='Bulto'`
- WHEN se agrega costo al margen del día
- THEN el costo del renglón es `PrecioCostoxR` firmado
- AND no se divide por `multiplicador_comp` ni `cantidad_dividir`

#### Scenario: Coherencia venta vs costo

- GIVEN facturas y notas de crédito del mismo día
- WHEN se calcula margen
- THEN venta y costo usan signo FA/NC sobre `PrecioNetoxR` y `PrecioCostoxR` respectivamente

### REQ-EXEC-MARG-05 — Metadatos de rentabilidad

- **`meta`** **MUST** incluir **`margen_costo_criterio`** = `precio_costoxr_linea` y **`margen_venta_criterio`** = `precio_netoxr_linea`.
- **`meta`** **MUST NOT** incluir `utiliza_embalaje_display_bulto` (el criterio de costo no depende de config embalaje).
- **`meta.nota_margen_costo_historico`** **SHOULD** documentar la alineación con informe rentabilidad AdministraNET.

#### Scenario: Trazabilidad del criterio de costo

- GIVEN una respuesta con bloque `margen_bruto`
- WHEN el cliente lee `meta`
- THEN `meta.margen_costo_criterio` es `precio_costoxr_linea`

## REMOVED Requirements

### REQ-EXEC-MARG-08 — Normalización costo unitario (Display/Bulto)

**Razón:** descartada tras análisis VB6 — el informe de rentabilidad y las vistas MySQL asociadas no aplican escala Display/Bulto; usar `PrecioCostoxR` crudo alinea Synap con AdministraNET.

## Escenarios globales (extensión)

8. **Dado** empresa con embalaje Display/Bulto activo, **cuando** se compara margen del panel con informe Crystal rentabilidad, **entonces** `costo_neto_lineas` coincide con `SUM(PrecioCostoxR)` firmado en el mismo universo de renglones.
9. **Dado** filtro `sucursal`, **cuando** se comparan rentabilidad y Top 10, **entonces** ambos usan el mismo subconjunto.
