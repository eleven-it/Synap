# Design: Inventario por depósito → catálogo Reportes

## Architecture

```
Menu Reports / MPR / Catalog
        │
        ▼
/reports/dashboard/inventario-deposito-articulo/
        │
        ├─ GET  DashboardDetailView (template dedicada)
        ├─ POST /api/reports/query/  → inventario_deposito_runner
        └─ POST /api/reports/export/?type=xlsx → export_service
                │
                ▼
        mpr.services_inventario_deposito.consultar_inventario_deposito
                ├─ hoy → stock_deposito
                └─ pasado → stock.saldos_stock_a_fecha
```

Hub legacy: `GET /mpr/reportes/?grupo=demanda&reporte=inventario_deposito` → 302 al dashboard.

## Permissions

| Superficie | Regla |
|------------|-------|
| Dashboard GET | `reports.view_operational` **o** `mpr.reportes` **o** `mpr.ver` |
| Query/Export API | Misma OR **solo** si `slug=inventario-deposito-articulo`; resto de informes sin cambio |

## UI

Plantilla dedicada (no inflar `dashboard_detail.html`):

- Hero: título, breadcrumb catálogo, 3 KPIs, Actualizar, Exportar Excel
- Filtros: fecha_corte, depósitos, marcas, q, incluir_2da (default No)
- Tabla jerárquica Depósito → Marca → filas (Artículo, Talle, Stock, UM, Docenas)
- Paleta slate/sky Reportes; sin diálogos nativos

## Export

Solo Excel vía API (`export_service` → columnas Depósito, Marca, Artículo, Talle, Stock, Docenas + TOTAL SUM(docenas)).

## Risks

- Usuarios MPR sin `reports.view_operational` → mitigado con OR
- Migración 0038 vs tip Desarrollo (0037 BOM) → depender del tip real al mergear
- `dashboard.js` monolítico → JS dedicado `inventario_deposito.js`
