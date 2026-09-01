# 10 — Evaluación Responsive

**Estado:** COMPLETE

## Clasificación por capacidad

| Capability | Classification | Evidence |
|------------|----------------|----------|
| MPR parte operario móvil | **MOBILE CRITICAL** | `mpr/mobile/parte_operario.html` |
| Stock conteo inventario | **MOBILE CRITICAL** | `stock/conteo/mobile/` |
| TPV kiosco | **MOBILE CRITICAL** (tablet) | `base_tpv.html` |
| Ecom pedidos hub (PWA) | **MOBILE USEFUL** | `pwa_nivel_a.py` includes ecom |
| Reports dashboards | **DESKTOP PRIMARY** | `reports_responsive.js` partial |
| MPR wizard / OPT admin | **DESKTOP ONLY ACCEPTABLE** | dense tables |
| Contabilidad auditoría | **DESKTOP PRIMARY** | export tables |
| Core usuarios/permisos | **DESKTOP PRIMARY** | forms wide |
| TN configuration | **DESKTOP ONLY ACCEPTABLE** | complex wizard |

## Breakpoints

- Tailwind defaults (`sm`, `md`, `lg`, `xl`, `2xl`)
- MPR container: `px-3 … 2xl:px-12` (`mpr-contenedor-pagina`)
- No custom breakpoints in `tailwind.config.js` (`extend: {}` empty)

## PWA

- `theme/static/sw.js` service worker
- Icons `theme/static/img/pwa/icon-*.png`
- Mobile Level A restricts menu (`core/pwa_nivel_a.py`)

**Not all ERP screens need mobile parity** — document per capability.
