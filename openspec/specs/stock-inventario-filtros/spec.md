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
- Toggle **Todos | Con stock | Sin stock** (spec `stock-inventario-tabla` REQ-INV-08)
- Acción **Limpiar** que restablece filtros (excepto presentación si producto decide conservarla)

### REQ-FIL-02 — Filtro multi-marca (tags)

The system MUST usar el mismo patrón de UI que reportes:

- Plantilla de referencia: `reports/templates/reports/includes/filters_stock_existencias.html` (bloque Marcas)
- JS: `reports/static/reports/js/tags_filter.mjs` → `initializeTagsFilter`

Estructura MUST incluir `<select multiple hidden>` + contenedor `*_tags_container` con chips y dropdown.

Query param MUST ser `marcas_incluidos` repetido o lista separada por comas (ej. `?marcas_incluidos=3&marcas_incluidos=7`).

Vacío = **todas las marcas**.

Filtrado MUST aplicarse en servidor: `articulo.CodigoMarca IN (...)`.

Al aplicar filtros, MUST preservarse en URL `filtro_stock`, `presentacion`, `page`, `q`, `id_articulo`.

### REQ-FIL-03 — Búsqueda predictiva (API)

The system MUST exponer `GET /stock/api/inventario/articulos/` con permiso `stock.consultas`.

Parámetros:

| Param | Descripción |
|-------|-------------|
| `q` | Texto ≥ 2 caracteres |
| `limit` | Default 15; máx. 50 sugerencias en dropdown |
| `marcas_incluidos` | Lista de `CodMarca`; opcional |
| `filtro_stock` | `todos`/`con_stock`/`sin_stock`; mismo criterio que tabla (legacy `incluir_ceros`) |

**Alcance:** la API MUST buscar en el **universo completo** de artículos que cumplen `marcas_incluidos` y `filtro_stock`, **sin** restricción por `page` ni `offset` de la tabla.

Respuesta JSON: array `articulos` con `id_articulo`, `codigo_compuesto`, `id_manual`, `cod_art_prov`, `nombre`, `marca_nombre`.

Criterios LIKE: `id_manual`, `CodArtProv`, `NombreArticulo`, `NroCodBarra`, `NroCodBarraF`.

Con `q` < 2 caracteres: `articulos: []`.

### REQ-FIL-04 — Buscar en tabla (cliente)

El campo **Buscar en tabla** MUST filtrar en vivo (Alpine/`data-search`) las filas **ya cargadas** del ámbito, sin GET por tecla.

MUST indexar al menos nombre, talle, color y código compuesto.

La API predictiva `GET /stock/api/inventario/articulos/` permanece disponible para integraciones / evolución a combobox; no es el canal del campo de la barra de filtros en v1 de carga completa.

### REQ-FIL-05 — Filtro por id_articulo

`id_articulo` MUST mostrar **una fila** para ese artículo, aunque consolidado sea 0.

Si no existe: empty state sin error 500.

### REQ-FIL-06 — Texto `q` en URL (opcional)

Si la URL trae `q`, MUST usarse solo como valor inicial del filtro cliente (prefill). MUST NOT reducir el universo SQL de la tabla (salvo `id_articulo`).

### REQ-FIL-07 — Combinación de filtros

`marcas_incluidos`, `id_articulo`, `filtro_stock` MUST aplicarse en servidor al cargar la grilla.

El texto de «Buscar en tabla» MUST aplicarse solo en cliente sobre ese resultado.

### REQ-FIL-08 — Persistencia en URL

Filtros de servidor activos MUST reflejarse en URL GET (`ambito`, `filtro_stock`, `presentacion`, `marcas_incluidos`, `id_articulo`).

Al enviar **Actualizar** / cambiar ámbito / presentación / saldo, MUST usarse modal de espera Synap con demora de **2000 ms** (`data-synap-loading-delay-ms`) para no parpadear en cargas rápidas.

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

### ESC-FIL-05 — API con marcas y filtro_stock

- **GIVEN** artículo marca 3 con saldo ≤ 0 en el ámbito
- **WHEN** `GET .../articulos/?q=test&marcas_incluidos=3&filtro_stock=con_stock`
- **THEN** ese artículo MUST NOT aparecer
- **WHEN** `filtro_stock=todos` (o ausente)
- **THEN** MAY aparecer si coincide `q`

### ESC-FIL-06 — Limpiar filtros

- **GIVEN** URL con `marcas_incluidos`, `q`, `id_articulo`, `filtro_stock=sin_stock`
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
