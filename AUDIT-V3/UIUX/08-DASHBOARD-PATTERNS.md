# 08 — Patrones de Dashboard

**Estado:** COMPLETE

## Tipos

| Type | Example | Engine |
|------|---------|--------|
| Interactive report | `/reports/dashboard/<slug>/` | declarative-v1 + widget_engine |
| Executive summary | `executive_summary.html` | dedicated JS |
| Command center | `command_center.html` | `command_center.js` |
| MPR tablero | `/mpr/` tablero_produccion | server render + charts |
| Core module dashboard | `/core/dashboard/` | module cards |

## Componentes dashboard reports

- Hero slate + action bar (`dashboard_detail.html`)
- Filter includes (`reports/includes/filters_*.html` — 21 variants)
- KPI widgets (cards, gauges, tables)
- D3 charts (`widget_engine.js`)
- Export Excel button → `/api/reports/export/`
- Fullscreen mode (`body.reports-fullscreen`)
- Loading: widget-level spinners

## Metric → source mapping (pattern)

Each widget config JSON links:
- `metric_id` → SQL expression or runner
- `filters` → session base_empresa + user filters
- Business meaning: documented in ReportDefinition.description (PG)

## Issues

- `dashboard_detail.html` monolith (~5300 lines)
- Per-slug legacy JS files coexist with declarative engine
- Filter UX inconsistent across 21 filter partials
