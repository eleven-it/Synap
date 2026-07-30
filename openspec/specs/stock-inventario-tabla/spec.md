# Spec — Inventario tabla MPR (Stock)

**Capability:** `stock-inventario-tabla`  
**Change:** `stock-inventario-tabla-mpr`  
**Ruta:** `/stock/inventario/`

---

## Purpose

Consulta operativa de inventario en el módulo **Stock**: tabla pivote con una fila por artículo y columnas por **etapa física MPR** (`deposito.tipo_mpr`), más columna **Consolidado**. Sustituye por completo el antiguo stub `/stock/consulta-ficha/` (eliminado).

---

## Requirements

### REQ-INV-01 — Ruta y permiso

The system MUST expose `GET /stock/inventario/` con nombre de URL Django `stock:inventario`.

Access MUST require permiso `stock.consultas` y sesión con `base_empresa` válida.

Sin `base_empresa`, the system MUST redirigir al dashboard con mensaje de error en español.

### REQ-INV-02 — Menú Stock

The subítem de menú **Inventario** bajo Stock MUST apuntar a `stock:inventario`.

The label visible MUST permanecer **Inventario**; permiso de menú: `stock.consultas`.

### REQ-INV-03 — Columnas fijas de la tabla

The table MUST mostrar exactamente estas columnas, en este orden:

| # | Encabezado UI | Origen de datos |
|---|---------------|-----------------|
| 1 | Artículo | `articulo.id_manual`, `articulo.CodArtProv`, `articulo.NombreArticulo` |
| 2 | Producción | Suma saldos `tipo_mpr = Produccion` |
| 3 | Semi elaborado | Suma saldos `tipo_mpr = SemiElaborado` |
| 4 | 2da Selección | Suma saldos `tipo_mpr = 2daSeleccion` |
| 5 | Terminado | Suma saldos `tipo_mpr = Terminado` |
| 6 | Consolidado | Suma de columnas 2–5 |

Scrap, Planchado y demás `tipo_mpr` MUST NOT aparecer como columnas en v1.

### REQ-INV-04 — Columna Artículo

Línea principal MUST mostrar `id_manual` normalizado con `str_codigo_manual_articulo`.

Si `CodArtProv` no está vacío, MUST concatenar ` - {CodArtProv}`.

Si `CodArtProv` está vacío, MUST NOT mostrar guión colgante.

Línea secundaria MUST mostrar `NombreArticulo` truncado en `text-xs`.

### REQ-INV-05 — Fuente de saldos

Saldos MUST leerse de `stock_deposito.saldo` unido a `deposito` y `articulo`.

Solo MUST incluirse depósitos con `COALESCE(deposito.anulado, 'No') = 'No'` y `COALESCE(deposito.suma_stock, 'Si') = 'Si'`.

Si varios depósitos comparten el mismo `tipo_mpr`, the system MUST sumar sus saldos en la columna correspondiente.

Valores MUST normalizarse con utilidades `core.utils.administranet_types` al leer/escribir MySQL.

### REQ-INV-06 — Consolidado

**Consolidado** MUST ser la suma aritmética de Producción + Semi elaborado + 2da Selección + Terminado para cada fila.

The system MUST NOT incluir Scrap ni etapas virtuales en el consolidado.

Semántica MUST alinearse con `TIPOS_QUE_SUMAN_STOCK` en `mpr/pipeline.py`.

### REQ-INV-07 — Universo de filas por defecto

Por defecto (`filtro_stock` ausente o `todos`), the system MUST listar **todos** los artículos del ámbito (tras filtros de marca y búsqueda), **incluyendo** saldos en cero y negativos.

### REQ-INV-08 — Toggle de saldo: Todos | Con stock | Sin stock

The UI MUST ofrecer un control segmentado **Todos | Con stock | Sin stock** con query param `filtro_stock=todos|con_stock|sin_stock` (default: `todos`).

| Valor | Criterio (etapas del ámbito) |
|-------|------------------------------|
| `todos` | Sin filtro de saldo |
| `con_stock` | Al menos una etapa con saldo **> 0** |
| `sin_stock` | Ninguna etapa con saldo > 0 (ceros y negativos) |

Compat URL legacy: `incluir_ceros=1` → `todos`; `incluir_ceros=0` → `con_stock`.

The system MUST mostrar saldos **negativos** en las celdas (sin clampear a 0) para permitir ajustes.

El control MUST indicar visualmente el modo activo.

### REQ-INV-09 — Toggle Unidades / Docenas

The UI MUST ofrecer toggle **Unidades | Docenas** persistente en query param `presentacion=unidades|docenas` (default: `unidades`).

En modo **unidades**, celdas numéricas MUST mostrar enteros.

En modo **docenas**, cada celda MUST mostrar **docenas arriba y unidades abajo**, con la misma semántica que `mpr/reportes/partials/stock.html` y `mpr/reportes_presentacion.py` (divisor 12 o `cantidad_promedio_bulto` del pack).

Thead MUST duplicar subencabezados Docenas/Unidades cuando `presentacion=docenas`.

### REQ-INV-10 — Carga completa del ámbito (sin paginación de tabla)

The system MUST cargar en **una sola respuesta** todos los artículos del ámbito/filtros de servidor (marcas, saldo, `id_articulo`), con tope de seguridad configurable (`PAGE_SIZE`, default 5000).

The UI MUST NOT paginar la grilla (sin `page` / Anterior / Siguiente).

Si el total supera el tope, MUST mostrarse aviso de truncado y la cantidad cargada.

La búsqueda de texto en grilla MUST filtrar en **cliente** sobre las filas ya cargadas (ver `stock-inventario-filtros`).

Si la carga (inicial o al cambiar filtros) tarda más de **2 segundos**, MUST mostrarse el modal de espera Synap (`synap-post-loading` / `synapShowPostLoadingProgress`).

### REQ-INV-11 — UI canónica

The pantalla MUST seguir patrones de `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md` y reutilizar estructura visual de `mpr/reportes/partials/stock.html` (columna artículo sticky, scroll horizontal, dark mode).

The pantalla MUST NOT usar como referencia visual plantillas de Objetivos de venta ni Presupuestos en `ventas/templates/`.

Todos los textos visibles MUST estar en español.

### REQ-INV-12 — Estados vacíos y configuración

Si no hay filas tras filtros, MUST mostrarse mensaje: «No hay artículos con los filtros seleccionados.»

Si ningún depósito tiene `tipo_mpr` configurado entre los que suman stock, MUST mostrarse banner informativo en español indicando configurar depósitos MPR.

---

## REMOVED Requirements

### Requirement: Consulta ficha de stock (`/stock/consulta-ficha/`)

(Razón: reemplazada por `/stock/inventario/`.)

The system MUST NOT exponer `/stock/consulta-ficha/`, la vista `consulta_ficha_stock_view`, la plantilla `consulta_ficha_stock.html` ni el nombre de URL `stock:consulta_ficha_stock`.

Tests y referencias de menú a `stock:consulta_ficha_stock` MUST eliminarse o actualizarse a `stock:inventario`.

---

## Scenarios

### ESC-INV-01 — Acceso autorizado (default)

- **GIVEN** usuario con `stock.consultas` y `base_empresa` en sesión
- **WHEN** navega a `/stock/inventario/`
- **THEN** ve tabla con columnas Artículo, Producción, Semi elaborado, 2da Selección, Terminado, Consolidado
- **AND** lista todos los artículos del ámbito (incluye ceros y negativos)
- **AND** presentación en unidades por defecto
- **AND** filtro de saldo activo = **Todos**

### ESC-INV-02 — Con stock / Sin stock / Todos

- **GIVEN** artículo A con todas las etapas ≤ 0 y artículo B con alguna etapa > 0
- **WHEN** usuario elige **Con stock** (`filtro_stock=con_stock`)
- **THEN** solo aparece B
- **WHEN** usuario elige **Sin stock** (`filtro_stock=sin_stock`)
- **THEN** solo aparece A (y se ven valores negativos si los hay)
- **WHEN** usuario elige **Todos**
- **THEN** aparecen A y B

### ESC-INV-03 — Toggle docenas

- **GIVEN** artículo con 25 unidades en Terminado y `cantidad_promedio_bulto=12`
- **WHEN** usuario cambia a `presentacion=docenas`
- **THEN** celda Terminado muestra 2 docenas arriba y 1 unidad abajo
- **AND** encabezados de etapa muestran subfilas Docenas/Unidades

### ESC-INV-04 — Código artículo compuesto

- **GIVEN** artículo con `id_manual = '12A'` y `CodArtProv = 'PRV-88'`
- **WHEN** aparece en la tabla
- **THEN** línea principal muestra `12A - PRV-88`
- **AND** línea secundaria muestra el nombre del artículo

### ESC-INV-05 — CodArtProv vacío

- **GIVEN** artículo con `id_manual = '12A'` y `CodArtProv` vacío o NULL
- **WHEN** aparece en la tabla
- **THEN** línea principal muestra solo `12A` sin ` - ` final

### ESC-INV-06 — Suma por tipo_mpr

- **GIVEN** artículo con saldo 30 y 20 en dos depósitos `tipo_mpr=Produccion` (`suma_stock=Si`)
- **WHEN** se renderiza la fila
- **THEN** columna Producción muestra 50

### ESC-INV-07 — Consolidado

- **GIVEN** saldos: Producción 10, Semi 5, 2da 0, Terminado 20
- **WHEN** se renderiza la fila
- **THEN** Consolidado muestra 35

### ESC-INV-08 — Carga completa del ámbito

- **GIVEN** 200 artículos del ámbito que cumplen filtros
- **WHEN** carga `/stock/inventario/`
- **THEN** muestra las 200 filas en una sola grilla (sin paginación)
- **WHEN** el usuario escribe en «Buscar en tabla»
- **THEN** se ocultan filas en cliente sin nuevo GET
- **WHEN** la carga supera 2 s
- **THEN** aparece el modal de espera Synap hasta completar

### ESC-INV-09 — Ruta legacy eliminada

- **GIVEN** despliegue con el change aplicado
- **WHEN** usuario navega a `/stock/consulta-ficha/`
- **THEN** recibe HTTP 404 (ruta no registrada)

### ESC-INV-10 — Scrap excluido del consolidado

- **GIVEN** saldo 40 solo en depósito `tipo_mpr=Scrap`
- **WHEN** `filtro_stock=con_stock`
- **THEN** el artículo MUST NOT listarse (Scrap no cuenta como etapa del ámbito)
- **WHEN** `filtro_stock=todos` o `sin_stock`
- **THEN** el artículo MAY listarse con consolidado 0 y columna Scrap sin mostrarse

### ESC-INV-11 — Negativos visibles

- **GIVEN** artículo Terminado con saldo −52 en depósito Terminado
- **WHEN** se renderiza la fila (filtro Todos o Sin stock)
- **THEN** la celda muestra `-52` (no `0`) y se destaca visualmente
