# Delta spec — Margen ejecutivo costo Display/Bulto

**Cambio:** `margen-ejecutivo-costo-display-bulto`  
**Base:** `openspec/specs/reports-ejecutivo-ventas/spec.md`

## MODIFIED Requirements

### REQ-EXEC-MARG-01 — Definición de margen bruto (día)

- El payload **MUST** incluir **`margen_bruto`** con **`venta_neta_lineas`**, **`costo_neto_lineas`**, **`margen_absoluto`**, **`pct_sobre_venta_lineas`** (`null` si venta de líneas es 0), calculados con el mismo signo FA/NC y los mismos filtros de renglón que **`top_productos`** / unidades del día.
- **`venta_neta_lineas`** **MUST** ser la suma firmada de **`stock.PrecioNetoxR`** (criterio vigente, sin cambio).
- **`costo_neto_lineas`** **MUST** ser la suma firmada, por renglón elegible, de **`costo_unitario_efectivo × COALESCE(stock.Cantidad, 0)`**, donde **`stock.Cantidad`** está en **unidad base** y **`costo_unitario_efectivo`** se obtiene según **REQ-EXEC-MARG-08**.
- El sistema **MUST NOT** usar **`articulo.PrecioCosto`** actual ni **`SUM(PrecioCostoxR)`** crudo como costo agregado del panel.
- La misma expresión de costo normalizado **MUST** alimentar **`margen_por_rubro`** y **`margen_por_subrubro`**.

(Previously: costo agregado = suma directa de `PrecioCostoxR` del renglón de comprobante.)

#### Scenario: Renglón Display con empaque múltiple

- GIVEN un renglón `stock` del día con `tipo_unidad='Display'`, `cantidad_unidad_display > 1` y venta coherente con empaque
- WHEN se consulta `GET /api/reports/executive-summary/`
- THEN `margen_bruto.costo_neto_lineas` refleja costo en unidad base (no el subtotal crudo de `PrecioCostoxR` si este quedó en unidad comercial distinta a la venta)
- AND `margen_bruto.venta_neta_lineas` sigue basado en `PrecioNetoxR`

#### Scenario: Renglón Bulto

- GIVEN un renglón con `tipo_unidad='Bulto'` y `multiplicador_comp > 1`
- WHEN se agrega costo al margen del día
- THEN el costo del renglón usa factor **`multiplicador_comp`** según REQ-EXEC-MARG-08
- AND no se aplica doble escala sobre `cantidad_dividir` ya persistida en `stock.Cantidad`

#### Scenario: Regresión Unidad

- GIVEN renglones con `tipo_unidad='Unidad'` (o sin embalaje) y costo persistido coherente
- WHEN se consulta el panel antes y después del cambio
- THEN `margen_bruto.costo_neto_lineas` difiere en menos del umbral acordado en piloto respecto al criterio legacy `PrecioCostoxR`

### REQ-EXEC-MARG-05 — Metadatos de rentabilidad

- **`meta`** **MUST** incluir **`margen_costo_criterio`** = `costo_unitario_efectivo_x_cantidad_base` y **`margen_venta_criterio`** = `precio_netoxr_linea`.
- **`meta.definicion`** **SHOULD** reflejar el contrato extendido cuando el payload incluya rentabilidad.
- La documentación operativa **SHOULD** indicar que totales históricos del panel bajo `precio_costoxr_linea` pueden no ser comparables línea a línea tras el cambio.

(Previously: `margen_costo_criterio` = `precio_costoxr_linea`.)

#### Scenario: Trazabilidad del criterio de costo

- GIVEN una respuesta con bloque `margen_bruto`
- WHEN el cliente lee `meta`
- THEN `meta.margen_costo_criterio` es `costo_unitario_efectivo_x_cantidad_base`
- AND `meta.margen_venta_criterio` permanece `precio_netoxr_linea`

## ADDED Requirements

### REQ-EXEC-MARG-08 — Normalización costo unitario (Display/Bulto)

- Para cada renglón elegible, el sistema **MUST** calcular **`costo_unitario_efectivo`** a partir del costo persistido en el renglón (`PrecioCostoxU`, `PrecioCostoxR`, `cantidad_dividir`, `cantidad_unidad_display`) y aplicar el factor de unidad comercial según paridad VB6 **`Calculo_Costo_Display_Bulto`**:
  - **`tipo_unidad` = `Unidad` o `Display`:** factor de costo unitario = **1** (salvo excepción TPV).
  - **`tipo_unidad` = `Bulto`:** factor = **`COALESCE(stock.multiplicador_comp, 1)`**.
  - **Excepción TPV:** si `tipo_unidad='Display'` y el artículo tiene **`articulo.precio_unidad='Unidad'`**, el factor **MUST** tratarse como **1** (equivalente a `cantidad_dividir=1` en persistencia).
- Valores nulos o ≤ 0 en **`cantidad_dividir`**, **`cantidad_unidad_display`** o **`multiplicador_comp`** **MUST** tratarse como **1** (`COALESCE`) salvo que la regla de Bulto exija explícitamente `multiplicador_comp`.
- El costo agregado firmado del renglón **MUST** ser **`costo_unitario_efectivo × stock.Cantidad`** con el mismo `CASE` FA/NC que la venta.

#### Scenario: Excepción TPV Display con precio por Unidad

- GIVEN un renglón TPV con `tipo_unidad='Display'` y `articulo.precio_unidad='Unidad'`
- WHEN se calcula costo para margen
- THEN el factor de normalización es 1
- AND el costo agregado no se multiplica por `cantidad_unidad_display` ni por `cantidad_dividir` distinto de 1

#### Scenario: Campos legacy incompletos

- GIVEN un renglón con `cantidad_dividir` NULL o 0 y `tipo_unidad='Unidad'`
- WHEN se normaliza costo
- THEN el factor aplicado es 1
- AND la API responde sin error

#### Scenario: Paridad signo FA/NC

- GIVEN facturas y notas de crédito del mismo día con renglones Display
- WHEN se suma costo normalizado
- THEN facturas suman y notas de crédito restan, igual que `PrecioNetoxR`

## Escenarios globales (extensión)

8. **Dado** renglones Display con margen negativo espurio bajo `PrecioCostoxR` crudo, **cuando** se aplica normalización, **entonces** `margen_bruto.margen_absoluto` mejora coherencia con venta en unidad comercial sin alterar `venta_neta_lineas`.
9. **Dado** filtro `sucursal`, **cuando** se comparan rentabilidad y Top 10, **entonces** ambos usan el mismo subconjunto; el costo normalizado respeta ese filtro.
