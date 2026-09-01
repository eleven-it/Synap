# 04 — Catálogo de Pantallas

**Estado:** COMPLETE | ~250–300 pantallas únicas (471 templates incl. partials)

## Metodología

Screen = ruta HTTP única con template render principal. Partials/includes no cuentan como pantalla.

## Resumen por módulo

| Module | Screens est. | Template ref | Criticality |
|--------|-------------:|--------------|:-----------:|
| mpr | ~95 | `base_mpr.html` | HIGH |
| core | ~55 | `base_app.html` | HIGH |
| ecom | ~35 | `base_pedidos.html`, `base_app` | HIGH |
| reports | ~18 | `dashboard_detail.html` | HIGH |
| self_checkout | ~18 | `base_tpv.html` | HIGH |
| tiendanube | ~22 | `base_app.html` | MEDIUM |
| stock | ~15 | `base_app.html` | HIGH |
| ventas | ~8 | mixed | MEDIUM |
| login | ~10 | `login_base.html` | CRITICAL |
| contabilidad | ~8 | `base_app.html` | MEDIUM |
| ia | ~4 | `base_app.html` | LOW |
| compras/captura | ~5 | `base_app.html` | MEDIUM |

## Pantallas canónicas (referencia diseño)

| ID | Name | URL | Template | Purpose |
|----|------|-----|----------|---------|
| SCR-R01 | Dashboard reporte genérico | `/reports/dashboard/<slug>/` | `dashboard_detail.html` | Informe interactivo |
| SCR-R02 | Command Center | `/reports/dashboard/command-center-gerencial/` | `command_center.html` | KPIs gerenciales |
| SCR-M01 | MPR Wizard | `/mpr/wizard/` | `wizard.html` | Flujo OPT |
| SCR-M02 | OPT lista | `/mpr/opt/` | `opt_list.html` | Listado producción |
| SCR-M03 | OPT detalle | `/mpr/opt/<id>/` | `opt_detail.html` | Detalle OPT |
| SCR-E01 | Pedidos hub | `/ecom/mayoristapp/pedidos/` | `pedidos_hub.html` | Kanban pedidos |
| SCR-S01 | Alta movimiento | `/stock/ingreso-movimiento/` | `alta_movimiento.html` | Stock + QR |
| SCR-T01 | Kiosco TPV | `/self_checkout/kiosco/<id>/` | kiosco templates | Venta |
| SCR-L01 | Login | `/login/` | `login.html` | Auth |

## Pantallas con deuda explícita

| Screen | Issue |
|--------|-------|
| `ventas/objetivos_venta.html` | Excluida canon — rediseñar |
| `ventas/presupuesto_*.html` | Excluida canon |
| `* 2.html` duplicates | Legacy drift |
| `dashboard_detail.html` | ~5300 líneas monolito |

## Ficha tipo (aplicar a cada screen en refactor)

```text
ID, Name, URL, Module, Template, Purpose, Roles, Actions,
Data sources, APIs, Components, Nav entry, Responsive, UX issues, Criticality
```

*Detalle completo por pantalla disponible bajo demanda en fase de refactor por módulo.*
