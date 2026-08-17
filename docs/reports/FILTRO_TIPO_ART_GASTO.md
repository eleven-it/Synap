# Filtro fijo: excluir artículos tipo Gasto

**Fecha:** 17/08/2026  
**Helper canónico:** `core/utils/articulo_tipo_sql.py` → `sql_excluir_tipo_art_gasto(alias)`  
**Reexport reports:** `reports/services/articulo_venta_sql.py`

## Regla

Se excluyen renglones cuyo `articulo.tipo_art = 'Gasto'` en:

- **Reportes de artículos de venta**
- **Inventario por etapa** (`/stock/inventario/` y `/mpr/inventario/`, servicio `inventario_tabla`)

- Conserva renglones **sin artículo** (LEFT JOIN: `IDArt` nulo) y `tipo_art` nulo: no son Gasto.
- No exige `tipo_art = 'Articulo'` (el valor `Servicio` sigue salvo que el informe tenga otra regla).
- **No aplica** a listados cuyo objeto sea precisamente gastos.

En Best Sox local, `articulo.tipo_art` suele ser `Articulo` / `Gasto` / `Servicio` (VARCHAR). No confundir con `tipo_art_fab`.

## Dónde está cableado

| Informe / servicio | Alias | Notas |
|--------------------|-------|--------|
| Ventas marcas mensual + export | `art` | Via `sql_base_where_clauses()` |
| Ventas mensuales licenciatarios (tramo ANET) | `art` | Misma cláusula VMM |
| Ventas por marca y SuperArt | `art` | WHERE del runner |
| Ventas netas (dimensiones stock) | `art` | rubro/subrubro/artículo/marca/zona/tipo cliente/proveedor |
| Utilidad gerencial | `arti` | Consultas sobre `_JOINS` de stock |
| Resumen ejecutivo (unidades, margen, rankings) | `a` | Totales de renglón + rankings |
| Objetivos de ventas / BO por cliente | `art` / `a` | Unidades, detalle venta y REM/PED |
| BO `bo-stock-facturacion` | `a` | Ya existía; ahora usa el helper |
| Dashboard cruzados | `a` | Ya existía; ahora usa el helper |
| DABRA consolidado remitos (líneas FA) | `a` | Líneas de factura |
| Inventario por etapa (`/stock/inventario/`, `/mpr/inventario/`) | `a` | `_build_articulo_where` |

Stock existencias / métricas de inventario siguen filtrando `tipo_art = 'Articulo'` (más estricto; ya excluye Gasto).

## Totales de cabecera

Dimensiones que suman **solo** `cuentacliente` (p. ej. ventas netas por mes/cliente/vendedor, facturación BO por `SubtotalDesc`) no pueden excluir Gasto a nivel renglón sin cambiar el criterio a stock. Esas vistas siguen el total de cabecera.

## Tests

`reports/tests/test_articulo_venta_sql.py` (helper + VMM/VML). `stock/tests/test_inventario_tabla.py` (WHERE de `/stock/inventario/`).
