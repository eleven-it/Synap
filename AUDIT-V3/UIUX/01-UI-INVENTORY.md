# 01 — Inventario UI

**Estado:** COMPLETE | **471 plantillas HTML**

## Stack

| Capa | Tecnología | Evidencia |
|------|------------|-----------|
| Templates | Django | `*/templates/` |
| CSS | Tailwind 3 + CDN runtime | `theme/`, `cdn.tailwindcss.com` en `base_app.html` |
| JS | Alpine 3 (~85 templates), vanilla ES modules | `unpkg.com/alpinejs` |
| Charts | D3 (reports) | `reports/static/reports/vendor/d3.min.js` |
| Icons | Material Icons (CDN) | `navbar.html` |
| Font | Inter (Google Fonts) | `font-inter` |

## Layouts base

| Layout | Uso | Templates |
|--------|-----|----------:|
| `theme/templates/base_app.html` | Shell principal | ~140 |
| `mpr/templates/mpr/base_mpr.html` | Canon MPR + aligned | 63 |
| `login/login_base.html` | Login standalone | 5 |
| `self_checkout/base_tpv.html` | TPV | 15 |
| `ecom/base_pedidos.html` | Hub pedidos | 8 |

## Por módulo

| App | Templates | UI density |
|-----|----------:|------------|
| mpr | 109 | Alta — tablas, wizard, móvil |
| core | 68 | Media — forms admin |
| self_checkout | 53 | Media — kiosco |
| tiendanube | 45 | Media |
| ecom | 45 | Alta — kanban, matriz |
| reports | 36 | Alta — dashboards |
| stock | 22 | Media — tablas + móvil |
| login | 21 | Baja |

## UI canónica (normativa)

**Fuente:** `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md`

- Reports: `reports/dashboard_detail.html`
- MPR: `mpr/base_mpr.html`, `wizard.html`, `opt_list.html`, `opt_detail.html`
- **Excluido como referencia:** `ventas/objetivos-venta`, `ventas/presupuestos`

## JS modules (selección)

- `theme/static/js/synap-messages.js` — toasts globales
- `reports/static/reports/js/widget_engine.js` — dashboards declarativos
- `ecom/static/ecom/js/pedidos_shell.js` — hub pedidos
- `mpr/static/mpr/js/modal_comprobante_movimiento.js`
