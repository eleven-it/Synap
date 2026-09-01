# Especificación: Filtros transversales Sucursal y Punto de Venta en informes de ventas

**Capability:** `reports-filtros-sucursal-punto-venta`  
**Origen:** change `filtros-pv-sucursal-ventas`  
**Alcance:** Contrato transversal para filtros de sucursal y PV en informes de ventas de `/reports/`

## Purpose

Contrato centralizado que define cómo los informes de ventas reciben, validan, aplican y muestran filtros de sucursal y punto de venta, garantizando consistencia en payload, SQL, UI includes y comportamiento por defecto (sin selección = todas).

## Requirements

### REQ-FSPV-001: Formato de payload para filtros sucursal y PV

El sistema **MUST** aceptar en `filters` del payload de informes de ventas los campos **`sucursales`** (lista de enteros con `CodSucursal`) y **`punto_venta`** (lista de enteros con `id_pv` de tabla MySQL `punto_venta`).

- Lista vacía o ausente **MUST** interpretarse como "todas las sucursales" o "todos los PV".
- Ambos filtros presentes **MUST** aplicarse en conjunción (AND): sólo comprobantes que cumplan ambas condiciones.
- Valores no numéricos **MUST** descartarse sin abortar la consulta.
- Normalización **MUST** usar `core.utils.administranet_types.to_int_or_none`.

#### Escenario: Sin filtros seleccionados devuelve el total histórico

- DADO un informe de ventas sin `sucursales` ni `punto_venta` en `filters`
- CUANDO se ejecuta la consulta
- ENTONCES el resultado incluye todas las sucursales y todos los PV
- Y los totales coinciden con el comportamiento actual del informe

#### Escenario: Filtro solo por sucursal

- DADO `filters.sucursales = [2, 5]` y `filters.punto_venta = []`
- CUANDO se ejecuta la consulta SQL sobre `cuentacliente` o `comp_ped`
- ENTONCES la cláusula WHERE incluye `CodSucursal IN (2, 5)`
- Y no hay restricción sobre `id_pv`

#### Escenario: Filtro solo por PV

- DADO `filters.sucursales = []` y `filters.punto_venta = [10, 11]`
- CUANDO se ejecuta la consulta SQL
- ENTONCES la cláusula WHERE incluye `id_pv IN (10, 11)`
- Y no hay restricción sobre `CodSucursal`

#### Escenario: Ambos filtros en conjunción AND

- DADO `filters.sucursales = [2]` y `filters.punto_venta = [10, 11]`
- CUANDO se ejecuta la consulta
- ENTONCES la cláusula WHERE incluye `CodSucursal = 2 AND id_pv IN (10, 11)`

#### Escenario: Valor no numérico se descarta

- DADO `filters.punto_venta = [10, 'DROP TABLE', 11]`
- CUANDO se normaliza con `to_int_or_none`
- ENTONCES el sistema descarta 'DROP TABLE'
- Y aplica `id_pv IN (10, 11)` con parámetros vinculados

---

### REQ-FSPV-002: Helper de normalización compartido

El sistema **MUST** proveer una función helper `_parse_sucursales_pv(filters: dict) -> tuple[list[int], list[int]]` que normalice ambas listas y las devuelva limpias para construcción SQL.

- La función **MUST** vivir en módulo compartido (ej. `reports/services/filter_utils.py`).
- **MUST** descartar valores `None` tras `to_int_or_none`.
- **MUST** devolver listas vacías cuando el campo no existe o está vacío.

#### Escenario: Helper normaliza y limpia valores

- DADO `filters = {"sucursales": [2, "x", 5], "punto_venta": None}`
- CUANDO se llama `_parse_sucursales_pv(filters)`
- ENTONCES el resultado es `([2, 5], [])`

---

### REQ-FSPV-003: SQL con placeholders y parámetros vinculados

El sistema **MUST** construir cláusulas SQL con placeholders `%s` para cada valor en las listas normalizadas, **nunca** concatenando IDs directamente en la sentencia.

- Para listas vacías, **MUST** omitir la cláusula correspondiente (no agregar `1=1` innecesario).
- Las tablas objetivo **MUST** ser `cuentacliente` (columna `CodSucursal`, `id_pv`) o `comp_ped` (columnas `CodSucursal`, `id_pv`) según el informe.

#### Escenario: Construcción SQL segura con placeholders

- DADO `sucursales=[2, 5]` y `punto_venta=[10]`
- CUANDO se construye la cláusula WHERE
- ENTONCES se genera `CodSucursal IN (%s, %s) AND id_pv = %s`
- Y los parámetros vinculados son `[2, 5, 10]`

---

### REQ-FSPV-004: UI includes canónicos para filtros de sucursal y PV

El sistema **MUST** ofrecer dos includes reutilizables en `reports/templates/reports/includes/`:

- **`filters_bo.html`**: include extendido para informes de familia BO (VO, VPV, VPA, VMSA, BOM) con whitelist de slugs de ventas para mostrar bloque PV.
- **`filters_simple.html`**: include simple sin bloque PV visible.

Cada include **MUST**:
- Cargar opciones de sucursales y PV mediante `GET /api/reports/filters/?report_slug={slug}`.
- Usar tags `<select multiple>` para selección múltiple con Alpine.js.
- Sincronizar selecciones con payload `filters` del runner.
- Mostrar etiquetas en español: "Sucursales", "Puntos de venta".

#### Escenario: Include BO muestra PV para slugs de ventas

- DADO un informe con slug en whitelist de ventas (ej. `ventas-por-vendedor`)
- CUANDO se renderiza `filters_bo.html` con `report_slug`
- ENTONCES el bloque `<div id="punto_venta">` aparece en el DOM
- Y el selector múltiple carga opciones desde `/api/reports/filters/`

#### Escenario: Include BO oculta PV para slugs fuera de whitelist

- DADO un informe con slug `bo-stock-facturacion`
- CUANDO se renderiza `filters_bo.html`
- ENTONCES el bloque `<div id="punto_venta">` **MUST NOT** aparecer en el DOM

#### Escenario: Include simple nunca muestra PV

- DADO cualquier informe que use `filters_simple.html`
- CUANDO se renderiza la plantilla
- ENTONCES no existe `<div id="punto_venta">` en el DOM bajo ninguna condición

---

### REQ-FSPV-005: API de opciones de filtros

El sistema **MUST** exponer **`GET /api/reports/filters/?report_slug={slug}`** que devuelva:

```json
{
  "sucursales": [{"id": 1, "nombre": "Casa Central"}, ...],
  "punto_venta": [{"id": 10, "nombre": "PV Mayorista"}, ...]
}
```

- Sucursales: todas las filas activas de `sucursales` (MySQL) con `COALESCE(anulado,'No')='No'`.
- PV: todas las filas activas de `punto_venta` con `anulado='No'`.
- El endpoint **MUST** ser accesible para cualquier usuario autenticado con permiso de reportes.

#### Escenario: API devuelve opciones activas

- DADO existen 3 sucursales activas y 5 PV activos en MySQL
- CUANDO se llama `/api/reports/filters/`
- ENTONCES la respuesta incluye 3 sucursales y 5 PV
- Y ninguna sucursal ni PV anulado aparece

---

### REQ-FSPV-006: Whitelist de slugs de ventas para visibilidad de PV

El sistema **MUST** mantener una whitelist de slugs de informes de ventas donde el filtro PV es relevante y **MUST** mostrarse en la UI.

Whitelist inicial (Oleada 1 y 2):
- `ventas-por-vendedor`
- `ventas-por-articulo`
- `ventas-por-cliente`
- `ventas-marca-superarticulo`
- `ventas-bom-docenas`
- `ventas-mensuales-licenciatarios`
- `clientes-sin-ventas-vendedor`

El sistema **MUST NOT** mostrar PV en:
- `bo-stock-facturacion` (include compartido con inventario)
- `pedidos-pendientes`
- `remitos-no-facturados`
- Informes gerenciales agregados (`resumen-ejecutivo-ventas`, `command-center-gerencial`) donde PV se maneja distinto

#### Escenario: Whitelist controla visibilidad de PV en UI

- DADO un slug en la whitelist
- CUANDO se carga la pantalla del informe
- ENTONCES el filtro PV aparece en la UI
- Y el gate JS permite enviar `filters.punto_venta` al runner

#### Escenario: Slug fuera de whitelist oculta PV

- DADO `bo-stock-facturacion` no está en la whitelist
- CUANDO se carga la pantalla
- ENTONCES el filtro PV no aparece
- Y el runner no recibe `filters.punto_venta` aunque se manipule el DOM

---

### REQ-FSPV-007: Metadatos de filtros aplicados

El sistema **SHOULD** incluir en `meta` del payload de respuesta del informe los campos:

- `sucursales_filtradas`: lista de IDs aplicados o `null` si todas.
- `punto_venta_filtrados`: lista de IDs aplicados o `null` si todos.
- `filtros_aplicados_solo_tramo_anet`: `true` cuando el informe es híbrido y solo el tramo AdministraNET post-cutover aplica los filtros (ej. licenciatarios con seed global).

#### Escenario: Metadatos reflejan filtros aplicados

- DADO `filters.sucursales = [2, 5]` y `filters.punto_venta = []`
- CUANDO se genera la respuesta del informe
- ENTONCES `meta.sucursales_filtradas = [2, 5]`
- Y `meta.punto_venta_filtrados = null`

---

### REQ-FSPV-008: Export Excel aplica los mismos filtros

El sistema **MUST** garantizar que el export Excel de un informe aplique exactamente los mismos filtros de sucursal y PV que la vista en pantalla.

- El endpoint de export **MUST** recibir el mismo payload `filters` que el runner.
- La query SQL del export **MUST** construirse con el mismo helper `_parse_sucursales_pv`.

#### Escenario: Export Excel coherente con pantalla

- DADO un informe con `filters.sucursales = [2]` en pantalla
- CUANDO el usuario descarga Excel
- ENTONCES el archivo Excel contiene solo datos de sucursal 2
- Y no hay filas de otras sucursales

---

### REQ-FSPV-009: Restricciones de uso — informes fuera de alcance

El sistema **MUST NOT** aplicar filtros de sucursal ni PV en los siguientes informes:

- `bo-stock-facturacion`: el include BO es compartido y no debe mostrar PV.
- `pedidos-pendientes`: fuera de alcance explícito.
- `remitos-no-facturados`: fuera de alcance explícito.
- `documento-presupuesto-ventas`: fuera de alcance explícito.
- `evolucion-precios`: fuera de alcance explícito.

El sistema **MUST NOT** crear un tercer include de filtros solo para estos informes excluidos.

#### Escenario: Informe fuera de alcance no muestra ni aplica PV

- DADO el informe `bo-stock-facturacion`
- CUANDO se carga la pantalla
- ENTONCES el filtro PV no aparece en la UI
- Y el runner no recibe ni aplica `filters.punto_venta`

---

### REQ-FSPV-010: Compatibilidad con relay Ventas Netas

El relay **`reports/services/ventas_netas.py`** **MUST** aceptar listas `sucursales` y `punto_venta` en el payload, manteniendo compatibilidad con el parámetro escalar `punto_venta_id` existente.

- Si se recibe `punto_venta_id` (escalar), el sistema **SHOULD** convertirlo internamente a lista `[punto_venta_id]`.
- El relay **MUST** aplicar los filtros en la query SQL con el mismo helper `_parse_sucursales_pv`.

#### Escenario: Relay acepta lista de PV

- DADO una llamada al relay con `{"punto_venta": [10, 11]}`
- CUANDO se ejecuta la consulta
- ENTONCES el SQL incluye `id_pv IN (10, 11)`

#### Escenario: Compatibilidad escalar

- DADO una llamada legacy con `{"punto_venta_id": 10}`
- CUANDO se normaliza el payload
- ENTONCES el sistema lo trata como `{"punto_venta": [10]}`

---

## Implementation Constraints

- Helper `_parse_sucursales_pv` **MUST** vivir en `reports/services/filter_utils.py`.
- Includes UI **MUST** seguir canon visual de reportes (`docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md`).
- Alpine.js **MUST** manejar estado de tags y sincronización con payload.
- Todos los informes **MUST** usar `core.utils.administranet_types` para normalización de IDs.
- SQL **MUST** usar parámetros vinculados (`cursor.execute(sql, params)`).
- Textos al usuario en español; sin `alert`/`confirm` nativos.
