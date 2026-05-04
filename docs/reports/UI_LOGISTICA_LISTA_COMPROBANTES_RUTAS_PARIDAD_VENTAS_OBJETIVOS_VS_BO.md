# Paridad visual — Lista comprobantes en rutas vs. Ventas objetivos vs BO

**Fecha de referencia:** 30/04/2026  
**Informes:** `comprobantes-rutas` (Synap) y `ventas-objetivos-vs-bo` (tabla jerárquica VO).

## Objetivo

Unificar la **experiencia de contenedor, scroll, toolbar y celdas** del listado logístico con los patrones ya probados en **Ventas objetivos vs BO**, sin copiar la semántica de cabecera en dos filas ni la paleta por grupos de columnas de ese informe.

## Cambios aplicados (resumen)

| Área | Antes | Después (paridad VO) |
|------|--------|----------------------|
| Card del widget (`dashboard_detail.html`) | `shadow-lg` + hover translate | Para este slug: `border-slate-200/90`, `shadow-sm`, sin hover translate (misma familia que la sección de tabla VO). |
| Scroll | `max-h-[500px]` en un `div` creado por JS | Contenedor `#logistica-lista-cr-scroll` en plantilla: `h-[min(75vh,56rem)] min-h-[14rem] overflow-auto overscroll-contain` (igual que `#vo-jerarquia-container`). **Cabecera fija:** cada `th` lleva `sticky top-0` + `z-10`; la tabla **no** usa `overflow-hidden` para que el sticky respete ese scrollport. |
| Tabla (`dashboard.js`) | Clases propias + scroll interno | `vo-jerarquia-table`, **rejilla** `border` en cada `th`/`td` (como celdas VO), contenedor con `border` + `rounded-t-md`. |
| Celdas | `px-3 py-2` + bordes por celda | `LOGISTICA_LISTA_CR_TD_*` + **`logisticaListaCrColumnStyle`**: alineación cabecera/cuerpo (fechas y comprobantes a la derecha con `tabular-nums`, estados centrados, textos largos a la izquierda); franjas pastel por bloque (esmeralda, ámbar, violeta, etc.); **TOTAL REMITO** violeta y **ACCIONES** cielo (misma lógica visual que columnas TOTAL / BO TOTAL en VO). Las alineaciones de importe y acciones siguen gobernadas por `synap-lc-col-money` / `synap-lc-col-actions`. |
| Toolbar | Borde `slate-100` | Misma base que `#vo-bo-toolbar` (`mb-3`, `border-slate-200`, `gap-x-2`, etc.). |
| Estilos Synap | Se mantienen | `ensureSynapLogisticaListaCrTableStylesOnce` sigue activo por **Tailwind CDN** + clases generadas solo en JS (`base_app.html`). |

## Archivos tocados

- `reports/templates/reports/dashboard_detail.html`
- `reports/templates/reports/includes/logistica_lista_comprobantes_rutas_tabla_toolbar.html`
- `reports/static/reports/js/dashboard.js`

## Filas de agrupación (sin rejilla vertical)

Cuando hay «Agrupar por», cada fila de grupo se renderiza con **una sola celda** `colspan` = número de columnas (`renderLogisticaGroupedTreeHtml` en `dashboard.js`): barra continua con borde perimetral, título + chevron a la izquierda e importes de totales por columna métrica alineados a la derecha, **sin** líneas verticales que simulen columnas en esa fila.

El detalle va en **tablas anidadas** dentro de `tr.logistica-group-children`: clase `logistica-group-nested` (ancho 100 %, sin borde exterior) + **fila ancla** `logistica-col-anchor` al inicio del `tbody` principal (una `td` por columna, altura 0) para que la rejilla del cuerpo coincida con el `thead` y el `colgroup`. El scroll `#logistica-lista-cr-scroll` usa `[scrollbar-gutter:stable]` para reducir saltos por barra vertical.

**Contenido en celdas:** `min-w-0`, `max-w-full`, `break-words` y `px-2.5` en celdas base; fechas/hora de ruta y cabeceras largas sin `whitespace-nowrap` en el cuerpo; números de remito/factura siguen en una línea. Importes siguen con `nowrap` solo en `.synap-lc-money-inner`.

## Columna «MOTIVO NO ENTREGA»

No se muestra en la grilla (no forma parte del orden fijo `logisticaListaCrOrder` en `dashboard.js`). El campo sigue en la respuesta del API y en cada fila; la **búsqueda en tabla** también considera `motivo_no_entrega` vía `LOGISTICA_LISTA_CR_SEARCH_KEYS_EXTRA`, para poder filtrar por texto del motivo sin ver la columna.

## Fuera de esta paridad

- Cabecera de dos niveles y colspan de grupos (Objetivo / Ventas / BO) del informe VO.
- KPIs superiores del bloque VO.

## Referencias de código

- VO tabla / `tdNum`: `reports/static/reports/js/objetivos_ventas_bo.js`
- VO shell scroll: `reports/templates/reports/dashboard_detail.html` (`#vo-jerarquia-container`)
