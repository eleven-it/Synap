# Tasks: Cabecera comercial de pedidos e-commerce

**Change:** `ecom-pedido-cabecera-comercial`

> UI: fechas en **dd/MM/yyyy**. Tests: `docker exec Synap_app python manage.py test ecom`.

## Phase 0: Spike (preguntas abiertas)

- [x] 0.1 Confirmar columnas `cond_venta` en schema legacy (`Codigo`, `Descripcion`, `Dias`) vía `docs/general/tablas` o query MySQL; documentar hallazgo.
- [x] 0.2 Decidir trigger recálculo precios al cambiar lista en checkout simple (PATCH carrito vs endpoint preview) y anotar en `design.md`.

## Phase 1: Core service

- [x] 1.1 Crear `ecom/services/pedido_cabecera_comercial.py` con dataclass `PedidoCabeceraComercial`.
- [x] 1.2 Implementar `dias_condicion()` y lookup descripción en tabla `cond_venta`.
- [x] 1.3 Implementar `resolver_cabecera_comercial()`: defaults cliente, `vencimiento=fecha_pedido+Dias`, validaciones `≥ fecha_pedido`, enforcement rol.
- [x] 1.4 Añadir `condiciones_venta_relay_json()` en `ecom/services/precio_relays.py`.

## Phase 2: Checkout / CheckoutInput

- [x] 2.1 Extender `CheckoutInput` en `ecom/services/mayorista_checkout_service.py` con campos cabecera.
- [x] 2.2 Integrar resolver en `confirmar()`: quitar `hoy`/`+30`, persistir `comp_ped` + `cliente_datos_adicionales` + `stockp.lista_precio` con `administranet_types`.
- [x] 2.3 Fijar `cart.lista_id` desde cabecera y `_reprice_items` antes de commit; bloquear si falla.
- [x] 2.4 Actualizar `ecom/checkout_relay_views.py`: parsear body cabecera (ISO), resolver por rol, armar `CheckoutInput`.

## Phase 3: Masivo

- [x] 3.1 Actualizar `ecom/services/batch_checkout_masivo.py`: `calcular_totales_lote_masivo` y `confirmar_lote_masivo` reciben cabecera resuelta.
- [x] 3.2 Propagar misma cabecera a cada `CheckoutInput`/PED del lote (REQ-MAS-21).
- [x] 3.3 Actualizar `ecom/pedido_masivo_views.py`: API contexto (defaults, catálogos) y confirmación con cabecera del body.

## Phase 4: UI simple (checkout mayorista)

- [x] 4.1 Template `ecom/templates/ecom/compra_mayorista.html`: panel cabecera canon MPR/slate (fechas dd/MM/yyyy, condición, lista).
- [x] 4.2 `ecom/static/ecom/js/compra_mayorista_checkout.mjs`: hidratar cabecera, recalc vencimiento al cambiar fecha/condición, relays catálogo.
- [x] 4.3 JS: recalcular precios al cambiar lista (supervisor); domicilio/ruta opcional si costo bajo.
- [x] 4.4 Vendedor: lista y condición solo lectura; supervisor editable (REQ-CHK-013).

## Phase 5: UI masivo

- [x] 5.1 `ecom/templates/ecom/pedido_masivo_sucursales.html`: cabecera en barra contexto (fechas dd/MM/yyyy, condición, lista).
- [x] 5.2 `ecom/static/ecom/js/pedido_masivo_app.mjs`: estado cabecera en borrador, sync preview/confirmar, recalc vencimiento y precios.
- [x] 5.3 Supervisor edita lista/condición en barra; vendedor solo lectura (REQ-MAS-17/20).

## Phase 6: Permisos

- [x] 6.1 Implementar `puede_editar_cabecera_comercial()` reutilizando `_si_no_supervisor` de `vendedor_operativo`.
- [x] 6.2 Exponer `puede_editar`/`es_supervisor` en contexto JSON de checkout y pedido masivo.
- [x] 6.3 Server-side: ignorar overrides lista/condición/vencimiento si no supervisor (REQ-CC-04/05).

## Phase 7: Docs

- [x] 7.1 Documentar cabecera comercial, permisos y fechas en `docs/ecom/` (checkout + masivo).

## Phase 8: Tests

- [x] 8.1 Crear `ecom/tests/test_pedido_cabecera_comercial.py`: vencimiento=Fecha+Dias, recalc, override supervisor, enforcement vendedor.
- [x] 8.2 Extender `ecom/tests/test_mayorista_checkout_service.py`: persistencia cabecera y `lista_precio` en `stockp`.
- [x] 8.3 Extender `ecom/tests/test_batch_checkout_masivo.py`: misma cabecera a N PED del lote.
- [x] 8.4 Ejecutar: `docker exec Synap_app python manage.py test ecom.tests.test_pedido_cabecera_comercial ecom.tests.test_mayorista_checkout_service ecom.tests.test_batch_checkout_masivo`.
