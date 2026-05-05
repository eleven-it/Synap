# UI catálogo de reportes (`/reports/`)

## Vista lista: iconografía por reporte

En la vista **Lista** del catálogo (`reports/templates/reports/partials/_catalog_list.html`), cada fila usa un ícono y color representativo según `slug`/nombre del reporte:

- **Caja / flujo**: verde/teal, ícono de cruce financiero.
- **Stock / inventario / BO**: índigo/violeta, ícono de caja.
- **Ventas / facturación / comprobantes**: azul/celeste, ícono de documento.
- **Pedidos / logística / rutas / entregas**: ámbar/naranja, ícono de transporte.
- **Resumen ejecutivo / KPI**: fucsia/púrpura, ícono de tendencia.
- **Fallback**: gris pizarra para reportes no clasificados.

## Criterio técnico

- El contenedor del ícono se marca con `data-report-list-icon`.
- Un script inline (`applyCatalogListIcons` + `resolveReportListVisual`) resuelve:
  - `path` SVG del ícono
  - clases de color para fondo/ring/texto en claro y oscuro
- El estilo resultante se aplica con clases Tailwind que incluyen variantes `dark:*`.

## Objetivo UX

Mejorar el reconocimiento visual rápido en modo lista, manteniendo contraste y legibilidad en ambos temas (claro/oscuro).
