## Exploration: ecom-pedidos-usabilidad-supervisor

**Change:** `ecom-pedidos-usabilidad-supervisor`  
**Fecha:** 13/07/2026  
**Alcance:** Pedido simple (`/ecom/mayoristapp/venta/`) + pedido masivo; descuentos línea/pie; lista de precios solo lectura; Design System slate/sky; supervisor elige vendedor y opera en su nombre con paridad VCM.

---

### Current State

#### Pedido simple (`/venta/`)

- **Shell UI:** OrderShell F1–F5 implementado (`compra_mayorista.html` + mixins `.mjs`). Tokens `.pedidos-*` en `pedidos_page_styles.html`. Post-F5 quedaron acentos **purple** en breadcrumb, toggle PED activo y CTA confirmar (documentado en `docs/order-ui-redesign/10-estado-implementacion.md`).
- **Cliente:** Búsqueda predictiva (`ecom_predictive.mjs` + `pedidos_order_header.html`). Filtro por `cliente_relay._where_viajante` → `CodViajante` / `vendedor_a_cargo` / `todos_clientes` (**no** filtra por ternas `ecom_vendedor_cliente_marca`).
- **Marcas:** Filtro UI multi-marca (`compra_mayorista_marcas.mjs`) sobre catálogo; no es equivalente a restricción VCM obligatoria.
- **Descuento renglón:** Backend aplica `descRenglon` del cliente al **motor de precios** al agregar (`agregar_item` + `_obtener_lista_id_y_cliente`). Campo `EcomCartItem.porcentaje_descuento` existe; API `PATCH …/carrito/items/<id>/` acepta `porcentaje_descuento` (`carrito_relay_views.py`). **UI:** `pedidos_lineas_tabla.html` no expone columna ni input de descuento por línea.
- **Descuento pie:** Input en `pedidos_order_summary.html` + `aplicarDescuentoPie()` → API `POST …/carrito/descuento-pie/`. `descPie` se inicializa en `0` y solo se sincroniza desde `cart.descuento_pie_pct` vía `setCart()`; **no** se precarga desde `cliente.Descuento` al seleccionar cliente (`cliente_seleccion_relay` sí trae `descPie`).
- **Lista de precios:** Se resuelve en backend desde `cliente.ListaPrecio` / `codListaPrecio` en sesión (`catalogo_producto_relay_views._obtener_lista_id_y_cliente`). PDF en `lista_precios_pdf`. **No hay badge solo lectura** ni enlace PDF visible en el header de captura.
- **Checkout CodViajante:** Bug confirmado en `_session_cod_viajante` (`checkout_relay_views.py`): lee `user.cod_viajante` / `codViajante` pero **no** `id_vendedor_usr` (donde Synap persiste el CodViajante). Puede grabar PED con viajante nulo/incorrecto.
- **Totales:** Solo backend (`mayorista_cart_service.serializar_carrito`); frontend no recalcula — cumple decisión de producto.

#### Pedido masivo (`/pedido-masivo-sucursales/`)

- **UI:** Alpine inline en `pedido_masivo_sucursales.html` (~330 líneas JS en template). Estilo MPR header slate + **purple** en CTAs, focos y selección. Confirmación usa `confirm()` nativo (línea 539).
- **VCM:** Clientes vía `listar_clientes_con_ternas`; artículos vía `buscar_articulos_filtrados_ternas` (marcas de terna). Paridad parcial con producto (simple aún no).
- **Precios:** Columna «Precio lista 1» muestra `articulo.Precio1V` (referencial). `buscar_articulos_filtrados_ternas` acepta `descuento_cliente` pero la vista no lo usa; `confirmar_lote_masivo` recibe `descuento_cliente=Decimal("0")` por defecto.
- **Descuentos:** Sin UI de % por fila ni descuento pie de lote; sin preview de totales antes de confirmar.
- **CodViajante en PED:** `cod_viajante_sesion(sess)` → `id_vendedor_usr` del usuario logueado (no operativo supervisor).

#### Sesión / supervisor

- **`mayoristapp_sesion_contexto.py`:** Hidrata desde MySQL `id_vendedor_usr`, `todos_clientes`, `supervisor_venta`. **`vendedor_a_cargo` no se carga de MySQL** — solo normaliza lo ya presente en sesión (lista/JSON). Docs (`SPEC_MAYORISTAPP_FUNDACIONES.md`) afirman hidratación completa; código no la implementa.
- **Impersonación:** No existe `cod_viajante_operativo` ni selector de vendedor en ningún módulo ecom pedidos.
- **Supervisor hoy:** `where_vendedor_cliente` amplía alcance con `vendedor_a_cargo` si `supervisor_venta=Si`, pero sin lista poblada el supervisor solo ve su propio `CodViajante`.

#### Specs y docs existentes

| Artefacto | Relevancia |
|-----------|------------|
| `openspec/specs/ecom-vendedor-cliente-marca` | Ternas VCM; REQ-VCM-04 pide límite por viajante en flujos pedido |
| `openspec/specs/ecom-pedido-masivo-sucursales` | Matriz, borrador, rollback; UI canon MPR |
| `openspec/specs/ecom-checkout-mayorista` | Checkout transaccional, descuentos en servicio |
| `docs/order-ui-redesign/05-design-system-pedidos.md` | Canon slate/sky, tokens `.pedidos-*` |
| `docs/reverse-engineering/orders/14-functional-equivalence-matrix.md` | Gaps P0/P1 conocidos (domicilio en simple, etc.) |

---

### Affected Areas

| Ruta | Motivo |
|------|--------|
| `ecom/services/mayoristapp_sesion_contexto.py` | Hidratar `vendedor_a_cargo`; nueva clave `cod_viajante_operativo` en sesión mayoristapp |
| `ecom/checkout_relay_views.py` | Fix `_session_cod_viajante`; usar viajante operativo |
| `ecom/services/cliente_relay.py`, `vendedor_asignacion_sql.py` | Alcance cliente/catálogo con viajante operativo + VCM en simple |
| `ecom/services/pedido_masivo_matriz.py`, `batch_checkout_masivo.py` | Precio real, descuentos fila/pie, preview totales, viajante operativo |
| `ecom/pedido_masivo_views.py` | APIs preview/confirm con descuentos; lista precios cliente |
| `ecom/carrito_relay_views.py`, `mayorista_cart_service.py` | Precarga desc pie; coherencia desc renglón UI↔API |
| `ecom/catalogo_producto_relay_views.py`, `cliente_seleccion_relay.py` | Lista precios solo lectura en contexto; descPie al seleccionar |
| `ecom/templates/ecom/compra_mayorista.html` + includes `pedidos_*` | UI desc línea, badge lista, slate/sky, selector supervisor |
| `ecom/templates/ecom/pedido_masivo_sucursales.html` | Extraer JS, modal canon, descuentos, precio real, tokens |
| `ecom/static/ecom/js/compra_mayorista_*.mjs` | descPie preload, desc línea, supervisor, lista precios |
| `ecom/mayoristapp_web_views.py`, `urls.py` | Vista/API selector vendedores supervisor |
| `docs/ecom/*`, `docs/order-ui-redesign/*` | Actualización post-cambio (política repo) |
| `openspec/changes/.../specs/*` | Deltas REQ supervisor, descuentos, VCM simple, UI |

---

### Approaches

#### 1. **Corte vertical por capability (recomendado)**

Implementar en oleadas entregables: (A) fundaciones sesión + fix CodViajante + selector supervisor; (B) paridad VCM + lista precios badge en **simple**; (C) descuentos línea/pie simple; (D) masivo: precio real + descuentos + preview + modal; (E) barrido visual slate/sky.

- **Pros:** Cada oleada es testeable; alinea con decisiones ya fijadas; reutiliza APIs existentes (carrito descuento, PATCH item).
- **Cons:** Requiere coordinar backend sesión antes de UI supervisor; masivo depende de motor precios (más pesado que CSS).
- **Effort:** Medium–High (estimado 4–6 sesiones apply)

#### 2. **UI-first (solo presentación)**

Purple→sky, badge lista, inputs descuento en templates; posponer supervisor y VCM simple.

- **Pros:** Mejora visible rápida; bajo riesgo en checkout.
- **Cons:** **Incumple** decisiones de producto (supervisor, VCM simple, masivo precio real); deja bug `_session_cod_viajante` en producción.
- **Effort:** Low

#### 3. **Backend monolítico único**

Un solo PR con sesión operativa, VCM, descuentos, masivo y UI.

- **Pros:** Paridad completa de una vez.
- **Cons:** Review/QA difícil; alto riesgo de regresión checkout; contradice flujo SDD por fases.
- **Effort:** High

---

### Recommendation

**Approach 1 (corte vertical)** con este orden técnico:

1. **Sesión operativa:** Introducir `mayoristapp.cod_viajante_operativo` (default = `id_vendedor_usr`). API listar vendedores bajo cartera supervisor (`supervisor_venta` + `vendedor_a_cargo` una vez hidratado). Centralizar resolución en helper único usado por checkout, masivo y cliente relay.
2. **Fix inmediato:** `_session_cod_viajante` debe leer `id_vendedor_usr` / operativo (paridad `cod_viajante_desde_sesion_usuario`).
3. **VCM en simple:** Cuando hay viajante efectivo, restringir búsqueda cliente y catálogo como masivo (`listar_clientes_con_ternas` / filtro marcas terna) — feature flag o regla: siempre cuando operativo ≠ null.
4. **Descuentos simple:** Precargar `descPie` desde cliente al seleccionar + POST descuento-pie; columna % editable por línea → PATCH `porcentaje_descuento` (totales vía `setCart` only).
5. **Lista precios:** Badge solo lectura + link PDF en header (`cliente.listaPrecio`); sin selector override.
6. **Masivo:** Extraer `pedido_masivo_app.mjs`; integrar `price_rules_engine` por fila; columnas % desc + pie lote; endpoint preview totales; reemplazar `confirm()` por `pedidos_modal.html`.
7. **Visual:** Sustituir clases `purple-*` por tokens `.pedidos-btn-primary` / sky en venta, masivo, hub (alcance acotado a flujos pedido).

Investigar en **propose/design** el origen MySQL de `vendedor_a_cargo` en PHP `control.php` (no está en `_cargar_campos_mayoristapp_mysql` hoy).

---

### Risks

- **`vendedor_a_cargo` sin fuente MySQL clara en Synap:** supervisor podría no ver cartera hasta definir query legacy (tabla permisos / relación supervisor-vendedor).
- **VCM en simple reduce catálogo** vs. asignación por `cliente.CodViajante`: vendedores acostumbrados al alcance amplio pueden reportar «clientes faltantes»; requiere comunicación y datos VCM completos.
- **Regresión checkout** al corregir CodViajante: validar PED con viajante correcto en entornos donde hoy pasaba null.
- **Masivo + motor precios:** latencia en preview de lote grande; necesita endpoint agregado y límites (similar guardrails PDF).
- **Sesión operativa:** olvidar limpiar `cod_viajante_operativo` al logout o cambiar vendedor puede grabar PED en nombre equivocado — UX debe mostrar banner persistente «Operando como: …».
- **Divergencia docs vs código** en fundaciones sesión: actualizar `SPEC_MAYORISTAPP_FUNDACIONES.md` al implementar.

---

### Ready for Proposal

**Sí.** Las decisiones de producto están cerradas; el AS-IS está verificado en código. El orchestrator debe lanzar **sdd-propose** con:

- Alcance por oleadas (tabla arriba).
- REQ explícitos: supervisor operativo, VCM simple, descuentos, lista RO, masivo precio real, UI slate/sky.
- Spike propuesto: origen PHP/MySQL de `vendedor_a_cargo`.
- Fuera de alcance v1: override lista precios, impersonación fuera de pedidos, edición PED confirmado.
