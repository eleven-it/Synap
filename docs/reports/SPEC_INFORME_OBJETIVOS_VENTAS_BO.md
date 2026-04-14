# Especificación: informe Objetivos de ventas (base BO) y CRUD asociado

## Alcance

- **Informe nuevo** en el módulo Reportes (**nombre en catálogo: «Objetivos de ventas por vendedor»**, slug `ventas-objetivos-vs-bo`): seguimiento de cumplimiento de **objetivos de ventas** por **cliente**, agrupados en UI bajo **Vendedor** (en base de datos: **viajante**).
- **CRUD** en módulo **Ventas**, subítem **Objetivos de venta**: listado de períodos; **nuevo período** se define en un **modal** (intervalo fijo, **descripción** opcional ej. «Abril 2026») y el detalle por cliente en pantalla dedicada. Cabecera **`viajantes_objetivos_periodo`** (`descripcion`, `anulado` Si/No) y detalle **`viajantes_objetivos_ventas`** (`id_periodo`). En el detalle, los campos de **importe objetivo** muestran vacío si el valor guardado es 0 (la DB puede seguir almacenando 0); al **enfocar** se selecciona todo el texto; **sin separadores de miles** mientras hay foco; formato **es-AR con separadores** al **perder foco**; el guardado envía el valor numérico parseado.
- **Temporalidad del informe**: igual que **BO vs Stock vs Facturación** (`bo-stock-facturacion`): un rango para **facturación y remitos** y otro para **backorder**.
- **Filtro «Vendedores a excluir»**: lista de `CodViajante`; se excluyen del informe los clientes (y sus objetivos y métricas) cuyo vendedor actual coincida con alguno de los códigos seleccionados.

## Reglas de negocio acordadas

| Tema | Regla |
|------|--------|
| Objetivo | Por **cliente**; período del registro: **`fecha_desde` / `fecha_hasta`**. |
| Histórico vendedor | Al guardar objetivo se persiste **`CodViajante` en la fila** (snapshot). Si el cliente cambia de viajante, los registros viejos **no se reasignan**. |
| Informe: etiqueta | Siempre **«Vendedor»** en pantalla (origen DB: viajante). |
| Objetivo vs operación | Sin fila objetivo o importe 0 → mostrar **0** y calcular **Falta** partiendo de 0. |
| CRUD: clientes listados | Solo clientes con **vendedor asignado** (`cliente.CodViajante` no nulo / válido), **`cliente.Estado = Activo`** y **`viajantes.anulado = No`** (esquema legacy: `cliente` no tiene columna `anulado` en todas las bases). |
| Falta | **`Falta = Objetivo − Facturación − Remitos`** (importes del período de facturación/remitos del informe). |
| Total (columna tipo Excel) | **`Total = Facturación + Remitos`** (coherente con Falta). |
| Cantidades vendidas | En el informe la columna se muestra como **«Unidades vendidas»** (para distinguir de forecast u otros usos de “unidades”). Criterio numérico: el **mismo que movimientos de stock en ventas**: renglones tabla `stock` ligados a `cuentacliente` por `CodigoMovimiento`, tipos de comprobante FA/FB/FC/FE/FM y notas de crédito NCA…NCM, `stock.Anulado = 'No'`, `stock.TipoComp IN ('Venta', 'Venta TPV', 'Devol - Cliente', 'ND Anul NC')`, signo según factura vs NC (paridad [`reports/services/ventas_netas.py`](../../reports/services/ventas_netas.py) `_sum_unidades_sql_stock_line`). Rango de fechas: **rango facturación** del informe. |
| Solapes de objetivos | **Períodos activos** (cabecera con `anulado = No`): no deben solaparse entre sí. Por cliente y **dentro del mismo `id_periodo`**, el detalle se consolida al último `id` guardado. |
| Anulación | **No** se borra el detalle: la cabecera pasa a `anulado = Si` (paridad con otras tablas AdministraNET). El informe **no** aplica objetivos de períodos anulados. |

## Tabla MySQL `viajantes_objetivos_ventas`

- DDL de referencia: [`docs/general/sql/viajantes_objetivos_ventas.sql`](../general/sql/viajantes_objetivos_ventas.sql).
- Inventario de campos: [`docs/general/tablas/viajantes_objetivos_ventas.md`](../general/tablas/viajantes_objetivos_ventas.md).
- Creación/alter vía herramienta global: [`core/services/legacy_mysql_schema/catalog.py`](../../core/services/legacy_mysql_schema/catalog.py) (proveedor dedicado).

## Matching objetivo ↔ período del informe

Se considera vigente para el informe todo registro cuyo intervalo **solape** el rango de facturación del filtro **`[fecha_inicio_facturacion, fecha_fin_facturacion]`** (inclusive):

```text
objetivo.fecha_desde <= fecha_fin_facturacion
AND objetivo.fecha_hasta >= fecha_inicio_facturacion
```

Si hay más de un registro solapado para el mismo cliente, el comportamiento debe ser **determinístico** (recomendación de implementación: rechazar al guardar; si legacy admitiera duplicados, definir prioridad — p. ej. el de `fecha_desde` más reciente — y documentarlo en release notes).

## Informe: slug y payload

- **Slug propuesto**: `ventas-objetivos-vs-bo` (definitivo al implementar; debe registrarse en `ReportDefinition` y en el catálogo de reportes).
- **Filtros**: mismos que `bo-stock-facturacion` para período dual, sucursales, clientes excluidos, depósitos, lista de precio donde aplique al BO.
- **Dataset jerárquico** (contrato sugerido para `meta.extra`):

  - Lista de nodos **padre** (vendedor): `cod_viajante`, `nombre_vendedor`, totales agregados de hijos.
  - Lista de **hijos** (cliente): `codigo_cliente`, `nombre_cliente`, `objetivo`, `facturacion`, `remitos`, `total`, `falta`, `cantidades_vendidas`, columnas BO (total y, si aplica, con stock / con ingreso / sin stock) en **importe**, alineadas al criterio del BO actual por cliente.

- **Exportación Excel** (`ExportService`): filas ordenadas por **cód. vendedor** y luego **cód. cliente**. Se inserta una **fila de encabezado por vendedor** (texto «Vendedor {cod} — {nombre}») y las filas de clientes quedan con **nivel de esquema 1** bajo esa sección (`outlinePr` con resumen arriba), de modo que Excel permite **contraer/expandir** el bloque de clientes por vendedor. Nombre de archivo descargado: **`Ventas_objetivo_vendedores_{fecha_inicio_facturación}_{fecha_fin_facturación}.xlsx`** (filtros `fecha_inicio_facturacion` / `fecha_fin_facturacion`; si falta alguna fecha, el segmento se reemplaza por `sin_fecha`).

- **Agregación BO por cliente**: nueva consulta (no existe hoy en el BO como grid único); debe reutilizar criterios de `_run_backorder_vs_stock_vs_facturacion` (PED Pendiente, `stockp.Fecha` en rango BO, exclusiones, etc.).

## CRUD Ventas: UX

- Enlace **Reporte** desde el detalle de un período: abre el informe `ventas-objetivos-vs-bo` con query `fecha_inicio_facturacion` y `fecha_fin_facturacion` iguales al intervalo del período. El **período de backorder** del informe no se envía por URL: se mantiene la última configuración guardada en `localStorage` (`report_filters_ventas-objetivos-vs-bo`). Tras aplicar las fechas de facturación, el cliente elimina esos parámetros de la barra de dirección (`history.replaceState`).
- Selector **fecha desde / fecha hasta** del **período que se está editando** (objetivos a cargar para ese intervalo).
- Vista **anidada**: Vendedor → clientes con campo **Objetivo** editable.
- **Búsqueda predictiva** por nombre de vendedor (filtra/resalta grupos).
- Permisos: grupo **Ventas** existente en Synap (`ventas.ver` / `ventas.editar` o permiso específico si se añade).

## Contrato ejecutable (Python)

Reglas puras de solape de fechas y **Falta** están en [`reports/services/objetivos_ventas_contract.py`](../../reports/services/objetivos_ventas_contract.py) y cubiertas por [`reports/tests/test_objetivos_ventas_contract.py`](../../reports/tests/test_objetivos_ventas_contract.py).

## Pruebas de integración

Ver [`reports/tests/test_objetivos_ventas_informe_integration.py`](../../reports/tests/test_objetivos_ventas_informe_integration.py): quedan **omitidas** hasta existir slug, migración de tabla y `QueryRunner`.

## Referencias de código existente

- BO: [`reports/services/query_runner.py`](../../reports/services/query_runner.py) `_run_backorder_vs_stock_vs_facturacion`.
- UI BO dual período: [`reports/static/reports/js/dashboard.js`](../../reports/static/reports/js/dashboard.js), plantilla BO en [`reports/templates/reports/dashboard_detail.html`](../../reports/templates/reports/dashboard_detail.html).
- Unidades ventas: [`reports/services/ventas_netas.py`](../../reports/services/ventas_netas.py).
