# 14 — Arquitectura Frontend

**Estado:** COMPLETE (Fase 14)  
**Fecha:** 25/08/2026

---

## Stack tecnológico

| Tecnología | Versión/Uso | Ubicación |
|------------|------------|-----------|
| Django Templates | SSR principal | `*/templates/` (~977 HTML) |
| Tailwind CSS | 3.x via django-tailwind | `theme/static_src/`, `theme/static/` |
| Alpine.js | Embebido en templates | MPR, ecom, reports, core |
| JavaScript ES Modules | `.mjs` | `ecom/static/ecom/js/` |
| D3.js | Gráficos reportes | `reports/static/` |
| Crispy Forms + Tailwind | Formularios | settings CRISPY_TEMPLATE_PACK |
| PWA | Service Worker | `sw.js`, `manifest.json` |
| WebAuthn | Passkeys | login PWA |

**No hay React/Vue/Angular** en la app principal. React solo en `support/frontend/`.

**Clasificación:** CONFIRMADO POR CÓDIGO

---

## Patrones UI

### Canon UI Synap

Fuente de verdad: `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md`

| Patrón | Referencia | Uso |
|--------|-----------|-----|
| Dashboard reportes | `reports/dashboard_detail.html` | Informes |
| Wizard MPR | `mpr/wizard.html`, `mpr/base_mpr.html` | Producción |
| Lista OPT | `mpr/opt_list.html`, `opt_detail.html` | OPT |
| Hub pedidos | `ecom/pedidos_hub.html` | E-commerce |
| Modales Synap | Overlay + panel (no alert/confirm) | Global |

**Excluidos del canon:** ventas/objetivos-venta, ventas/presupuestos (hasta levantamiento explícito).

### Server-Side Rendering (SSR)

Flujo dominante:
```
View → Template Django → context_processors (menú, permisos, empresa)
     → Tailwind CSS → HTML → Browser
     → Alpine.js hidrata interactividad
     → fetch() a APIs internas para datos dinámicos
```

### Módulos con JS significativo

| Módulo | Archivos JS/MJS | Patrón |
|--------|:--------------:|--------|
| ecom | 30+ .mjs | Alpine mixins modulares (carrito, catálogo, checkout) |
| mpr | 15+ .js | Tablero, wizard, grilla editable |
| reports | 10+ .js | Dashboard widgets, filtros, export |
| self_checkout | 8+ .js | TPV, scanner, caja |
| core | 5+ .js | Dashboard, PWA, device hint |

---

## Estado y APIs consumidas

| Pantalla | Estado | API consumida |
|----------|--------|--------------|
| Dashboard reportes | Alpine + fetch | `/api/reports/dashboards/{slug}/data/` |
| Hub pedidos ecom | Alpine local | `/ecom/api/pedidos/` |
| Compra mayorista | ES modules + Alpine | `/ecom/api/catalogo/`, `/ecom/api/carrito/` |
| TPV self-checkout | Alpine + fetch | `/api/self-checkout/*` |
| MPR tablero | Alpine + grilla | `/mpr/api/tablero/` |
| Captura factura | Alpine + fetch | `/api/compras/expediente/` |

---

## PWA y móvil

| Componente | Archivo | Función |
|------------|---------|---------|
| Service Worker | `core/views/pwa_views.py` → `sw.js` | Cache offline |
| Manifest | `manifest.json` | Instalable |
| Nivel A móvil | `core/pwa_nivel_a.py` | Restricción rutas móvil |
| Device hint | `core/views/device_views.py` | Cookie `device_hint` |
| Offline page | `templates/offline.html` | Fallback |

Rutas Nivel A: login, TPV, pedidos ecom, perfil, PWA.

---

## Lógica de negocio en frontend

| Ubicación | Lógica | Riesgo |
|-----------|--------|--------|
| `ecom/static/ecom/js/compra_mayorista_*.mjs` | Cálculo totales, validación carrito | Media — debe re-validarse en backend |
| `mpr/static/` tablero | Cálculo KPIs locales | Baja — datos vienen del server |
| `reports/static/` | Formateo fechas, agregaciones display | Baja |
| `self_checkout/static/` | Cálculo vuelto, descuentos | **Alta** — validar server-side |

**Regla:** Toda lógica crítica de negocio debe existir en backend. Frontend es presentación + UX.

---

## CSS y theming

- `theme/static_src/input.css` → Tailwind build → `theme/static/css/`
- Node 20 en Docker para build CSS
- Dark mode: no implementado globalmente
- CDN Cloudflare para estáticos en producción

---

*Generado por auditoría READ ONLY.*
