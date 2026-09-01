# Delta para reports-clientes-sin-ventas

## ADDED Requirements

### Requirement: Filtros de sucursal y PV en clientes sin ventas

El sistema **MUST** permitir filtrar el universo de "clientes sin ventas" por sucursal y punto de venta, aplicando los filtros sobre la tabla `cuentacliente` tanto para verificar ausencia de comprobantes en el período como para clasificar clientes según sucursal/PV asignado.

- El payload **MUST** aceptar `filters.sucursales` (lista de enteros) y `filters.punto_venta` (lista de enteros).
- Listas vacías **MUST** interpretarse como "todas las sucursales" / "todos los PV".
- Ambos filtros presentes **MUST** aplicarse en conjunción (AND).
- La SQL de "sin ventas" **MUST** verificar ausencia de comprobantes con `CodSucursal` / `id_pv` dentro del conjunto filtrado.
- La columna "Última compra" **MUST** considerar solo comprobantes históricos que cumplan los filtros de sucursal/PV aplicados.

(Previously: No existía filtro de sucursal ni PV en este informe)

#### Escenario: Cliente sin ventas en sucursal filtrada aparece

- DADO un cliente activo sin comprobantes en sucursal 2 durante el período
- Y `filters.sucursales = [2]`
- CUANDO se ejecuta el informe
- ENTONCES el cliente aparece en "datos"
- Y su "Última compra" muestra la fecha del último comprobante en sucursal 2 o "-" si nunca compró en esa sucursal

#### Escenario: Cliente con ventas solo en otra sucursal aparece como "sin ventas"

- DADO un cliente con comprobantes en sucursal 3 pero no en sucursal 2
- Y `filters.sucursales = [2]`
- CUANDO se ejecuta el informe
- ENTONCES el cliente aparece como "sin ventas" en sucursal 2

#### Escenario: Filtro PV acota el universo de clientes

- DADO `filters.punto_venta = [10]`
- CUANDO se ejecuta el informe
- ENTONCES solo aparecen clientes sin comprobantes con `id_pv = 10` en el período

#### Escenario: Ambos filtros en AND

- DADO `filters.sucursales = [2]` y `filters.punto_venta = [10, 11]`
- CUANDO se ejecuta el informe
- ENTONCES solo aparecen clientes sin ventas en sucursal 2 **Y** PV 10 u 11

#### Escenario: Sin filtros devuelve total histórico

- DADO `filters.sucursales = []` y `filters.punto_venta = []`
- CUANDO se ejecuta el informe
- ENTONCES el resultado incluye todos los clientes sin ventas en cualquier sucursal/PV
- Y los totales coinciden con el comportamiento actual del informe

---

### Requirement: UI con filtros sucursal y PV

La pantalla `/reports/dashboard/clientes-sin-ventas-vendedor/` **MUST** incluir selectores múltiples para sucursales y PV, cargados mediante `GET /api/reports/filters/`.

- El slug `clientes-sin-ventas-vendedor` **MUST** estar en la whitelist de informes de ventas con PV visible.
- El filtro PV **MUST** mostrarse en la UI.
- Los tags seleccionados **MUST** sincronizarse con `filters` en el payload del runner.

(Previously: No existían selectores de sucursal ni PV en la UI)

#### Escenario: Selectores cargados en UI

- DADO un usuario abre `/reports/dashboard/clientes-sin-ventas-vendedor/`
- CUANDO la página se carga
- ENTONCES aparecen selectores múltiples "Sucursales" y "Puntos de venta"
- Y las opciones se cargan desde `/api/reports/filters/?report_slug=clientes-sin-ventas-vendedor`

---

### Requirement: Export Excel con filtros aplicados

El export Excel del informe **MUST** aplicar los mismos filtros de sucursal y PV que la vista en pantalla.

(Previously: No existía filtro, por lo que el export siempre incluía todas las sucursales/PV)

#### Escenario: Excel coherente con pantalla filtrada

- DADO el usuario filtra por sucursal 2 en pantalla
- CUANDO descarga Excel
- ENTONCES el archivo contiene solo clientes sin ventas en sucursal 2
- Y no hay filas de otras sucursales

---

## Implementation Constraints

- Normalización con `core.utils.administranet_types`.
- Helper `_parse_sucursales_pv` desde `reports/services/filter_utils.py`.
- SQL con placeholders `%s` y parámetros vinculados.
- UI canónica de reportes (`docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md`).
- Textos en español; sin diálogos nativos.
