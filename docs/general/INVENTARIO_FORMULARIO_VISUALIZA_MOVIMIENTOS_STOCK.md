# Inventario: Listado de movimientos de stock (Consultas y Anulaciones)

Referencia VB6: **Visualiza_CargaMovStock.frm**. Este documento inventaria la parte de **consulta/listado** de movimientos (no el flujo "visualizar y re-guardar"). Synap migra listado + detalle + PDF; la reconfirmación desde el visor se deja para una fase posterior.

## 1. Objetivo del formulario origen

- Consultar movimientos de stock ya grabados (movimiento_stock + stock).
- Filtrar por fecha, depósito, motivo, número de comprobante.
- Abrir detalle de un movimiento y opcionalmente re-guardar (VB6); en Synap solo lectura + PDF.

## 2. Inventario de componentes (listado)

| Componente VB6 / Origen     | Descripción                         | Equivalente Synap                          |
|-----------------------------|-------------------------------------|--------------------------------------------|
| Criterios de búsqueda       | Filtros para acotar la lista        | Form GET: fecha desde/hasta, depósito, motivo, nro. comprobante |
| Grilla / lista de movimientos | Filas: comprobante, fecha, motivo, depósitos, detalle, usuario | Tabla HTML con columnas equivalentes        |
| Acción "Ver / Abrir"        | Abrir detalle del movimiento       | Enlace a `stock:detalle_movimiento`        |
| Comprobante / Impresión     | Ver o imprimir comprobante         | Enlace a `stock:movimiento_pdf`             |

## 3. Campos del listado (columnas)

| Campo origen              | Origen (tabla/campo)           | Synap (listar_movimientos)     |
|---------------------------|---------------------------------|--------------------------------|
| Código movimiento         | movimiento_stock.codigo_movimiento | codigo_movimiento              |
| Nro. comprobante          | movimiento_stock.nro_comprobante  | nro_comprobante                |
| Fecha                     | movimiento_stock.fecha            | fecha                          |
| Motivo                    | movimiento_stock.motivo_movimiento| motivo_movimiento              |
| Dep. origen               | movimiento_stock.deposito_origen   | nombre_dep_origen (resuelto)    |
| Dep. destino              | movimiento_stock.deposito_destino  | nombre_dep_destino (resuelto)   |
| Detalle                   | movimiento_stock.detalle           | detalle                        |
| Usuario                   | movimiento_stock.id_usuario       | id_usuario (o nombre si se agrega luego) |

## 4. Filtros

| Filtro        | Tipo    | Origen VB6        | Synap (GET)     |
|---------------|---------|-------------------|-----------------|
| Fecha desde   | Fecha   | Criterio búsqueda | fecha_desde     |
| Fecha hasta   | Fecha   | Criterio búsqueda  | fecha_hasta     |
| Depósito      | Combo   | Depósito          | id_deposito     |
| Motivo        | Combo   | Motivo            | motivo          |
| Nro. comprobante | Texto | Nro comprobante    | nro_comprobante |
| **Agrupar por** | Combo  | —                 | agrupar_por     |

## 5. Agrupaciones (artefacto BO – aplicada sobre los resultados)

La **agrupación está separada de la búsqueda**: el formulario de filtros (fecha, depósito, motivo, nro. comprobante) se envía con **Buscar**; los resultados se muestran en tabla. Encima de la tabla aparece el control **"Agrupar por"** (mismo artefacto que en reportes BO): etiqueta, campo "Buscar campo de agrupación...", chips y texto *"Puedes seleccionar múltiples campos para agrupar. El orden determina los niveles de agrupación. Se aplica sobre los resultados mostrados."*

- **Comportamiento:** La agrupación se aplica **en el cliente** sobre los movimientos ya cargados (no se reenvía el formulario). Al elegir o quitar campos, la tabla se reagrupa al instante.
- **UI:** `<select multiple>` oculto + contenedor de tags (chips + input + dropdown). No forma parte del formulario de búsqueda.
- **Tabla agrupada:** Filas de encabezado por grupo (chevron para colapsar/expandir, indentación por nivel, cantidad de movimientos). Cada grupo puede estar **colapsado** (solo se ve el encabezado) o **expandido** (se ven las filas hijas). Por defecto los grupos inician colapsados, como en el reporte BO Backorder.

| Valor `agrupar_por`   | Etiqueta           | Orden de grupos                          |
|-----------------------|--------------------|------------------------------------------|
| fecha                 | Fecha              | Fechas en orden descendente (más reciente primero) |
| motivo_movimiento     | Motivo             | Alfabético por nombre de motivo          |
| nombre_dep_origen     | Depósito origen    | Alfabético por nombre de depósito        |
| nombre_dep_destino    | Depósito destino   | Alfabético por nombre de depósito        |
| nombre_usuario        | Usuario            | Alfabético por nombre de usuario         |

Si no se selecciona ningún campo, la tabla se muestra plana (sin agrupación). Referencia de diseño: **reports/templates/reports/dashboard_detail.html** (tabs BO) y **reports/static/reports/js/bo_stock_facturacion.js** (`initializeBoGroupByUI`).

## 6. Acciones por fila

- **Ver detalle:** navegación a `/stock/movimientos/<codigo_movimiento>/`.
- **Descargar PDF:** enlace a `/stock/movimientos/<codigo_movimiento>/pdf/`.

## 7. Comparación origen vs Synap

- **Listado:** Implementado en Synap con filtros (fecha, depósito, motivo, nro. comprobante), selector **Agrupar por** (fecha, motivo, dep. origen, dep. destino, usuario) y tabla con nombres de depósito y usuario resueltos; cuando hay agrupación, filas de encabezado por grupo con cantidad de movimientos.
- **Detalle:** Página de detalle con cabecera y renglones (solo lectura); enlace al PDF.
- **Tabla de renglones en detalle:** Columnas Código, Descripción, **Depósito** (nombre del depósito de cada fila, para identificar entrada/salida), Entrada, Salida, **Saldo** (saldo del artículo en ese depósito tras el movimiento). Los datos vienen de `obtener_renglones_movimiento`, que enriquece cada renglón con `nombre_deposito` vía `get_nombres_depositos`.
- **Anulaciones:** No migrado en esta fase (VB6 puede anular desde el visor); queda como extensión futura.
- **Re-guardar desde visor:** No migrado; Synap usa solo "Ingreso Mov. Stock" para alta.

## 8. Referencias

- [ANALISIS_FORMULARIOS_STOCK_INVENTARIO_VB6.md](ANALISIS_FORMULARIOS_STOCK_INVENTARIO_VB6.md)
- [INVENTARIO_ACEPTAR_MOVIMIENTO_STOCK.md](INVENTARIO_ACEPTAR_MOVIMIENTO_STOCK.md)
- Servicio: `core.services.administranet_stock.listar_movimientos`, `get_nombres_depositos`, `get_depositos`, `MOTIVOS_MOVIMIENTO`.
