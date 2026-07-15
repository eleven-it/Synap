# Tasks: Usabilidad pedidos mayorista + supervisor operativo

**Change:** `ecom-pedidos-usabilidad-supervisor` · **Orden:** A→E · **Tests:** `docker exec Synap_app python manage.py test …`

## Oleada A — Sesión y vendedor operativo

- [x] A.1 Crear `ecom/services/vendedor_operativo.py` con `resolver_viajante_operativo(sess)` — REQ-VOP-01/06
- [x] A.2 En `mayoristapp_sesion_contexto.py`: hidratar `cod_viajante_operativo` (default `id_vendedor_usr`) y `vendedor_a_cargo` desde `configuracion_ecom` clave `ecom_vendedores_a_cargo_<CodViajante>` vía `ecom_config_mysql.py`; fallback `[cv]` — REQ-VOP-01/02 (sin DDL; sin hardcode Python prod)
- [x] A.3 Documentar mapeo PHP hardcode `control.php` L472–507 en `docs/ecom/SPEC_MAYORISTAPP_FUNDACIONES.md`; script/doc seed opcional para `configuracion_ecom`
- [x] A.4 APIs `GET …/vendedores-cartera/` y `POST …/vendedor-operativo/` en `ecom/urls.py` + views — REQ-VOP-03
- [x] A.5 Fix `_session_cod_viajante` en `checkout_relay_views.py` usando resolver — REQ-CHK-010/011
- [x] A.6 Integrar resolver en `batch_checkout_masivo.py`, `cliente_relay.py`, `pedido_masivo_matriz.py` — REQ-CHK-012, VOP-06
- [x] A.7 Crear `includes/pedidos_selector_vendedor.html`; modal canon al cambiar operativo → limpiar cliente+carrito/borrador — REQ-VOP-03/05, VTA-07
- [x] A.8 Banner «Operando como» en selector; reset operativo en logout mayoristapp — REQ-VOP-04/05, VTA-08
- [x] A.9 Tests: `test_vendedor_operativo.py`, extender `test_mayoristapp_sesion_contexto.py`, checkout CodViajante — REQ-VOP-*, CHK-010/011

## Oleada B — VCM simple + lista RO

- [x] B.1 `cliente_relay.py` / `vendedor_asignacion_sql.py`: clientes por ternas con viajante efectivo — REQ-VCM-04/05
- [x] B.2 Catálogo simple: filtro marcas ternas; 400 sin cliente — REQ-CAT-004, VCM-04
- [x] B.3 Crear `includes/pedidos_lista_badge.html` + integrar en `pedidos_order_header.html` — REQ-VTA-05, UI-04
- [x] B.4 `cliente_relay_views.py`: payload `listaPrecio` + PDF; sin override lista — REQ-CAT-005/006
- [x] B.5 Insertar selector+badge en `compra_mayorista.html` y `pedido_masivo_sucursales.html` — REQ-MAS-11, VTA-07
- [x] B.6 Tests VCM simple vs masivo con operativo≠logueado — REQ-VCM-04/05

## Oleada C — Descuentos pedido simple

- [x] C.1 `pedidos_lineas_tabla.html`: columna «% desc.» → PATCH `porcentaje_descuento` — REQ-VTA-06, CAR-006, DSC-01
- [x] C.2 `pedidos_order_summary.html` + relay: precarga `descPie`; POST `descuento-pie/` — REQ-VTA-09, CAR-005, DSC-02
- [x] C.3 `mayorista_cart_service.py` / `carrito_relay_views.py`: precarga `descRenglon`; sin recálculo JS totales — REQ-CAR-006/007, DSC-04/05
- [x] C.4 Tests descuentos renglón+pie y orden aplicación — REQ-DSC-01/02/05

## Oleada D — Pedido masivo (precio, desc, preview)

- [x] D.1 `pedido_masivo_matriz.py`: precio `price_rules_engine`; %desc fila + pie; precarga `descRenglon` — REQ-MAS-07/08/09, DSC-03
- [x] D.2 `POST …/pedido-masivo/preview/` en `pedido_masivo_views.py`; límite blando ≤200 celdas≠0 o timeout amigable; warning sin bloquear confirmar — REQ-MAS-10
- [x] D.3 `batch_checkout_masivo.py`: descuentos fila/pie y `CodViajante` operativo — REQ-MAS-03, CHK-012, DSC-03
- [x] D.4 Extraer JS a `static/ecom/pedido_masivo_app.mjs`; matriz en `pedido_masivo_sucursales.html` — REQ-MAS-07/08
- [x] D.5 Modal canon `pedidos_modal.html` reemplaza `confirm()` — REQ-MAS-06, UI-03
- [x] D.6 Tests preview/límites/operativo en `test_pedido_masivo_matriz.py`, `test_batch_checkout_masivo.py` — REQ-MAS-*

## Oleada E — Visual slate/sky

- [x] E.1 `pedidos_page_styles.html`: tokens `.pedidos-*` y `.pedidos-badge-lista`; sin purple salvo `.pedidos-btn-gradient` — REQ-UI-01/04
- [x] E.2 Barrido purple en `pedidos_breadcrumb.html`, `compra_mayorista.html`, `pedido_masivo_sucursales.html`, includes — REQ-UI-02
- [x] E.3 Actualizar `docs/order-ui-redesign/05-design-system-pedidos.md` y `10-estado-implementacion.md` — REQ-UI-01
- [x] E.4 Actualizar `docs/ecom/PEDIDO_MASIVO_SUCURSALES.md`, `UI_COMPRA_MAYORISTA_P3.md`, `SPEC_MAYORISTAPP_FUNDACIONES.md` — oleadas A–E
