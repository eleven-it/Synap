# Informe: Stock y existencias (`stock-existencias`)

**Slug:** `stock-existencias`  
**Runner:** `reports/services/query_runner.py` → `_run_stock_existencias`  
**Última actualización:** 2026-04-13

## Objetivo

Listado por **artículo y depósito** (`stock_deposito`) de artículos activos para venta, con **stock** (`saldo`), **reservado** (misma lógica que el informe BO: `stockp` + `comp_ped` PED en *En preparación* o *Preparado*, agregado por `IDArt` y `CodDeposito`, **sin** exclusión por cliente en este informe) y **disponible**:

`GREATEST(0, stock − reservado)` — **no** se usa `stock_deposito.saldo_pedido_cliente`.

La **búsqueda** (predictiva, mínimo 2 caracteres) y el **orden** por columnas (nombre artículo, marca, rubro, subrubro) se aplican **en el navegador** sobre **todo** el resultado devuelto por el servidor (sin tope artificial de filas en la consulta). La barra de resultados replica el patrón BO: **Agrupar por** (tags, varios niveles en orden de selección) a la izquierda (~70 %) y **Buscar** a la derecha (~30 %). Con agrupación activa, la tabla sigue el mismo modelo que el detalle **Backorder** del informe BO: filas de grupo con chevron (expandir/colapsar), subtotales de **Stock**, **Reservado** y **Disponible** alineados a las columnas numéricas, niveles anidados en tabla interna y pie de texto tipo «Agrupado por: … · N agrupaciones». En la tabla no se muestran columnas «ID sistema» ni «Código artículo» ni **Cliente**. El resumen superior **no** muestra KPI de cantidad de filas.

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

Compatibilidad: si llegan `codigo_marca`, `codigo_rubro` o `id_subrubro` (valor único), se interpretan como un solo elemento en el filtro correspondiente.

Artículos incluidos: `Discontinuo = 'No'`, `disponible_vta = 'Si'`, `tipo_art = 'Articulo'`.

## Columnas devueltas (detalle)

Incluyen entre otras: `id_deposito`, `deposito_nombre`, `marca_nombre`, `rubro_nombre`, `subrubro_nombre`, `codigo_barras`, cantidades `stock`, `reservado`, `disponible`.

## API de opciones de filtro

`GET …/filters/?type=marcas|rubros|subrubros` (además de `depositos`), mismo patrón de etiqueta/valor que depósitos.

## Límites y rendimiento

- La consulta SQL **no** aplica `LIMIT`: se devuelven **todas** las filas que cumplan filtros (sujeto a memoria del servidor, tiempo de ejecución MySQL `max_execution_time` 300 s en sesión y hint en la consulta, y timeout HTTP del cliente ~5 min).
- `meta.row_count` indica la cantidad de filas devueltas.
- No se envía total agregado en `totals` (sin KPI «FILAS» en el resumen declarativo).

## Migración desde mayorista PHP

Referencia: `docs/reports/INFORME_VB6_STOCK_DISPONIBLE_BACKORDER_VS_BO.md` (sección plan) y relay histórico `listado-stock-existencias.php`.
