# Delta para reports-executive-dashboard

## MODIFIED Requirements

### Requirement: REQ-ED-FILT-01 — Parámetros de consulta comunes

| Parámetro | Formato | Default | Uso |
|-----------|---------|---------|-----|
| `fecha_inicio` | `yyyy-MM-dd` | fecha local (hoy) | Inicio período agregados |
| `fecha_fin` | `yyyy-MM-dd` | fecha local (hoy) | Fin período agregados |
| `fecha` | `yyyy-MM-dd` | — | Atajo legacy: un solo día (`fecha_inicio` = `fecha_fin` = `fecha`) |
| `sucursal` | **lista de int o vacío** | sin filtro | `CodSucursal` en tablas de comprobante |
| **`punto_venta`** | **lista de int o vacío** | sin filtro | `id_pv` en `cuentacliente` / `comp_ped` |
| `limit` | int 1–500 | 100 | Solo endpoints P1 con filas |
| `offset` | int ≥ 0 | 0 | Solo endpoints P1 |

- **`sucursal` ahora acepta múltiples valores** (lista de enteros) además del valor escalar legacy `todas`.
- **`punto_venta` es nuevo** (lista de enteros).
- Lista vacía o ausente **MUST** interpretarse como "todas las sucursales" / "todos los PV".
- Ambos filtros presentes **MUST** aplicarse en conjunción (AND).
- Si `fecha_inicio` > `fecha_fin`, la API **MUST** responder **400**.
- Fechas inválidas **MUST** ignorarse con fallback al default.

(Previously: `sucursal` era un escalar o `todas`; no existía `punto_venta`)

#### Escenario: Filtro sucursal como lista multiselección

- DADO `sucursal=[2, 5]` en el query
- CUANDO se ejecuta cualquier endpoint del dashboard
- ENTONCES los agregados incluyen solo comprobantes con `CodSucursal` en (2, 5)

#### Escenario: Filtro PV multiselección

- DADO `punto_venta=[10, 11]`
- CUANDO se ejecuta el endpoint
- ENTONCES los agregados incluyen solo comprobantes con `id_pv` en (10, 11)

#### Escenario: Ambos filtros en AND

- DADO `sucursal=[2]` y `punto_venta=[10]`
- CUANDO se ejecuta el endpoint
- ENTONCES solo se incluyen comprobantes con `CodSucursal=2` **Y** `id_pv=10`

#### Escenario: Compatibilidad escalar legacy en sucursal

- DADO `sucursal=2` (escalar, no lista)
- CUANDO se normaliza el parámetro
- ENTONCES el sistema lo trata internamente como `[2]`

---

### Requirement: REQ-ED-META-01 — Metadatos obligatorios

Toda respuesta **MUST** incluir objeto **`meta`** con al menos:
- `definicion`: literal `executive-dashboard-v1`
- `base_empresa`: string usado en la consulta
- `fecha_referencia`: `yyyy-MM-dd` (derivada de `fecha_fin`)
- `periodo`: `{ "inicio": "yyyy-MM-dd", "fin": "yyyy-MM-dd" }`
- `cod_sucursal_filtro`: **lista de int o `null`** (era int o null escalar)
- **`punto_venta_filtros`: lista de int o `null`** (nuevo)
- `notas_semanticas`: arreglo de strings

(Previously: `cod_sucursal_filtro` era escalar; no existía `punto_venta_filtros`)

#### Escenario: Metadatos reflejan listas de filtros

- DADO `sucursal=[2, 5]` y `punto_venta=[10]`
- CUANDO se genera la respuesta
- ENTONCES `meta.cod_sucursal_filtro = [2, 5]`
- Y `meta.punto_venta_filtros = [10]`

#### Escenario: Sin filtros devuelve null

- DADO `sucursal=[]` y `punto_venta=[]`
- CUANDO se genera la respuesta
- ENTONCES `meta.cod_sucursal_filtro = null`
- Y `meta.punto_venta_filtros = null`

---

## ADDED Requirements

### Requirement: UI Command Center con selectores múltiples de sucursal y PV

La pantalla `/reports/dashboard/command-center-gerencial/` **MUST** ofrecer selectores múltiples para sucursales y PV.

- Las opciones **MUST** cargarse desde `GET /api/reports/filters/`.
- Los tags seleccionados **MUST** sincronizarse con query params `sucursal` y `punto_venta` al orquestador.
- El selector PV **SHOULD** estar habilitado de forma independiente (sin cascada obligatoria desde sucursal en v1).

(Previously: Solo existía selector escalar de sucursal con opción "todas")

#### Escenario: Selectores cargados en UI

- DADO un usuario abre `/reports/dashboard/command-center-gerencial/`
- CUANDO la página se carga
- ENTONCES aparecen selectores múltiples "Sucursales" y "Puntos de venta"
- Y las opciones se cargan desde `/api/reports/filters/?report_slug=command-center-gerencial`

---

### Requirement: Cascada sucursal a PV opcional en UI

La UI **MAY** implementar cascada donde al seleccionar una sucursal, el selector PV muestre solo los PV de esa sucursal.

- Si no hay sucursal seleccionada, el selector PV **MAY** mostrar todos los PV o deshabilitarse (decisión UX).
- Si hay múltiples sucursales seleccionadas, el selector PV **SHOULD** mostrar la unión de PV de esas sucursales.

(Previously: No aplicaba; es una nueva funcionalidad opcional)

#### Escenario: Cascada sucursal a PV en UI

- DADO el usuario selecciona sucursal 2
- CUANDO se carga el selector PV
- ENTONCES muestra solo los PV de sucursal 2
- Y el usuario puede filtrar por PV dentro de esa sucursal

---

## Implementation Constraints

- Helper `_parse_sucursales_pv` aplicable a todos los endpoints del dashboard.
- SQL con placeholders `%s` y parámetros vinculados.
- Normalización con `core.utils.administranet_types`.
- UI canónica de reportes (`docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md`).
- Compatibilidad con valor escalar legacy en `sucursal` (convertir a lista internamente).
- Textos en español; sin diálogos nativos.
