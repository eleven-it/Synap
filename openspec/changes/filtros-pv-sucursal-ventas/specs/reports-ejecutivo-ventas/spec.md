# Delta para reports-ejecutivo-ventas

## MODIFIED Requirements

### Requirement: REQ-EXEC-PV-01 — Clasificación PV en PostgreSQL

El modelo **`PuntoVentaCanalEjecutivo`** **MUST** persistir en PostgreSQL (Synap), no en MySQL legacy. La migración **`reports.0031_add_puntoventacanalejecutivo`** **MUST** existir en el repo; el comando de arranque **`fix_reports_migrations`** **MUST NOT** eliminar archivos `0030_*` ni `0031_*` oficiales.

**El panel ejecutivo ventas **MUST** clasificar ventas por PV dentro del alcance de sucursales, usando la tabla `PuntoVentaCanalEjecutivo` para agrupar PV en canales (mayorista/salón) cuando la sucursal filtrada tiene múltiples PV clasificados.**

(Previously: No contemplaba agrupación de PV dentro de sucursales filtradas)

#### Escenario: Ventas por PV clasificado en sucursal filtrada

- DADO `sucursal=2` en el query
- Y la sucursal 2 tiene PV 10 (mayorista) y PV 11 (salón) en `PuntoVentaCanalEjecutivo`
- CUANDO se carga el panel
- ENTONCES el split mayorista/salón refleja la clasificación de PV 10 y 11
- Y los KPIs generales incluyen la suma de ambos PV

#### Escenario: Sucursal con un solo PV no afecta clasificación

- DADO `sucursal=3` con un único PV 20 clasificado como mayorista
- CUANDO se carga el panel
- ENTONCES el split mayorista refleja toda la venta de sucursal 3
- Y salón es 0 (o no se muestra si no hay clasificación dual)

#### Escenario: Sin sucursal filtrada usa todas las clasificaciones

- DADO `sucursal=` (sin filtro)
- CUANDO se carga el panel
- ENTONCES el split mayorista/salón considera todos los PV clasificados en cualquier sucursal

---

## ADDED Requirements

### Requirement: Filtro opcional por lista de PV en panel ejecutivo ventas

El panel **`resumen-ejecutivo-ventas`** (`GET /api/reports/executive-summary/`) **MUST** aceptar query opcional `punto_venta` (lista de enteros con `id_pv`) además del filtro `sucursal` existente.

- Lista vacía o ausente **MUST** interpretarse como "todos los PV".
- Cuando se informa `punto_venta`, **todos** los agregados del payload (KPIs, series, split mayorista/salón, Top 10, margen) **MUST** limitarse a esos PV.
- `sucursal` y `punto_venta` presentes **MUST** aplicarse en conjunción (AND).
- El payload **MUST** incluir `meta.punto_venta_filtrados` (lista de IDs aplicados o `null` si todos).

(Previously: Solo existía filtro `sucursal` escalar, sin capacidad de filtrar por lista de PV)

#### Escenario: Filtro solo por lista de PV

- DADO `punto_venta=[10, 11]` y sin `sucursal`
- CUANDO se carga el panel
- ENTONCES los KPIs y Top 10 incluyen solo ventas con `id_pv` en (10, 11)

#### Escenario: Filtro sucursal y PV en conjunción

- DADO `sucursal=2` y `punto_venta=[10]`
- CUANDO se carga el panel
- ENTONCES los agregados incluyen solo ventas con `CodSucursal=2` **Y** `id_pv=10`
- Y `meta.punto_venta_filtrados = [10]`

#### Escenario: Sin filtro PV mantiene comportamiento actual

- DADO `punto_venta=[]` (o ausente)
- CUANDO se carga el panel
- ENTONCES se incluyen todos los PV de la sucursal filtrada (o todas si no hay `sucursal`)
- Y `meta.punto_venta_filtrados = null`

---

### Requirement: UI panel ejecutivo con selector PV opcional

La pantalla del panel ejecutivo **MAY** ofrecer un selector múltiple de PV en cascada con la selección de sucursal, cargando opciones según `sucursal_id` seleccionada.

- El selector PV **SHOULD** deshabilitarse si no hay sucursal seleccionada (comportamiento UX a validar con producto).
- Los tags PV seleccionados **MUST** sincronizarse con query param `punto_venta` al endpoint.

(Previously: No existía selector PV en el panel ejecutivo)

#### Escenario: Selector PV habilitado tras seleccionar sucursal

- DADO el usuario selecciona sucursal 2
- CUANDO el selector PV se renderiza
- ENTONCES muestra solo los PV de sucursal 2
- Y el usuario puede seleccionar uno o más PV para filtrar

---

## Implementation Constraints

- Normalización de listas con `core.utils.administranet_types`.
- Helper `_parse_sucursales_pv` aplicable al panel ejecutivo para coherencia.
- SQL con placeholders `%s`.
- UI canónica de reportes (`docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md`).
- Textos en español.
