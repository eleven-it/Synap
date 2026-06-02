# Informes Synap — UI móvil (responsive)

## Alcance

Todo el módulo `/reports/` está permitido en dispositivos móviles (middleware Nivel A). La presentación usa el mismo diseño en **escritorio** (`lg` y superior) y tarjetas en **móvil** (`< lg`, 1023px).

## Implementación

| Pieza | Rol |
|-------|-----|
| `reports/static/reports/js/reports_responsive.js` | Utilidad compartida: `mountDualTableView`, `enhanceWidgetTableContainer`, `installAutoEnhance` |
| `dashboard.js` → `renderTable` | Tablas genéricas y logística: dual view al renderizar |
| `widget_engine.js` → `renderTable` / `renderTableWithGrouping` | Widgets declarativos (pedidos, ventas netas, etc.) |
| Auto-mejora en `#dashboard-root` | Tablas dinámicas (BO stock, pestañas con HTML inyectado) |

## Patrón visual

- **Escritorio:** `hidden lg:block` + tabla actual (sin cambios de estilos).
- **Móvil:** `lg:hidden` + tarjetas (`rounded-xl`, mismos tokens slate/sky que Command Center).

Informes con lógica propia (Command Center modales, resumen ejecutivo, movimientos detallados de caja) conservan su JS dedicado; el patrón es equivalente.

## Tarjetas por informe

| Slug / variante | Comportamiento móvil |
|-----------------|----------------------|
| `pedidos-pendientes` | Tarjeta por comprobante (cliente, fecha, importe) |
| `stock-existencias` | Tarjeta por renglón (artículo, depósito, stock/disponible) |
| `cash_flow_by_account` | Tarjeta por caja (saldos y flujos) |
| `ventas-por-articulo` | Tarjeta por artículo (unidades + facturación) |
| `ventas-objetivos-vs-bo`, `ventas-por-vendedor` | Tarjeta por vendedor (métricas resumidas) |
| Resto (genérico) | Tarjeta derivada de columnas de la tabla |

## Límites

- Hasta **250** filas en tarjetas móvil por rendimiento; el resto se indica en leyenda.
- Workspace **TV** (`data-workspace-tv`): solo tabla (sin tarjetas).
- Gráficos D3: se adaptan por contenedor; no se duplican en tarjetas.
- Jerarquías VO en móvil muestran nivel resumido (artículo o vendedor); el detalle anidado completo queda en escritorio.

## Referencias

- `docs/general/MOBILE_SOLO_NIVEL_A.md` — política de rutas móviles.
- `core/middleware/mobile_level_a_middleware.py` — prefijos `/reports/` y `/api/reports/`.
