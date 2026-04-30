# Diseño: columna «Pedidos en armado» en informe Objetivos de ventas vs BO

## Contexto

El KPI **PEDIDOS EN ARMADO** del reporte **`total-consolidado-operativo`** suma importes de `comp_ped` con `TipoComprobante = 'PED'`, estados **En preparación** / **Preparado**, **sin filtro de fechas** (`QueryRunnerService._get_pedidos_pendientes_total(..., filtrar_por_fecha=False)`).

Se incorpora el mismo criterio **por cliente** en **`ventas-objetivos-vs-bo`** para alinear la columna **TOTAL** (`total`) con el **total consolidado** por fila.

## Decisiones

| Decisión | Detalle |
|---------|---------|
| Nombre de campo JSON | **`pedidos_en_armado`** (snake_case como el resto del payload). |
| Columna **`total`** | Se mantiene el nombre **`total`**. Semántica nueva: **facturación + remitos + pedidos_en_armado** (`calcular_total_consolidado_objetivos`). |
| **Falta** | **Objetivo − facturación − remitos − pedidos_en_armado** (`calcular_falta` con cuarto argumento). Coherente con el total consolidado por fila. |
| Filtros SQL pedidos / remitos / facturación | **Sucursales**, **`punto_venta`** (`id_pv` en `cuentacliente` / `comp_ped`), **clientes excluidos**, **vendedores excluidos**; join a **cliente** para excluir por `CodViajante`. Normalización vía `QueryRunnerService._parse_sucursales_pv` (paridad con `total-consolidado-operativo`). |
| Jerarquía rubro/subrubro/artículo | Sin desglose operativo de PED por línea; UI muestra **—** en REMITOS, PEDIDOS EN ARMADO y TOTAL (como ya se hace con remitos/total). |
| Export Excel | Columna **`pedidos_en_armado`** entre **`remitos`** y **`total`**; etiqueta traducida «PEDIDOS EN ARMADO» / «TOTAL CONSOLIDADO» según fila de headers. |

## Archivos tocados

- `reports/services/objetivos_ventas_contract.py` — funciones puras y tests.
- `reports/services/ventas_objetivos_bo_runner.py` — consulta agregada `GROUP BY cp.Codigo`.
- `reports/static/reports/js/objetivos_ventas_bo.js` — `colspan`, thead, `metricCellsFull`, fallback jerárquico.
- `reports/services/export_service.py` — orden de headers y formato moneda.
- `reports/templates/reports/dashboard_detail.html` — texto de ayuda KPI FALTA y versión estática JS.

## Referencias

- [`TOTAL_CONSOLIDADO_OPERATIVO_VALIDACION.md`](./TOTAL_CONSOLIDADO_OPERATIVO_VALIDACION.md)
- [`SPEC_INFORME_OBJETIVOS_VENTAS_BO.md`](./SPEC_INFORME_OBJETIVOS_VENTAS_BO.md)
