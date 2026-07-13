# UI web — Compra mayorista — Fase P3 (item 4)

Change SDD: `openspec/changes/catalogo-carrito-checkout-mayorista/` · Fase **P3**.
Pantalla web que integra el vertical **catálogo → carrito → checkout** consumiendo las APIs
ya migradas (P0/P1/P2/P3). Sigue la fuente de verdad de UI (`docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md`).

## Ruta y vista

- **Ruta:** `/ecom/mayoristapp/compra/` (`ecom:mayoristapp_compra`).
- **Vista:** `CompraMayoristaView` (`ecom/mayoristapp_web_views.py`), con `MayoristappWebSessionMixin`
  (requiere sesión `user` con `base_empresa`). Solo arma URLs con `reverse()` (sin MySQL).
- **Plantilla:** `ecom/templates/ecom/compra_mayorista.html` (extiende `base_pedidos.html`).
- Título dinámico según modo: **Pedido de venta** / **Presupuesto de venta** / **Devolución de venta**.

## Diseño (patrones canónicos)

- Hero **slate** con degradado, contenedor **full-width** (`px-4 … lg:px-12`), tarjetas
  `rounded-3xl` con `shadow-2xl` — mismos patrones que `presupuestos_vendedor.html` y reports/MPR.
- **Toggle de comprobante** (`ecom/includes/pedidos_toggle_comprobante.html`): tres modos **PED / PRE / DEV**
  con paridad visual al toggle de armado MPR (1ra/2da selección). Persiste en carrito vía
  `PATCH /carrito/tipo-comprobante/`.
- **Identidad visual por modo** (clases `compra-modo-ped|pre|dev` en `pedidos_page_styles.html`):
  - **PED (sky):** borde/banner azul; reserva stock al confirmar.
  - **PRE (amber):** borde/banner ámbar; no reserva stock.
  - **DEV (rose):** borde/banner rosa; no valida stock al agregar.
- Banner superior de modo y botón de confirmar con color acorde al tipo activo.
- **Búsqueda de artículos:** include `ecom/includes/pedidos_busqueda_articulos_tpv.html` — paridad visual
  y de interacción con TPV (`self_checkout/includes/_search_scan.html`): input grande, hint ↑↓/Enter,
  tabla Código / Nombre / Stock / Precio, fila destacada en azul.
- **Alpine 3** (ya disponible en `base_app.html`); componente `compraMayorista()` registrado en
  `alpine:init`. URLs de API pasadas al cliente vía `json_script` (`compra-mayorista-urls`).
- Layout responsive: en **móvil/tablet** catálogo y carrito se apilan (`order-1` / `order-2`);
  en **desktop** búsqueda 2/3 y carrito 1/3. Inputs con `min-height` táctil en viewport &lt; 1024px.

## Flujo e integración con APIs

| Acción UI | API |
|---|---|
| Cambiar modo PED/PRE/DEV | `PATCH /carrito/tipo-comprobante/` (`{tipo}`) |
| Buscar artículos (predictivo / ↓ lista) | `POST /catalogo/articulos/listado/` con `filtros.busqueda_tpv: true` (campos de búsqueda TPV; catálogo `ecommerce='Si'`) y `filtros.marcas: [id, …]` opcional |
| Filtrar por marca(s) | Tags multi (`compra_mayorista_marcas.mjs`) → `GET /catalogo/marcas/?ajax=1` + recarga listado |
| Agregar con Enter o clic en fila | `POST /carrito/` |
| Ver carrito | `GET /carrito/` |
| Agregar / cambiar cantidad / quitar | `POST /carrito/`, `PATCH /carrito/items/<id>/`, `DELETE /carrito/items/<id>/` |
| Vaciar / descuento al pie | `POST /carrito/vaciar/`, `POST /carrito/descuento-pie/` |
| Confirmar comprobante | `POST /checkout/confirmar/` (`tipo` = PED/PRE/DEV) |
| Detalle post-éxito PED | `/mayoristapp/pedidos/<cod_mov>/` |
| Detalle post-éxito PRE/DEV | `/mayoristapp/comprobantes/<cod_mov>/` (`comprobante_comercial_detalle.html`) |
| Lista de precios | link a `GET /catalogo/lista-precios.pdf` |

- El **precio y el stock** los calcula el backend (motor de precios + StockService); la UI solo muestra.
- Errores del backend (stock insuficiente en PED/PRE, crédito, etc.) se muestran como mensaje inline en español.
- En modo **DEV** el carrito **no valida stock** al agregar ni al cambiar cantidad.

## Comportamiento por tipo (gaps cerrados)

| Modo | Stock al agregar | Checkout | Tras confirmar |
|------|------------------|----------|----------------|
| **PED** | Valida disponible | Reserva stock, fecha entrega | Detalle pedido + listado pedidos |
| **PRE** | Valida disponible | No toca stock | Detalle comprobante + listado presupuestos |
| **DEV** | Sin validación | Incrementa stock | Detalle comprobante (sin listado web dedicado) |

## Notas / follow-up

- **Rediseño OrderShell (10/07/2026):** la pantalla de compra migró a layout de cinco regiones (header sticky, captura TPV, líneas, summary sticky/bottom bar, checkout colapsable). Alpine extraído a módulos `.mjs`; modales del canon reemplazan `confirm()` en flujo compra. Documentación: `docs/order-ui-redesign/10-estado-implementacion.md`. Sin cambios de backend ni contratos API.
- El **punto de venta** por defecto se toma de la sesión; el campo permite override manual.
- Selector de **cliente** embebido (`compra_mayorista_cliente.mjs`) y filtro **marcas** al lado del cliente.
- El cliente **no persiste** entre cargas de `/compra/` ni tras confirmar: al abrir/refrescar la pantalla o al terminar el checkout se limpia sesión y carrito borrador (vendedor).
- Imágenes de producto e info extendida de ficha: la tabla es compacta (follow-up de ficha visual).

## Tests

```bash
docker exec Synap_app python manage.py test \
  ecom.tests.test_mayorista_cart_service \
  ecom.tests.test_compra_mayorista_view \
  ecom.tests.test_pedido_gestion \
  --keepdb
```

Cobertura relevante: toggle/URLs en vista, `actualizar_tipo_comprobante`, stock omitido en DEV,
`cabecera_comp_ped_relay` para PRE/DEV.
