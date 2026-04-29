# Especificación: informe Objetivos de ventas (base BO) y CRUD asociado

## Alcance

- **Informe nuevo** en el módulo Reportes (**nombre en catálogo: «Objetivos de ventas por vendedor»**, slug `ventas-objetivos-vs-bo`): seguimiento de cumplimiento de **objetivos de ventas** por **cliente**, agrupados en UI bajo **Vendedor** (en base de datos: **viajante**).
- **CRUD** en módulo **Ventas**, subítem **Objetivos de venta**: listado de períodos; **nuevo período** se define en un **modal** (intervalo fijo, **descripción** opcional ej. «Abril 2026») y el detalle por cliente en pantalla dedicada. Cabecera **`viajantes_objetivos_periodo`** (`descripcion`, `anulado` Si/No) y detalle **`viajantes_objetivos_ventas`** (`id_periodo`). En el detalle, los campos de **importe objetivo** muestran vacío si el valor guardado es 0 (la DB puede seguir almacenando 0); al **enfocar** se selecciona todo el texto; **sin separadores de miles** mientras hay foco; formato **es-AR con separadores** al **perder foco**; el guardado envía el valor numérico parseado. En la **grilla de solo lectura** (ponderación e importe por cliente), la **ponderación** es el prorrateo `base_ventas / suma base del vendedor` expresado en **porcentaje 0–100** (dos decimales); el **importe** se muestra como **entero con punto como separador de miles** y **sin símbolo de moneda** (ej. `2.833.102`), alineado con `Intl.NumberFormat("es-AR", { maximumFractionDigits: 0 })` tras recalcular (`core.templatetags.core_extras.formato_entero_miles`; `ventas/services/objetivos_mysql.py`: `peso_prorrateo_pct`, `objetivo_entero`). La primera columna de cliente usa **`cliente.id_manual_cli`** (código manual); el **código interno** `cliente.Codigo` sigue en `data-codigo` para guardado. En la fila de cabecera por vendedor solo se muestra el **nombre** del vendedor (sin contador entre paréntesis ni `#CodViajante`).
- **Temporalidad del informe**: igual que **BO vs Stock vs Facturación** (`bo-stock-facturacion`): un rango para **facturación y remitos** y otro para **backorder**.
- **Filtro «Vendedores a excluir»**: lista de `CodViajante`; se excluyen del informe los clientes (y sus objetivos y métricas) cuyo vendedor actual coincida con alguno de los códigos seleccionados.

## Reglas de negocio acordadas

| Tema | Regla |
|------|--------|
| Objetivo | Por **cliente**; período del registro: **`fecha_desde` / `fecha_hasta`**. |
| Histórico vendedor | Al guardar objetivo se persiste **`CodViajante` en la fila** (snapshot). Si el cliente cambia de viajante, los registros viejos **no se reasignan**. |
| Informe: etiqueta | Siempre **«Vendedor»** en pantalla (origen DB: viajante). |
| Orden jerárquico (árbol web y export) | Nivel **vendedor**: por **suma de objetivo** del grupo **descendente** (mayor primero); empates: nombre del vendedor, luego `CodViajante`. Nivel **cliente** y niveles **rubro → subrubro → artículo**: **alfabético** por nombre visible (empate numérico por código/id). Implementación: `ventas_objetivos_bo_runner.py` y `export_service._vo_objetivos_vs_bo_sort_export_rows`; fallback JS `buildJerarquiaDesdeFilas` en `objetivos_ventas_bo.js`. |
| Objetivo vs operación | Sin fila objetivo o importe 0 → mostrar **0** y calcular **Falta** partiendo de 0. |
| CRUD: clientes listados | Solo clientes con **vendedor asignado** (`cliente.CodViajante` no nulo / válido), **`cliente.Estado = Activo`** y **`viajantes.anulado = No`** (esquema legacy: `cliente` no tiene columna `anulado` en todas las bases). |
| Falta | **`Falta = Objetivo − Facturación − Remitos`** (importes del período de facturación/remitos del informe). |
| Total (columna tipo Excel) | **`Total = Facturación + Remitos`** (coherente con Falta). |
| Cantidades vendidas | En pantalla y export Excel la etiqueta es **«Unidades»**. Criterio numérico: el **mismo que movimientos de stock en ventas**: renglones tabla `stock` ligados a `cuentacliente` por `CodigoMovimiento`, tipos de comprobante FA/FB/FC/FE/FM y notas de crédito NCA…NCM, `stock.Anulado = 'No'`, `stock.TipoComp IN ('Venta', 'Venta TPV', 'Devol - Cliente', 'ND Anul NC')`, signo según factura vs NC (paridad [`reports/services/ventas_netas.py`](../../reports/services/ventas_netas.py) `_sum_unidades_sql_stock_line`). Rango de fechas: **rango facturación** del informe. |
| Solapes de objetivos | **Períodos activos** (cabecera con `anulado = No`): no deben solaparse entre sí. Por cliente y **dentro del mismo `id_periodo`**, el detalle se consolida al último `id` guardado. |
| Anulación | **No** se borra el detalle: la cabecera pasa a `anulado = Si` (paridad con otras tablas AdministraNET). El informe **no** aplica objetivos de períodos anulados. |
| Universo de filas (cliente) | Además de clientes con movimiento u objetivo en el **período** del filtro, se incluyen **todos los clientes con histórico de facturación neta** en `cuentacliente` (FA/FB/… neto de NC, `Anulado = No`), **sin acotar por la ventana de fechas** del informe. Si en el período no hubo ventas, el cliente **sigue figurando** y las columnas de facturación/remitos/unidades de ese período muestran **0** (salvo otros movimientos que sí caigan en el rango). Respeta exclusiones de clientes y de vendedores; **no** filtra sucursal en la consulta de histórico (solo en métricas por período donde aplique). |

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
  - Bajo cada cliente, opcionalmente **`venta_detalle`**: árbol **rubro → subrubro → artículo** con agregados de **`cantidades_vendidas`** y **`facturacion`** por nodo (misma ventana y filtros que la consulta de unidades del informe; importe por renglón coherente con criterio de ventas netas). En la tabla web, esas filas solo muestran datos en **Unidades** y **Facturación**; el resto de columnas se muestra como vacío/—. La UI replica expansión/colapso por vendedor, cliente, rubro y subrubro (persistencia en `localStorage` bajo clave `synap:report-view:ventas-objetivos-vs-bo:jerarquia`). Cabeceras en **mayúsculas**; grupo **VENTAS PERÍODO** con `colspan="4"` sobre **UNIDADES**, **FACTURACIÓN**, **REMITOS** y **TOTAL** (misma idea visual que **BACKORDER** sobre sus cuatro subcolumnas); columnas **OBJETIVO** (fondo verde suave) y **FALTA** (fondo rojo suave) con `rowspan="2"`; subcabecera **TOTAL** con tono violeta un poco más marcado; grupo **BACKORDER** con **BO TOTAL** al final más oscuro; fila **Totales** resaltada.
  - **Cabecera y scroll:** `thead` sticky en bloque único (como MPR ventana-pack). **Dos filas:** «VENDEDOR / CLIENTE / RUBRO», **OBJETIVO** y **FALTA** con `rowspan="2"`; en la primera fila, **VENTAS PERÍODO** (`colspan="4"`) y **BACKORDER** (`colspan="4"`); en la segunda fila, **UNIDADES**, **FACTURACIÓN**, **REMITOS**, **TOTAL** y las cuatro BO. En cada fila del cuerpo, **icono y nombre comparten una celda** (`flex`, `gap-1`): `padding-left` desplaza junto el chevron y el texto (sin columna vacía entre flecha y nombre). Jerarquía vendedor→cliente→rubro→subrubro→artículo con **el mismo incremento** de `padding-left` por nivel; chevrons **▸**/**▾** salvo en artículo (reserva de ancho). Solo **Rubro** y **Subrubro** llevan etiqueta discreta antes del nombre. En la grilla web **no** se muestran códigos numéricos junto al nombre; los códigos siguen en el JSON para toggles y exportación.
  - **Controles de grilla (web):** barra sobre la tabla con **Expandir todo** / **Contraer todo** (misma idea que `/ventas/objetivos-venta/<id>/`), **búsqueda predictiva** (mín. 2 caracteres, filtra por texto de vendedor/cliente/rubro/subrubro/artículo; la fila Totales no se oculta), valores numéricos **negativos en rojo** en celdas de importe y unidades (KPI «Total objetivo» en rojo si es negativo). Las utilidades Tailwind usadas en `reports/static/reports/js/objetivos_ventas_bo.js` deben entrar en el build: en `theme/static_src/tailwind.config.js` el `content` incluye `../../reports/static/**/*.js`. Bloque KPI y tabla separados visualmente (`margin` entre secciones).
  - **KPI «Falta para el objetivo»:** muestra siempre el **valor absoluto** de la brecha agregada (`|Σ objetivo − facturación − remitos|`). **Rojo** (tarjeta, importe, icono y texto de estado) si la brecha es **pendiente** (falta mayor que cero: aún no se alcanza el objetivo total). **Verde** si **objetivo alcanzado** (brecha cero) o **superado** (brecha negativa en el dato bruto). Debajo del importe, una línea **Estado: …** explica el significado para evitar confusiones con el signo en la tabla detalle.
  - **Grilla (robustez):** el cliente normaliza `meta.extra.tabs.objetivos_jerarquia` a array (incluye intento de `JSON.parse` si llegara como string). Si el árbol viene vacío pero `data` tiene filas planas, se reagrupa por vendedor en el navegador (sin rubro/subrubro/artículo). Se ignoran nodos `null` en `children` del árbol. Cualquier excepción al renderizar muestra mensaje en el contenedor en lugar de dejar el texto «Cargando…».
  - **KPI icono SVG:** no asignar `className` al `<svg id="vo-kpi-falta-icon">` (en SVG es de solo lectura); usar `setAttribute("class", …)` vía helper en `objetivos_ventas_bo.js`.

- **Exportación Excel** (`ExportService`): mismas columnas y **orden** que la tabla web (objetivo, falta, unidades, facturación, remitos, total, BO c/stock, BO c/ingreso, BO s/stock, BO total). Cabeceras de datos en **mayúsculas**. Filas ordenadas por **cód. vendedor** y luego **cód. cliente**. Se inserta una **fila de encabezado por vendedor** (texto «Vendedor {cod} — {nombre}») y las filas de clientes quedan con **nivel de esquema 1** bajo esa sección (`outlinePr` con resumen arriba), de modo que Excel permite **contraer/expandir** el bloque de clientes por vendedor. Nombre de archivo descargado: **`Ventas_objetivo_vendedores_{fecha_inicio_facturación}_{fecha_fin_facturación}.xlsx`** (filtros `fecha_inicio_facturacion` / `fecha_fin_facturacion`; si falta alguna fecha, el segmento se reemplaza por `sin_fecha`).

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
