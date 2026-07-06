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

Por defecto (`incluir_ceros` ausente o `0`), the system MUST listar solo artículos con **consolidado > 0** (tras filtros de marca y búsqueda).

### REQ-INV-08 — Botón «Ver todos los artículos»

The UI MUST ofrecer un control (botón o toggle) **Ver todos los artículos** que active `incluir_ceros=1` en la URL.

Con `incluir_ceros=1`, the system MUST incluir artículos con **consolidado ≤ 0** que cumplan filtros de marca y búsqueda.

El control MUST indicar visualmente el modo activo (solo con stock / todos).

Al desactivar, MUST volver al universo default (consolidado > 0).

### REQ-INV-09 — Toggle Unidades / Docenas

The UI MUST ofrecer toggle **Unidades | Docenas** persistente en query param `presentacion=unidades|docenas` (default: `unidades`).

En modo **unidades**, celdas numéricas MUST mostrar enteros.

En modo **docenas**, cada celda MUST mostrar **docenas arriba y unidades abajo**, con la misma semántica que `mpr/reportes/partials/stock.html` y `mpr/reportes_presentacion.py` (divisor 12 o `cantidad_promedio_bulto` del pack).

Thead MUST duplicar subencabezados Docenas/Unidades cuando `presentacion=docenas`.

### REQ-INV-10 — Paginación de tabla

The system MUST paginar la **tabla renderizada** en servidor con **150** filas por página.

Query param `page` (entero ≥ 1) MUST controlar la página.

The UI MUST mostrar total de artículos que cumplen filtros y página actual en español.

La paginación MUST NOT limitar el universo de la búsqueda predictiva (ver `stock-inventario-filtros`).

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
- **AND** solo artículos con consolidado > 0
- **AND** presentación en unidades por defecto

### ESC-INV-02 — Ver todos los artículos

- **GIVEN** artículo A con consolidado 0 y artículo B con consolidado 10
- **WHEN** usuario activa **Ver todos los artículos** (`incluir_ceros=1`)
- **THEN** la tabla incluye A y B (si pasan filtros marca/búsqueda)
- **WHEN** desactiva el control
- **THEN** solo aparece B

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

### ESC-INV-08 — Paginación

- **GIVEN** 200 artículos con consolidado > 0 que cumplen filtros
- **WHEN** carga `?page=1`
- **THEN** muestra 150 filas y enlace a página 2
- **WHEN** carga `?page=2`
- **THEN** muestra 50 filas restantes

### ESC-INV-09 — Ruta legacy eliminada

- **GIVEN** despliegue con el change aplicado
- **WHEN** usuario navega a `/stock/consulta-ficha/`
- **THEN** recibe HTTP 404 (ruta no registrada)

### ESC-INV-10 — Scrap excluido del consolidado

- **GIVEN** saldo 40 solo en depósito `tipo_mpr=Scrap`
- **WHEN** `incluir_ceros=0`
- **THEN** el artículo MUST NOT listarse
- **WHEN** `incluir_ceros=1`
- **THEN** el artículo MAY listarse con consolidado 0 y columna Scrap sin mostrarse
