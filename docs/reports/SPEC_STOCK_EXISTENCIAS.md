# Informe: Stock y existencias (`stock-existencias`)

**Slug:** `stock-existencias`  
**Runner:** `reports/services/stock_existencias_query.py` (vía `query_runner._run_stock_existencias`)  
**Última actualización:** 29/06/2026

## Objetivo

Listado por **artículo y depósito** (`stock_deposito`) de artículos activos para venta, con **stock** (`saldo`), **reservado** (misma lógica que el informe BO: `stockp` + `comp_ped` PED en *En preparación* o *Preparado*, agregado por `IDArt` y `CodDeposito`, **sin** exclusión por cliente en este informe) y **disponible**:

`GREATEST(0, stock − reservado)` — **no** se usa `stock_deposito.saldo_pedido_cliente`.

La **búsqueda** (predictiva, mínimo 2 caracteres) y el **orden** por columnas (**ID manual**, **Código barras**, nombre artículo, rubro, subrubro) se resuelven **en el servidor** con **paginación** (150 filas por página, scroll infinito al desplazar). La tabla en modo plano usa **virtual scroll** en el DOM (solo filas visibles). Al **pulsar una cabecera de orden** o **buscar**, se consulta de nuevo el API. La barra de resultados replica el patrón BO: **Agrupar por** (tags, varios niveles en orden de selección) a la izquierda (~70 %) y **Buscar** a la derecha (~30 %). Dimensiones de agrupación: depósito, nombre artículo, rubro, subrubro (**no** marca). **Con agrupación activa** se descarga el universo completo y la agrupación se aplica en el cliente (mismo modelo BO: chevron, subtotales, niveles anidados). En la tabla no se muestran columnas «ID sistema» ni «Código artículo» ni **Cliente** ni **Marca**. El resumen superior **no** muestra KPI de cantidad de filas.

En la sección **Filtros** del formulario, los controles van en **rejilla de dos columnas** desde breakpoint `md` (≈50 % de ancho cada uno en pantallas medianas/grandes).

Durante la petición al API y hasta que la tabla termina de renderizar en el cliente, se usa el **modal de carga compartido** del dashboard legacy (`#reports-legacy-query-loading-modal` en `dashboard_detail.html`), mismo patrón que informes BO y Ventas netas. El cliente usa **timeout de red de 5 minutos** en esta consulta, mayor que el default, acorde a volúmenes grandes.

## Filtros (payload `filters`)

| Parámetro | Descripción |
|-----------|-------------|
| `depositos_incluidos` | Lista de IDs de depósito. Si está vacío, se incluyen todas las filas de `stock_deposito` (según resto de filtros). |
| `incluir_stock_cero` | `si` / `no` (default: ocultar filas con `saldo` 0 en ese depósito). |
| `marcas_incluidos` | Lista de `CodMarca`; vacío = todas. |
| `rubros_incluidos` | Lista de `CodigoRubro`; vacío = todos. |
| `subrubros_incluidos` | Lista de `IDSubRubro`; vacío = todos. |
| `busqueda` | Texto libre (mín. 2 caracteres); filtro LIKE en servidor. |
| `sort_col` | Columna de orden (`nombre`, `id_manual`, `codigo_barras`, `rubro_nombre`, `subrubro_nombre`, `deposito_nombre`). |
| `sort_dir` | `asc` o `desc`. |
| `agrupacion_activa` | `true` cuando hay «Agrupar por» en UI → sin paginación. |

Compatibilidad: si llegan `codigo_marca`, `codigo_rubro` o `id_subrubro` (valor único), se interpretan como un solo elemento en el filtro correspondiente.

**Payload raíz:** `limit` (default 150), `offset` (default 0).

Artículos incluidos: `Discontinuo = 'No'`, `disponible_vta = 'Si'`, `tipo_art = 'Articulo'`.

## Columnas devueltas (detalle)

Incluyen entre otras: `id_deposito`, `deposito_nombre`, `marca_nombre`, `rubro_nombre`, `subrubro_nombre`, `codigo_barras`, cantidades `stock`, `reservado`, `disponible`.

**`codigo_barras`:** se arma en SQL priorizando **`articulo.NroCodBarraF`** (trim, no vacío); si no hay valor útil, se usa **`NroCodBarra`**. Así se evita mostrar códigos corruptos en notación científica cuando el EAN correcto está en el campo secundario (comportamiento alineado a búsqueda TPV por `NroCodBarra` / `NroCodBarraF`).

**Tabla en cliente:** anchos relativos vía `colgroup` (columnas Stock / Reservado / Disponible ~20 % más estrechas que en un reparto 9× igual; el ancho liberado repartido entre nombre de artículo, rubro y subrubro). Ver `docs/reports/UI_STOCK_EXISTENCIAS_TABLA_VO.md`.

## API de opciones de filtro

`GET …/filters/?type=marcas|rubros|subrubros` (además de `depositos`), mismo patrón de etiqueta/valor que depósitos.

## Límites y rendimiento

- Consulta SQL con **`LIMIT`/`OFFSET`** salvo agrupación activa (universo completo).
- `meta.row_count`: filas en la página actual; `meta.total_registros`: total con filtros; `meta.has_more`: hay más páginas.
- Pool MySQL compartido; join desde `stock_deposito` (`STRAIGHT_JOIN articulo`).
- Timeout HTTP del cliente ~5 min (agrupación / bases grandes).
- No se envía total agregado en `totals` (sin KPI «FILAS» en el resumen declarativo).

**Runner:** `reports/services/stock_existencias_query.py` (invocado desde `query_runner._run_stock_existencias`).

## Migración desde mayorista PHP

Referencia: `docs/reports/INFORME_VB6_STOCK_DISPONIBLE_BACKORDER_VS_BO.md` (sección plan) y relay histórico `listado-stock-existencias.php`.
