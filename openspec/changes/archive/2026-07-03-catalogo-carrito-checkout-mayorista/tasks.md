# Tasks — Catálogo, carrito y checkout mayorista

**Change:** `catalogo-carrito-checkout-mayorista`
**Leyenda:** `[ ]` pendiente · `[~]` en curso · `[x]` hecho

---

## Fase 0 — SDD (esta entrega)

- [x] Exploración PHP catálogo/precios, PHP carrito/checkout, inventario Synap `ecom/`
- [x] `proposal.md` (alcance por fases, riesgos, decisiones abiertas)
- [x] `exploration.md`
- [x] `specs/ecom-catalogo-producto-mayorista/spec.md` (P0)
- [x] `design.md` (arquitectura global + P0 detallado)
- [x] `tasks.md`
- [ ] **Validación de alcance/fases con el usuario** (decisiones abiertas #1–#3)

---

## Fase P0 — Catálogo de producto (lectura, riesgo bajo)

- [x] Extender `ecom/services/catalogo_articulo.py`: `listar_articulos_paginado(...)`
- [x] Extender `ecom/services/catalogo_articulo.py`: `obtener_detalle_articulo(...)`
- [x] Unificar lectura de stock disponible con `self_checkout.StockService`
- [ ] Resolver imagen del artículo (paridad `foto.php`)
- [x] `ecom/catalogo_producto_relay_views.py`: `CatalogoArticulosListadoRelayAPIView`, `CatalogoArticuloDetalleRelayAPIView`
- [x] Rutas en `ecom/urls.py`
- [x] Tests: `test_catalogo_producto_listado.py`, `test_catalogo_producto_detalle.py`
- [x] Verificar precio == relay existente (REQ-CAT-003)
- [x] `docker exec Synap_app python manage.py test ecom` verde
- [ ] Docs `docs/ecom/` + nota en DELTA

## Fase P1 — Carrito mayorista (riesgo medio) ✅

- [x] Decidir persistencia — **`ecom_cart`/`ecom_cart_item` propios en Postgres synap** (decisión #1)
- [x] `specs/ecom-carrito-mayorista/spec.md` (11 escenarios)
- [x] Modelos `EcomCart`/`EcomCartItem` + migración `ecom/0015_ecomcart_ecomcartitem_and_more.py`
- [x] `ecom/services/mayorista_cart_service.py` (obtener/agregar/actualizar cantidad/descuento/quitar/limpiar/descuento-pie/recalcular)
- [x] Precio del renglón vía motor único (`catalogo_producto.resolver_precio_articulo`) — paridad P0
- [x] Validación de stock al agregar y al actualizar cantidad (`StockService`)
- [x] Totales con desglose 21/10,5/exento + impuesto interno + descuento al pie (paridad `Jcart.update_subtotal`)
- [x] Vistas API carrito + rutas (`CarritoRelayAPIView`, `CarritoItemRelayAPIView`, `CarritoVaciarRelayAPIView`, `CarritoDescuentoPieRelayAPIView`)
- [x] Tests carrito (15) — totales, IVA 21/10,5/exento, impuesto interno, descuentos renglón/pie, stock, consolidación
- [x] `docker exec Synap_app python manage.py test ecom.tests.test_mayorista_cart_service` verde (15/15)
- [x] Docs `docs/ecom/CARRITO_MAYORISTA_P1.md` + nota en DELTA

## Fase P2 — Checkout / alta de comprobante (riesgo ALTO, escritura legacy) ✅

- [x] **Spec + design detallados de P2** (escrituras, numeración, validaciones) — `specs/ecom-checkout-mayorista/spec.md` (13 escenarios) + `design.md` §4 detallado (mapeo de campos reales, SQL numeración FOR UPDATE, crédito/autorización, idempotencia)
- [x] Adapter de escritura legacy (comp_ped/stockp/stock_deposito/cliente_datos_adicionales) — `mayorista_checkout_service.py`
- [x] Numeración segura `talonarios` (`FOR UPDATE`) + `codmov` (`FOR UPDATE`)
- [x] Validaciones pre-commit: stock (UPDATE condicional), límite de crédito, autorización, idempotencia
- [x] Selección de punto de venta (body / sesión) en la vista
- [x] `mayorista_checkout_service.confirmar(...)` transaccional (PED/PRE)
- [x] Recálculo de precios en commit (motor `resolver_precio_articulo`)
- [x] Vista API checkout + ruta (`CheckoutConfirmarRelayAPIView`, `/api/mayoristapp/checkout/confirmar/`)
- [x] Campos resultado en `EcomCart` + migración `0017_...` (idempotencia)
- [x] Tests (11): PED/PRE ok, sin stock, rollback parcial, numeración `FOR UPDATE`, autorización, idempotencia, validaciones
- [x] Checkpoint `mayoristapp_checkout` (`0018_checkpoint_mayoristapp_checkout.py`)
- [x] Percepciones IIBB (`percep_cli`, `total_percep`) — implementado en **P4** (ver abajo)
- [ ] Migración esquema legacy si hace falta (único `comp_ped.CodigoMovimiento`) vía `legacy_mysql_schema/catalog.py` — no requerido en P2

## Fase P3 — Extras (riesgo medio)

- [x] **Alta de devolución (DEV)** — reutiliza `mayorista_checkout_service.confirmar(tipo='DEV')`; stock `+=` sin validación (paridad legacy), numeración talonario `DEV` (corrige bug PHP), `TipoComp='Devolucion'`; tipo `DEV` en `EcomCart` (migración `0019`); endpoint compartido `/checkout/confirmar/` (body `tipo='DEV'`); tests 13/13; checkpoint `mayoristapp_devolucion` (`0020`). Doc: `CHECKOUT_MAYORISTA_P2.md` §Devolución
- [x] **Export lista de precios PDF** — reportlab A3-L, reutiliza catálogo P0 (filtros + motor de precios) sin paginar; guardrails volumen/tiempo (settings `LP_PDF_MAX_*`, página amigable español); servicio `ecom/services/lista_precio_pdf.py`, vista + ruta `GET /catalogo/lista-precios.pdf`; helpers `contar_articulos_catalogo`/`obtener_filas_catalogo`; tests 4/4; checkpoint `mayoristapp_lista_precios_pdf` (`0021`). Docs `LISTA_PRECIOS_PDF_P3.md` + runbook. Gaps: imágenes embebidas, background (Celery off)
- [x] **Restricciones de catálogo por PV (ex-AMICO, config BD)** — modelo `EcomCatalogoRestriccionPV` (Postgres, migración `0022`) reemplaza el baneo hardcodeado por config genérica por PV (artículo/rubro/subrubro); servicio `catalogo_restricciones.py` inyecta `excluir_*` a filtros y `_construir_where_catalogo` los traduce a `NOT IN`; aplicado en listado + export PDF; gestionable por Django admin; tests 8/8; checkpoint `mayoristapp_restricciones_pv` (`0023`). Doc `RESTRICCIONES_CATALOGO_PV_P3.md`
- [x] **UI web (catálogo/carrito/checkout) patrones canónicos** — pantalla POS `/ecom/mayoristapp/compra/` (`CompraMayoristaView` + `compra_mayorista.html`, extiende `base_app.html`, Alpine 3, hero slate, full-width); consume APIs P0/P1/P2/P3 (listado, carrito CRUD/vaciar/descuento-pie, checkout PED/PRE/DEV, link PDF); tests 3/3; checkpoint `mayoristapp_ui_compra` (`0024`). Doc `UI_COMPRA_MAYORISTA_P3.md`. Gaps: selector de cliente embebido y ficha visual (follow-up)
- [x] **Actualizar DELTA** (cerrados: export PDF ✅ y AMICO/restricciones PV ✅ en P3; destacados sigue diferido — depende de ficha/destacados web, no de este vertical)

## Fase P4 — Percepciones IIBB (configurable por implementación, escritura legacy) 

- [x] **Spec REQ-CHK-009** (delta) + sección de design P4 (fórmula, tablas, base imponible, edge cases)
- [x] Servicio `ecom/services/mayorista_percepciones.py`: `calcular_percepciones(cur, base_empresa, id_cliente, base, agente_percep)` → `(detalle, total)`; lee `percep_cli_param` + `percep_cli_tipo`, `importe = base × alícuota / 100` (sin `importe_minimo`, paridad `jcart.php`)
- [x] Resolución del flag `agente_percep` desde la sucursal del usuario (`_fetch_agente_percep`, `usuarios→sucursales`) + override de sesión (`CheckoutInput.agente_percep`) — toggle configurable por implementación
- [x] Integración transaccional en `mayorista_checkout_service.confirmar`: INSERT `percep_cli` por tipo + `comp_ped.total_percep` (PED/PRE); bloqueo con ROLLBACK si `agente_percep='Si'` y cliente sin `percep_cli_param`
- [x] Tests: agente off (percep=0), agente on con tipos (importe/total), agente on sin param (bloquea)
- [x] Checkpoint `mayoristapp_percepciones_iibb` + doc `docs/ecom/PERCEPCIONES_IIBB_P4.md`

---

## Verificación transversal (por fase)

- [ ] Sin escritura legacy fuera de commit/transacción (P2)
- [ ] Parametrización SQL + `administranet_types` en todo acceso MySQL
- [ ] Tests en contenedor verdes
- [ ] Docs `docs/ecom/` actualizadas
