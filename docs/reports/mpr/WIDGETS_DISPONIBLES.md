# Widgets de gráfico disponibles (reportes MPR y módulo Reports)

Los reportes del dashboard pueden usar distintos tipos de widget. En el código (`reports/static/reports/js/dashboard.js`) están registrados los siguientes.

## Tipos de widget

| Tipo            | Uso típico                          | Config típica |
|-----------------|-------------------------------------|---------------|
| **d3-bar**      | Barras simples (categoría vs número) | `x_field`, `y_field` |
| **d3-bar-grouped** | Barras agrupadas por categoría     | `x_field`, `y_field`, `group_field` |
| **d3-bar-stacked** | Barras apiladas                    | `x_field`, `y_field`, `group_field` |
| **d3-cards**    | Tarjetas KPI (valores resumidos)     | `fields` (lista de campos) o datos `{ label, value }` |
| **d3-line**     | Líneas / tendencia en el tiempo      | `x_field`, `y_fields` |
| **d3-line-area**| Área bajo la línea                   | igual que d3-line |
| **d3-area**     | Gráfico de área                      | `x_field`, `y_field` |
| **d3-heatmap**  | Mapa de calor                        | según config |
| **d3-gauge**    | Medidor / gauge                      | según config |
| **d3-waterfall**| Gráfico cascada (flujo)              | usado en cash flow |
| **d3-lollipop** | Gráfico de paletas                   | `x_field`, `y_field` |
| **d3-bullet**   | Bullet chart                         | según config |
| **d3-connected-scatter** | Scatter conectado              | según config |
| **pivot-table** | Solo tabla (sin gráfico)             | columnas/dimensiones |

## Para "Resumen pedidos por estado" (mpr-pedidos-estado)

Los datos son una lista de `{ estado, cantidad }` (ej. Pendiente, Producción, Parcial, Terminado).

- **Recomendado: d3-bar**  
  Gráfico de barras: eje X = estado, eje Y = cantidad.  
  Config: `{ "x_field": "estado", "y_field": "cantidad" }`.

- **Alternativa: d3-cards**  
  Si se transforman los datos a lista de `{ label, value }`, se pueden mostrar como tarjetas (similar a Total consolidado operativo).

- **Tabla: pivot-table**  
  Muestra la misma información en tabla; si no hay otro widget, el dashboard ya muestra una tabla por defecto para reportes MPR.

## Cómo se asigna el widget

- **Por migración**: se crea un `ReportWidget` vinculado al `ReportDefinition` (slug del reporte), con `widget_type` y `configuration` en JSON.
- **Por catálogo/builder**: en el módulo Reports, al editar el reporte se puede agregar o cambiar widgets y su configuración.

La migración `0032_add_mpr_pedidos_estado_widget` agrega un widget **d3-bar** al reporte `mpr-pedidos-estado` con la config anterior.
