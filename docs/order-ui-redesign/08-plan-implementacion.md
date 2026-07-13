# Plan de implementación — Rediseño UI de pedidos

**Proyecto:** Synap · `ecom` mayoristapp  
**Fecha de referencia:** 10/07/2026  
**Estrategia:** incremental, sin big-bang; la pantalla `/ecom/mayoristapp/compra/` debe permanecer operativa en cada fase.

**Estado (10/07/2026):** F1–F5 **completadas**. Detalle en `10-estado-implementacion.md`.

**Documentos relacionados:** `01-inventario-funcional.md`, `09-checklist-regresion.md`, `10-estado-implementacion.md`.

---

## 1. Principios de ejecución

1. **No tocar backend** listado en inventario (`pedido_gestion_views`, relays, `mayorista_*_service`, `EcomCart`, permisos, `.env`).
2. **Contratos API inmutables:** mismos métodos, URLs, cuerpos JSON y campos de `serializar_carrito`.
3. **Precios/totales solo backend:** la UI muestra valores devueltos por el servidor; prohibido recalcular en front.
4. **Extracción Alpine → `.mjs`:** mover lógica de `compra_mayorista.html` a módulos ES sin cambiar firmas de `api()` ni shape de estado.
5. **Canon UI Synap:** tokens slate/sky, hero, cards y botones alineados a `base_pedidos.html` y `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md`.
6. **Sin HTMX:** mantener fetch + Alpine 3 + JS vanilla.
7. **Feature flags visuales:** clases CSS nuevas conviven con las actuales hasta validar regresión.

---

## 2. Visión por fases

```mermaid
flowchart LR
  F1[F1 Fundaciones] --> F2[F2 Carga principal]
  F2 --> F3[F3 Secundarios]
  F3 --> F4[F4 Responsive + a11y]
  F4 --> F5[F5 Consolidación QA]
```

| Fase | Nombre | Entregable principal |
|------|--------|---------------------|
| F1 | Fundaciones | `OrderShell`, tokens, estados globales, navegación |
| F2 | Carga principal | Cliente, búsqueda, líneas, cantidades, precios RO, totales |
| F3 | Secundarios | Entrega, notas, validaciones, diálogos confirmación |
| F4 | Responsive + a11y | Layout móvil/tablet, teclado, ARIA, contraste |
| F5 | Consolidación QA | Limpieza CSS, docs, checklist regresión completa |

---

## 3. Fase 1 — Fundaciones

### 3.1 Objetivo

Establecer el shell visual unificado (`OrderShell`), variables de diseño, estados de carga/error/vacío y navegación coherente entre hub, compra, listados y detalle.

### 3.2 Archivos afectados

| Tipo | Path |
|------|------|
| Layout base | `ecom/templates/ecom/base_pedidos.html` |
| Estilos | `ecom/templates/ecom/includes/pedidos_page_styles.html` |
| Shell JS | `ecom/static/ecom/js/pedidos_shell.js` |
| Hub | `ecom/templates/ecom/pedidos_hub.html` |
| Breadcrumb | `ecom/templates/ecom/includes/pedidos_breadcrumb.html` |
| Hero actions | `ecom/templates/ecom/includes/pedidos_hero_actions_*.html` |
| Compra (estructura) | `ecom/templates/ecom/compra_mayorista.html` (solo layout/grid, sin lógica) |

### 3.3 Componentes nuevos / refactorizados

- **OrderShell:** wrapper semántico (`order-shell`, regiones `order-shell__header`, `__main`, `__aside`, `__footer`).
- **Design tokens CSS:** espaciado, radios, sombras, colores PED/PRE/DEV (emerald/amber/rose).
- **Estado global Alpine:** `ui.loading`, `ui.error`, `ui.empty` centralizados en store ligero (módulo `order_ui_state.mjs`).
- **Nav pedidos:** breadcrumb + CTA hub/listado unificados en todas las pantallas del flujo.

### 3.4 Dependencias

- Ninguna fase previa.
- Requiere revisión de `FUENTE_VERDAD_UI_REPORTES_MPR.md`.

### 3.5 Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Regresión visual en listados existentes | Cambios solo en clases nuevas; no eliminar clases `pedidos-*` hasta F5 |
| Conflicto dark mode | Probar `pedidos_page_styles.html` en ambos temas |
| Alpine `x-data` en section rompe hijos | Mantener un solo root `compraMayorista()`; store como objeto anidado |

### 3.6 Criterios de aceptación

- [ ] Hub, compra y listado comparten hero, breadcrumb y tipografía sin saltos visuales.
- [ ] Tokens PED/PRE/DEV aplicados al toggle comprobante.
- [ ] `pedidos_shell.js` sigue manejando refresh interval y fullscreen sin errores consola.
- [ ] GET `/ecom/mayoristapp/compra/` carga y muestra layout vacío correctamente (vendedor y cliente).

### 3.7 Pruebas

```bash
docker exec Synap_app python manage.py test ecom.tests.test_compra_mayorista_view
docker exec Synap_app python manage.py test ecom.tests.test_pedidos_vendedor
```

---

## 4. Fase 2 — Carga principal

### 4.1 Objetivo

Rediseñar el núcleo operativo de toma de pedido: panel cliente, búsqueda de artículos, grilla catálogo, carrito lateral, cantidades, visualización de precios (solo lectura) y bloque de totales.

### 4.2 Archivos afectados

| Tipo | Path |
|------|------|
| Compra plantilla | `ecom/templates/ecom/compra_mayorista.html` |
| Búsqueda TPV | `ecom/templates/ecom/includes/pedidos_busqueda_articulos_tpv.html` |
| Cliente módulo | `ecom/static/ecom/js/compra_mayorista_cliente.mjs` |
| Marcas módulo | `ecom/static/ecom/js/compra_mayorista_marcas.mjs` |
| **Nuevo** carrito UI | `ecom/static/ecom/js/compra_mayorista_carrito.mjs` |
| **Nuevo** catálogo UI | `ecom/static/ecom/js/compra_mayorista_catalogo.mjs` |
| **Nuevo** entry Alpine | `ecom/static/ecom/js/compra_mayorista_app.mjs` |
| Predictivo | `ecom/static/ecom/js/ecom_predictive.mjs` |

### 4.3 Componentes

- **ClientePanel:** autocomplete, widget crédito, mensajes validación (reutiliza relay existente).
- **CatalogoGrid:** POST listado, filtros marcas, loading/empty, barcode parcial vía campo búsqueda.
- **CarritoPanel:** líneas, qty stepper, eliminar, vaciar; siempre sincronizado con GET carrito post-mutación.
- **TotalesPanel:** subtotal, descuento pie, IVA, total — binding directo a `carrito.totales` del JSON backend.
- **PreciosDisplay:** `tabular-nums`, formato moneda; **sin** edición de precio unitario.

### 4.4 Dependencias

- F1 completada (OrderShell y tokens).
- Endpoints: `compra/contexto`, `clientes/*`, `catalogo/articulos/listado`, `carrito/*`, `catalogo/marcas`.

### 4.5 Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Desincronización totales UI vs backend | Una sola fuente: respuesta `serializar_carrito`; tests manuales tras cada PATCH |
| Race en búsqueda artículos | Conservar `AbortController` actual al extraer módulo catálogo |
| Cambio cliente no vacía carrito | Verificar que `compra_mayorista_cliente.mjs` sigue llamando relay seleccionar |
| Regresión atajos teclado | Portar handlers ↑↓ Enter al módulo catálogo con tests manuales |

### 4.6 Criterios de aceptación

- [ ] Flujo completo: seleccionar cliente → agregar 3 artículos → modificar cantidades → totales correctos vs API.
- [ ] Precios mostrados coinciden con `test_mayorista_cart_service` (misma lista cliente).
- [ ] Vendedor: GET compra limpia cliente y carrito previo.
- [ ] Cambio de cliente vacía líneas y muestra mensaje coherente.
- [ ] DEV no bloquea por stock; PED/PRE sí.
- [ ] Módulos `.mjs` cargados con `type="module"`; Alpine root delega a imports.

### 4.7 Pruebas

```bash
docker exec Synap_app python manage.py test ecom.tests.test_compra_mayorista_view
docker exec Synap_app python manage.py test ecom.tests.test_compra_mayorista_cliente
docker exec Synap_app python manage.py test ecom.tests.test_mayorista_cart_service
```

---

## 5. Fase 3 — Secundarios

### 5.1 Objetivo

Completar campos periféricos del checkout, validaciones de formulario, mensajes de error contextuales y diálogos de confirmación (vaciar carrito, confirmar pedido, repetir pedido).

### 5.2 Archivos afectados

| Tipo | Path |
|------|------|
| Compra plantilla | `ecom/templates/ecom/compra_mayorista.html` (panel checkout / footer) |
| Toggle comprobante | `ecom/templates/ecom/includes/pedidos_toggle_comprobante.html` |
| Modal repetir | `ecom/templates/ecom/includes/repetir_pedido_modal.html` |
| JS repetir | `ecom/static/ecom/js/repetir_pedido_modal.js` |
| **Nuevo** checkout UI | `ecom/static/ecom/js/compra_mayorista_checkout.mjs` |
| **Nuevo** diálogos | `ecom/static/ecom/js/order_dialogs.mjs` |
| Alert desktop | `ecom/templates/ecom/includes/pedidos_alert_desktop.html` |

### 5.3 Componentes

- **EntregaField:** texto fecha entrega (mejora UX; sigue siendo PARCIAL hasta datepicker en iteración posterior).
- **ObservacionesField:** textarea observaciones checkout.
- **DescuentoPieControl:** input + PATCH `carrito/descuento-pie/`.
- **ConfirmDialog:** confirmar PED/PRE/DEV con resumen totales.
- **RepetirPedidoFlow:** preview + POST `carrito/desde-pedido/` (sin cambiar contrato).
- **Flash / validación:** cliente obligatorio, carrito vacío, errores 409 stock.

### 5.4 Dependencias

- F2 (carrito y totales estables).
- Endpoints: `checkout/confirmar`, `carrito/descuento-pie`, `carrito/tipo-comprobante`, `carrito/desde-pedido/*`, `pedidos/recientes`.

### 5.5 Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Doble submit checkout | Deshabilitar botón durante POST; respetar idempotencia backend |
| Modal repetir rompe carrito activo | Confirmación explícita antes de POST desde-pedido |
| Mensaje éxito checkout | Conservar bloque `exitoCheckout` con enlaces detalle/listado |

### 5.6 Criterios de aceptación

- [ ] Confirmar PED crea comprobante y muestra panel éxito con link a detalle.
- [ ] Confirmar PRE y DEV con mismos patrones visuales (colores tipo).
- [ ] Descuento pie actualiza totales solo vía respuesta servidor.
- [ ] Repetir pedido desde chips recientes y modal funciona con preview.
- [ ] Vaciar carrito pide confirmación y llama `carrito/vaciar/`.

### 5.7 Pruebas

```bash
docker exec Synap_app python manage.py test ecom.tests.test_mayorista_cart_service
docker exec Synap_app python manage.py test ecom.tests.test_pedido_gestion
docker exec Synap_app python manage.py test ecom.tests.test_compra_mayorista_view
```

---

## 6. Fase 4 — Responsive y accesibilidad

### 6.1 Objetivo

Adaptar OrderShell y compra a viewports móvil/tablet, mejorar navegación por teclado, roles ARIA y contraste; mantener paridad funcional desktop.

### 6.2 Archivos afectados

| Tipo | Path |
|------|------|
| Estilos | `ecom/templates/ecom/includes/pedidos_page_styles.html` |
| Compra | `ecom/templates/ecom/compra_mayorista.html` |
| Listado | `ecom/templates/ecom/pedidos_vendedor.html` |
| Detalle PED | `ecom/templates/ecom/pedido_detalle.html` |
| Presupuestos | `ecom/templates/ecom/presupuestos_vendedor.html` |
| Shell | `ecom/static/ecom/js/pedidos_shell.js` (focus trap modales si aplica) |
| Módulos compra | `compra_mayorista_*.mjs` |

### 6.3 Componentes

- **Carrito drawer móvil:** panel inferior o off-canvas en `< md`.
- **Catálogo stack:** una columna; búsqueda sticky.
- **Touch targets:** mínimo 44px en botones qty y CTA confirmar.
- **ARIA:** `combobox` cliente, `aria-live` para flashes, labels en toggle PED/PRE/DEV.
- **Teclado:** atajos documentados; foco visible; Escape cierra modales.

### 6.4 Dependencias

- F1–F3 funcionalmente completas.

### 6.5 Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Panel carrito oculta totales en móvil | Barra fija inferior con total + CTA |
| Regresión listado tabla ancha | Scroll horizontal preservado; sticky primera columna opcional |
| Alpine `x-show` y foco | Mover foco al abrir drawer carrito |

### 6.6 Criterios de aceptación

- [ ] Compra usable en viewport 375px: agregar ítem, ver total, confirmar.
- [ ] Lighthouse a11y ≥ 90 en compra (sin bloquear deploy por métrica única).
- [ ] Navegación teclado búsqueda artículos sin mouse.
- [ ] Listado pedidos operable en tablet (filtros + tabla).

### 6.7 Pruebas

```bash
docker exec Synap_app python manage.py test ecom.tests.test_compra_mayorista_view
docker exec Synap_app python manage.py test ecom.tests.test_pedidos_vendedor
```

Pruebas manuales: checklist sección Responsive y Teclado en `09-checklist-regresion.md`.

---

## 7. Fase 5 — Consolidación y QA

### 7.1 Objetivo

Eliminar deuda CSS duplicada, alinear listados/detalle/hub al nuevo shell, ejecutar checklist de regresión completa y actualizar documentación.

### 7.2 Archivos afectados

| Tipo | Path |
|------|------|
| Todos los templates pedidos | `ecom/templates/ecom/pedidos_*.html`, `compra_mayorista.html`, `pedido_detalle.html` |
| Includes | `ecom/templates/ecom/includes/pedidos_*` |
| JS listados | `pedidos_vendedor.js`, `presupuestos_vendedor.js`, `repetir_pedido_modal.js` |
| Módulos compra | `ecom/static/ecom/js/compra_mayorista_*.mjs`, `order_*.mjs` |
| Docs | `docs/order-ui-redesign/*`, `docs/ecom/` (actualización cruzada si aplica) |

### 7.3 Componentes

- Deprecar clases CSS legacy no usadas (tras grep en repo).
- Unificar formato moneda y fechas **dd/MM/yyyy** en toda la UI pedidos.
- Verificar compatibilidad con `base_app.html` y barra estado Synap.

### 7.4 Dependencias

- F1–F4 cerradas.
- Checklist `09-checklist-regresion.md` preparado.

### 7.5 Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Eliminar clase aún usada en otra pantalla | Grep global antes de borrar; mantener alias una versión |
| Drift documentación | Actualizar inventario si cambia matriz funcional |

### 7.6 Criterios de aceptación

- [ ] Checklist regresión 100 % casos críticos (PED/PRE/DEV, carrito, checkout, permisos).
- [ ] Suite tests ecom pedidos en verde (ver §8).
- [ ] Sin errores consola en flujos principales.
- [ ] Documentación `01-inventario-funcional.md` refleja estado final o gaps aceptados.

### 7.7 Pruebas

```bash
docker exec Synap_app python manage.py test ecom.tests.test_compra_mayorista_view
docker exec Synap_app python manage.py test ecom.tests.test_compra_mayorista_cliente
docker exec Synap_app python manage.py test ecom.tests.test_mayorista_cart_service
docker exec Synap_app python manage.py test ecom.tests.test_pedido_gestion
docker exec Synap_app python manage.py test ecom.tests.test_pedidos_vendedor
docker exec Synap_app python manage.py test ecom.tests.test_api_v1_pedidos
```

Ejecutar íntegramente `09-checklist-regresion.md` en staging.

---

## 8. Suite de regresión automatizada (referencia)

| Test module | Cubre |
|-------------|-------|
| `ecom.tests.test_compra_mayorista_view` | GET compra, contexto URLs, permisos, limpieza vendedor |
| `ecom.tests.test_compra_mayorista_cliente` | Flujo autogestión cliente |
| `ecom.tests.test_mayorista_cart_service` | `serializar_carrito`, stock, promos, descuentos |
| `ecom.tests.test_pedido_gestion` | Hub, detalle, APIs gestión, PDF, convertir PRE |
| `ecom.tests.test_pedidos_vendedor` | Listado vendedor, filtros |
| `ecom.tests.test_api_v1_pedidos` | API REST v1 listado/detalle pedidos |

Comando agregado recomendado antes de merge:

```bash
docker exec Synap_app python manage.py test \
  ecom.tests.test_compra_mayorista_view \
  ecom.tests.test_compra_mayorista_cliente \
  ecom.tests.test_mayorista_cart_service \
  ecom.tests.test_pedido_gestion \
  ecom.tests.test_pedidos_vendedor \
  ecom.tests.test_api_v1_pedidos
```

---

## 9. Estrategia de extracción Alpine (sin cambiar contratos)

### 9.1 Estado actual

`compra_mayorista.html` define `function compraMayorista()` inline (~700 líneas) con `x-data="compraMayorista()"`.

### 9.2 Estado objetivo

```
compra_mayorista_app.mjs       → export default compraMayorista (Alpine.data)
compra_mayorista_cliente.mjs → ya existe; ampliar si hace falta
compra_mayorista_marcas.mjs    → ya existe
compra_mayorista_catalogo.mjs  → búsqueda, grilla, atajos
compra_mayorista_carrito.mjs   → líneas, qty, vaciar
compra_mayorista_checkout.mjs  → confirmar, descuento pie, entrega
order_ui_state.mjs             → loading, flash, empty helpers
order_dialogs.mjs              → confirmaciones nativas / modales
```

### 9.3 Reglas de migración

1. Cada PR mueve **un dominio** (ej. solo catálogo) y deja compra usable.
2. El método `api(url, method, body)` se exporta compartido; mismos headers CSRF.
3. No renombrar propiedades Alpine consumidas en HTML hasta actualizar plantilla en el mismo PR.
4. Registrar componente: `Alpine.data('compraMayorista', compraMayorista)` en boot module.

---

## 10. Cronograma sugerido (orientativo)

| Fase | Duración estimada | Hito |
|------|-------------------|------|
| F1 | 3–5 días | Shell unificado en hub + compra |
| F2 | 5–8 días | Toma pedido modularizada |
| F3 | 3–5 días | Checkout y repetir pedido pulidos |
| F4 | 3–5 días | Móvil + a11y |
| F5 | 2–4 días | QA + docs |

Total orientativo: **16–27 días** según paralelismo y revisiones UX.

---

## 11. Definición de terminado (DoD) global

- Compra mayorista operativa para vendedor y cliente autogestión.
- Matriz funcional del inventario sin regresiones en ítems marcados **SÍ**.
- Backend fuera de alcance sin modificaciones.
- Checklist `09-checklist-regresion.md` ejecutada y firmada por QA/producto.
- Documentación actualizada en `docs/order-ui-redesign/`.

---

*Última actualización: 10/07/2026.*
