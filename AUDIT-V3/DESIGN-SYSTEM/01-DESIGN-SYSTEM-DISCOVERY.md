# 01 — Design System Discovery

**Estado:** COMPLETE

Synap **no tiene Design System formal** pero existe un **sistema implícito** documentado en:

- `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md`
- `openspec/specs/ui-fuente-verdad-reportes-mpr/spec.md`
- Patrones repetidos en `base_app.html`, `base_mpr.html`, `dashboard_detail.html`

## Familias visuales

| Family | Apps | Character |
|--------|------|-----------|
| **Reports** | reports | Hero oscuro slate, sky/violet accents, D3 widgets |
| **MPR** | mpr (+ aligned ecom/ventas) | Purple accent, dense tables, quick-nav |
| **App shell** | core, stock, TN, etc. | Navbar + status bar, `base_app` |
| **TPV** | self_checkout | Touch-first, simplified chrome |
| **Login** | login | Gradient purple standalone |

## Componentes compartidos reales

| Asset | Path |
|-------|------|
| SynapMessages | `theme/static/js/synap-messages.js` |
| Post-loading modal | `theme/templates/partials/synap_post_loading_modal.html` |
| MPR aviso modal | `mpr/templates/mpr/includes/mpr_aviso_modal.html` |
| Navbar | `theme/templates/partials/navbar.html` |
| Manual ayuda btn | `templates/includes/btn_manual_ayuda.html` |

## Gap vs canon

Ventas presupuestos/objetivos — **outside** design system reference until rewritten.
