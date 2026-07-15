# 10 · Estado de implementación — Rediseño UI toma de pedidos

**Change SDD:** `redisenio-ui-toma-pedidos`  
**Fecha cierre F5:** 10/07/2026  
**Alcance:** solo frontend (`/ecom/mayoristapp/compra/` + coherencia mínima hub/listados/detalle)

---

## Resumen

| Fase | Estado | Checkpoint tests |
|------|--------|------------------|
| F1 Fundaciones (OrderShell, tokens, módulos Alpine) | ✅ Completa | `test_compra_mayorista_view`, `test_pedidos_vendedor` |
| F2 Carga principal (cliente, búsqueda, líneas, UOM, summary) | ✅ Completa | + `test_compra_mayorista_cliente`, `test_mayorista_cart_service` |
| F3 Secundarios (checkout colapsable, modales canon, validaciones) | ✅ Completa | + `test_pedido_gestion` |
| F4 Responsive + a11y (bottom bar, cards mobile, ARIA, teclado) | ✅ Completa | + asserts ARIA en `test_compra_mayorista_view` |
| F5 Consolidación QA (CSS legacy, docs, checklist, suite completa) | ✅ Completa | Suite ecom pedidos (6 módulos) |

**Total tareas SDD:** 39/39 · **Listo para:** `sdd-verify`

### Ajuste visual post-F5 (10/07/2026)

Pantalla compra alineada al **tablero de producción MPR**:
- Hero card `slate-800` (sin gradient full-bleed) con toggle PED/PRE/DEV grande.
- Cliente | Marcas en la misma fila (`lg:grid-cols-2`) para recuperar altura.
- Hub/listados/detalle conservan el hero gradient anterior.

### Oleada E — barrido purple slate/sky (13/07/2026)

Cierre del change `ecom-pedidos-usabilidad-supervisor` (oleadas A–E). Barrido de violeta en el flujo de pedido simple y masivo:
- **PED = sky** en todos los CTAs: `pedidos_order_summary.html` (desktop + bottom bar) y `pedidos_modal.html` usan `.pedidos-btn-primary` (antes `bg-purple-600` / `.pedidos-btn-gradient`).
- Toggle grande `.compra-toggle-btn-lg-ped-active` y anillo de foco → `sky-600` / `sky-400` (antes `purple-600` / `purple-500`).
- Breadcrumb sobre tablero claro: `variant="board"` (sky/slate) en `compra_mayorista.html` (antes `variant="purple"`).
- Nuevo token compartido `.pedidos-badge-lista` (pedido simple y masivo, REQ-UI-04).
- `.pedidos-btn-gradient` queda `@deprecated`: único remanente de violeta, acotado a acciones de hero en listados/presupuestos; PROHIBIDO como CTA de venta/masivo.
- Sin purple en `pedido_masivo_sucursales.html` (ya limpio en oleada D).

---

## Entregables principales

### Plantillas / includes nuevos

- `pedidos_order_header.html`, `pedidos_lineas_tabla.html`, `pedidos_linea_card.html`
- `pedidos_qty_input.html`, `pedidos_uom_selector.html`, `pedidos_order_summary.html`
- `pedidos_checkout_section.html`, `pedidos_modal.html`

### Módulos JS (`.mjs`)

- `compra_mayorista_app.mjs` (compose + Alpine.data)
- `compra_mayorista_catalogo.mjs`, `compra_mayorista_carrito.mjs`, `compra_mayorista_checkout.mjs`
- `order_ui_state.mjs`, `order_dialogs.mjs`
- Boot Alpine robusto: registra siempre en `alpine:init` y remonta el root si el módulo carga después de Alpine.

### Tokens CSS (`pedidos_page_styles.html`)

- Regiones OrderShell: `.pedidos-order-shell`, header, capture, lines, summary, secondary
- Modo PED/PRE/DEV: `.pedidos-btn-modo-*`, bordes semánticos en shell
- Mobile: bottom bar sticky, cards `.pedidos-linea-card`, captura sticky
- F5: alias `@deprecated` `.compra-carrito-panel` / `.compra-carrito-scroll` → `.pedidos-order-lines*`
- Coherencia secundarias: `.pedidos-surface-muted`, `.pedidos-hub-highlight`

---

## Comportamiento preservado (sin cambios backend)

- Totales UI exclusivamente de `serializar_carrito` vía `setCart()`
- Contratos API carrito/checkout inmutables
- PED/PRE/DEV operativos; comprobantes confirmados no editables (anular + repetir)
- Fechas en UI: `dd/MM/yyyy` vía relay (`FechaB`) y APIs existentes

---

## Pendientes fuera de alcance (conocidos)

- Modales canon en **detalle/listado** (anular, mail, convertir PRE): siguen `confirm()`/`prompt()` nativos en `pedido_detalle.html`, `pedidos_vendedor.js`, `presupuestos_vendedor.js` — fuera del scope compra/OrderShell
- Checklist manual responsive (375px / 768px) en `09-checklist-regresion.md` §12 — requiere QA humano en browser
- UOM limitado a artículos con `presentacion.opciones` en respuesta de carrito (sin cambio backend)

---

## Verificación automatizada (F5)

```bash
docker exec Synap_app python manage.py test \
  ecom.tests.test_compra_mayorista_view \
  ecom.tests.test_mayorista_cart_service \
  ecom.tests.test_pedido_gestion \
  ecom.tests.test_compra_mayorista_cliente \
  ecom.tests.test_pedidos_vendedor \
  ecom.tests.test_api_v1_pedidos \
  --keepdb
```

Ver también `09-checklist-regresion.md` (ítems marcados como verificados por código/tests).

---

*Última actualización: 13/07/2026 (Oleada E — barrido purple slate/sky).*
