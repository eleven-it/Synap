# 07 — Patrones de Tabla / Data Grid

**Estado:** COMPLETE | **Crítico para ERP**

## Implementaciones distintas (~5)

| # | Context | Features | File |
|---|---------|----------|------|
| 1 | MPR lists | sort implicit, dense, row actions | `opt_list.html`, `parte_produccion.html` |
| 2 | Reports widgets | dynamic columns, export | `widget_engine.js` |
| 3 | Stock inventario | filters + tabla partial | `stock/inventario/_tabla.html` |
| 4 | Ecom hub | kanban (not table) + list views | `pedidos_hub.html` |
| 5 | Core admin | usuarios, roles standard tables | `core/templates/core/` |

## Feature matrix

| Feature | MPR | Reports | Stock | Core |
|---------|:---:|:-------:|:-----:|:----:|
| Sorting | Partial | Yes | Partial | Yes |
| Filtering | Yes | Yes | Yes | Yes |
| Search | Yes | Yes | Yes | Yes |
| Pagination | Yes | Yes | Yes | Yes |
| Selection/bulk | Rare | Some | No | Rare |
| Sticky header | Some | Yes | No | No |
| Totals row | Yes | Yes | Some | No |
| Export | CSV/XLSX | XLSX | XLSX | No |
| Responsive | scroll-x | scroll-x + sheet | mobile variant | scroll-x |
| Row actions | Yes | drill-down | Yes | Yes |
| Keyboard | Partial | Partial | **QR focus** | Partial |

## Information density

- MPR tables: **high density** — intentional for operarios
- Reports: medium-high with widget cards
- **Recommendation:** preserve compact row height in operational tables; improve scanability via typography hierarchy not whitespace reduction

## Target

Single `DataGrid` composite pattern in design system with density prop: `compact` | `comfortable`.
