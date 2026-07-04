# UI web — Compra mayorista — Fase P3 (item 4)

Change SDD: `openspec/changes/catalogo-carrito-checkout-mayorista/` · Fase **P3**.
Pantalla web que integra el vertical **catálogo → carrito → checkout** consumiendo las APIs
ya migradas (P0/P1/P2/P3). Sigue la fuente de verdad de UI (`docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md`).

## Ruta y vista

- **Ruta:** `/ecom/mayoristapp/compra/` (`ecom:mayoristapp_compra`).
- **Vista:** `CompraMayoristaView` (`ecom/mayoristapp_web_views.py`), con `MayoristappWebSessionMixin`
  (requiere sesión `user` con `base_empresa`). Solo arma URLs con `reverse()` (sin MySQL).
- **Plantilla:** `ecom/templates/ecom/compra_mayorista.html` (extiende `base_app.html`).

## Diseño (patrones canónicos)

- Hero **slate** con degradado, contenedor **full-width** (`px-4 … lg:px-12`), tarjetas
  `rounded-3xl` con `shadow-2xl` — mismos patrones que `presupuestos_vendedor.html` y reports/MPR.
- **Alpine 3** (ya disponible en `base_app.html`); componente `compraMayorista()` registrado en
  `alpine:init`. URLs de API pasadas al cliente vía `json_script` (`compra-mayorista-urls`).
- Layout POS de 3 columnas: **catálogo** (2/3, buscador + tabla paginada con precio/stock/cantidad)
  y **carrito + checkout** (1/3, renglones editables, totales, descuento al pie, formulario y confirmar).

## Flujo e integración con APIs

| Acción UI | API |
|---|---|
| Buscar artículos | `POST /catalogo/articulos/listado/` (filtros `q`, `solo_promocion`, paginado) |
| Ver carrito | `GET /carrito/` |
| Agregar / cambiar cantidad / quitar | `POST /carrito/`, `PATCH /carrito/items/<id>/`, `DELETE /carrito/items/<id>/` |
| Vaciar / descuento al pie | `POST /carrito/vaciar/`, `POST /carrito/descuento-pie/` |
| Confirmar comprobante | `POST /checkout/confirmar/` (`tipo` = PED/PRE/DEV) |
| Lista de precios | link a `GET /catalogo/lista-precios.pdf` |

- El **precio y el stock** los calcula el backend (motor de precios + StockService); la UI solo muestra.
- Errores del backend (stock insuficiente, crédito, etc.) se muestran como mensaje inline en español.
- Selector de **tipo de comprobante** (Pedido / Presupuesto / Devolución) en el hero.

## Notas / gaps

- El **punto de venta** por defecto se toma de la sesión; el campo permite override manual.
- Selección de **cliente** y **domicilio/ruta** se asumen ya resueltos en sesión (flujos de cliente
  ya migrados); esta pantalla se centra en catálogo→carrito→checkout. Integrar el selector de cliente
  embebido es un follow-up.
- Imágenes de producto e info extendida de ficha: la tabla es compacta (follow-up de ficha visual).

## Tests

`ecom/tests/test_compra_mayorista_view.py` (RequestFactory, sin middleware): redirección sin
sesión / sin `base_empresa`, y render OK con las URLs de API P0–P3 embebidas.

```bash
docker exec Synap_app python manage.py test ecom.tests.test_compra_mayorista_view --keepdb
```
