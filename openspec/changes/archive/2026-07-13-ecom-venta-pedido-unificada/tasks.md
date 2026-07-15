# Tasks — ecom-venta-pedido-unificada

## Phase 1 — Rutas y redirects
- [x] 1.1 Registrar `mayoristapp/venta/` (`mayoristapp_venta`) con `CompraMayoristaView`
- [x] 1.2 Redirect `mayoristapp/compra/` → venta (query preserved); alias name compra
- [x] 1.3 API `venta/contexto/` + alias `compra/contexto/`
- [x] 1.4 Menú `core/utils/utils.py` + `ecom/menu_config.py` → `mayoristapp_venta`
- [x] 1.5 `cliente_relay` frm=0 → venta; hardcode path `/venta/`
- [x] 1.6 Hub bootstrap / `pedidos_hub_pipeline` nuevo → venta

## Phase 2 — Deprecar detalle
- [x] 2.1 `PedidoDetalleView` → redirect a `venta/?cod_mov=`
- [x] 2.2 Cards hub PED + listados `detalle_tpl` → `/venta/?cod_mov=`
- [x] 2.3 `detalleTrasExitoUrl` post-checkout PED → venta

## Phase 3 — Modos OrderShell
- [x] 3.1 Bootstrap URLs detalle (cabecera, anular, pdf, mail, preview) en vista venta
- [x] 3.2 Alpine: leer `cod_mov` de query; cargar cabecera/líneas; flag `modo`
- [x] 3.3 Banner + stepper; hero Anular/Repetir/PDF/mail
- [x] 3.4 Solo lectura si no Pendiente: bloquear catálogo/qty/checkout
- [x] 3.5 Textos UI «Pedido de venta»

## Phase 4 — Editar Pendiente
- [x] 4.1 Cargar líneas del PED al carrito UI / servicio plantilla
- [x] 4.2 Modal Synap confirmar cambios (anula + nuevo)
- [x] 4.3 Orquestar anular + checkout; navegar al nuevo cod_mov

## Phase 5 — Docs y tests
- [x] 5.1 Actualizar `SPEC_GESTION_PEDIDOS_SYNAP.md` §6.2 y rutas
- [x] 5.2 Actualizar `UI_COMPRA_MAYORISTA_P3.md` (ruta `/venta/`)
- [x] 5.3 Tests redirects + reverse hub/frm=0 + vista venta
- [x] 5.4 Índice change en `docs/ecom/` si aplica
