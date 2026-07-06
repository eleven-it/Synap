# Spec — Filtros inventario tabla (Stock)

**Capability:** `stock-inventario-filtros`  
**Change:** `stock-inventario-tabla-mpr`  
**Pantalla:** `/stock/inventario/`

---

## Purpose

Filtros de la consulta **Inventario por etapa MPR**: selector **multi-marca con etiquetas** (mismo componente que reportes) y **buscador predictivo** sobre el universo completo de datos (sin límite de página), integrados en `/stock/inventario/`.

---

## Requirements

### REQ-FIL-01 — Barra de filtros

The pantalla MUST mostrar una barra de filtros sticky sobre la tabla con:

- Selector **multi-marca** con chips (tags)
- Campo de **búsqueda predictiva** de artículo
- Toggle **Unidades / Docenas** (spec `stock-inventario-tabla` REQ-INV-09)
- Control **Ver todos los artículos** (spec `stock-inventario-tabla` REQ-INV-08)
- Acción **Limpiar** que restablece filtros (excepto presentación si producto decide conservarla)

### REQ-FIL-02 — Filtro multi-marca (tags)

The system MUST usar el mismo patrón de UI que reportes:

- Plantilla de referencia: `reports/templates/reports/includes/filters_stock_existencias.html` (bloque Marcas)
- JS: `reports/static/reports/js/tags_filter.mjs` → `initializeTagsFilter`

Estructura MUST incluir `<select multiple hidden>` + contenedor `*_tags_container` con chips y dropdown.

Query param MUST ser `marcas_incluidos` repetido o lista separada por comas (ej. `?marcas_incluidos=3&marcas_incluidos=7`).

Vacío = **todas las marcas**.

Filtrado MUST aplicarse en servidor: `articulo.CodigoMarca IN (...)`.

Al aplicar filtros, MUST preservarse en URL `incluir_ceros`, `presentacion`, `page`, `q`, `id_articulo`.

### REQ-FIL-03 — Búsqueda predictiva (API)

The system MUST exponer `GET /stock/api/inventario/articulos/` con permiso `stock.consultas`.

Parámetros:

| Param | Descripción |
|-------|-------------|
| `q` | Texto ≥ 2 caracteres |
| `limit` | Default 15; máx. 50 sugerencias en dropdown |
| `marcas_incluidos` | Lista de `CodMarca`; opcional |
| `incluir_ceros` | `0`/`1`; mismo criterio que tabla |

**Alcance:** la API MUST buscar en el **universo completo** de artículos que cumplen `marcas_incluidos` e `incluir_ceros`, **sin** restricción por `page` ni `offset` de la tabla.

Respuesta JSON: array `articulos` con `id_articulo`, `codigo_compuesto`, `id_manual`, `cod_art_prov`, `nombre`, `marca_nombre`.

Criterios LIKE: `id_manual`, `CodArtProv`, `NombreArticulo`, `NroCodBarra`, `NroCodBarraF`.

Con `q` < 2 caracteres: `articulos: []`.

### REQ-FIL-04 — Búsqueda predictiva (UI)

Combobox MUST seguir accesibilidad de `mpr/reportes/_busqueda_tabla_articulos.html` (teclado, debounce ~300 ms).

Al seleccionar sugerencia, MUST navegar a `?id_articulo={IDArt}` preservando `marcas_incluidos`, `incluir_ceros`, `presentacion`.

La búsqueda MUST encontrar artículos en **cualquier página** del resultado paginado (ej. artículo en fila 200 con `page=1` activo).

### REQ-FIL-05 — Filtro por id_articulo

`id_articulo` MUST mostrar **una fila** para ese artículo, aunque consolidado sea 0.

MUST ignorar paginación (página 1, una fila).

Si no existe: empty state sin error 500.

### REQ-FIL-06 — Filtro por q (tabla)

`q` (≥ 2 caracteres) MUST filtrar la tabla en servidor sobre el **universo completo**, igual que la API, antes de paginar.

Resultado paginado: primero filtrar universo, luego `LIMIT 150 OFFSET`.

### REQ-FIL-07 — Combinación de filtros

`marcas_incluidos`, `q`, `id_articulo`, `incluir_ceros` MUST combinarse.

Si `id_articulo` presente: `q` ignorado; `marcas_incluidos` aplica (empty si marca no coincide).

### REQ-FIL-08 — Persistencia en URL

Filtros activos MUST reflejarse en URL GET.

Links de paginación MUST conservar `marcas_incluidos`, `q`, `id_articulo`, `incluir_ceros`, `presentacion`.

### REQ-FIL-09 — Contador de resultados

The UI MUST mostrar en español: total de artículos que cumplen filtros (todas las páginas) y, si hay marcas seleccionadas, cantidad de marcas activas.

### REQ-FIL-10 — Catálogo de marcas

Endpoint o contexto de vista MUST proveer catálogo `CodMarca` + `NombreMarca` para poblar el select oculto del tags filter (mismo origen que reportes stock-existencias).

---

## Scenarios

### ESC-FIL-01 — Multi-marca

- **GIVEN** marcas BEST (`3`) y SOX (`7`) con artículos con stock
- **WHEN** usuario selecciona ambas en tags y aplica
- **THEN** URL contiene `marcas_incluidos=3` y `marcas_incluidos=7`
- **AND** tabla muestra solo artículos con `CodigoMarca IN (3,7)` y consolidado > 0

### ESC-FIL-02 — Sin marcas (todas)

- **GIVEN** filtros previos con dos marcas
- **WHEN** usuario quita todos los chips y aplica
- **THEN** URL sin `marcas_incluidos`
- **AND** tabla incluye cualquier marca

### ESC-FIL-03 — Búsqueda fuera de página actual

- **GIVEN** 300 artículos con stock; artículo «PACK-Z» está en posición 280
- **WHEN** usuario en `?page=1` escribe «pack-z» en predictivo
- **THEN** API devuelve PACK-Z en sugerencias
- **WHEN** selecciona PACK-Z
- **THEN** navega a `?id_articulo={IDArt}` y ve esa fila aunque no estuviera en página 1

### ESC-FIL-04 — q en tabla sin paginar búsqueda

- **GIVEN** 250 artículos; 3 coinciden con `q=alfa`
- **WHEN** usuario aplica `?q=alfa`
- **THEN** total mostrado es 3
- **AND** página 1 muestra las 3 filas (no solo las de la página 1 del universo sin filtro)

### ESC-FIL-05 — API con marcas e incluir_ceros

- **GIVEN** artículo marca 3 con consolidado 0
- **WHEN** `GET .../articulos/?q=test&marcas_incluidos=3&incluir_ceros=0`
- **THEN** artículo con consolidado 0 MUST NOT aparecer
- **WHEN** `incluir_ceros=1`
- **THEN** MAY aparecer si coincide `q`

### ESC-FIL-06 — Limpiar filtros

- **GIVEN** URL con `marcas_incluidos`, `q`, `id_articulo`, `incluir_ceros=1`
- **WHEN** usuario pulsa **Limpiar**
- **THEN** navega a `/stock/inventario/` sin params de filtro (MUST conservar `presentacion` si estaba en docenas)

### ESC-FIL-07 — Componente tags igual a reportes

- **GIVEN** pantalla inventario cargada
- **WHEN** usuario interactúa con filtro Marcas
- **THEN** ve chips removibles, input «Buscar marca...» y dropdown con check — misma UX que stock-existencias en reportes

### ESC-FIL-08 — Paginación preserva marcas

- **GIVEN** 180 artículos con `marcas_incluidos=3`
- **WHEN** usuario en `?marcas_incluidos=3&page=2`
- **THEN** link página 1 incluye `marcas_incluidos=3`

### ESC-FIL-09 — id_articulo inexistente

- **GIVEN** `id_articulo` inválido
- **WHEN** carga la URL
- **THEN** empty state; sin error 500

### ESC-FIL-10 — Búsqueda CodArtProv

- **GIVEN** `CodArtProv='PRV-88'`
- **WHEN** `GET .../articulos/?q=prv-88`
- **THEN** artículo en sugerencias independientemente de la página visible
